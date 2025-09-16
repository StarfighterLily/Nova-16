"""
Astrid 2.0 Abstract Syntax Tree (AST) Definitions
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ASTNode(ABC):
    """Base class for all AST nodes."""

    def __init__(self, line: int = 0, column: int = 0):
        self.line = line
        self.column = column

    @abstractmethod
    def accept(self, visitor: 'ASTVisitor') -> Any:
        """Accept a visitor for traversal."""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class Type(Enum):
    """Type system for Astrid 2.0."""
    VOID = "void"
    INT8 = "int8"
    INT16 = "int16"
    UINT8 = "uint8"
    UINT16 = "uint16"
    CHAR = "char"
    STRING = "string"
    PIXEL = "pixel"
    COLOR = "color"
    SOUND = "sound"
    LAYER = "layer"
    SPRITE = "sprite"
    INTERRUPT = "interrupt"
    INTERRUPT_VECTOR = "interrupt_vector"
    MEMORY_REGION = "memory_region"


@dataclass
class ArrayType:
    """Array type with size information."""
    element_type: 'DataType'
    size: Optional['Expression'] = None

    def __str__(self):
        if self.size:
            return f"{self.element_type}[{self.size}]"
        return f"{self.element_type}[]"

@dataclass
class StructType:
    """User-defined struct type."""
    name: str
    fields: Optional[Dict[str, Type]] = None

    def __str__(self) -> str:
        return f"struct {self.name}"


# Type alias for all possible types
DataType = Union[Type, StructType]


# Expressions

class Expression(ASTNode):
    """Base class for expressions."""
    pass


@dataclass
class Literal(Expression):
    """Literal value expression."""
    value: Union[int, str, bool]
    type: Optional[DataType] = None

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_literal(self)


@dataclass
class Variable(Expression):
    """Variable reference expression."""
    name: str
    type: Optional[DataType] = None

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_variable(self)


@dataclass
class BinaryOp(Expression):
    """Binary operation expression."""
    left: Expression
    operator: str
    right: Expression
    type: Optional[DataType] = None

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_binary_op(self)


@dataclass
class UnaryOp(Expression):
    """Unary operation expression."""
    operator: str
    operand: Expression
    type: Optional[DataType] = None

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_unary_op(self)


@dataclass
class TernaryOp(Expression):
    """Ternary conditional expression (condition ? then_expr : else_expr)."""
    condition: Expression
    then_expr: Expression
    else_expr: Expression
    type: Optional[DataType] = None

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_ternary_op(self)


@dataclass
class FunctionCall(Expression):
    """Function call expression."""
    name: str
    arguments: List[Expression]
    type: Optional[DataType] = None

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_function_call(self)


@dataclass
class MemberAccess(Expression):
    """Member access expression (object.field)."""
    object: Expression
    member: str
    type: Optional[DataType] = None

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_member_access(self)


@dataclass
class ArrayAccess(Expression):
    """Array access expression (array[index])."""
    array: Expression
    index: Expression
    type: Optional[DataType] = None

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_array_access(self)


@dataclass
class HardwareAccess(Expression):
    """Hardware register access expression."""
    register: str
    type: Optional[DataType] = None

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_hardware_access(self)


# Statements

class Statement(ASTNode):
    """Base class for statements."""
    pass


@dataclass
class ExpressionStatement(Statement):
    """Expression statement."""
    expression: Expression

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_expression_statement(self)


@dataclass
class VariableDeclaration(Statement):
    """Variable declaration statement."""
    type: DataType
    name: str
    initializer: Optional[Expression] = None

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_variable_declaration(self)


@dataclass
class Assignment(Statement):
    """Assignment statement."""
    target: Expression
    value: Expression

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_assignment(self)


@dataclass
class IfStatement(Statement):
    """If statement."""
    condition: Expression
    then_branch: List[Statement]
    else_branch: Optional[List[Statement]] = None

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_if_statement(self)


@dataclass
class WhileStatement(Statement):
    """While loop statement."""
    condition: Expression
    body: List[Statement]

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_while_statement(self)


@dataclass
class ForStatement(Statement):
    """For loop statement."""
    initializer: Optional[Statement]
    condition: Optional[Expression]
    increment: Optional[Expression]
    body: List[Statement]

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_for_statement(self)


@dataclass 
class SwitchStatement(Statement):
    """Switch statement."""
    expression: Expression
    cases: List['SwitchCase']
    default_case: Optional[List[Statement]] = None

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_switch_statement(self)


@dataclass
class SwitchCase:
    """Switch case."""
    value: Expression  # The case value to match
    body: List[Statement]  # Statements to execute for this case


@dataclass
class BreakStatement(Statement):
    """Break statement."""
    
    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_break_statement(self)


@dataclass
class ContinueStatement(Statement):
    """Continue statement."""
    
    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_continue_statement(self)


@dataclass
class ReturnStatement(Statement):
    """Return statement."""
    value: Optional[Expression] = None

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_return_statement(self)


@dataclass
class BlockStatement(Statement):
    """Block statement (compound statement)."""
    statements: List[Statement]

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_block_statement(self)


# Declarations

class Declaration(ASTNode):
    """Base class for declarations."""
    pass


@dataclass
class StructDeclaration(Declaration):
    """Struct declaration."""
    name: str
    fields: List['StructField']

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_struct_declaration(self)


@dataclass
class StructField:
    """Struct field definition."""
    type: DataType
    name: str


@dataclass
class FunctionDeclaration(Declaration):
    """Function declaration."""
    return_type: DataType
    name: str
    parameters: List['Parameter']
    body: List[Statement]
    is_interrupt: bool = False

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_function_declaration(self)


@dataclass
class Parameter:
    """Function parameter."""
    type: DataType
    name: str
    default_value: Optional['Expression'] = None


# Program

@dataclass
class Program(ASTNode):
    """Root AST node representing a complete program."""
    declarations: List[Declaration]

    def __post_init__(self):
        super().__init__()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_program(self)

    @property
    def functions(self) -> List[FunctionDeclaration]:
        """Get all function declarations."""
        return [decl for decl in self.declarations if isinstance(decl, FunctionDeclaration)]

    @property
    def structs(self) -> List[StructDeclaration]:
        """Get all struct declarations."""
        return [decl for decl in self.declarations if isinstance(decl, StructDeclaration)]


# Visitor Pattern

class ASTVisitor(ABC):
    """Visitor interface for AST traversal."""

    def visit_program(self, node: Program) -> Any:
        """Visit a program node."""
        for decl in node.declarations:
            decl.accept(self)

    def visit_struct_declaration(self, node: StructDeclaration) -> Any:
        """Visit a struct declaration."""
        pass

    def visit_function_declaration(self, node: FunctionDeclaration) -> Any:
        """Visit a function declaration."""
        for param in node.parameters:
            pass  # Parameters don't need visiting as they're just type/name
        for stmt in node.body:
            stmt.accept(self)

    def visit_variable_declaration(self, node: VariableDeclaration) -> Any:
        """Visit a variable declaration."""
        if node.initializer:
            node.initializer.accept(self)

    def visit_assignment(self, node: Assignment) -> Any:
        """Visit an assignment."""
        node.target.accept(self)
        node.value.accept(self)

    def visit_if_statement(self, node: IfStatement) -> Any:
        """Visit an if statement."""
        node.condition.accept(self)
        for stmt in node.then_branch:
            stmt.accept(self)
        if node.else_branch:
            for stmt in node.else_branch:
                stmt.accept(self)

    def visit_while_statement(self, node: WhileStatement) -> Any:
        """Visit a while statement."""
        node.condition.accept(self)
        for stmt in node.body:
            stmt.accept(self)

    def visit_for_statement(self, node: ForStatement) -> Any:
        """Visit a for statement."""
        if node.initializer:
            node.initializer.accept(self)
        if node.condition:
            node.condition.accept(self)
        if node.increment:
            node.increment.accept(self)
        for stmt in node.body:
            stmt.accept(self)

    def visit_switch_statement(self, node: SwitchStatement) -> Any:
        """Visit a switch statement."""
        node.expression.accept(self)
        for case in node.cases:
            case.value.accept(self)
            for stmt in case.body:
                stmt.accept(self)
        if node.default_case:
            for stmt in node.default_case:
                stmt.accept(self)

    def visit_break_statement(self, node: BreakStatement) -> Any:
        """Visit a break statement."""
        pass

    def visit_continue_statement(self, node: ContinueStatement) -> Any:
        """Visit a continue statement."""
        pass

    def visit_return_statement(self, node: ReturnStatement) -> Any:
        """Visit a return statement."""
        if node.value:
            node.value.accept(self)

    def visit_expression_statement(self, node: ExpressionStatement) -> Any:
        """Visit an expression statement."""
        node.expression.accept(self)

    def visit_block_statement(self, node: BlockStatement) -> Any:
        """Visit a block statement."""
        for stmt in node.statements:
            stmt.accept(self)

    def visit_literal(self, node: Literal) -> Any:
        """Visit a literal."""
        pass

    def visit_variable(self, node: Variable) -> Any:
        """Visit a variable reference."""
        pass

    def visit_binary_op(self, node: BinaryOp) -> Any:
        """Visit a binary operation."""
        node.left.accept(self)
        node.right.accept(self)

    def visit_unary_op(self, node: UnaryOp) -> Any:
        """Visit a unary operation."""
        node.operand.accept(self)

    def visit_ternary_op(self, node: TernaryOp) -> Any:
        """Visit a ternary operation."""
        node.condition.accept(self)
        node.then_expr.accept(self)
        node.else_expr.accept(self)

    def visit_function_call(self, node: FunctionCall) -> Any:
        """Visit a function call."""
        for arg in node.arguments:
            arg.accept(self)

    def visit_member_access(self, node: MemberAccess) -> Any:
        """Visit a member access."""
        node.object.accept(self)

    def visit_array_access(self, node: ArrayAccess) -> Any:
        """Visit an array access."""
        node.array.accept(self)
        node.index.accept(self)

    def visit_hardware_access(self, node: HardwareAccess) -> Any:
        """Visit a hardware access."""
        pass
