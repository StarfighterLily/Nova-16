#!/usr/bin/env python3
"""
NoBASIC Compiler Error Classes
Error handling for the NoBASIC compiler pipeline.
"""

class CompilerError(Exception):
    """Base exception for all NoBASIC compiler errors."""

    def __init__(self, message: str, filename: str = "<unknown>", line: int = -1, column: int = -1):
        self.message = message
        self.filename = filename
        self.line = line
        self.column = column
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format the error message with location information."""
        if self.line >= 0:
            if self.column >= 0:
                return f"{self.filename}:{self.line}:{self.column}: {self.message}"
            else:
                return f"{self.filename}:{self.line}: {self.message}"
        else:
            return f"{self.filename}: {self.message}"


class LexerError(CompilerError):
    """Error during lexical analysis (tokenization)."""
    pass


class ParserError(CompilerError):
    """Error during syntax analysis (parsing)."""
    pass


class SemanticError(CompilerError):
    """Error during semantic analysis (type checking, symbol resolution)."""
    pass


class CodeGenError(CompilerError):
    """Error during code generation."""
    pass