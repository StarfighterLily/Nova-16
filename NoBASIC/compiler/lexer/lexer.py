"""
NoBASIC Lexer Implementation
"""

import re
from typing import List, Optional, Any

from ..utils.error import LexerError
from .tokens import (
    Token, TokenType, KEYWORDS, SINGLE_CHAR_TOKENS,
    MULTI_CHAR_OPERATORS
)


class Lexer:
    """Lexical analyzer for NoBASIC source code."""

    def __init__(self):
        self.source = ""
        self.filename = "<stdin>"
        self.position = 0
        self.line = 1
        self.column = 1
        self.tokens = []

    def tokenize(self, source: str, filename: str = "<stdin>") -> List[Token]:
        """
        Tokenize the source code into a list of tokens.

        Args:
            source: The source code to tokenize
            filename: Source filename for error reporting

        Returns:
            List of Token objects

        Raises:
            LexerError: If lexical analysis fails
        """
        self.source = source
        self.filename = filename
        self.position = 0
        self.line = 1
        self.column = 1
        self.tokens = []

        while not self.is_at_end():
            self.scan_token()

        self.tokens.append(Token(TokenType.EOF, "", None, self.line, self.column))
        return self.tokens

    def scan_token(self):
        """Scan the next token from the source."""
        self.start_position = self.position
        char = self.advance()

        # Comments (must check before single char tokens)
        if char == "/" and self.match("/"):
            while not self.is_at_end() and self.peek() != "\n":
                self.advance()
            return

        # Multi-character operators (must check before single char tokens)
        if char == "<" and self.match(">"):
            self.add_token(TokenType.NOT_EQUAL)
            return
        if char == "<" and self.match("="):
            self.add_token(TokenType.LESS_EQUAL)
            return
        if char == "<" and self.match("<"):
            self.add_token(TokenType.SHIFT_LEFT)
            return
        if char == ">" and self.match("="):
            self.add_token(TokenType.GREATER_EQUAL)
            return
        if char == ">" and self.match(">"):
            self.add_token(TokenType.SHIFT_RIGHT)
            return
        if char == "+" and self.match("+"):
            # Explicit ++ token so spacing ("- -x") does not become a decrement
            self.add_token(TokenType.INCREMENT)
            return
        if char == "-" and self.match("-"):
            # Explicit -- token so spaced "- -x" stays two unary minus operators
            self.add_token(TokenType.DECREMENT)
            return

        # Strings (must check before single char tokens)
        if char == "\"":
            self.string()
            return

        # Single character tokens
        if char in SINGLE_CHAR_TOKENS:
            token_type = SINGLE_CHAR_TOKENS[char]
            self.add_token(token_type)
            return

        # Numbers
        elif char.isdigit():
            self.number()
            return

        # Identifiers and keywords
        elif char.isalpha() or char == "_":
            self.identifier()
            return

        # Whitespace
        elif char in " \r\t":
            return
        elif char == "\n":
            self.line += 1
            self.column = 1
            return

        # Unexpected
        else:
            raise LexerError(f"Unexpected character: {char}", self.filename, self.line, self.column)

    def number(self):
        """Scan a number literal (supports decimal, hex 0x, binary 0b)."""
        start = self.position - 1
        has_dot = False

        # Check for hex (0x) or binary (0b) prefix
        if self.source[start] == '0' and not self.is_at_end():
            next_char = self.peek().lower()
            if next_char == 'x':
                # Hexadecimal
                self.advance()  # consume 'x'
                hex_start = self.position
                while not self.is_at_end() and self.peek() in '0123456789abcdefABCDEF':
                    self.advance()
                text = self.source[hex_start:self.position]
                if not text:
                    raise LexerError("Invalid hexadecimal number", self.filename, self.line, self.column)
                value = int(text, 16)
                self.add_token(TokenType.NUMBER_LITERAL, value)
                return
            elif next_char == 'b':
                # Binary
                self.advance()  # consume 'b'
                bin_start = self.position
                while not self.is_at_end() and self.peek() in '01':
                    self.advance()
                text = self.source[bin_start:self.position]
                if not text:
                    raise LexerError("Invalid binary number", self.filename, self.line, self.column)
                value = int(text, 2)
                self.add_token(TokenType.NUMBER_LITERAL, value)
                return

        # Regular decimal number
        while not self.is_at_end() and (self.peek().isdigit() or self.peek() == "."):
            if self.peek() == ".":
                if has_dot:
                    break
                has_dot = True
            self.advance()

        text = self.source[start:self.position]
        try:
            value = float(text) if has_dot else int(text)
            self.add_token(TokenType.NUMBER_LITERAL, value)
        except ValueError:
            raise LexerError(f"Invalid number: {text}", self.filename, self.line, self.column)

    def identifier(self):
        """Scan an identifier or keyword."""
        start = self.position - 1

        while not self.is_at_end() and (self.peek().isalnum() or self.peek() == "_"):
            self.advance()

        text = self.source[start:self.position].lower()  # Case insensitive
        token_type = KEYWORDS.get(text, TokenType.IDENTIFIER)
        
        # Special handling for Asm keyword - capture assembly block
        if token_type == TokenType.ASM:
            self.asm_block()
        else:
            self.add_token(token_type)

    def string(self):
        """Scan a string literal."""
        start_line = self.line
        start_pos = self.start_position

        while not self.is_at_end() and self.peek() != "\"":
            if self.peek() == "\n":
                self.line += 1
                self.column = 1
            self.advance()

        if self.is_at_end():
            raise LexerError("Unterminated string", self.filename, start_line, self.column)

        # Consume the closing quote
        self.advance()

        # Extract the string value (without quotes)
        value = self.source[start_pos + 1:self.position - 1]
        self.add_token(TokenType.STRING_LITERAL, value)

    def asm_block(self):
        """
        Scan an inline assembly block.
        Format: Asm
                  <assembly code>
                End
        Captures all text between Asm and End as raw assembly.
        """
        # First emit the ASM token
        self.add_token(TokenType.ASM)
        
        start_line = self.line
        asm_lines = []
        
        # Skip any whitespace/newlines after Asm keyword
        while not self.is_at_end() and self.peek() in " \t\r\n":
            if self.peek() == "\n":
                self.line += 1
                self.column = 1
            self.advance()
        
        # Capture everything until we find "End" as a keyword
        asm_start = self.position
        
        while not self.is_at_end():
            # Check if we've hit "End" keyword
            if self.peek().lower() == 'e':
                # Save current position
                saved_pos = self.position
                saved_line = self.line
                saved_col = self.column
                
                # Try to read "End"
                word_start = self.position
                while not self.is_at_end() and (self.peek().isalnum() or self.peek() == "_"):
                    self.advance()
                
                word = self.source[word_start:self.position].lower()
                
                # Check if it's "end" (case insensitive)
                if word == "end":
                    # Found the End keyword - extract assembly code
                    asm_code = self.source[asm_start:word_start].strip()
                    
                    # Emit the assembly block token
                    self.add_token(TokenType.ASM_BLOCK, asm_code)
                    
                    # Emit the END token
                    self.add_token(TokenType.END)
                    return
                else:
                    # Not "end", restore position and continue
                    self.position = saved_pos
                    self.line = saved_line
                    self.column = saved_col
            
            # Track newlines for line counting
            if self.peek() == "\n":
                self.line += 1
                self.column = 1
            
            self.advance()
        
        # If we get here, we reached EOF without finding End
        raise LexerError("Unterminated Asm block (missing 'End')", self.filename, start_line, self.column)

    def add_token(self, token_type: TokenType, literal: Optional[Any] = None):
        """Add a token to the token list."""
        # For all tokens, use the source text as lexeme to preserve case
        lexeme = self.source[self.start_position:self.position]
        self.tokens.append(Token(token_type, lexeme, literal, self.line, self.column))

    def advance(self) -> str:
        """Advance to the next character."""
        char = self.source[self.position]
        self.position += 1
        self.column += 1
        return char

    def match(self, expected: str) -> bool:
        """Check if the next character matches expected."""
        if self.is_at_end() or self.source[self.position] != expected:
            return False
        self.position += 1
        self.column += 1
        return True

    def peek(self) -> str:
        """Look at the next character without advancing."""
        if self.is_at_end():
            return "\0"
        return self.source[self.position]

    def is_at_end(self) -> bool:
        """Check if we've reached the end of the source."""
        return self.position >= len(self.source)