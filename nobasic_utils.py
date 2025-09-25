#!/usr/bin/env python3
"""
NoBASIC Compiler Utilities
Shared utilities, token types, AST nodes, and helper functions.
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from nobasic_errors import CompilerError


# Token Types
class TokenType(Enum):
    # Keywords
    CLRHOME = "CLRHOME"
    DISP = "DISP"
    INPUT = "INPUT"
    PROMPT = "PROMPT"
    IF = "IF"
    THEN = "THEN"
    ELSE = "ELSE"
    ELSEIF = "ELSEIF"
    END = "END"
    FOR = "FOR"
    TO = "TO"
    STEP = "STEP"
    NEXT = "NEXT"
    WHILE = "WHILE"
    WEND = "WEND"
    DO = "DO"
    LOOP = "LOOP"
    REPEAT = "REPEAT"
    UNTIL = "UNTIL"
    SELECT = "SELECT"
    CASE = "CASE"
    CALL = "CALL"
    RETURN = "RETURN"
    DIM = "DIM"
    BREAK = "BREAK"
    CONTINUE = "CONTINUE"
    PAUSE = "PAUSE"
    TRUE = "TRUE"
    FALSE = "FALSE"
    DEFINE = "DEFINE"
    GOTO = "GOTO"
    LBL = "LBL"
    TRY = "TRY"
    CATCH = "CATCH"
    SPLAY = "SPLAY"
    PLAY = "PLAY"
    STOP = "STOP"

    # Operators
    PLUS = "+"
    MINUS = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    POWER = "^"
    EQUALS = "="
    NOT_EQUALS = "!="
    LESS = "<"
    GREATER = ">"
    LESS_EQUAL = "<="
    GREATER_EQUAL = ">="
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    SHL = "SHL"
    SHR = "SHR"
    XOR = "XOR"
    MOD = "MOD"

    # Symbols
    LPAREN = "("
    RPAREN = ")"
    LBRACKET = "["
    RBRACKET = "]"
    COMMA = ","
    COLON = ":"
    QUOTE = '"'
    ARROW = "->"
    AMPERSAND = "&"

    # Literals
    NUMBER = "NUMBER"
    STRING = "STRING"
    IDENTIFIER = "IDENTIFIER"

    # Special
    EOF = "EOF"
    NEWLINE = "NEWLINE"


@dataclass
class Token:
    """A token from the lexer."""
    type: TokenType
    value: str
    line: int
    column: int
    filename: str = "<unknown>"

    def __str__(self) -> str:
        return f"Token({self.type}, '{self.value}', {self.line}:{self.column})"


# AST Node Types
@dataclass
class ASTNode:
    """Base class for all AST nodes."""
    pass


@dataclass
class Program(ASTNode):
    """Root node for a NoBASIC program."""
    statements: List[ASTNode]


@dataclass
class Statement(ASTNode):
    """Base class for statements."""
    pass


@dataclass
class Expression(ASTNode):
    """Base class for expressions."""
    pass


# Statements
@dataclass
class ClrHomeStmt(Statement):
    """ClrHome statement."""
    pass


@dataclass
class DispStmt(Statement):
    """Disp statement."""
    expressions: List[Expression]


@dataclass
class InputStmt(Statement):
    """Input statement."""
    prompt: Optional[str]
    variable: str


@dataclass
class AssignmentStmt(Statement):
    """Assignment statement."""
    target: Expression
    expression: Expression


@dataclass
class DimStmt(Statement):
    """DIM statement for array declaration."""
    array_name: str
    size: Expression


@dataclass
class IfStmt(Statement):
    """If statement."""
    condition: Expression
    then_stmts: List[Statement]
    elif_stmts: List['ElifClause']
    else_stmts: List[Statement]


@dataclass
class ElifClause:
    """Elif clause."""
    condition: Expression
    statements: List[Statement]


@dataclass
class BreakStmt(Statement):
    """Break statement."""
    pass


@dataclass
class ContinueStmt(Statement):
    """Continue statement."""
    pass


@dataclass
class ForStmt(Statement):
    """For loop statement."""
    variable: str
    start: Expression
    end: Expression
    step: Optional[Expression]
    statements: List[Statement]


@dataclass
class WhileStmt(Statement):
    """While loop statement."""
    condition: Expression
    statements: List[Statement]


@dataclass
class DoLoopStmt(Statement):
    """Do/Loop statement."""
    statements: List[Statement]
    condition: Optional[Expression] = None
    loop_type: str = "unconditional"  # "unconditional", "while", "until"


@dataclass
class RepeatUntilStmt(Statement):
    """Repeat/Until statement."""
    statements: List[Statement]
    condition: Expression


@dataclass
class SelectStmt(Statement):
    """Select Case statement."""
    expression: Expression
    cases: List['CaseClause']
    else_stmts: List[Statement]


@dataclass
class CaseClause:
    """Case clause."""
    values: List[Expression]  # List of values to match (can be ranges)
    statements: List[Statement]


@dataclass
class CallStmt(Statement):
    """Call statement."""
    subroutine: str
    arguments: List[Expression] = field(default_factory=list)


@dataclass
class ReturnStmt(Statement):
    """Return statement."""
    pass


@dataclass
class PauseStmt(Statement):
    """Pause statement."""
    pass


@dataclass
class DefineStmt(Statement):
    """Define subroutine statement."""
    name: str
    statements: List[Statement]


@dataclass
class GotoStmt(Statement):
    """Goto statement."""
    label: str


@dataclass
class LabelStmt(Statement):
    """Label statement."""
    name: str


@dataclass
class TryCatchStmt(Statement):
    """Try/Catch statement."""
    try_stmts: List[Statement]
    catch_stmts: List[Statement]


# Expressions
@dataclass
class BinaryExpr(Expression):
    """Binary expression."""
    left: Expression
    operator: str
    right: Expression


@dataclass
class UnaryExpr(Expression):
    """Unary expression."""
    operator: str
    operand: Expression


@dataclass
class LiteralExpr(Expression):
    """Literal expression."""
    value: Union[int, str]


@dataclass
class VariableExpr(Expression):
    """Variable reference."""
    name: str


@dataclass
class ArrayAccessExpr(Expression):
    """Array access expression."""
    array: str
    index: Expression


@dataclass
class FunctionCallExpr(Expression):
    """Function call expression."""
    name: str
    arguments: List[Expression]


@dataclass
class ArrayLiteralExpr(Expression):
    """Array literal expression."""
    elements: List[Expression]


# Utility functions
def is_keyword(word: str) -> bool:
    """Check if a word is a NoBASIC keyword."""
    try:
        TokenType(word.upper())
        return True
    except ValueError:
        return False


def get_keyword_token(word: str) -> Optional[TokenType]:
    """Get the token type for a keyword."""
    try:
        return TokenType(word.upper())
    except ValueError:
        return None


def format_error_location(filename: str, line: int, column: int = -1) -> str:
    """Format a location for error messages."""
    if column >= 0:
        return f"{filename}:{line}:{column}"
    else:
        return f"{filename}:{line}"