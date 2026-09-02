# Astrid Language Lexer
# File: astrid/lexer/lexer.py
# Enhanced with keywords for do-while, switch/case, and additional operators

import re
from typing import List, Optional

# Token types
TOKEN_TYPES = [
    'KEYWORD', 'IDENTIFIER', 'NUMBER', 'STRING', 'CHAR', 'OPERATOR', 'DELIMITER', 'COMMENT', 'EOF'
]

# Keywords in Astrid
KEYWORDS = {
    'int', 'char', 'void', 'if', 'else', 'while', 'for', 'break', 'continue', 'return',
    'do', 'switch', 'case', 'default', 'string', 'binary', 'float',
    # 'float' is a Q8.8 fixed-point type (16-bit: integer part in the high
    # byte, 1/256 fractional part in the low byte), the floating-point
    # representation the Nova-16 CPU implements via ITOF/FTOI/FMUL/FDIV.
    # C qualifiers/operators added for expanded C support:
    'const',    # const qualifier (accepted; treated as a normal variable)
    'sizeof',   # sizeof(type) / sizeof(expr) compile-time byte-size operator
    # C enum support:
    'enum',     # enum declarations introduce named integer constants
    # C struct support:
    'struct',   # struct Tag { field; ... }; definitions + member access (p.field)

    # C storage qualifiers (accepted and ignored -- the compiler treats the
    # declared entity exactly like its unqualified counterpart):
    'register', 'volatile', 'extern', 'static', 'inline',
    # C type modifiers (normalized to their base type by the parser):
    'signed', 'unsigned', 'long', 'short',
    # C type alias:
    'typedef',   # typedef int myint; -- declare a type alias
    # C unconditional jump:
    'goto',      # goto label; -- jump to a labeled statement
    # C overlapping storage (all members share byte offset 0):
    'union',     # union Tag { int i; char c; }; -- like struct, but overlapping

    # Multi-file compilation units:
    'include',   # include "file";   -- splice another file's definitions in
    'inherits',  # inherits "file";  -- pull in a base file, allowing overrides

    # Rust-style implementation blocks:
    'impl',      # impl TypeName { int method(self, ...) { ... } }
}

# Operators and delimiters
OPERATORS = {
    '+', '-', '*', '/', '%', '==', '!=', '<', '>', '<=', '>=', '=', '+=', '-=', '*=', '/=',
    '&=', '|=', '^=', '<<=', '>>=', '&&', '||', '!', '&', '|', '^', '~', '<<', '>>',
    '++', '--', '->', '?',
}
DELIMITERS = {'(', ')', '{', '}', '[', ']', ';', ',', '.', ':'}

# Token class
token_specification = [
    # Integer literals: hexadecimal (0x..), binary (0b..), octal (0o..),
    # and decimal. Python's int(value, 0) understands all four forms.
    # A decimal point introduces a floating-point literal (e.g. 1.5 or
    # 0.0625); those are Q8.8 fixed-point values handled by the codegen.
    ('NUMBER',   r'0x[0-9A-Fa-f]+|0[bB][01]+|0[oO][0-7]+|\d+\.\d+|\d+'),
    ('ID',       r'[A-Za-z_][A-Za-z0-9_]*'),
    ('STRING',   r'"(\\.|[^"\\])*"'),
    # Char literals: single character, standard escapes (\n, \t, ...),
    # or hex escapes (\x41).
    ('CHAR',     r'\'(\\x[0-9A-Fa-f]{2}|\\.|[^\\\'])\''),
    ('COMMENT',  r'//.*|/\*(.|\n)*?\*/'),
    ('OP',       r'==|!=|<=|>=|<<=|>>=|<<|>>|&&|\|\||\+\+|--|\+=|-=|\*=|/=|%=|&=|\|=|\^=|\-\>|\?|[+\-*/%&|^!~=<>]'),
    ('DELIM',    r'[(){}\[\];,.:]'),
    ('SKIP',     r'[ \t\r\n]+'),
    ('MISMATCH', r'.'),
]
tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)

class Token:
    def __init__(self, type_: str, value: str, line: int, column: int):
        self.type = type_
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, {self.line}, {self.column})"

class Lexer:
    def __init__(self, code: str):
        self.code = code
        self.tokens: List[Token] = []

    def tokenize(self) -> List[Token]:
        line_num = 1
        line_start = 0
        for mo in re.finditer(tok_regex, self.code):
            kind = mo.lastgroup
            value = mo.group()
            column = mo.start() - line_start + 1
            if kind == 'NUMBER':
                self.tokens.append(Token('NUMBER', value, line_num, column))
            elif kind == 'ID':
                if value in KEYWORDS:
                    self.tokens.append(Token('KEYWORD', value, line_num, column))
                else:
                    self.tokens.append(Token('IDENTIFIER', value, line_num, column))
            elif kind == 'STRING':
                self.tokens.append(Token('STRING', value, line_num, column))
            elif kind == 'CHAR':
                self.tokens.append(Token('CHAR', value, line_num, column))
            elif kind == 'OP':
                self.tokens.append(Token('OPERATOR', value, line_num, column))
            elif kind == 'DELIM':
                self.tokens.append(Token('DELIMITER', value, line_num, column))
            elif kind == 'COMMENT':
                continue  # Skip comments
            elif kind == 'SKIP':
                pass  # Skip whitespace
            elif kind == 'MISMATCH':
                raise RuntimeError(f'Unexpected character {value!r} at line {line_num} col {column}')
            if '\n' in value:
                line_num += value.count('\n')
                line_start = mo.end()
        self.tokens.append(Token('EOF', '', line_num, 1))
        return self.tokens


