#!/usr/bin/env python3
"""
NoBASIC Lexer
Tokenizes NoBASIC source            # Symbols
            (r'<=', TokenType.LESS_EQUAL),
            (r'>=', TokenType.GREATER_EQUAL),
            (r'!=', TokenType.NOT_EQUALS),
            (r'<>', TokenType.NOT_EQUALS),  # Alternative not equals
            (r'=', TokenType.EQUALS), into tokens.
"""

import re
from typing import List
from nobasic_utils import Token, TokenType
from nobasic_errors import LexerError


class Lexer:
    """Lexical analyzer for NoBASIC source code."""

    def __init__(self):
        # Token patterns
        self.token_patterns = [
            # Special compound keywords
            (r'endif\b', 'ENDIF_COMPOUND'),  # Special handling for EndIf
            (r'end\b', TokenType.END),
            
            # Keywords (case insensitive)
            (r'clrhome\b', TokenType.CLRHOME),
            (r'disp\b', TokenType.DISP),
            (r'input\b', TokenType.INPUT),
            (r'prompt\b', TokenType.PROMPT),
            (r'if\b', TokenType.IF),
            (r'then\b', TokenType.THEN),
            (r'else\b', TokenType.ELSE),
            (r'elseif\b', TokenType.ELSEIF),
            (r'for\b', TokenType.FOR),
            (r'to\b', TokenType.TO),
            (r'step\b', TokenType.STEP),
            (r'next\b', TokenType.NEXT),
            (r'while\b', TokenType.WHILE),
            (r'wend\b', TokenType.WEND),
            (r'do\b', TokenType.DO),
            (r'loop\b', TokenType.LOOP),
            (r'repeat\b', TokenType.REPEAT),
            (r'until\b', TokenType.UNTIL),
            (r'select\b', TokenType.SELECT),
            (r'case\b', TokenType.CASE),
            (r'call\b', TokenType.CALL),
            (r'return\b', TokenType.RETURN),
            (r'dim\b', TokenType.DIM),
            (r'break\b', TokenType.BREAK),
            (r'continue\b', TokenType.CONTINUE),
            (r'pause\b', TokenType.PAUSE),
            (r'true\b', TokenType.TRUE),
            (r'false\b', TokenType.FALSE),
            (r'define\b', TokenType.DEFINE),
            (r'goto\b', TokenType.GOTO),
            (r'lbl\b', TokenType.LBL),
            (r'try\b', TokenType.TRY),
            (r'catch\b', TokenType.CATCH),
            (r'struct\b', TokenType.STRUCT),
            (r'as\b', TokenType.AS),
            (r'splay\b', TokenType.SPLAY),
            (r'play\b', TokenType.PLAY),
            (r'stop\b', TokenType.STOP),

            # Operators
            (r'and\b', TokenType.AND),
            (r'or\b', TokenType.OR),
            (r'not\b', TokenType.NOT),
            (r'mod\b', TokenType.MOD),
            (r'shl\b', TokenType.SHL),
            (r'shr\b', TokenType.SHR),
            (r'xor\b', TokenType.XOR),

            # Comments (ignored)
            (r'rem.*', None),
            (r'//.*', None),
            (r';.*', None),

            # Symbols
            (r'<=', TokenType.LESS_EQUAL),
            (r'>=', TokenType.GREATER_EQUAL),
            (r'!=', TokenType.NOT_EQUALS),
            (r'<>', TokenType.NOT_EQUALS),  # Alternative not equals - must come before < and >
            (r'->', TokenType.ARROW),
            (r'=', TokenType.EQUALS),
            (r'&', TokenType.AMPERSAND),
            (r'\.', TokenType.DOT),
            (r'<', TokenType.LESS),
            (r'>', TokenType.GREATER),
            (r'\+', TokenType.PLUS),
            (r'-', TokenType.MINUS),
            (r'\*', TokenType.MULTIPLY),
            (r'/', TokenType.DIVIDE),
            (r'\^', TokenType.POWER),
            (r'\(', TokenType.LPAREN),
            (r'\)', TokenType.RPAREN),
            (r'\[', TokenType.LBRACKET),
            (r'\]', TokenType.RBRACKET),
            (r',', TokenType.COMMA),
            (r':', TokenType.COLON),

            # Strings
            (r'"([^"]*)"', TokenType.STRING),

            # Numbers
            (r'0[xX][0-9a-fA-F]+', TokenType.NUMBER),  # Hex numbers
            (r'\d+', TokenType.NUMBER),

            # Identifiers (variables, functions)
            (r'[a-zA-Z_][a-zA-Z0-9_]*', TokenType.IDENTIFIER),

            # Whitespace (ignored)
            (r'\s+', None),
        ]

        # Compile patterns
        self.compiled_patterns = [(re.compile(pattern, re.IGNORECASE), token_type)
                                  for pattern, token_type in self.token_patterns]

    def tokenize(self, source: str, filename: str = "<unknown>") -> List[Token]:
        """
        Tokenize NoBASIC source code.

        Args:
            source: The source code to tokenize
            filename: Source filename for error reporting

        Returns:
            List of tokens

        Raises:
            LexerError: If tokenization fails
        """
        # Strip BOM if present
        if source.startswith('\ufeff'):
            source = source[1:]
            
        tokens = []
        lines = source.splitlines()
        line_num = 1
        col_num = 1

        for line in lines:
            line_tokens = self._tokenize_line(line, filename, line_num, col_num)
            tokens.extend(line_tokens)
            # Add newline token
            tokens.append(Token(TokenType.NEWLINE, '\n', line_num, len(line) + 1, filename))
            line_num += 1
            col_num = 1

        # Add EOF token
        tokens.append(Token(TokenType.EOF, '', line_num, col_num, filename))

        return tokens

    def _tokenize_line(self, line: str, filename: str, line_num: int, start_col: int) -> List[Token]:
        """Tokenize a single line."""
        tokens = []
        pos = 0
        col_num = start_col

        while pos < len(line):
            matched = False

            for pattern, token_type in self.compiled_patterns:
                match = pattern.match(line, pos)
                if match:
                    if token_type == 'ENDIF_COMPOUND':  # Special handling for EndIf
                        tokens.append(Token(TokenType.END, 'End', line_num, col_num, filename))
                        tokens.append(Token(TokenType.IF, 'If', line_num, col_num + 3, filename))
                    elif token_type is not None:  # Skip whitespace
                        value = match.group(0)
                        if token_type == TokenType.STRING:
                            # Extract string content without quotes
                            value = match.group(1)
                        tokens.append(Token(token_type, value, line_num, col_num, filename))
                    pos = match.end()
                    col_num += match.end() - match.start()
                    matched = True
                    break

            if not matched:
                raise LexerError(f"Unexpected character '{line[pos]}'",
                                filename, line_num, col_num)

        return tokens