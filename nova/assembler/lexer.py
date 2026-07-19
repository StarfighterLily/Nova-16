"""
Nova-16 Assembler Lexer

Tokenizes assembly source text into a flat list of tokens.  The lexer is a
small state machine rather than a pile of regexes, which makes edge cases like
``P0:`` vs ``:P0``, quoted strings, and bracketed expressions straightforward.

Token kinds:
    MNEMONIC    instruction or directive name
    REGISTER    register token (R0-R9, P0-P9, P0:, :P0, VX, VY, ...)
    NUMBER      integer literal (decimal or 0x hex)
    CHAR        character literal like 'A' or '\n'
    STRING      double-quoted string
    LABEL_DEF   label definition ending with ':'
    IDENT       any other identifier (label reference, macro name, symbol)
    LBRACKET    '['
    RBRACKET    ']'
    PLUS        '+'
    MINUS       '-'
    COMMA       ','
    COLON       ':'
    NEWLINE     line break (preserved for line-number reporting)
    COMMENT     '; ...' (kept but skipped by parser)
    EOF         end of input
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple


class TokenKind(Enum):
    MNEMONIC = auto()
    REGISTER = auto()
    NUMBER = auto()
    CHAR = auto()
    STRING = auto()
    LABEL_DEF = auto()
    IDENT = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    PLUS = auto()
    MINUS = auto()
    COMMA = auto()
    COLON = auto()
    NEWLINE = auto()
    COMMENT = auto()
    EOF = auto()


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    value: str
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.kind.name}, {self.value!r}, L{self.line})"


# Directives and instructions are both treated as mnemonics by the lexer.
# The parser decides which are directives.
DIRECTIVES = {
    "ORG", "EQU", "DB", "DW", "DEFSTR", "DS", "DEFWORD", "DEFBYTE",
    "MACRO", "ENDM", "INCLUDE",
    "IF", "IFDEF", "IFNDEF", "ELSE", "ENDIF",
}

INSTRUCTIONS = {
    "HLT", "NOP", "RET", "IRET", "CLI", "STI",
    "MOV", "MOVZ", "MOVNZ", "XCHNG", "SWAP", "LEA",
    "ADD", "SUB", "MUL", "DIV", "MOD", "INC", "DEC", "NEG", "ABS",
    "ADC", "SBC", "MULH", "DIVH", "MIN", "MAX",
    "AND", "OR", "XOR", "NOT", "SHL", "SHR", "SAR", "SAL", "ROL", "ROR", "RCL", "RCR",
    "BTST", "BSET", "BCLR", "BFLIP",
    "CMP",
    "PUSH", "POP", "PUSHF", "POPF", "PUSHA", "POPA", "ENTER", "LEAVE",
    "JMP", "JZ", "JNZ", "JO", "JNO", "JC", "JNC", "JS", "JNS",
    "JGT", "JLT", "JGE", "JLE", "BR", "BRZ", "BRNZ",
    "CALL", "CALLZ", "CALLNZ", "RETN", "INT",
    "LOOP", "LOOPZ", "WHILE",
    "SED", "CLD", "CLA", "BCDA", "BCDS", "BCDCMP", "BCD2BIN", "BIN2BCD", "BCDADD", "BCDSUB",
    "POWR", "SQRT", "LOG", "EXP", "SIN", "COS", "TAN", "ATAN", "ASIN", "ACOS",
    "DEG", "RAD", "FLOOR", "CEIL", "ROUND", "TRUNC", "FRAC", "INTGR",
    "CLZ", "CTZ", "POPCNT",
    "RND", "RNDR",
    "FMUL", "FDIV", "FTOI", "ITOF",
    "ITOB", "BTOI", "ITOS", "STOI",
    "STRCPY", "STRCAT", "STRCMP", "STRLEN", "STRUPR", "STRLWR", "STRREV", "STRFIND", "STRFINDI", "STREXT", "STREXTI",
    "MEMCPY", "MEMSET", "MEMTEST", "MEMMOVE", "MEMCMP", "MEMSWAP",
    "SBLEND", "SREAD", "SWRITE", "SROL", "SROT", "SSHFT", "SFLIP", "SLINE", "SRECT", "SCIRC", "SINV", "SBLIT", "SFILL",
    "VREAD", "VWRITE", "VBLIT", "CHAR", "TEXT", "SPBLIT", "SPBLITALL",
    "LSWAP", "LMOVE", "LCOPY",
    "SPLAY", "SSTOP", "STRIG",
    "KEYIN", "KEYSTAT", "KEYCOUNT", "KEYCLEAR", "KEYCTRL",
    "SERIN", "SEROUT", "SERSTAT", "SERCTRL",
    "MOUSECTRL",
    "SETBP", "CLRBP", "ENABRK", "DISBRK", "ENATRAP", "DISATRAP",
    # Reserved opcodes with no CPU handler yet (see opcodes.py's
    # "# unimplemented" tags and codegen.UNIMPLEMENTED_INSTRUCTIONS). Listed
    # here so a line using one of these mnemonics still tokenizes as an
    # Instruction and hits codegen's clear "not implemented" error, instead
    # of silently tokenizing as an unrecognized IDENT and vanishing from the
    # assembled output with no diagnostic at all.
    "SMIX", "SECHO", "SREVERB", "SFILTER",
}

# Register tokens recognized by the lexer.  Includes special registers and
# byte-access forms.  SP/FP are aliases for P8/P9 and are handled here too.
REGISTER_TOKENS = {
    f"R{i}" for i in range(10)
} | {
    f"P{i}" for i in range(10)
} | {
    f"P{i}:" for i in range(10)
} | {
    f":P{i}" for i in range(10)
} | {
        "VX", "VY", "VM", "VC", "VL",
        "TT", "TM", "TC", "TS",
        "C0", "C1",
        "MX", "MY", "MB",
        "SP", "FP",
        "SA", "SF", "SV", "SW",
        "PA", "PB", "PC", "PD",
}


def _is_ident_start(ch: str) -> bool:
    return ch.isalpha() or ch == "_" or ch == "."


def _is_ident_part(ch: str) -> bool:
    return ch.isalnum() or ch in "_-"


def _parse_number(text: str) -> int:
    """Parse a decimal or hex integer literal."""
    text = text.strip()
    if text.startswith("0x") or text.startswith("0X"):
        return int(text, 16)
    if text.startswith("-"):
        return -int(text[1:])
    return int(text)


def _parse_char_literal(text: str) -> int:
    """Parse a single-quoted character literal."""
    # text includes the surrounding quotes, e.g. "'A'" or "'\\n'"
    content = text[1:-1]
    if content.startswith("\\") and len(content) == 2:
        esc = content[1]
        mapping = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", "'": "'", '"': '"'}
        return ord(mapping.get(esc, esc))
    if content == "\\":
        return ord("\\")
    return ord(content)


def _classify_ident(word: str) -> TokenKind:
    """Classify an identifier word as MNEMONIC, REGISTER, or IDENT."""
    upper = word.upper()
    if upper in REGISTER_TOKENS:
        return TokenKind.REGISTER
    if upper in INSTRUCTIONS or upper in DIRECTIVES:
        return TokenKind.MNEMONIC
    return TokenKind.IDENT


def tokenize(source: str) -> List[Token]:
    """Tokenize assembly source into a list of tokens."""
    tokens: List[Token] = []
    i = 0
    n = len(source)
    line = 1
    col = 1

    def emit(kind: TokenKind, value: str):
        tokens.append(Token(kind, value, line, col))

    while i < n:
        ch = source[i]

        if ch == "\n":
            emit(TokenKind.NEWLINE, "\n")
            i += 1
            line += 1
            col = 1
            continue

        if ch in " \t\r":
            i += 1
            col += 1
            continue

        if ch == ";":
            start = i
            while i < n and source[i] != "\n":
                i += 1
            emit(TokenKind.COMMENT, source[start:i])
            col += (i - start)
            continue

        if ch == ":":
            # Could be a label definition if it follows an identifier immediately
            # (handled below), or a stray colon.  Treat as COLON token.
            emit(TokenKind.COLON, ":")
            i += 1
            col += 1
            continue

        if ch == ",":
            emit(TokenKind.COMMA, ",")
            i += 1
            col += 1
            continue

        if ch == "[":
            emit(TokenKind.LBRACKET, "[")
            i += 1
            col += 1
            continue

        if ch == "]":
            emit(TokenKind.RBRACKET, "]")
            i += 1
            col += 1
            continue

        if ch == "+":
            emit(TokenKind.PLUS, "+")
            i += 1
            col += 1
            continue

        if ch == "-":
            emit(TokenKind.MINUS, "-")
            i += 1
            col += 1
            continue

        if ch == '"':
            start = i
            i += 1
            col += 1
            while i < n and source[i] != '"':
                if source[i] == "\\" and i + 1 < n:
                    i += 2
                    col += 2
                else:
                    i += 1
                    col += 1
            if i < n:
                i += 1  # consume closing quote
                col += 1
            emit(TokenKind.STRING, source[start:i])
            continue

        if ch == "'":
            start = i
            i += 1
            col += 1
            while i < n and source[i] != "'":
                if source[i] == "\\" and i + 1 < n:
                    i += 2
                    col += 2
                else:
                    i += 1
                    col += 1
            if i < n:
                i += 1
                col += 1
            emit(TokenKind.CHAR, source[start:i])
            continue

        if ch.isdigit() or (ch == "0" and i + 1 < n and source[i + 1] in "xX"):
            start = i
            if ch == "0" and i + 1 < n and source[i + 1] in "xX":
                i += 2
                col += 2
                while i < n and source[i].isalnum():
                    i += 1
                    col += 1
            else:
                i += 1
                col += 1
                while i < n and source[i].isdigit():
                    i += 1
                    col += 1
            emit(TokenKind.NUMBER, source[start:i])
            continue

        if _is_ident_start(ch):
            start = i
            i += 1
            col += 1
            while i < n and _is_ident_part(source[i]):
                i += 1
                col += 1
            word = source[start:i]

            # Label definition: word immediately followed by ':' with no space
            if i < n and source[i] == ":":
                # But not if word is a register like P0: — those are register tokens
                if word.upper() in REGISTER_TOKENS:
                    emit(TokenKind.REGISTER, word)
                    # leave the colon to be processed next loop iteration
                    continue
                i += 1
                col += 1
                emit(TokenKind.LABEL_DEF, word)
                continue

            kind = _classify_ident(word)
            emit(kind, word)
            continue

        # Unknown character: skip it but emit a raw token so the parser can
        # report a useful error.
        emit(TokenKind.IDENT, ch)
        i += 1
        col += 1

    # Do not emit a separate EOF token; the parser treats EOF as end of input.
    return tokens


def tokens_to_lines(tokens: List[Token]) -> List[List[Token]]:
    """Split a flat token list into lines (each line is a list of tokens)."""
    lines: List[List[Token]] = []
    current: List[Token] = []
    for tok in tokens:
        if tok.kind == TokenKind.NEWLINE:
            if current:
                lines.append(current)
                current = []
        else:
            current.append(tok)
    if current:
        lines.append(current)
    return lines


def line_text(tokens: List[Token]) -> str:
    """Reconstruct the original text of a token line (excluding comments)."""
    parts = []
    for tok in tokens:
        if tok.kind == TokenKind.COMMENT:
            continue
        parts.append(tok.value)
    return " ".join(parts)
