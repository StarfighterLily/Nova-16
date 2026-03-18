"""
NoBASIC Semantic Analyzer
"""

from typing import Dict, Set, List, Optional
from ..utils.error import SemanticError
from ..parser.ast import (
    Program, Statement, Expression, AssignmentStmt, ExpressionStmt, IfStmt, ForStmt,
    WhileStmt, RepeatStmt, GotoStmt, LabelStmt, StructDeclarationStmt, VarDeclarationStmt,
    FunctionCallStmt, FunctionDefStmt, ReturnStmt, VariableExpr, ListAccessExpr, MatrixAccessExpr,
    MemberAccessExpr, FunctionCallExpr, LiteralExpr, BinaryExpr, UnaryExpr, GroupingExpr,
    PxlOnStmt, PxlOffStmt, LineStmt, CircleStmt, TextStmt,
    SRolStmt, SRotStmt, SShftStmt, SFlipStmt,
    SetLayerStmt, SpriteOnStmt, SpriteOffStmt, PlayToneStmt,
    PlayWaveStmt, SetChannelStmt, InputStmt, DispStmt, DataType, StructType, VarScope,
    SerOutStmt, SerInStmt, SerStatStmt, SerCtrlStmt
)


class Scope:
    """Represents a single scope level."""
    
    def __init__(self, is_global: bool = False):
        self.is_global = is_global
        self.variables: Dict[str, DataType] = {}
        self.explicit_declarations: Set[str] = set()  # Variables explicitly declared with GLOBAL/LOCAL
        
    def define_variable(self, name: str, data_type: DataType, explicit: bool = False):
        """Define a variable in this scope."""
        self.variables[name] = data_type
        if explicit:
            self.explicit_declarations.add(name)
    
    def has_variable(self, name: str) -> bool:
        """Check if variable exists in this scope."""
        return name in self.variables
    
    def get_variable_type(self, name: str) -> Optional[DataType]:
        """Get variable type if it exists in this scope."""
        return self.variables.get(name)


class SymbolTable:
    """Symbol table for variables with scope support."""

    def __init__(self):
        # Scope stack: [global_scope, local_scope1, local_scope2, ...]
        self.scopes: List[Scope] = [Scope(is_global=True)]
        self.lists: Set[str] = set()
        self.matrices: Set[str] = set()
        self.labels: Set[str] = set()
        self.structs: Dict[str, StructType] = {}
        self.struct_instances: Dict[str, str] = {}  # var_name -> struct_name
        # Backwards-compatible view of global variables for tests/diagnostics
        self.variables = self.scopes[0].variables

    def push_scope(self):
        """Enter a new local scope."""
        self.scopes.append(Scope(is_global=False))
    
    def pop_scope(self):
        """Exit the current local scope."""
        if len(self.scopes) > 1:
            self.scopes.pop()
    
    def is_in_global_scope(self) -> bool:
        """Check if we're currently in global scope."""
        return len(self.scopes) == 1

    def define_variable(self, name: str, data_type: DataType, scope: VarScope = VarScope.IMPLICIT):
        """Define a variable with explicit scope control."""
        if scope == VarScope.GLOBAL:
            # Always define in global scope
            self.scopes[0].define_variable(name, data_type, explicit=True)
        elif scope == VarScope.LOCAL:
            # Define in current (local) scope
            if self.is_in_global_scope():
                raise SemanticError(f"Cannot declare LOCAL variable '{name}' in global scope", 0, 0)
            self.scopes[-1].define_variable(name, data_type, explicit=True)
        else:  # IMPLICIT
            # Match NoBASIC default scoping semantics:
            # 1) If the name already exists in any visible scope, update that scope.
            # 2) Otherwise create it in global scope (implicit globals by default).
            for scope_obj in reversed(self.scopes):
                if scope_obj.has_variable(name):
                    scope_obj.define_variable(name, data_type, explicit=False)
                    return
            self.scopes[0].define_variable(name, data_type, explicit=False)

    def get_variable_type(self, name: str) -> DataType:
        """Get the type of a variable (searches from current scope upward)."""
        # Search from current scope to global
        for scope in reversed(self.scopes):
            var_type = scope.get_variable_type(name)
            if var_type is not None:
                return var_type
        return DataType.NUMBER  # Default to NUMBER if not found
    
    def is_variable_defined(self, name: str) -> bool:
        """Check if a variable is defined in any accessible scope."""
        for scope in reversed(self.scopes):
            if scope.has_variable(name):
                return True
        return False
    
    def define_struct(self, name: str, fields: list):
        """Define a struct type."""
        self.structs[name.lower()] = StructType(name, [field.lower() for field in fields])
    
    def get_struct(self, name: str) -> StructType:
        """Get a struct type definition."""
        return self.structs.get(name.lower())
    
    def is_struct(self, name: str) -> bool:
        """Check if name is a struct type."""
        return name.lower() in self.structs
    
    def define_struct_instance(self, var_name: str, struct_name: str):
        """Define a struct instance variable."""
        self.struct_instances[var_name.lower()] = struct_name
    
    def get_struct_instance_type(self, var_name: str) -> str:
        """Get the struct type name for a variable."""
        return self.struct_instances.get(var_name.lower())

    def get_structs_with_field(self, field_name: str) -> List[StructType]:
        """Return all struct definitions containing the given field."""
        field_key = field_name.lower()
        return [struct_def for struct_def in self.structs.values() if field_key in struct_def.fields]

    def infer_struct_instance_type(self, var_name: str, member: str) -> Optional[str]:
        """Infer and cache a struct instance type from member usage when possible."""
        existing_struct = self.get_struct_instance_type(var_name)
        if existing_struct:
            return existing_struct

        matching_structs = self.get_structs_with_field(member)
        if len(matching_structs) == 1:
            struct_name = matching_structs[0].name
            self.define_struct_instance(var_name, struct_name)
            return struct_name

        if not matching_structs and len(self.structs) == 1:
            struct_name = next(iter(self.structs.values())).name
            self.define_struct_instance(var_name, struct_name)
            return struct_name

        return None

    def is_list(self, name: str) -> bool:
        """Check if name is a list."""
        return name in self.lists

    def is_matrix(self, name: str) -> bool:
        """Check if name is a matrix."""
        return name in self.matrices

    def is_defined(self, name: str) -> bool:
        """Check if a name is defined (variable, list, or matrix)."""
        return self.is_variable_defined(name) or name in self.lists or name in self.matrices

    def get_type(self, name: str) -> DataType:
        """Get the type of a defined name."""
        if self.is_variable_defined(name):
            return self.get_variable_type(name)
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
        self.functions: Dict[str, FunctionDefStmt] = {}  # function_name -> definition
        self.current_function: Optional[str] = None  # Currently analyzing function (or None for global)

    def _semantic_error(self, message: str, node=None) -> SemanticError:
        """Create a semantic error using any available AST source coordinates."""
        line = getattr(node, "line", 0)
        column = getattr(node, "column", 0)
        return SemanticError(message, self.filename, line, column)

    def analyze(self, program: Program, filename: str = "<stdin>"):
        """
        Analyze the program semantically.

        Args:
            program: The AST to analyze
            filename: Source filename for error reporting

        Raises:
            SemanticError: If semantic analysis fails
        """
        # Reset analysis state so one SemanticAnalyzer instance can safely analyze
        # multiple independent programs without leaking symbols/functions/gotos.
        self.symbol_table = SymbolTable()
        self.pending_gotos = []
        self.functions = {}
        self.current_function = None
        self.filename = filename

        # Initialize some built-in variables
        for i in range(1, 7):  # L1 to L6
            self.symbol_table.lists.add(f"L{i}")
        for name in ["MatA", "MatB", "MatC"]:  # Some matrices
            self.symbol_table.matrices.add(name)

        # First pass: collect all function definitions
        for stmt in program.statements:
            if isinstance(stmt, FunctionDefStmt):
                func_key = stmt.name.lower()
                if func_key in self.functions:
                    raise self._semantic_error(f"Function '{stmt.name}' already defined", stmt)
                self.functions[func_key] = stmt

        # Second pass: analyze all statements
        for stmt in program.statements:
            self.analyze_statement(stmt)

        # Check all pending GOTOs
        for label_name, line, column in self.pending_gotos:
            if not self.symbol_table.is_label_defined(label_name):
                raise SemanticError(f"Undefined label '{label_name}'", line, column)

    def analyze_statement(self, stmt: Statement):
        """Analyze a statement."""
        if isinstance(stmt, VarDeclarationStmt):
            self.analyze_var_declaration(stmt)
        elif isinstance(stmt, FunctionDefStmt):
            self.analyze_function_def(stmt)
        elif isinstance(stmt, ReturnStmt):
            self.analyze_return(stmt)
        elif isinstance(stmt, AssignmentStmt):
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
        elif isinstance(stmt, ExpressionStmt):
            self.analyze_expression_statement(stmt)
        elif isinstance(stmt, (PxlOnStmt, PxlOffStmt, LineStmt, CircleStmt, TextStmt,
                      SRolStmt, SRotStmt, SShftStmt, SFlipStmt,
                              SetLayerStmt, SpriteOnStmt, SpriteOffStmt, PlayToneStmt,
                              PlayWaveStmt, SetChannelStmt, InputStmt, DispStmt,
                              SerOutStmt, SerCtrlStmt)):
            # These statements have expressions that need checking
            self.analyze_graphics_sound_statement(stmt)
        elif isinstance(stmt, (SerInStmt, SerStatStmt)):
            # SerIn/SerStat define a variable via their operand
            self.symbol_table.define_variable(stmt.variable, DataType.NUMBER)
        # Other statements don't need special analysis

    def analyze_function_def(self, stmt: FunctionDefStmt):
        """Analyze a function definition."""
        # Save current function context
        prev_function = self.current_function
        self.current_function = stmt.name.lower()
        
        # Push new scope for function
        self.symbol_table.push_scope()
        
        # Define parameters as variables in function scope
        for param_name, default_value in stmt.params:
            self.symbol_table.define_variable(param_name, DataType.NUMBER)
            if default_value:
                self.analyze_expression(default_value)
        
        # Analyze function body
        for body_stmt in stmt.body:
            self.analyze_statement(body_stmt)
        
        # Pop function scope
        self.symbol_table.pop_scope()
        
        # Restore previous function context
        self.current_function = prev_function

    def analyze_return(self, stmt: ReturnStmt):
        """Analyze a return statement."""
        if self.current_function is None:
            raise self._semantic_error("Return outside of function", stmt)
        
        if stmt.value:
            self.analyze_expression(stmt.value)

    def analyze_function_call_statement(self, stmt: FunctionCallStmt):
        """Analyze a function call statement."""
        self.analyze_expression(stmt.function_call)

    def analyze_expression_statement(self, stmt: ExpressionStmt):
        """Analyze an expression statement."""
        self.analyze_expression(stmt.expression)

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
        self.pending_gotos.append((stmt.label, getattr(stmt, "line", 0), getattr(stmt, "column", 0)))

    def analyze_label(self, stmt: LabelStmt):
        """Analyze a label statement."""
        if self.symbol_table.is_label_defined(stmt.label):
            raise self._semantic_error("Label already defined", stmt)
        self.symbol_table.define_label(stmt.label)

    def analyze_struct_declaration(self, stmt: StructDeclarationStmt):
        """Analyze a struct declaration."""
        # Check if struct name is already defined
        if self.symbol_table.is_struct(stmt.name):
            raise self._semantic_error(f"Struct '{stmt.name}' is already defined", stmt)
        
        # Check for duplicate field names
        field_set = set()
        for field in stmt.fields:
            field_key = field.lower()
            if field_key in field_set:
                raise self._semantic_error(f"Duplicate field '{field}' in struct '{stmt.name}'", stmt)
            field_set.add(field_key)
        
        # Define the struct
        self.symbol_table.define_struct(stmt.name, stmt.fields)

    def analyze_var_declaration(self, stmt: VarDeclarationStmt):
        """Analyze a variable declaration (GLOBAL/LOCAL)."""
        if stmt.scope == VarScope.LOCAL and self.symbol_table.is_in_global_scope():
            raise self._semantic_error(
                f"Cannot declare LOCAL variable '{stmt.variables[0]}' in global scope",
                stmt,
            )

        for var_name in stmt.variables:
            # Check if variable is already explicitly declared in current scope
            if stmt.scope == VarScope.LOCAL and not self.symbol_table.is_in_global_scope():
                current_scope = self.symbol_table.scopes[-1]
                if var_name in current_scope.explicit_declarations:
                    raise self._semantic_error(f"Variable '{var_name}' already declared in this scope", stmt)
            elif stmt.scope == VarScope.GLOBAL:
                global_scope = self.symbol_table.scopes[0]
                if var_name in global_scope.explicit_declarations:
                    raise self._semantic_error(f"Variable '{var_name}' already declared as global", stmt)
            
            # Define the variable in appropriate scope
            self.symbol_table.define_variable(var_name, DataType.NUMBER, stmt.scope)

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
            if self._is_list_name(expr.name):
                self.symbol_table.lists.add(expr.name)
                return DataType.LIST
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
                if self._is_list_name(expr.list_name):
                    self.symbol_table.lists.add(expr.list_name)
                else:
                    raise self._semantic_error(f"Undefined list: {expr.list_name}", expr)
            if not self.symbol_table.is_list(expr.list_name):
                raise self._semantic_error(f"Undefined list: {expr.list_name}", expr)
            index_type = self.analyze_expression(expr.index)
            if index_type != DataType.NUMBER:
                raise self._semantic_error("List index must be numeric", expr)
            return DataType.NUMBER
        elif isinstance(expr, MatrixAccessExpr):
            if not self.symbol_table.is_matrix(expr.matrix_name):
                raise self._semantic_error(f"Undefined matrix: {expr.matrix_name}", expr)
            row_type = self.analyze_expression(expr.row)
            col_type = self.analyze_expression(expr.col)
            if row_type != DataType.NUMBER or col_type != DataType.NUMBER:
                raise self._semantic_error("Matrix indices must be numeric", expr)
            return DataType.NUMBER
        elif isinstance(expr, MemberAccessExpr):
            # Analyze struct member access
            object_type = self.analyze_expression(expr.object)
            
            # Check if object is a struct instance
            if isinstance(expr.object, VariableExpr):
                var_name = expr.object.name
                struct_name = self.symbol_table.infer_struct_instance_type(var_name, expr.member)
                if not struct_name:
                    raise self._semantic_error(f"Variable '{var_name}' is not a struct instance", expr)
                
                if struct_name:
                    struct_def = self.symbol_table.get_struct(struct_name)
                    if struct_def and expr.member.lower() in struct_def.fields:
                        return DataType.NUMBER  # All struct fields are 16-bit numbers
                    else:
                        raise self._semantic_error(f"Struct '{struct_name}' has no field '{expr.member}'", expr)
                else:
                    raise self._semantic_error(f"Variable '{var_name}' is not a struct instance", expr)
            else:
                raise self._semantic_error("Cannot access member of non-struct expression", expr)
        elif isinstance(expr, BinaryExpr):
            left_type = self.analyze_expression(expr.left)
            right_type = self.analyze_expression(expr.right)
            # Basic type checking for arithmetic
            if expr.operator in ['+', '-', '*', '/', '^']:
                if expr.operator == '+' and (left_type == DataType.STRING or right_type == DataType.STRING):
                    # Allow string concatenation with + (TI-BASIC style)
                    return DataType.STRING
                elif left_type == DataType.STRING or right_type == DataType.STRING:
                    raise self._semantic_error("Cannot perform arithmetic on strings", expr)
                return DataType.NUMBER
            elif expr.operator in ['=', '<>', '<', '>', '<=', '>=']:
                return DataType.NUMBER  # Comparison results
            elif expr.operator in ['and', 'or']:
                return DataType.NUMBER  # Logical results
            return DataType.NUMBER
        elif isinstance(expr, UnaryExpr):
            # Support ++/-- on assignable targets
            if expr.operator in ("++", "--"):
                target = expr.expression
                if isinstance(target, (VariableExpr, ListAccessExpr, MatrixAccessExpr, MemberAccessExpr)):
                    # Ensure target is defined as numeric
                    # For variables, implicitly define if needed
                    if isinstance(target, VariableExpr) and not self.symbol_table.is_variable_defined(target.name):
                        self.symbol_table.define_variable(target.name, DataType.NUMBER)
                    # Analyze inner expression to catch index/member types
                    self.analyze_expression(target)
                    return DataType.NUMBER
                else:
                    raise self._semantic_error("Increment/decrement requires an assignable target", expr)
            return self.analyze_expression(expr.expression)
        elif isinstance(expr, FunctionCallExpr):
            # Check if function is user-defined first
            func_name_lower = expr.name.lower()
            if func_name_lower in self.functions:
                # User-defined function
                func_def = self.functions[func_name_lower]
                # Check argument count - allow fewer args if defaults are provided
                param_specs = func_def.params  # List of (name, default)
                min_args = sum(1 for _, default in param_specs if default is None)
                max_args = len(param_specs)
                
                if not (min_args <= len(expr.arguments) <= max_args):
                    raise self._semantic_error(
                        f"Wrong number of arguments for function '{expr.name}': expected {min_args}-{max_args}, got {len(expr.arguments)}", 
                        expr
                    )
                # Analyze provided argument expressions
                for arg in expr.arguments:
                    self.analyze_expression(arg)
                # Note: Default values are analyzed in function definition, not here
                return DataType.NUMBER
            
            # Check if function is built-in
            func_name = expr.name.upper()
            if not self.is_builtin_function(func_name):
                raise self._semantic_error(f"Undefined function '{expr.name}'", expr)
            # Check argument count
            expected_args = self.get_function_arg_count(func_name)
            if expected_args is not None:
                if isinstance(expected_args, (list, tuple, set)):
                    if len(expr.arguments) not in expected_args:
                        raise self._semantic_error(
                            f"Wrong number of arguments for function '{expr.name}': expected {list(expected_args)}, got {len(expr.arguments)}",
                            expr
                        )
                elif len(expr.arguments) != expected_args:
                    raise self._semantic_error(
                        f"Wrong number of arguments for function '{expr.name}': expected {expected_args}, got {len(expr.arguments)}",
                        expr,
                    )
            # Check argument types
            expected_types = self.get_function_arg_types(func_name)
            for i, arg in enumerate(expr.arguments):
                arg_type = self.analyze_expression(arg)
                if i < len(expected_types) and expected_types[i] is not None:
                    expected_type = expected_types[i]
                    # Allow type coercion in BASIC: NUMBER can be used where STRING is expected
                    if arg_type != expected_type and not (arg_type == DataType.NUMBER and expected_type == DataType.STRING):
                        raise self._semantic_error(
                            f"Invalid argument type for function '{expr.name}': argument {i+1} expected {expected_types[i].value}, got {arg_type.value}",
                            expr,
                        )
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
            "SIN", "COS", "TAN", "SQRT", "ABS", "RAND", "RND", "RNDR", "RANDOMIZE", "LEN", "LENGTH",
            "MIN", "MAX", "LOG", "LN", "EXP", "POW", "INT", "ROUND",
            # Extended math functions
            "ATAN", "ASIN", "ACOS", "DEG", "RAD", "FLOOR", "CEIL", "TRUNC", "FRAC", "INTGR", "POWR",
            # String functions
            "STRLEN", "STRCPY", "STRCAT", "STRCMP", "STRUPR", "STRLWR", "STRREV",
            "STRFIND", "STRFINDI", "STREXT", "STREXTI", "SUB",
            "INSTRING", "UPSTRING", "LOWSTRING", "LENSTRING",
            # Bit manipulation functions
            "BTST", "BSET", "BCLR", "BFLIP", "CLZ", "CTZ", "POPCNT",
            # Shift and rotate functions
            "SHL", "SHR", "SAL", "SAR", "ROL", "ROR", "RCL", "RCR",
            # Bitwise logical functions
            "BAND", "BOR", "BXOR", "BNOT",
            # Memory functions
            "MEMREAD", "MEMWRITE",
            "MEMCPY", "MEMSET", "MEMTEST", "MEMMOVE", "MEMCMP", "MEMSWAP",
            # Enhanced arithmetic
            "ADC", "SBC", "MULH", "DIVH", "SWAP", "XCHNG", "MOVZ", "MOVNZ", "LEA",
            # Type conversion
            "ITOB", "BTOI", "ITOS", "STOI", "STR",
            # Graphics functions
            "CLRDRAW", "SETLAYER", "PXLON", "PXLOFF", "LINE", "CIRCLE", "TEXT", "RECT",
            # List/Array functions
            "SUM", "MEAN", "DIM", "SORTA", "SORTD", "FILL", "SEQ", "REVERSE",
            # I/O functions
            "GETKEY", "PAUSE",
            # Serial I/O functions
            "SERIN", "SERSTAT"
        ]

    def _is_list_name(self, name: str) -> bool:
        """Return True for TI-style list identifiers (L1, L2, ...)."""
        if not name.startswith("L"):
            return False
        suffix = name[1:]
        return suffix.isdigit() and len(suffix) > 0

    def get_function_arg_count(self, name: str) -> int:
        """Get the expected number of arguments for a built-in function."""
        arg_counts = {
            # Original functions
            "SIN": 1, "COS": 1, "TAN": 1, "SQRT": 1, "ABS": 1, "RAND": 0, "RND": 0, "RNDR": 2, "RANDOMIZE": 1,
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
            "MEMREAD": 1, "MEMWRITE": 2,
            "MEMCPY": 3, "MEMSET": 3, "MEMTEST": 3, "MEMMOVE": 3, "MEMCMP": 4, "MEMSWAP": 3,
            # Enhanced arithmetic
            "ADC": 3, "SBC": 3, "MULH": 3, "DIVH": 3,
            "SWAP": 1, "XCHNG": 2, "MOVZ": 2, "MOVNZ": 2, "LEA": 2,
            # Type conversion
            "ITOB": 2, "BTOI": 2, "ITOS": 2, "STOI": 2, "STR": 1,
            # Graphics functions
            "CLRDRAW": 0, "SETLAYER": 1, "PXLON": 3, "PXLOFF": 2, "LINE": 5, "CIRCLE": 4, "TEXT": 4, "RECT": 5,
            # List/Array functions
            "SUM": 1, "MEAN": 1, "DIM": 1, "SORTA": 1, "SORTD": 1, "FILL": 2, "SEQ": (4, 5), "REVERSE": 1,
            # I/O functions
            "GETKEY": 0, "PAUSE": 0,
            # Serial I/O functions
            "SERIN": 0, "SERSTAT": 0,
            # Additional String functions
            "INSTRING": 2, "UPSTRING": 1, "LOWSTRING": 1, "LENSTRING": 1,
        }
        return arg_counts.get(name)

    def get_function_arg_types(self, name: str) -> list:
        """Get the expected argument types for a built-in function."""
        # None means any type is accepted
        arg_types = {
            # Math functions that expect numbers
            "SIN": [DataType.NUMBER], "COS": [DataType.NUMBER], "TAN": [DataType.NUMBER], 
            "SQRT": [DataType.NUMBER], "ABS": [DataType.NUMBER], "RAND": [], "RND": [], 
            "RNDR": [DataType.NUMBER, DataType.NUMBER], "RANDOMIZE": [DataType.NUMBER], "INT": [DataType.NUMBER], 
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
            "MEMREAD": [None], "MEMWRITE": [None, None],
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
            "SORTA": [DataType.LIST], "SORTD": [DataType.LIST], "FILL": [DataType.LIST, DataType.NUMBER],
            "REVERSE": [DataType.LIST],
            # Seq parameters are loosely typed: expression, iterator, start, end, [step]
            "SEQ": [None, None, DataType.NUMBER, DataType.NUMBER, DataType.NUMBER],
            # I/O functions
            "GETKEY": [], "PAUSE": [],
            # Serial I/O functions
            "SERIN": [], "SERSTAT": [],
            # Additional string functions
            "INSTRING": [DataType.STRING, DataType.STRING], "UPSTRING": [DataType.STRING],
            "LOWSTRING": [DataType.STRING], "LENSTRING": [DataType.STRING],
        }
        return arg_types.get(name, [])

    def get_function_return_type(self, name: str) -> DataType:
        """Get the return type for a built-in function."""
        return_types = {
            # String functions return strings
            "STRCPY": DataType.STRING, "STRCAT": DataType.STRING, "STRUPR": DataType.STRING, 
            "STRLWR": DataType.STRING, "STRREV": DataType.STRING, "STREXT": DataType.STRING, 
            "STREXTI": DataType.STRING, "SUB": DataType.STRING, "STR": DataType.STRING,
            # Additional string functions
            "UPSTRING": DataType.STRING, "LOWSTRING": DataType.STRING,
            "INSTRING": DataType.NUMBER, "LENSTRING": DataType.NUMBER,
            # Most others return numbers
        }
        return return_types.get(name, DataType.NUMBER)

    def analyze_assignable_expression(self, expr: Expression, value_type: DataType):
        """Analyze an expression that can be assigned to (left-hand side of assignment)."""
        line = getattr(expr, "line", 0)
        column = getattr(expr, "column", 0)
        if isinstance(expr, VariableExpr):
            # Variables are dynamically typed and implicitly global by default,
            # unless an existing local/parameter binding already exists.
            self.symbol_table.define_variable(expr.name, value_type, VarScope.IMPLICIT)
        elif isinstance(expr, MemberAccessExpr):
            # Struct member assignment
            if isinstance(expr.object, VariableExpr):
                var_name = expr.object.name
                struct_name = self.symbol_table.infer_struct_instance_type(var_name, expr.member)
                if not struct_name:
                    raise self._semantic_error(f"Variable '{var_name}' is not a struct instance", expr)
                
                struct_def = self.symbol_table.get_struct(struct_name)
                if not struct_def or expr.member.lower() not in struct_def.fields:
                    raise self._semantic_error(f"Struct '{struct_name}' has no field '{expr.member}'", expr)
                
                # Struct fields must be numbers
                if value_type != DataType.NUMBER:
                    raise self._semantic_error("Struct fields can only hold numeric values", expr)
            else:
                raise self._semantic_error("Cannot assign to member of non-struct expression", expr)
        elif isinstance(expr, ListAccessExpr):
            # Check that the list exists and index is valid
            list_name = expr.list_name
            if self._is_list_name(list_name):
                self.symbol_table.lists.add(list_name)
            elif not self.symbol_table.is_defined(list_name):
                # Auto-define list
                self.symbol_table.lists.add(list_name)
            elif self.symbol_table.get_type(list_name) != DataType.LIST:
                raise SemanticError(f"'{list_name}' is not a list", self.filename, line, column)
            # Check index expression
            index_type = self.analyze_expression(expr.index)
            if index_type != DataType.NUMBER:
                raise SemanticError("List index must be a number", self.filename, line, column)
        elif isinstance(expr, MatrixAccessExpr):
            # Check that the matrix exists and indices are valid
            matrix_name = expr.matrix_name
            if not self.symbol_table.is_defined(matrix_name):
                # Auto-define matrix
                self.symbol_table.matrices.add(matrix_name)
            elif self.symbol_table.get_type(matrix_name) != DataType.MATRIX:
                raise SemanticError(f"'{matrix_name}' is not a matrix", self.filename, line, column)
            # Check index expressions
            row_type = self.analyze_expression(expr.row)
            col_type = self.analyze_expression(expr.col)
            if row_type != DataType.NUMBER or col_type != DataType.NUMBER:
                raise SemanticError("Matrix indices must be numbers", self.filename, line, column)
        else:
            raise SemanticError("Invalid assignment target", self.filename, line, column)