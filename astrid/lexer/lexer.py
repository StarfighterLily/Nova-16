# Astrid Language Lexer
# File: astrid/lexer/lexer.py
# Enhanced with keywords for do-while, switch/case, and additional operators

import re
from typing import List, Optional

from astrid.errors import LexerError, did_you_mean

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
                # Classify the offending character so the diagnostic says
                # *why* it is unacceptable and how to fix it, rather than
                # only naming it. The lexer owns the full source text, so
                # the error can render a snippet with a caret.
                self._raise_lex_error(value, line_num, column)
            if '\n' in value:
                # Advance the line counter and re-anchor line_start to the
                # FIRST COLUMN of the new line -- the index just past the
                # last newline in the matched text. Anchoring to mo.end()
                # instead would swallow the new line's leading indentation
                # and shift every subsequent column on the line to the left
                # (a multi-line comment or indented line would then report
                # columns relative to the first token, not the line).
                line_num += value.count('\n')
                line_start = mo.start() + value.rfind('\n') + 1
        self.tokens.append(Token('EOF', '', line_num, 1))
        return self.tokens

    def _raise_lex_error(self, value: str, line_num: int, column: int):
        """Raise a LexerError for an unlexable character, with a diagnosis.

        The MISMATCH rule catches anything no other pattern matched; this
        distinguishes the common cases (unterminated string/char literals,
        stray identifiers with a leading digit context, operator typos)
        so the message explains the likely cause and the fix.
        """
        hint = None
        if value == '"':
            message = 'unterminated string literal'
            hint = ('strings must be closed with a matching double quote '
                    '(use \\" for a literal quote inside the string)')
        elif value == "'":
            message = 'unterminated character literal'
            hint = ("character literals are a single character in single "
                    "quotes, e.g. 'A' or '\\n' (use \\' for a literal quote)")
        elif value.isalpha() or value == '_':
            # An identifier-shaped character no pattern matched: it must
            # have started mid-token, e.g. `3abc` (number followed by
            # identifier characters without a separator).
            message = (f"unexpected character {value!r} -- identifiers "
                       f"cannot start here")
            hint = ('separate numbers from identifiers with a space or '
                    'operator, or start identifiers with a letter or '
                    'underscore')
        else:
            message = f'unexpected character {value!r}'
            # Operator typos are the most common cause of stray symbols;
            # suggest the closest valid operator/keyword spelling.
            suggestion = did_you_mean(value, OPERATORS, max_distance=1)
            if suggestion is not None:
                hint = f"did you mean the operator '{suggestion}'?"
            else:
                hint = ('allowed characters: letters, digits, whitespace, '
                        'operators and delimiters')
        raise LexerError(
            message, line=line_num, column=column,
            length=len(value), hint=hint, source_text=self.code)


