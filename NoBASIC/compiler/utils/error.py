"""
NoBASIC Compiler Error Classes
"""

from typing import Optional


class CompilerError(Exception):
    """Base class for compiler errors."""

    def __init__(self, message: str, filename: str = "<stdin>", line: int = 0, column: int = 0):
        self.message = message
        self.filename = filename
        self.line = line
        self.column = column
        super().__init__(self.format_message())

    def format_message(self) -> str:
        if self.filename == "<stdin>":
            return f"Error: {self.message}"
        return f"Error in {self.filename} at line {self.line}, column {self.column}: {self.message}"


class LexerError(CompilerError):
    """Lexer-specific errors."""
    pass


class ParserError(CompilerError):
    """Parser-specific errors."""
    pass


class SemanticError(CompilerError):
    """Semantic analysis errors."""
    pass


class CodeGenError(CompilerError):
    """Code generation errors."""
    pass