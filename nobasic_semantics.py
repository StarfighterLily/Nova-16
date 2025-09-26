#!/usr/bin/env python3
"""
NoBASIC Semantic Analyzer
Performs type checking and symbol resolution.
"""

from typing import Dict, Set, List
from nobasic_utils import (
    Program, Statement, Expression, VariableExpr, ArrayAccessExpr,
    AssignmentStmt, DimStmt, InputStmt, IfStmt, ForStmt, WhileStmt, DoLoopStmt, DispStmt,
    BreakStmt, ContinueStmt, ArrayLiteralExpr, TryCatchStmt, StructStmt, StructField, StructFieldStmt
)
from nobasic_errors import SemanticError


class SymbolTable:
    """Symbol table for variables and their types."""

    def __init__(self):
        self.variables: Dict[str, str] = {}  # name -> type
        self.arrays: Dict[str, str] = {}     # name -> type
        self.strings: Dict[str, str] = {}    # name -> type

    def declare_variable(self, name: str, var_type: str = "integer"):
        """Declare a variable."""
        if name in self.variables:
            raise SemanticError(f"Variable '{name}' already declared")
        self.variables[name] = var_type

    def declare_array(self, name: str, var_type: str = "integer"):
        """Declare an array."""
        if name in self.arrays:
            raise SemanticError(f"Array '{name}' already declared")
        self.arrays[name] = var_type

    def declare_string(self, name: str):
        """Declare a string variable."""
        if name in self.strings:
            raise SemanticError(f"String '{name}' already declared")
        self.strings[name] = "string"

    def is_variable(self, name: str) -> bool:
        """Check if name is a declared variable."""
        return name in self.variables

    def is_array(self, name: str) -> bool:
        """Check if name is a declared array."""
        return name in self.arrays

    def is_string(self, name: str) -> bool:
        """Check if name is a declared string."""
        return name in self.strings

    def get_type(self, name: str) -> str:
        """Get the type of a symbol."""
        if name in self.variables:
            return self.variables[name]
        elif name in self.arrays:
            return self.arrays[name]
        elif name in self.strings:
            return self.strings[name]
        else:
            raise SemanticError(f"Undefined symbol '{name}'")


class SemanticAnalyzer:
    """Semantic analyzer for NoBASIC."""

    def __init__(self):
        self.symbol_table = SymbolTable()
        self.errors: List[SemanticError] = []
        self.loop_depth = 0

    def analyze(self, program: Program):
        """
        Analyze the program for semantic errors.

        Args:
            program: The AST program node

        Raises:
            SemanticError: If semantic errors are found
        """
        self.errors = []
        self._analyze_program(program)

        if self.errors:
            error_msg = f"Semantic analysis found {len(self.errors)} errors:\n"
            for error in self.errors:
                error_msg += f"  {error}\n"
            raise SemanticError(error_msg.strip())

    def _analyze_program(self, program: Program):
        """Analyze the program."""
        # Pre-declare standard variables
        for var in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            self.symbol_table.declare_variable(var)

        # Pre-declare boolean constants
        self.symbol_table.declare_variable('TRUE')
        self.symbol_table.declare_variable('FALSE')

        # Pre-declare color constants
        colors = {
            'BLACK': 0, 'WHITE': 15, 'RED': 1, 'GREEN': 2, 'BLUE': 4,
            'YELLOW': 3, 'MAGENTA': 5, 'CYAN': 6, 'ORANGE': 9, 'PURPLE': 13,
            'LIME': 10, 'PINK': 12, 'TEAL': 14, 'BROWN': 8, 'LIGHTBLUE': 11,
            'LIGHTGREEN': 10, 'LIGHTRED': 9
        }
        for color, value in colors.items():
            self.symbol_table.declare_variable(color)

        # Pre-declare string variables
        for i in range(1, 10):
            self.symbol_table.declare_string(f"Str{i}")

        # Pre-declare arrays L1-L6
        for i in range(1, 7):
            self.symbol_table.declare_array(f"L{i}")

        # Analyze statements
        for stmt in program.statements:
            self._analyze_statement(stmt)

    def _analyze_statement(self, stmt: Statement):
        """Analyze a statement."""
        try:
            if isinstance(stmt, AssignmentStmt):
                self._analyze_assignment(stmt)
            elif isinstance(stmt, DimStmt):
                self._analyze_dim(stmt)
            elif isinstance(stmt, InputStmt):
                self._analyze_input(stmt)
            elif isinstance(stmt, TryCatchStmt):
                self._analyze_try_catch(stmt)
            elif isinstance(stmt, StructStmt):
                self._analyze_struct(stmt)
            elif isinstance(stmt, IfStmt):
                self._analyze_if(stmt)
            elif isinstance(stmt, ForStmt):
                self._analyze_for(stmt)
            elif isinstance(stmt, WhileStmt):
                self._analyze_while(stmt)
            elif isinstance(stmt, DoLoopStmt):
                self._analyze_do_loop(stmt)
            elif isinstance(stmt, DispStmt):
                self._analyze_disp(stmt)
            elif isinstance(stmt, BreakStmt):
                self._analyze_break(stmt)
            elif isinstance(stmt, ContinueStmt):
                self._analyze_continue(stmt)
            # Add other statement types as needed
        except SemanticError as e:
            self.errors.append(e)

    def _analyze_assignment(self, stmt: AssignmentStmt):
        """Analyze assignment statement."""
        # Declare variable if target is VariableExpr and not already declared
        if isinstance(stmt.target, VariableExpr):
            if not (self.symbol_table.is_variable(stmt.target.name) or
                    self.symbol_table.is_string(stmt.target.name) or
                    self.symbol_table.is_array(stmt.target.name)):
                # Check if expression is an array literal
                if isinstance(stmt.expression, ArrayLiteralExpr):
                    self.symbol_table.declare_array(stmt.target.name)
                else:
                    self.symbol_table.declare_variable(stmt.target.name)
            elif isinstance(stmt.expression, ArrayLiteralExpr) and self.symbol_table.is_variable(stmt.target.name):
                # Re-declare as array if assigning array literal to a variable
                # Remove from variables and add to arrays
                if stmt.target.name in self.symbol_table.variables:
                    del self.symbol_table.variables[stmt.target.name]
                if not self.symbol_table.is_array(stmt.target.name):
                    self.symbol_table.declare_array(stmt.target.name)
            # Note: Assignment to already declared arrays is allowed
        else:
            # Analyze complex targets (like array access)
            self._analyze_expression(stmt.target)
        
        # Analyze the expression
        self._analyze_expression(stmt.expression)

    def _analyze_dim(self, stmt: DimStmt):
        """Analyze DIM statement."""
        # Declare array if not already declared
        if self.symbol_table.is_array(stmt.array_name):
            raise SemanticError(f"Array '{stmt.array_name}' already declared")
        self.symbol_table.declare_array(stmt.array_name)

        # Analyze the size expression
        self._analyze_expression(stmt.size)

    def _analyze_input(self, stmt: InputStmt):
        """Analyze INPUT statement."""
        # Auto-declare the variable if not already declared
        if not self.symbol_table.is_variable(stmt.variable):
            self.symbol_table.declare_variable(stmt.variable)

    def _analyze_try_catch(self, stmt: TryCatchStmt):
        """Analyze TRY/CATCH statement."""
        for s in stmt.try_stmts:
            self._analyze_statement(s)
        for s in stmt.catch_stmts:
            self._analyze_statement(s)

    def _analyze_struct(self, stmt: StructStmt):
        """Analyze STRUCT statement."""
        # For now, just validate field names
        field_names = set()
        for field in stmt.fields:
            if field.name in field_names:
                raise SemanticError(f"Duplicate field name '{field.name}' in struct '{stmt.name}'")
            field_names.add(field.name)
        # TODO: Store struct definitions for later validation

    def _analyze_if(self, stmt: IfStmt):
        """Analyze if statement."""
        self._analyze_expression(stmt.condition)
        for s in stmt.then_stmts:
            self._analyze_statement(s)
        for elif_clause in stmt.elif_stmts:
            self._analyze_expression(elif_clause.condition)
            for s in elif_clause.statements:
                self._analyze_statement(s)
        for s in stmt.else_stmts:
            self._analyze_statement(s)

    def _analyze_for(self, stmt: ForStmt):
        """Analyze for loop."""
        # Auto-declare variable if not already declared
        if not self.symbol_table.is_variable(stmt.variable):
            self.symbol_table.declare_variable(stmt.variable)

        self._analyze_expression(stmt.start)
        self._analyze_expression(stmt.end)
        if stmt.step:
            self._analyze_expression(stmt.step)
        
        self.loop_depth += 1
        for s in stmt.statements:
            self._analyze_statement(s)
        self.loop_depth -= 1

    def _analyze_while(self, stmt: WhileStmt):
        """Analyze while loop."""
        self._analyze_expression(stmt.condition)
        
        self.loop_depth += 1
        for s in stmt.statements:
            self._analyze_statement(s)
        self.loop_depth -= 1

    def _analyze_do_loop(self, stmt: DoLoopStmt):
        """Analyze do loop."""
        self.loop_depth += 1
        for s in stmt.statements:
            self._analyze_statement(s)
        self.loop_depth -= 1
        
        if stmt.condition:
            self._analyze_expression(stmt.condition)

    def _analyze_disp(self, stmt: DispStmt):
        """Analyze disp statement."""
        for expr in stmt.expressions:
            self._analyze_expression(expr)

    def _analyze_break(self, stmt: BreakStmt):
        """Analyze break statement."""
        if self.loop_depth == 0:
            raise SemanticError("Break statement must be inside a loop")

    def _analyze_continue(self, stmt: ContinueStmt):
        """Analyze continue statement."""
        if self.loop_depth == 0:
            raise SemanticError("Continue statement must be inside a loop")

    def _analyze_expression(self, expr: Expression):
        """Analyze an expression."""
        if isinstance(expr, VariableExpr):
            if not (self.symbol_table.is_variable(expr.name) or
                    self.symbol_table.is_string(expr.name)):
                raise SemanticError(f"Undefined variable '{expr.name}'")
        elif isinstance(expr, ArrayAccessExpr):
            if not self.symbol_table.is_array(expr.array):
                raise SemanticError(f"Undefined array '{expr.array}'")
            self._analyze_expression(expr.index)
        elif isinstance(expr, ArrayLiteralExpr):
            for element in expr.elements:
                self._analyze_expression(element)
        # Add more expression types as needed