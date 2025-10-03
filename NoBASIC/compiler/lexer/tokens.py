"""
NoBASIC Token Definitions
"""

from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass


class TokenType(Enum):
    """Token types for NoBASIC lexer."""

    # Keywords
    CLRDRAW = "CLRDRAW"
    PXLOFF = "PXLOFF"
    PXLON = "PXLON"
    LINE = "LINE"
    CIRCLE = "CIRCLE"
    TEXT = "TEXT"
    SETLAYER = "SETLAYER"
    SPRITEON = "SPRITEON"
    SPRITEOFF = "SPRITEOFF"
    PLAYTONE = "PLAYTONE"
    PLAYWAVE = "PLAYWAVE"
    STOPSOUND = "STOPSOUND"
    SETCHANNEL = "SETCHANNEL"
    GETKEY = "GETKEY"
    INPUT = "INPUT"
    DISP = "DISP"
    PAUSE = "PAUSE"
    IF = "IF"
    THEN = "THEN"
    ELSE = "ELSE"
    END = "END"
    FOR = "FOR"
    TO = "TO"
    STEP = "STEP"
    NEXT = "NEXT"
    WHILE = "WHILE"
    REPEAT = "REPEAT"
    UNTIL = "UNTIL"
    GOTO = "GOTO"
    DIM = "DIM"
    LET = "LET"
    STRUCT = "STRUCT"
    GLOBAL = "GLOBAL"
    LOCAL = "LOCAL"

    # Built-in functions
    SIN = "SIN"
    COS = "COS"
    TAN = "TAN"
    SQRT = "SQRT"
    ABS = "ABS"
    INT = "INT"
    ROUND = "ROUND"
    RAND = "RAND"
    LENGTH = "LENGTH"
    SUB = "SUB"
    CONCAT = "CONCAT"
    SUM = "SUM"
    MEAN = "MEAN"
    MEMREAD = "MEMREAD"
    MEMWRITE = "MEMWRITE"

    # Operators
    PLUS = "+"
    MINUS = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    POWER = "^"
    EQUAL = "="
    NOT_EQUAL = "<>"
    LESS = "<"
    LESS_EQUAL = "<="
    GREATER = ">"
    GREATER_EQUAL = ">="
    BITWISE_AND = "&"
    BITWISE_OR = "|"
    SHIFT_LEFT = "<<"
    SHIFT_RIGHT = ">>"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"

    # Delimiters
    LPAREN = "("
    RPAREN = ")"
    LBRACKET = "["
    RBRACKET = "]"
    COMMA = ","
    QUOTE = "\""
    COLON = ":"
    AT = "@"
    DOT = "."

    # Literals
    NUMBER_LITERAL = "NUMBER_LITERAL"
    STRING_LITERAL = "STRING_LITERAL"
    IDENTIFIER = "IDENTIFIER"

    # Special
    EOF = "EOF"
    COMMENT = "COMMENT"
    WHITESPACE = "WHITESPACE"


@dataclass
class Token:
    """Represents a lexical token."""
    type: TokenType
    lexeme: str
    literal: Optional[Any] = None
    line: int = 0
    column: int = 0

    def __str__(self) -> str:
        if self.literal is not None:
            return f"{self.type.value} {self.lexeme} {self.literal}"
        return f"{self.type.value} {self.lexeme}"

    def __repr__(self) -> str:
        return self.__str__()


# Keywords mapping
KEYWORDS = {
    "clrdraw": TokenType.CLRDRAW,
    "pxloff": TokenType.PXLOFF,
    "pxlon": TokenType.PXLON,
    "line": TokenType.LINE,
    "circle": TokenType.CIRCLE,
    "text": TokenType.TEXT,
    "setlayer": TokenType.SETLAYER,
    "spriteon": TokenType.SPRITEON,
    "spriteoff": TokenType.SPRITEOFF,
    "playtone": TokenType.PLAYTONE,
    "playwave": TokenType.PLAYWAVE,
    "stopsound": TokenType.STOPSOUND,
    "setchannel": TokenType.SETCHANNEL,
    "getkey": TokenType.GETKEY,
    "input": TokenType.INPUT,
    "disp": TokenType.DISP,
    "pause": TokenType.PAUSE,
    "if": TokenType.IF,
    "then": TokenType.THEN,
    "else": TokenType.ELSE,
    "end": TokenType.END,
    "for": TokenType.FOR,
    "to": TokenType.TO,
    "step": TokenType.STEP,
    "next": TokenType.NEXT,
    "while": TokenType.WHILE,
    "repeat": TokenType.REPEAT,
    "until": TokenType.UNTIL,
    "goto": TokenType.GOTO,
    "dim": TokenType.DIM,
    "let": TokenType.LET,
    "struct": TokenType.STRUCT,
    "global": TokenType.GLOBAL,
    "local": TokenType.LOCAL,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
    # Built-in functions that can be used as keywords
    "sin": TokenType.SIN,
    "cos": TokenType.COS,
    "tan": TokenType.TAN,
    "sqrt": TokenType.SQRT,
    "abs": TokenType.ABS,
    "int": TokenType.INT,
    "round": TokenType.ROUND,
    "rand": TokenType.RAND,
    "length": TokenType.LENGTH,
    "sub": TokenType.SUB,
    "concat": TokenType.CONCAT,
    "sum": TokenType.SUM,
    "mean": TokenType.MEAN,
    "memread": TokenType.MEMREAD,
    "memwrite": TokenType.MEMWRITE,
}

# Single character tokens
SINGLE_CHAR_TOKENS = {
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.MULTIPLY,
    "/": TokenType.DIVIDE,
    "^": TokenType.POWER,
    "=": TokenType.EQUAL,
    "<": TokenType.LESS,
    ">": TokenType.GREATER,
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    "[": TokenType.LBRACKET,
    "]": TokenType.RBRACKET,
    ",": TokenType.COMMA,
    "\"": TokenType.QUOTE,
    ":": TokenType.COLON,
    "@": TokenType.AT,
    ".": TokenType.DOT,
    "&": TokenType.BITWISE_AND,
    "|": TokenType.BITWISE_OR,
}

# Multi-character operators
MULTI_CHAR_OPERATORS = {
    "<>": TokenType.NOT_EQUAL,
    "<=": TokenType.LESS_EQUAL,
    ">=": TokenType.GREATER_EQUAL,
    "<<": TokenType.SHIFT_LEFT,
    ">>": TokenType.SHIFT_RIGHT,
}