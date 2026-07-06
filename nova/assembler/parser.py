"""
Nova-16 Assembler Parser

Converts a token stream (after macro expansion) into a list of IR nodes:
    Label, Instruction, Directive, Data

The parser also handles INCLUDE directives by recursively loading and tokenizing
included files, and evaluates conditional directives (IF/IFDEF/IFNDEF/ELSE/ENDIF)
using a simple two-pass approach: first collect EQU symbols, then evaluate
conditionals.
"""

import os
from typing import List, Set, Tuple

from .lexer import Token, TokenKind, tokenize, tokens_to_lines, line_text
from .ir import IRNode, Label, Instruction, Directive, Data


class ParseError(Exception):
    """Error during parsing."""
    pass


# Directives that emit data bytes
DATA_DIRECTIVES = {"DB", "DW", "DEFSTR", "DS", "DEFWORD", "DEFBYTE"}

# Directives that control assembly flow
CONTROL_DIRECTIVES = {"ORG", "EQU", "MACRO", "ENDM", "INCLUDE",
                      "IF", "IFDEF", "IFNDEF", "ELSE", "ENDIF"}

# Instructions that take zero operands (bare mnemonic = instruction, not label)
ZERO_OPERAND_INSTRUCTIONS = {
    "HLT", "NOP", "RET", "IRET", "CLI", "STI",
    "PUSHF", "POPF", "PUSHA", "POPA",
    "SED", "CLD", "CLA",
    "SINV", "SBLIT", "SPLAY", "SSTOP", "SPBLIT", "SPBLITALL",
    "ENABRK", "DISBRK", "ENATRAP", "DISATRAP",
    "LEAVE",
    "SERIN", "SEROUT", "SERSTAT", "SERCTRL",  # Serial I/O
    # Instructions that can be called with zero operands (uses implicit VC operand)
    "SWRITE", "SREAD", "SBLEND", "SROL", "SROT", "SSHFT", "SFLIP",
    "SLINE", "SRECT", "SCIRC", "SFILL",
}


def _extract_equ_symbols(lines: List[List[Token]]) -> Set[str]:
    """Pre-scan token lines for symbols defined by EQU."""
    defined: Set[str] = set()
    for line in lines:
        if not line:
            continue
        first = line[0]
        if first.kind == TokenKind.IDENT and len(line) >= 3:
            if line[1].kind == TokenKind.MNEMONIC and line[1].value.upper() == "EQU":
                defined.add(first.value.upper())
    return defined


def _evaluate_condition(line: List[Token], defined: Set[str]) -> bool:
    """Evaluate an IF/IFDEF/IFNDEF condition."""
    if len(line) < 2:
        raise ParseError(f"Missing condition at line {line[0].line}")
    directive = line[0].value.upper()
    if directive == "IF":
        cond = line_text(line[1:]).strip().upper()
        return cond in {"1", "TRUE"}
    if directive == "IFDEF":
        symbol = line[1].value.upper()
        return symbol in defined
    if directive == "IFNDEF":
        symbol = line[1].value.upper()
        return symbol not in defined
    raise ParseError(f"Unknown conditional directive '{directive}'")


def _apply_conditionals(lines: List[List[Token]], defined: Set[str]) -> List[List[Token]]:
    """Filter token lines according to IF/IFDEF/IFNDEF/ELSE/ENDIF blocks."""
    output: List[List[Token]] = []
    stack: List[bool] = []  # current inclusion state per nested block

    for line in lines:
        if not line:
            continue
        first = line[0]
        if first.kind != TokenKind.MNEMONIC:
            if not stack or all(stack):
                output.append(line)
            continue

        directive = first.value.upper()

        if directive in {"IF", "IFDEF", "IFNDEF"}:
            include = _evaluate_condition(line, defined)
            stack.append(include)
            continue

        if directive == "ELSE":
            if not stack:
                raise ParseError(f"ELSE without IF at line {first.line}")
            stack[-1] = not stack[-1]
            continue

        if directive == "ENDIF":
            if not stack:
                raise ParseError(f"ENDIF without IF at line {first.line}")
            stack.pop()
            continue

        if not stack or all(stack):
            output.append(line)

    if stack:
        raise ParseError("Unclosed conditional directive")
    return output


def _parse_include(line: List[Token], base_dir: str) -> str:
    """Extract the include file path from an INCLUDE directive."""
    if len(line) < 2:
        raise ParseError(f"Invalid INCLUDE directive at line {line[0].line}")
    path = line_text(line[1:]).strip()
    path = path.strip('"').strip("'")
    if not os.path.isabs(path):
        path = os.path.join(base_dir, path)
    return os.path.abspath(path)


def _load_includes(lines: List[List[Token]], base_dir: str,
                   included: Set[str]) -> List[List[Token]]:
    """Recursively expand INCLUDE directives, detecting circular includes."""
    output: List[List[Token]] = []
    for line in lines:
        if not line:
            continue
        first = line[0]
        if first.kind == TokenKind.MNEMONIC and first.value.upper() == "INCLUDE":
            include_path = _parse_include(line, base_dir)
            if include_path in included:
                raise ParseError(f"Circular include: {include_path}")
            included.add(include_path)
            try:
                with open(include_path, "r", encoding="utf-8") as f:
                    source = f.read()
            except IOError as e:
                raise ParseError(f"Could not include {include_path}: {e}")
            tokens = tokenize(source)
            included_lines = tokens_to_lines(tokens)
            expanded = _load_includes(included_lines, os.path.dirname(include_path), included)
            output.extend(expanded)
            continue
        output.append(line)
    return output


def _parse_operand_tokens(tokens: List[Token]) -> str:
    """Convert a sequence of operand tokens back into a source string."""
    parts: List[str] = []
    for tok in tokens:
        if tok.kind == TokenKind.COMMA:
            continue
        if tok.kind == TokenKind.LBRACKET:
            parts.append("[")
        elif tok.kind == TokenKind.RBRACKET:
            parts.append("]")
        elif tok.kind == TokenKind.PLUS:
            parts.append("+")
        elif tok.kind == TokenKind.MINUS:
            parts.append("-")
        elif tok.kind == TokenKind.COLON:
            parts.append(":")
        else:
            parts.append(tok.value)
    return "".join(parts)


def _split_operands(tokens: List[Token]) -> List[List[Token]]:
    """Split a list of operand tokens by top-level commas."""
    operands: List[List[Token]] = []
    current: List[Token] = []
    depth = 0
    for tok in tokens:
        if tok.kind == TokenKind.LBRACKET:
            depth += 1
            current.append(tok)
        elif tok.kind == TokenKind.RBRACKET:
            depth -= 1
            current.append(tok)
        elif tok.kind == TokenKind.COMMA and depth == 0:
            if current:
                operands.append(current)
                current = []
        else:
            current.append(tok)
    if current:
        operands.append(current)
    return operands


def _parse_line(line: List[Token]) -> List[IRNode]:
    """Parse a single token line into zero or more IR nodes."""
    nodes: List[IRNode] = []
    if not line:
        return nodes

    # Skip pure comment lines
    if all(t.kind == TokenKind.COMMENT for t in line):
        return nodes

    i = 0
    line_num = line[0].line

    # Optional leading label definition
    if line[i].kind == TokenKind.LABEL_DEF:
        nodes.append(Label(line[i].value, line_num))
        i += 1
        if i >= len(line):
            return nodes

    # A bare identifier followed by EQU is a symbol definition without a colon.
    if (line[i].kind == TokenKind.IDENT
            and i + 1 < len(line)
            and line[i + 1].kind == TokenKind.MNEMONIC
            and line[i + 1].value.upper() == "EQU"):
        nodes.append(Label(line[i].value, line_num))
        i += 1

    # A bare identifier followed by a data directive is treated as a label
    # definition (e.g. ``BUFFER DS 10``).  This matches the old assembler.
    if (line[i].kind == TokenKind.IDENT
            and i + 1 < len(line)
            and line[i + 1].kind == TokenKind.MNEMONIC
            and line[i + 1].value.upper() in DATA_DIRECTIVES):
        nodes.append(Label(line[i].value, line_num))
        i += 1
        line_num = line[i].line

    # A bare identifier on its own line is treated as a label definition.
    # This matches the old assembler's behavior for labels without colons.
    if line[i].kind == TokenKind.IDENT and i + 1 >= len(line):
        nodes.append(Label(line[i].value, line_num))
        return nodes

    # A bare mnemonic on its own line is treated as a label definition,
    # UNLESS it's a zero-operand instruction (NOP, HLT, RET, STI, etc.)
    # which should be emitted as an instruction instead.
    if line[i].kind == TokenKind.MNEMONIC and i + 1 >= len(line):
        mnemonic = line[i].value.upper()
        if mnemonic in ZERO_OPERAND_INSTRUCTIONS:
            nodes.append(Instruction(mnemonic, [], line_num))
            return nodes
        nodes.append(Label(line[i].value, line_num))
        return nodes

    # What follows must be a mnemonic (instruction or directive)
    if line[i].kind != TokenKind.MNEMONIC:
        # Could be a bare label reference or unknown token; ignore for now
        return nodes

    mnemonic = line[i].value.upper()
    i += 1
    rest = line[i:]

    if mnemonic in DATA_DIRECTIVES:
        operands = [_parse_operand_tokens(op) for op in _split_operands(rest)]
        nodes.append(Data(mnemonic, operands, line_num))
    elif mnemonic in CONTROL_DIRECTIVES:
        args = [_parse_operand_tokens(op) for op in _split_operands(rest)]
        nodes.append(Directive(mnemonic, args, line_num))
    else:
        operands = [_parse_operand_tokens(op) for op in _split_operands(rest)]
        nodes.append(Instruction(mnemonic, operands, line_num))

    return nodes


def parse(source: str, base_dir: str = ".") -> List[IRNode]:
    """Parse assembly source into IR nodes.

    Args:
        source: Assembly source text.
        base_dir: Directory used to resolve relative INCLUDE paths.

    Returns:
        List of IRNode objects.
    """
    tokens = tokenize(source)
    lines = tokens_to_lines(tokens)

    # Expand includes first
    included: Set[str] = set()
    lines = _load_includes(lines, base_dir, included)

    # Pre-scan EQU symbols for IFDEF/IFNDEF
    defined = _extract_equ_symbols(lines)

    # Apply conditional blocks
    lines = _apply_conditionals(lines, defined)

    # Parse into IR
    nodes: List[IRNode] = []
    for line in lines:
        nodes.extend(_parse_line(line))
    return nodes
