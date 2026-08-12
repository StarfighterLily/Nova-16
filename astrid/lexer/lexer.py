# Astrid Language Lexer
# File: astrid/lexer/lexer.py

import re
from typing import List, Optional

# Token types
TOKEN_TYPES = [
    'KEYWORD', 'IDENTIFIER', 'NUMBER', 'STRING', 'CHAR', 'OPERATOR', 'DELIMITER', 'COMMENT', 'EOF'
]

# Keywords in Astrid
KEYWORDS = {
    'int', 'char', 'void', 'if', 'else', 'while', 'for', 'break', 'continue', 'return',
}

# Operators and delimiters
OPERATORS = {
    '+', '-', '*', '/', '%', '==', '!=', '<', '>', '<=', '>=', '=', '+=', '-=', '*=', '/=', '&&', '||', '!', '&', '|', '^', '~', '<<', '>>'
}
DELIMITERS = {'(', ')', '{', '}', '[', ']', ';', ',', '.'}

# Token class
token_specification = [
    ('NUMBER',   r'0x[0-9A-Fa-f]+|\d+'),
    ('ID',       r'[A-Za-z_][A-Za-z0-9_]*'),
    ('STRING',   r'"(\\.|[^"\\])*"'),
    ('CHAR',     r'\'(\\.|[^\\\'])\''),
    ('COMMENT',  r'//.*|/\*(.|\n)*?\*/'),
    ('OP',       r'==|!=|<=|>=|<<|>>|\+=|-=|\*=|/=|\+\+|--|&&|\|\||[+\-*/%&|^~!=<>]'),
    ('DELIM',    r'[(){}\[\];,\.]'),
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
