"""
NoBASIC Abstract Syntax Tree Definitions
"""

from typing import List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class VarScope(Enum):
    """Variable scope types."""
    GLOBAL = "global"
    LOCAL = "local"
    IMPLICIT = "implicit"  # Default scope (global by default)


class DataType(Enum):
    """Data types in NoBASIC."""
    NUMBER = "number"
    STRING = "string"
    LIST = "list"
    MATRIX = "matrix"
    STRUCT = "struct"


@dataclass
class StructType:
    """User-defined struct type."""
    name: str
    fields: List[str]  # Field names (all 16-bit)
    
    def __str__(self):
        return f"struct {self.name}"


@dataclass
class ASTNode:
    """Base class for all AST nodes."""
    pass


@dataclass
class Program(ASTNode):
    """Root node of the AST."""
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
class ClrDrawStmt(Statement):
    """ClrDraw statement."""
    pass


@dataclass
class PxlOnStmt(Statement):
    """PxlOn(x, y, color) statement."""
    x: Expression
    y: Expression
    color: Expression


@dataclass
class PxlOffStmt(Statement):
    """PxlOff(x, y) statement."""
    x: Expression
    y: Expression


@dataclass
class LineStmt(Statement):
    """Line(x1, y1, x2, y2, color) statement."""
    x1: Expression
    y1: Expression
    x2: Expression
    y2: Expression
    color: Expression


@dataclass
class CircleStmt(Statement):
    """Circle(x, y, radius, color) statement."""
    x: Expression
    y: Expression
    radius: Expression
    color: Expression


@dataclass
class TextStmt(Statement):
    """Text(x, y, "string", color) statement."""
    x: Expression
    y: Expression
    text: Expression
    color: Expression


@dataclass
class SetLayerStmt(Statement):
    """SetLayer(layer) statement."""
    layer: Expression


@dataclass
class SpriteOnStmt(Statement):
    """SpriteOn(spriteId, x, y) statement."""
    sprite_id: Expression
    x: Expression
    y: Expression


@dataclass
class SpriteOffStmt(Statement):
    """SpriteOff(spriteId) statement."""
    sprite_id: Expression


@dataclass
class PlayToneStmt(Statement):
    """PlayTone(frequency, duration, volume) statement."""
    frequency: Expression
    duration: Expression
    volume: Expression


@dataclass
class PlayWaveStmt(Statement):
    """PlayWave(waveform, frequency, volume) statement."""
    waveform: Expression
    frequency: Expression
    volume: Expression


@dataclass
class StopSoundStmt(Statement):
    """StopSound statement."""
    pass


@dataclass
class SetChannelStmt(Statement):
    """SetChannel(channel) statement."""
    channel: Expression


@dataclass
class GetKeyStmt(Statement):
    """GetKey statement."""
    pass


@dataclass
class InputStmt(Statement):
    """Input(prompt, variable) statement."""
    prompt: Optional[Expression]
    variable: str


@dataclass
class DispStmt(Statement):
    """Disp "text" statement."""
    text: Expression


@dataclass
class PauseStmt(Statement):
    """Pause statement."""
    pass


@dataclass
class FunctionCallStmt(Statement):
    """Function call statement."""
    function_call: Expression  # This should be a FunctionCallExpr


@dataclass
class AssignmentStmt(Statement):
    """expression = expression statement."""
    variable: Expression
    expression: Expression


@dataclass
class IfStmt(Statement):
    """If condition Then statements [Else statements] End statement."""
    condition: Expression
    then_branch: List[Statement]
    else_branch: Optional[List[Statement]] = None


@dataclass
class ForStmt(Statement):
    """For variable = start To end [Step step] statements Next statement."""
    variable: str
    start: Expression
    end: Expression
    step: Optional[Expression]
    body: List[Statement]


@dataclass
class WhileStmt(Statement):
    """While condition statements End statement."""
    condition: Expression
    body: List[Statement]


@dataclass
class RepeatStmt(Statement):
    """Repeat statements Until condition statement."""
    body: List[Statement]
    condition: Expression


@dataclass
class GotoStmt(Statement):
    """Goto label statement."""
    label: str


@dataclass
class LabelStmt(Statement):
    """Label: statement."""
    label: str


@dataclass
class StructDeclarationStmt(Statement):
    """STRUCT name field1 field2 ... END statement."""
    name: str
    fields: List[str]


@dataclass
class VarDeclarationStmt(Statement):
    """GLOBAL/LOCAL variable declaration statement."""
    scope: VarScope
    variables: List[str]  # Support multiple variables in one declaration


@dataclass
class AsmBlockStmt(Statement):
    """Inline assembly block statement (Asm ... End)."""
    assembly_code: str  # Raw assembly code to be inserted


# Expressions
@dataclass
class LiteralExpr(Expression):
    """Literal value (number or string)."""
    value: Any
    data_type: DataType


@dataclass
class VariableExpr(Expression):
    """Variable reference."""
    name: str


@dataclass
class ListAccessExpr(Expression):
    """List access: L1(index)"""
    list_name: str
    index: Expression


@dataclass
class MatrixAccessExpr(Expression):
    """Matrix access: MatA(row, col)"""
    matrix_name: str
    row: Expression
    col: Expression


@dataclass
class MemberAccessExpr(Expression):
    """Member access: struct.field"""
    object: Expression
    member: str


@dataclass
class BinaryExpr(Expression):
    """Binary operation: left op right"""
    left: Expression
    operator: str
    right: Expression


@dataclass
class UnaryExpr(Expression):
    """Unary operation: op expression"""
    operator: str
    expression: Expression


@dataclass
class FunctionCallExpr(Expression):
    """Function call: func(arg1, arg2, ...)"""
    name: str
    arguments: List[Expression]


@dataclass
class GroupingExpr(Expression):
    """Grouped expression: (expression)"""
    expression: Expression