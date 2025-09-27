"""
NoBASIC Semantic Analyzer
"""

from typing import Dict, Set
from ..utils.error import SemanticError
from ..parser.ast import (
    Program, Statement, Expression, AssignmentStmt, IfStmt, ForStmt,
    WhileStmt, RepeatStmt, VariableExpr, ListAccessExpr, MatrixAccessExpr,
    FunctionCallExpr, LiteralExpr, BinaryExpr, UnaryExpr, GroupingExpr,
    PxlOnStmt, PxlOffStmt, LineStmt, CircleStmt, TextStmt,
    SetLayerStmt, SpriteOnStmt, SpriteOffStmt, PlayToneStmt,
    PlayWaveStmt, SetChannelStmt, InputStmt, DispStmt, DataType
)


class SymbolTable:
    """Symbol table for variables."""

    def __init__(self):
        self.variables: Dict[str, DataType] = {}
        self.lists: Set[str] = set()
        self.matrices: Set[str] = set()

    def define_variable(self, name: str, data_type: DataType):
        """Define a variable."""
        self.variables[name] = data_type

    def get_variable_type(self, name: str) -> DataType:
        """Get the type of a variable."""
        return self.variables.get(name, DataType.NUMBER)  # Default to NUMBER

    def is_list(self, name: str) -> bool:
        """Check if name is a list."""
        return name in self.lists

    def is_matrix(self, name: str) -> bool:
        """Check if name is a matrix."""
        return name in self.matrices


class SemanticAnalyzer:
    """Semantic analyzer for NoBASIC."""

    def __init__(self):
        self.symbol_table = SymbolTable()
        self.filename = "<stdin>"

    def analyze(self, program: Program, filename: str = "<stdin>"):
        """
        Analyze the program semantically.

        Args:
            program: The AST to analyze
            filename: Source filename for error reporting

        Raises:
            SemanticError: If semantic analysis fails
        """
        self.filename = filename

        # Initialize some built-in variables
        for i in range(1, 7):  # L1 to L6
            self.symbol_table.lists.add(f"L{i}")
        for name in ["MatA", "MatB", "MatC"]:  # Some matrices
            self.symbol_table.matrices.add(name)

        for stmt in program.statements:
            self.analyze_statement(stmt)

    def analyze_statement(self, stmt: Statement):
        """Analyze a statement."""
        if isinstance(stmt, AssignmentStmt):
            self.analyze_assignment(stmt)
        elif isinstance(stmt, IfStmt):
            self.analyze_if(stmt)
        elif isinstance(stmt, ForStmt):
            self.analyze_for(stmt)
        elif isinstance(stmt, WhileStmt):
            self.analyze_while(stmt)
        elif isinstance(stmt, RepeatStmt):
            self.analyze_repeat(stmt)
        elif isinstance(stmt, (PxlOnStmt, PxlOffStmt, LineStmt, CircleStmt, TextStmt,
                              SetLayerStmt, SpriteOnStmt, SpriteOffStmt, PlayToneStmt,
                              PlayWaveStmt, SetChannelStmt, InputStmt, DispStmt)):
            # These statements have expressions that need checking
            self.analyze_graphics_sound_statement(stmt)
        # Other statements don't need special analysis

    def analyze_assignment(self, stmt: AssignmentStmt):
        """Analyze an assignment statement."""
        # Check the expression
        expr_type = self.analyze_expression(stmt.expression)
        # Variables are dynamically typed, so just define it
        self.symbol_table.define_variable(stmt.variable, expr_type)

    def analyze_if(self, stmt: IfStmt):
        """Analyze an if statement."""
        self.analyze_expression(stmt.condition)
        for s in stmt.then_branch:
            self.analyze_statement(s)
        if stmt.else_branch:
            for s in stmt.else_branch:
                self.analyze_statement(s)

    def analyze_for(self, stmt: ForStmt):
        """Analyze a for statement."""
        self.symbol_table.define_variable(stmt.variable, DataType.NUMBER)
        self.analyze_expression(stmt.start)
        self.analyze_expression(stmt.end)
        if stmt.step:
            self.analyze_expression(stmt.step)
        for s in stmt.body:
            self.analyze_statement(s)

    def analyze_while(self, stmt: WhileStmt):
        """Analyze a while statement."""
        self.analyze_expression(stmt.condition)
        for s in stmt.body:
            self.analyze_statement(s)

    def analyze_repeat(self, stmt: RepeatStmt):
        """Analyze a repeat statement."""
        for s in stmt.body:
            self.analyze_statement(s)
        self.analyze_expression(stmt.condition)

    def analyze_graphics_sound_statement(self, stmt):
        """Analyze graphics/sound statements with expressions."""
        # Just analyze all expressions in the statement
        for attr_name in dir(stmt):
            if not attr_name.startswith('_'):
                attr = getattr(stmt, attr_name)
                if isinstance(attr, Expression):
                    self.analyze_expression(attr)
                elif isinstance(attr, list):
                    for item in attr:
                        if isinstance(item, Expression):
                            self.analyze_expression(item)

    def analyze_expression(self, expr: Expression) -> DataType:
        """Analyze an expression and return its type."""
        if isinstance(expr, LiteralExpr):
            return expr.data_type
        elif isinstance(expr, VariableExpr):
            if self.symbol_table.is_list(expr.name):
                return DataType.LIST
            elif self.symbol_table.is_matrix(expr.name):
                return DataType.MATRIX
            else:
                return self.symbol_table.get_variable_type(expr.name)
        elif isinstance(expr, ListAccessExpr):
            if not self.symbol_table.is_list(expr.list_name):
                raise SemanticError(f"Undefined list: {expr.list_name}", self.filename)
            index_type = self.analyze_expression(expr.index)
            if index_type != DataType.NUMBER:
                raise SemanticError(f"List index must be numeric", self.filename)
            return DataType.NUMBER
        elif isinstance(expr, MatrixAccessExpr):
            if not self.symbol_table.is_matrix(expr.matrix_name):
                raise SemanticError(f"Undefined matrix: {expr.matrix_name}", self.filename)
            row_type = self.analyze_expression(expr.row)
            col_type = self.analyze_expression(expr.col)
            if row_type != DataType.NUMBER or col_type != DataType.NUMBER:
                raise SemanticError(f"Matrix indices must be numeric", self.filename)
            return DataType.NUMBER
        elif isinstance(expr, BinaryExpr):
            left_type = self.analyze_expression(expr.left)
            right_type = self.analyze_expression(expr.right)
            # Basic type checking for arithmetic
            if expr.operator in ['+', '-', '*', '/', '^']:
                if expr.operator == '+' and left_type == DataType.STRING and right_type == DataType.STRING:
                    # Allow string concatenation with +
                    return DataType.STRING
                elif left_type == DataType.STRING or right_type == DataType.STRING:
                    raise SemanticError(f"Cannot perform arithmetic on strings", self.filename)
                return DataType.NUMBER
            elif expr.operator in ['=', '<>', '<', '>', '<=', '>=']:
                return DataType.NUMBER  # Comparison results
            elif expr.operator in ['and', 'or']:
                return DataType.NUMBER  # Logical results
            return DataType.NUMBER
        elif isinstance(expr, UnaryExpr):
            return self.analyze_expression(expr.expression)
        elif isinstance(expr, FunctionCallExpr):
            # Check if function is defined
            func_name = expr.name.upper()
            if not self.is_builtin_function(func_name):
                raise SemanticError(f"Undefined function '{expr.name}'", self.filename)
            # Check argument count
            expected_args = self.get_function_arg_count(func_name)
            if expected_args is not None and len(expr.arguments) != expected_args:
                raise SemanticError(f"Wrong number of arguments for function '{expr.name}': expected {expected_args}, got {len(expr.arguments)}", self.filename)
            # Check arguments
            for arg in expr.arguments:
                self.analyze_expression(arg)
            # Built-in functions return numbers unless specified
            return DataType.NUMBER
        elif isinstance(expr, GroupingExpr):
            return self.analyze_expression(expr.expression)
        else:
            return DataType.NUMBER  # Default

    def is_builtin_function(self, name: str) -> bool:
        """Check if a function name is a built-in function."""
        return name in [
            "SIN", "COS", "TAN", "SQRT", "ABS", "RND", "LEN", "LENGTH",
            "MIN", "MAX", "LOG", "LN", "EXP", "POW", "INT", "ROUND"
        ]

    def get_function_arg_count(self, name: str) -> int:
        """Get the expected number of arguments for a built-in function."""
        arg_counts = {
            "SIN": 1, "COS": 1, "TAN": 1, "SQRT": 1, "ABS": 1, "RND": 0,
            "LEN": 1, "LENGTH": 1, "INT": 1, "ROUND": 1,
            "MIN": 2, "MAX": 2
        }
        return arg_counts.get(name)