"""
NoBASIC Semantic Analyzer
"""

from typing import Dict, Set
from ..utils.error import SemanticError
from ..parser.ast import (
    Program, Statement, Expression, AssignmentStmt, IfStmt, ForStmt,
    WhileStmt, RepeatStmt, GotoStmt, LabelStmt, StructDeclarationStmt, FunctionCallStmt, VariableExpr, ListAccessExpr, MatrixAccessExpr,
    MemberAccessExpr, FunctionCallExpr, LiteralExpr, BinaryExpr, UnaryExpr, GroupingExpr,
    PxlOnStmt, PxlOffStmt, LineStmt, CircleStmt, TextStmt,
    SetLayerStmt, SpriteOnStmt, SpriteOffStmt, PlayToneStmt,
    PlayWaveStmt, SetChannelStmt, InputStmt, DispStmt, DataType, StructType
)


class SymbolTable:
    """Symbol table for variables."""

    def __init__(self):
        self.variables: Dict[str, DataType] = {}
        self.lists: Set[str] = set()
        self.matrices: Set[str] = set()
        self.labels: Set[str] = set()
        self.structs: Dict[str, StructType] = {}
        self.struct_instances: Dict[str, str] = {}  # var_name -> struct_name

    def define_variable(self, name: str, data_type: DataType):
        """Define a variable."""
        self.variables[name] = data_type

    def get_variable_type(self, name: str) -> DataType:
        """Get the type of a variable."""
        return self.variables.get(name, DataType.NUMBER)  # Default to NUMBER
    
    def define_struct(self, name: str, fields: list):
        """Define a struct type."""
        self.structs[name] = StructType(name, fields)
    
    def get_struct(self, name: str) -> StructType:
        """Get a struct type definition."""
        return self.structs.get(name)
    
    def is_struct(self, name: str) -> bool:
        """Check if name is a struct type."""
        return name in self.structs
    
    def define_struct_instance(self, var_name: str, struct_name: str):
        """Define a struct instance variable."""
        self.struct_instances[var_name] = struct_name
    
    def get_struct_instance_type(self, var_name: str) -> str:
        """Get the struct type name for a variable."""
        return self.struct_instances.get(var_name)

    def is_list(self, name: str) -> bool:
        """Check if name is a list."""
        return name in self.lists

    def is_matrix(self, name: str) -> bool:
        """Check if name is a matrix."""
        return name in self.matrices

    def is_defined(self, name: str) -> bool:
        """Check if a name is defined (variable, list, or matrix)."""
        return name in self.variables or name in self.lists or name in self.matrices

    def get_type(self, name: str) -> DataType:
        """Get the type of a defined name."""
        if name in self.variables:
            return self.variables[name]
        elif name in self.lists:
            return DataType.LIST
        elif name in self.matrices:
            return DataType.MATRIX
        else:
            raise KeyError(f"Undefined name: {name}")

    def define_label(self, name: str):
        """Define a label."""
        if name in self.labels:
            raise SemanticError("Label already defined", 0, 0)  # Line/column not available
        self.labels.add(name)

    def is_label_defined(self, name: str) -> bool:
        """Check if a label is defined."""
        return name in self.labels


class SemanticAnalyzer:
    """Semantic analyzer for NoBASIC."""

    def __init__(self):
        self.symbol_table = SymbolTable()
        self.filename = "<stdin>"
        self.pending_gotos = []  # List of (label_name, line, column) tuples

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

        # Check all pending GOTOs
        for label_name, line, column in self.pending_gotos:
            if not self.symbol_table.is_label_defined(label_name):
                raise SemanticError(f"Undefined label '{label_name}'", line, column)

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
        elif isinstance(stmt, GotoStmt):
            self.analyze_goto(stmt)
        elif isinstance(stmt, LabelStmt):
            self.analyze_label(stmt)
        elif isinstance(stmt, StructDeclarationStmt):
            self.analyze_struct_declaration(stmt)
        elif isinstance(stmt, FunctionCallStmt):
            self.analyze_function_call_statement(stmt)
        elif isinstance(stmt, (PxlOnStmt, PxlOffStmt, LineStmt, CircleStmt, TextStmt,
                              SetLayerStmt, SpriteOnStmt, SpriteOffStmt, PlayToneStmt,
                              PlayWaveStmt, SetChannelStmt, InputStmt, DispStmt)):
            # These statements have expressions that need checking
            self.analyze_graphics_sound_statement(stmt)
        # Other statements don't need special analysis

    def analyze_function_call_statement(self, stmt: FunctionCallStmt):
        """Analyze a function call statement."""
        self.analyze_expression(stmt.function_call)

    def analyze_assignment(self, stmt: AssignmentStmt):
        """Analyze an assignment statement."""
        # Check the expression
        expr_type = self.analyze_expression(stmt.expression)
        # Analyze the left-hand side (must be assignable)
        self.analyze_assignable_expression(stmt.variable, expr_type)

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

    def analyze_goto(self, stmt: GotoStmt):
        """Analyze a goto statement."""
        # Defer checking until all labels are collected
        self.pending_gotos.append((stmt.label, 0, 0))

    def analyze_label(self, stmt: LabelStmt):
        """Analyze a label statement."""
        self.symbol_table.define_label(stmt.label)

    def analyze_struct_declaration(self, stmt: StructDeclarationStmt):
        """Analyze a struct declaration."""
        # Check if struct name is already defined
        if self.symbol_table.is_struct(stmt.name):
            raise SemanticError(f"Struct '{stmt.name}' is already defined", 0, 0)
        
        # Check for duplicate field names
        field_set = set()
        for field in stmt.fields:
            if field in field_set:
                raise SemanticError(f"Duplicate field '{field}' in struct '{stmt.name}'", 0, 0)
            field_set.add(field)
        
        # Define the struct
        self.symbol_table.define_struct(stmt.name, stmt.fields)

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
            elif self.symbol_table.is_defined(expr.name):
                return self.symbol_table.get_variable_type(expr.name)
            else:
                # Undefined variables can be any type in BASIC
                return DataType.NUMBER  # Default, but allow type coercion
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
        elif isinstance(expr, MemberAccessExpr):
            # Analyze struct member access
            object_type = self.analyze_expression(expr.object)
            
            # Check if object is a struct instance
            if isinstance(expr.object, VariableExpr):
                var_name = expr.object.name
                struct_name = self.symbol_table.get_struct_instance_type(var_name)
                
                if not struct_name:
                    # Auto-infer struct type if only one struct is defined
                    if len(self.symbol_table.structs) == 1:
                        struct_name = list(self.symbol_table.structs.keys())[0]
                        self.symbol_table.define_struct_instance(var_name, struct_name)
                    else:
                        raise SemanticError(f"Variable '{var_name}' is not a struct instance", self.filename)
                
                if struct_name:
                    struct_def = self.symbol_table.get_struct(struct_name)
                    if struct_def and expr.member in struct_def.fields:
                        return DataType.NUMBER  # All struct fields are 16-bit numbers
                    else:
                        raise SemanticError(f"Struct '{struct_name}' has no field '{expr.member}'", self.filename)
                else:
                    raise SemanticError(f"Variable '{var_name}' is not a struct instance", self.filename)
            else:
                raise SemanticError(f"Cannot access member of non-struct expression", self.filename)
        elif isinstance(expr, BinaryExpr):
            left_type = self.analyze_expression(expr.left)
            right_type = self.analyze_expression(expr.right)
            # Basic type checking for arithmetic
            if expr.operator in ['+', '-', '*', '/', '^']:
                if expr.operator == '+' and (left_type == DataType.STRING or right_type == DataType.STRING):
                    # Allow string concatenation with + (TI-BASIC style)
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
            # Check argument types
            expected_types = self.get_function_arg_types(func_name)
            for i, arg in enumerate(expr.arguments):
                arg_type = self.analyze_expression(arg)
                if i < len(expected_types) and expected_types[i] is not None:
                    expected_type = expected_types[i]
                    # Allow type coercion in BASIC: NUMBER can be used where STRING is expected
                    if arg_type != expected_type and not (arg_type == DataType.NUMBER and expected_type == DataType.STRING):
                        raise SemanticError(f"Invalid argument type for function '{expr.name}': argument {i+1} expected {expected_types[i].value}, got {arg_type.value}", self.filename)
            # Built-in functions return numbers unless specified
            return self.get_function_return_type(func_name)
        elif isinstance(expr, GroupingExpr):
            return self.analyze_expression(expr.expression)
        else:
            return DataType.NUMBER  # Default

    def is_builtin_function(self, name: str) -> bool:
        """Check if a function name is a built-in function."""
        return name in [
            # Original math functions
            "SIN", "COS", "TAN", "SQRT", "ABS", "RAND", "RND", "LEN", "LENGTH",
            "MIN", "MAX", "LOG", "LN", "EXP", "POW", "INT", "ROUND",
            # Extended math functions
            "ATAN", "ASIN", "ACOS", "DEG", "RAD", "FLOOR", "CEIL", "TRUNC", "FRAC", "INTGR", "POWR",
            # String functions
            "STRLEN", "STRCPY", "STRCAT", "STRCMP", "STRUPR", "STRLWR", "STRREV",
            "STRFIND", "STRFINDI", "STREXT", "STREXTI", "SUB",
            # Bit manipulation functions
            "BTST", "BSET", "BCLR", "BFLIP", "CLZ", "CTZ", "POPCNT",
            # Shift and rotate functions
            "SHL", "SHR", "SAL", "SAR", "ROL", "ROR", "RCL", "RCR",
            # Bitwise logical functions
            "BAND", "BOR", "BXOR", "BNOT",
            # Memory functions
            "MEMCPY", "MEMSET", "MEMTEST", "MEMMOVE", "MEMCMP", "MEMSWAP",
            # Enhanced arithmetic
            "ADC", "SBC", "MULH", "DIVH", "SWAP", "XCHNG", "MOVZ", "MOVNZ", "LEA",
            # Type conversion
            "ITOB", "BTOI", "ITOS", "STOI", "STR",
            # Graphics functions
            "CLRDRAW", "SETLAYER", "PXLON", "PXLOFF", "LINE", "CIRCLE", "TEXT", "RECT",
            # List/Array functions
            "SUM", "MEAN", "DIM",
            # I/O functions
            "GETKEY", "PAUSE"
        ]

    def get_function_arg_count(self, name: str) -> int:
        """Get the expected number of arguments for a built-in function."""
        arg_counts = {
            # Original functions
            "SIN": 1, "COS": 1, "TAN": 1, "SQRT": 1, "ABS": 1, "RAND": 0, "RND": 0,
            "LEN": 1, "LENGTH": 1, "INT": 1, "ROUND": 1,
            "MIN": 2, "MAX": 2,
            # Extended math functions
            "ATAN": 1, "ASIN": 1, "ACOS": 1, "DEG": 1, "RAD": 1,
            "FLOOR": 1, "CEIL": 1, "ROUND": 1, "TRUNC": 1, "FRAC": 1, "INTGR": 1,
            "POWR": 2, "LOG": 1, "EXP": 1,
            # String functions
            "STRLEN": 1, "STRCPY": 2, "STRCAT": 2, "STRCMP": 3,
            "STRUPR": 1, "STRLWR": 1, "STRREV": 1,
            "STRFIND": 2, "STRFINDI": 2, "STREXT": 4, "STREXTI": 4, "SUB": 3,
            # Bit manipulation functions
            "BTST": 2, "BSET": 2, "BCLR": 2, "BFLIP": 2,
            "CLZ": 1, "CTZ": 1, "POPCNT": 1,
            # Shift and rotate functions
            "SHL": 2, "SHR": 2, "SAL": 2, "SAR": 2,
            "ROL": 2, "ROR": 2, "RCL": 2, "RCR": 2,
            # Bitwise logical functions
            "BAND": 2, "BOR": 2, "BXOR": 2, "BNOT": 1,
            # Memory functions
            "MEMCPY": 3, "MEMSET": 3, "MEMTEST": 3, "MEMMOVE": 3, "MEMCMP": 4, "MEMSWAP": 3,
            # Enhanced arithmetic
            "ADC": 3, "SBC": 3, "MULH": 3, "DIVH": 3,
            "SWAP": 1, "XCHNG": 2, "MOVZ": 2, "MOVNZ": 2, "LEA": 2,
            # Type conversion
            "ITOB": 2, "BTOI": 2, "ITOS": 2, "STOI": 2, "STR": 1,
            # Graphics functions
            "CLRDRAW": 0, "SETLAYER": 1, "PXLON": 3, "PXLOFF": 2, "LINE": 5, "CIRCLE": 4, "TEXT": 4, "RECT": 5,
            # List/Array functions
            "SUM": 1, "MEAN": 1, "DIM": 1,
            # I/O functions
            "GETKEY": 0, "PAUSE": 0
        }
        return arg_counts.get(name)

    def get_function_arg_types(self, name: str) -> list:
        """Get the expected argument types for a built-in function."""
        # None means any type is accepted
        arg_types = {
            # Math functions that expect numbers
            "SIN": [DataType.NUMBER], "COS": [DataType.NUMBER], "TAN": [DataType.NUMBER], 
            "SQRT": [DataType.NUMBER], "ABS": [DataType.NUMBER], "RAND": [], "RND": [], "INT": [DataType.NUMBER], 
            "ROUND": [DataType.NUMBER], "ATAN": [DataType.NUMBER], "ASIN": [DataType.NUMBER], 
            "ACOS": [DataType.NUMBER], "DEG": [DataType.NUMBER], "RAD": [DataType.NUMBER],
            "FLOOR": [DataType.NUMBER], "CEIL": [DataType.NUMBER], "TRUNC": [DataType.NUMBER], 
            "FRAC": [DataType.NUMBER], "INTGR": [DataType.NUMBER], "LOG": [DataType.NUMBER], 
            "EXP": [DataType.NUMBER], "POWR": [DataType.NUMBER, DataType.NUMBER],
            "MIN": [DataType.NUMBER, DataType.NUMBER], "MAX": [DataType.NUMBER, DataType.NUMBER],
            # String functions
            "LEN": [DataType.STRING], "LENGTH": [DataType.STRING], "STRLEN": [DataType.STRING],
            "STRCPY": [DataType.STRING, DataType.STRING], "STRCAT": [DataType.STRING, DataType.STRING],
            "STRCMP": [DataType.STRING, DataType.STRING, DataType.NUMBER],
            "STRUPR": [DataType.STRING], "STRLWR": [DataType.STRING], "STRREV": [DataType.STRING],
            "STRFIND": [DataType.STRING, DataType.STRING], "STRFINDI": [DataType.STRING, DataType.STRING],
            "STREXT": [DataType.STRING, DataType.NUMBER, DataType.NUMBER, DataType.STRING],
            "STREXTI": [DataType.STRING, DataType.NUMBER, DataType.NUMBER, DataType.STRING],
            "SUB": [DataType.STRING, DataType.NUMBER, DataType.NUMBER],
            # Functions with no type restrictions
            "RND": [], "BTST": [None, None], "BSET": [None, None], "BCLR": [None, None], 
            "BFLIP": [None, None], "CLZ": [None], "CTZ": [None], "POPCNT": [None],
            "SHL": [None, None], "SHR": [None, None], "SAL": [None, None], "SAR": [None, None],
            "ROL": [None, None], "ROR": [None, None], "RCL": [None, None], "RCR": [None, None],
            "BAND": [None, None], "BOR": [None, None], "BXOR": [None, None], "BNOT": [None],
            "MEMCPY": [None, None, None], "MEMSET": [None, None, None], "MEMTEST": [None, None, None], 
            "MEMMOVE": [None, None, None], "MEMCMP": [None, None, None, None], "MEMSWAP": [None, None, None],
            "ADC": [None, None, None], "SBC": [None, None, None], "MULH": [None, None, None], 
            "DIVH": [None, None, None], "SWAP": [None], "XCHNG": [None, None], "MOVZ": [None, None], 
            "MOVNZ": [None, None], "LEA": [None, None],
            "ITOB": [None, None], "BTOI": [None, None], "ITOS": [None, None], "STOI": [None, None], "STR": [DataType.NUMBER],
            # Graphics functions
            "CLRDRAW": [], "SETLAYER": [DataType.NUMBER], "PXLON": [DataType.NUMBER, DataType.NUMBER, DataType.NUMBER],
            "PXLOFF": [DataType.NUMBER, DataType.NUMBER], "LINE": [DataType.NUMBER, DataType.NUMBER, DataType.NUMBER, DataType.NUMBER, DataType.NUMBER],
            "CIRCLE": [DataType.NUMBER, DataType.NUMBER, DataType.NUMBER, DataType.NUMBER], "TEXT": [DataType.NUMBER, DataType.NUMBER, DataType.STRING, DataType.NUMBER],
            "RECT": [DataType.NUMBER, DataType.NUMBER, DataType.NUMBER, DataType.NUMBER, DataType.NUMBER],
            # List/Array functions
            "SUM": [DataType.LIST], "MEAN": [DataType.LIST], "DIM": [DataType.LIST],
            # I/O functions
            "GETKEY": [], "PAUSE": []
        }
        return arg_types.get(name, [])

    def get_function_return_type(self, name: str) -> DataType:
        """Get the return type for a built-in function."""
        return_types = {
            # String functions return strings
            "STRCPY": DataType.STRING, "STRCAT": DataType.STRING, "STRUPR": DataType.STRING, 
            "STRLWR": DataType.STRING, "STRREV": DataType.STRING, "STREXT": DataType.STRING, 
            "STREXTI": DataType.STRING, "SUB": DataType.STRING, "STR": DataType.STRING,
            # Most others return numbers
        }
        return return_types.get(name, DataType.NUMBER)

    def analyze_assignable_expression(self, expr: Expression, value_type: DataType):
        """Analyze an expression that can be assigned to (left-hand side of assignment)."""
        if isinstance(expr, VariableExpr):
            # Variables are dynamically typed
            self.symbol_table.define_variable(expr.name, value_type)
        elif isinstance(expr, MemberAccessExpr):
            # Struct member assignment
            if isinstance(expr.object, VariableExpr):
                var_name = expr.object.name
                struct_name = self.symbol_table.get_struct_instance_type(var_name)
                
                if not struct_name:
                    # Auto-infer struct type if only one struct is defined
                    if len(self.symbol_table.structs) == 1:
                        struct_name = list(self.symbol_table.structs.keys())[0]
                        self.symbol_table.define_struct_instance(var_name, struct_name)
                    else:
                        raise SemanticError(f"Variable '{var_name}' is not a struct instance", 0, 0)
                
                struct_def = self.symbol_table.get_struct(struct_name)
                if not struct_def or expr.member not in struct_def.fields:
                    raise SemanticError(f"Struct '{struct_name}' has no field '{expr.member}'", 0, 0)
                
                # Struct fields must be numbers
                if value_type != DataType.NUMBER:
                    raise SemanticError(f"Struct fields can only hold numeric values", 0, 0)
            else:
                raise SemanticError(f"Cannot assign to member of non-struct expression", 0, 0)
        elif isinstance(expr, ListAccessExpr):
            # Check that the list exists and index is valid
            list_name = expr.list_name
            if not self.symbol_table.is_defined(list_name):
                # Auto-define list
                self.symbol_table.lists.add(list_name)
            elif self.symbol_table.get_type(list_name) != DataType.LIST:
                raise SemanticError(f"'{list_name}' is not a list", expr.line, expr.column)
            # Check index expression
            index_type = self.analyze_expression(expr.index)
            if index_type != DataType.NUMBER:
                raise SemanticError("List index must be a number", expr.line, expr.column)
        elif isinstance(expr, MatrixAccessExpr):
            # Check that the matrix exists and indices are valid
            matrix_name = expr.matrix_name
            if not self.symbol_table.is_defined(matrix_name):
                # Auto-define matrix
                self.symbol_table.matrices.add(matrix_name)
            elif self.symbol_table.get_type(matrix_name) != DataType.MATRIX:
                raise SemanticError(f"'{matrix_name}' is not a matrix", expr.line, expr.column)
            # Check index expressions
            row_type = self.analyze_expression(expr.row)
            col_type = self.analyze_expression(expr.col)
            if row_type != DataType.NUMBER or col_type != DataType.NUMBER:
                raise SemanticError("Matrix indices must be numbers", expr.line, expr.column)
        else:
            raise SemanticError("Invalid assignment target", expr.line, expr.column)