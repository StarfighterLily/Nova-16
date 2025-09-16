"""
Astrid Compiler Error Handling
"""

from typing import Optional
import sys


class CompilerError(Exception):
    """Base exception for all Astrid compiler errors."""

    def __init__(self, message: str, filename: Optional[str] = None,
                 line: Optional[int] = None, column: Optional[int] = None):
        self.message = message
        self.filename = filename
        self.line = line
        self.column = column
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the error message with location information."""
        parts = []
        if self.filename and self.filename != "<stdin>":
            parts.append(f"{self.filename}")
        if self.line is not None:
            parts.append(f"line {self.line}")
            if self.column is not None:
                parts.append(f"column {self.column}")

        location = ":".join(parts)
        if location:
            return f"{location}: {self.message}"
        return self.message


class LexerError(CompilerError):
    """Error during lexical analysis."""
    pass


class ParserError(CompilerError):
    """Error during syntax analysis."""
    pass


class SemanticError(CompilerError):
    """Error during semantic analysis."""
    pass


class IRError(CompilerError):
    """Error during IR generation or optimization."""
    pass


class CodeGenError(CompilerError):
    """Error during code generation."""
    pass
