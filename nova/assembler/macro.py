"""
Nova-16 Assembler Macro Expander

Pure-function macro expansion on a token stream.  The expander:

1. Collects macro definitions (``MACRO name params ... ENDM``) in a first pass.
2. Removes the definitions from the stream.
3. Expands macro invocations recursively, substituting positional parameters.

This keeps macro processing separate from parsing and avoids the exponential
worst-case behavior of the old inline expansion.

Supported features:
    - Macros with zero or more comma-separated parameters
    - Nested macro calls inside macro bodies
    - Macro redefinition (last definition wins)
    - Recursive macro detection (raises an error)
    - Parameters substituted as whole tokens (word boundaries)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from .lexer import Token, TokenKind, tokenize, line_text


class MacroError(Exception):
    """Error during macro expansion."""
    pass


@dataclass
class Macro:
    """A collected macro definition."""
    name: str
    params: List[str]
    body: List[List[Token]]  # token lines of the body
    line_num: int = 0


def _is_macro_directive(line: List[Token]) -> bool:
    return (len(line) >= 1
            and line[0].kind == TokenKind.MNEMONIC
            and line[0].value.upper() == "MACRO")


def _is_endm_directive(line: List[Token]) -> bool:
    return (len(line) >= 1
            and line[0].kind == TokenKind.MNEMONIC
            and line[0].value.upper() == "ENDM")


def _parse_macro_header(line: List[Token]) -> tuple:
    """Parse ``MACRO name p1, p2, ...`` and return (name, params, line_num)."""
    if len(line) < 2:
        raise MacroError(f"Invalid MACRO directive at line {line[0].line}")
    name_tok = line[1]
    if name_tok.kind not in (TokenKind.IDENT, TokenKind.MNEMONIC):
        raise MacroError(
            f"Invalid macro name '{name_tok.value}' at line {name_tok.line}"
        )
    name = name_tok.value.upper()

    params: List[str] = []
    i = 2
    while i < len(line):
        tok = line[i]
        if tok.kind == TokenKind.COMMA:
            i += 1
            continue
        if tok.kind in (TokenKind.IDENT, TokenKind.MNEMONIC, TokenKind.REGISTER):
            params.append(tok.value.upper())
            i += 1
        else:
            raise MacroError(
                f"Unexpected token '{tok.value}' in macro parameter list "
                f"at line {tok.line}"
            )
    return name, params, name_tok.line


def _collect_macros(lines: List[List[Token]]) -> tuple:
    """Collect macro definitions and return (macros dict, output lines)."""
    macros: Dict[str, Macro] = {}
    output: List[List[Token]] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        if _is_macro_directive(line):
            name, params, line_num = _parse_macro_header(line)
            i += 1
            body: List[List[Token]] = []
            while i < n and not _is_endm_directive(lines[i]):
                body.append(lines[i])
                i += 1
            if i >= n:
                raise MacroError(
                    f"Macro '{name}' starting at line {line_num} missing ENDM"
                )
            macros[name] = Macro(name, params, body, line_num)
            i += 1  # skip ENDM
            continue
        output.append(line)
        i += 1

    return macros, output


def _substitute_line(line: List[Token], arg_map: Dict[str, str]) -> List[Token]:
    """Return a new token line with parameters replaced by arguments."""
    new_line: List[Token] = []
    for tok in line:
        if tok.kind in (TokenKind.IDENT, TokenKind.MNEMONIC, TokenKind.REGISTER):
            upper = tok.value.upper()
            if upper in arg_map:
                # Preserve token kind of the original token; the value is the
                # argument text.  The parser/lexer will reclassify if needed.
                new_line.append(Token(tok.kind, arg_map[upper], tok.line, tok.col))
            else:
                new_line.append(tok)
        else:
            new_line.append(tok)
    return new_line


def _expand_lines(lines: List[List[Token]], macros: Dict[str, Macro],
                  expanding: Optional[Set[str]] = None,
                  depth: int = 0) -> List[List[Token]]:
    """Recursively expand macro invocations in a list of token lines."""
    if expanding is None:
        expanding = set()
    if depth > 100:
        raise MacroError("Macro expansion too deep (possible recursion)")

    result: List[List[Token]] = []
    for line in lines:
        if not line:
            continue
        first = line[0]
        if first.kind in (TokenKind.IDENT, TokenKind.MNEMONIC):
            name = first.value.upper()
            if name in macros and name not in expanding:
                macro = macros[name]
                # Parse arguments from the rest of the line
                args: List[str] = []
                i = 1
                while i < len(line):
                    tok = line[i]
                    if tok.kind == TokenKind.COMMA:
                        i += 1
                        continue
                    args.append(tok.value)
                    i += 1

                if len(args) > len(macro.params):
                    raise MacroError(
                        f"Macro '{name}' expects {len(macro.params)} arguments, "
                        f"got {len(args)} at line {first.line}"
                    )

                arg_map = {
                    param: (args[i] if i < len(args) else "")
                    for i, param in enumerate(macro.params)
                }

                # Substitute into body, then recursively expand the body
                substituted = [_substitute_line(l, arg_map) for l in macro.body]
                nested_expanding = expanding | {name}
                expanded_body = _expand_lines(
                    substituted, macros, nested_expanding, depth + 1
                )
                result.extend(expanded_body)
                continue
            elif name in expanding:
                raise MacroError(
                    f"Recursive macro expansion of '{name}' at line {first.line}"
                )
        result.append(line)
    return result


def expand_macros(source: str) -> str:
    """Expand macros in source text and return the resulting source text."""
    tokens = tokenize(source)
    from .lexer import tokens_to_lines
    lines = tokens_to_lines(tokens)
    macros, body = _collect_macros(lines)
    expanded = _expand_lines(body, macros)
    # Reconstruct text.  Preserve line numbers is not required; the parser will
    # re-tokenize.  We just need valid assembly source.
    text_lines: List[str] = []
    for line in expanded:
        if not line:
            continue
        # Skip pure comment lines
        if all(t.kind == TokenKind.COMMENT for t in line):
            text_lines.append(line_text(line))
            continue
        text_lines.append(line_text(line))
    return "\n".join(text_lines) + "\n"


def expand_macros_from_tokens(tokens: List[Token]) -> List[Token]:
    """Expand macros directly on a token stream and return a new token stream."""
    from .lexer import tokens_to_lines
    lines = tokens_to_lines(tokens)
    macros, body = _collect_macros(lines)
    expanded = _expand_lines(body, macros)
    # Flatten back to tokens with newlines between original lines
    result: List[Token] = []
    last_line = 1
    for line in expanded:
        if not line:
            continue
        result.extend(line)
        # Use the line number of the last token for the synthetic newline
        last_line = line[-1].line if line else 1
        result.append(Token(TokenKind.NEWLINE, "\n", last_line, 0))
    return result
