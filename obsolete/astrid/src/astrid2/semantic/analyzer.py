"""
Astrid Semantic Analyzer
"""

from typing import Dict, List, Optional
from .scope import ScopeManager, Symbol
from ..utils.logger import get_logger
from ..utils.error import CompilerError, SemanticError
from ..parser.ast import (
    Program, ASTVisitor, Declaration, FunctionDeclaration, StructDeclaration,
    VariableDeclaration, Statement, Expression, BinaryOp, UnaryOp,
    FunctionCall, Variable, Literal, Type, DataType, StructType,
    HardwareAccess, MemberAccess, ArrayAccess, Parameter, StructField,
    SwitchStatement, SwitchCase, BreakStatement, ContinueStatement
)

logger = get_logger(__name__)


class Symbol:
    """Symbol table entry."""

    def __init__(self, name: str, type: DataType, kind: str = 'variable',
                 line: int = 0, column: int = 0):
        self.name = name
        self.type = type
        self.kind = kind  # 'variable', 'function', 'struct', 'parameter'
        self.line = line
        self.column = column
        self.used = False

    def __repr__(self) -> str:
        return f"Symbol({self.name}, {self.type}, {self.kind})"


class Scope:
    """Symbol scope for managing variable visibility."""

    def __init__(self, parent: Optional['Scope'] = None):
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}
        self.children: List['Scope'] = []

    def define(self, symbol: Symbol) -> None:
        """Define a symbol in this scope."""
        if symbol.name in self.symbols:
            existing = self.symbols[symbol.name]
            raise CompilerError(
                f"Symbol '{symbol.name}' already defined in this scope",
                symbol.line, symbol.column
            )
        self.symbols[symbol.name] = symbol

    def resolve(self, name: str) -> Optional[Symbol]:
        """Resolve a symbol by name, searching parent scopes if needed."""
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.resolve(name)
        return None

    def get_variable_type(self, name: str) -> Optional[DataType]:
        """Get the type of a variable by name, searching all scopes."""
        symbol = self.current_scope.resolve(name)
        if symbol:
            return symbol.type
        return None


class SemanticAnalyzer(ASTVisitor):
    """Semantic analyzer for Astrid."""

    def __init__(self):
        self.global_scope = Scope()
        self.current_scope = self.global_scope
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.current_function: Optional[FunctionDeclaration] = None

        # Hardware register mappings
        self.hardware_registers = {
            'vmode': Type.INT8,      # Video mode register
            'vlayer': Type.INT8,     # Video layer register
            'vx': Type.PIXEL,        # Video X coordinate
            'vy': Type.PIXEL,        # Video Y coordinate
            'sa': Type.INT16,        # Sound address
            'sf': Type.INT16,        # Sound frequency
            'sv': Type.INT8,         # Sound volume
            'sw': Type.INT8,         # Sound waveform
            'tt': Type.INT8,         # Timer value
            'tm': Type.INT8,         # Timer match
            'tc': Type.INT8,         # Timer control
            'ts': Type.INT8,         # Timer speed
        }

        # Built-in functions with return types
        self.builtin_functions = {
            # Graphics functions
            'set_pixel': Type.VOID,
            'get_pixel': Type.INT8,
            'clear_screen': Type.VOID,
            
            # String functions
            'strlen': Type.INT8,
            'strcpy': Type.VOID,
            'strcat': Type.VOID,
            'strcmp': Type.INT8,
            'strchr': Type.INT16,
            'substr': Type.VOID,
            'print_string': Type.VOID,
            'char_at': Type.CHAR,
            'string_to_int': Type.INT16,
            'int_to_string': Type.VOID,
            'string_clear': Type.VOID,
            'string_fill': Type.VOID,
            'draw_line': Type.VOID,
            'draw_rect': Type.VOID,
            'fill_rect': Type.VOID,
            'set_layer': Type.VOID,
            'set_blend_mode': Type.VOID,
            'scroll_layer': Type.VOID,
            'roll_screen_x': Type.VOID,
            'roll_screen_y': Type.VOID,
            'flip_screen_x': Type.VOID,
            'flip_screen_y': Type.VOID,
            'rotate_screen_left': Type.VOID,
            'rotate_screen_right': Type.VOID,
            'shift_screen_x': Type.VOID,
            'shift_screen_y': Type.VOID,
            'set_sprite': Type.VOID,
            'move_sprite': Type.VOID,
            'show_sprite': Type.VOID,
            'hide_sprite': Type.VOID,

            # Sound functions
            'play_tone': Type.VOID,
            'stop_channel': Type.VOID,
            'set_volume': Type.VOID,
            'set_waveform': Type.VOID,
            'play_sample': Type.VOID,
            'set_master_volume': Type.VOID,
            'set_channel_pan': Type.VOID,

            # System functions
            'enable_interrupts': Type.VOID,
            'disable_interrupts': Type.VOID,
            'set_interrupt_handler': Type.VOID,
            'configure_timer': Type.VOID,
            'read_keyboard': Type.INT8,
            'clear_keyboard_buffer': Type.VOID,
            'get_timer_value': Type.INT8,
            'set_timer_match': Type.VOID,
            'memory_read': Type.INT8,
            'memory_write': Type.VOID,
            'halt': Type.VOID,
            'reset': Type.VOID,
            'setup_timer_interrupt': Type.VOID,
            'setup_keyboard_interrupt': Type.VOID,
            'clear_timer_interrupt': Type.VOID,
            'clear_keyboard_interrupt': Type.VOID,
            'software_interrupt': Type.VOID,

            # Random number generation functions
            'random': Type.INT16,
            'random_range': Type.INT16,

            # Hardware initialization functions
            'vector': Type.INTERRUPT_VECTOR,
            'memory.region': Type.MEMORY_REGION,
            'hardware.reset': Type.VOID,
            'memory.initialize_heap': Type.VOID,

            # Legacy functions
            'layer': Type.LAYER,
            'sprite': Type.SPRITE,
            'channel': Type.SOUND,
            'load_sample': Type.SOUND,

            # String functions
            'strlen': Type.INT16,
            'strcpy': Type.STRING,
            'strcat': Type.STRING,
            'strcmp': Type.INT8,
            'strchr': Type.INT16,  # Returns index or -1
            'substr': Type.STRING,
            'print_string': Type.VOID,
            'char_at': Type.CHAR,
            'string_to_int': Type.INT16,
            'int_to_string': Type.STRING,
            'string_clear': Type.VOID,
            'string_fill': Type.VOID,
        }

        # Built-in function signatures with parameter types
        self.builtin_signatures = {
            'set_pixel': [Type.PIXEL, Type.PIXEL, Type.COLOR],  # x, y, color (fixed)
            'get_pixel': [Type.PIXEL, Type.PIXEL],  # x, y (fixed)
            'clear_screen': [Type.COLOR],  # color (fixed)
            'draw_line': [Type.PIXEL, Type.PIXEL, Type.PIXEL, Type.PIXEL, Type.COLOR],  # x1, y1, x2, y2, color (fixed)
            'draw_rect': [Type.PIXEL, Type.PIXEL, Type.PIXEL, Type.PIXEL, Type.COLOR],  # x, y, w, h, color (fixed)
            'fill_rect': [Type.PIXEL, Type.PIXEL, Type.PIXEL, Type.PIXEL, Type.COLOR],  # x, y, w, h, color (fixed)
            'set_layer': [Type.LAYER],  # layer (fixed)
            'set_blend_mode': [Type.INT8],  # mode
            'scroll_layer': [Type.LAYER, Type.INT8],  # layer, amount (fixed)
            'roll_screen_x': [Type.INT8],  # amount
            'roll_screen_y': [Type.INT8],  # amount
            'flip_screen_x': [],  # no parameters
            'flip_screen_y': [],  # no parameters
            'rotate_screen_left': [Type.INT8],  # times
            'rotate_screen_right': [Type.INT8],  # times
            'shift_screen_x': [Type.INT8],  # amount
            'shift_screen_y': [Type.INT8],  # amount
            'set_sprite': [Type.SPRITE, Type.PIXEL, Type.PIXEL, Type.PIXEL, Type.PIXEL, Type.INT16],  # id, x, y, w, h, data_addr (fixed)
            'move_sprite': [Type.SPRITE, Type.PIXEL, Type.PIXEL],  # id, x, y (fixed)
            'show_sprite': [Type.SPRITE],  # id (fixed)
            'hide_sprite': [Type.SPRITE],  # id (fixed)
            'play_tone': [Type.INT16, Type.INT8, Type.INT8],  # frequency, volume, channel
            'stop_channel': [Type.INT8],  # channel
            'set_volume': [Type.INT8, Type.INT8],  # channel, volume
            'set_waveform': [Type.INT8, Type.INT8],  # channel, waveform
            'play_sample': [Type.INT8, Type.INT16],  # channel, address
            'set_master_volume': [Type.INT8],  # volume
            'set_channel_pan': [Type.INT8, Type.INT8],  # channel, pan
            'enable_interrupts': [],
            'disable_interrupts': [],
            'set_interrupt_handler': [Type.INTERRUPT_VECTOR],
            'configure_timer': [Type.INT8, Type.INT8, Type.INT8],  # tt, tm, tc
            'read_keyboard': [],
            'clear_keyboard_buffer': [],
            'get_timer_value': [],
            'set_timer_match': [Type.INT8],  # match
            'memory_read': [Type.INT16],  # address
            'memory_write': [Type.INT16, Type.INT8],  # address, value
            'halt': [],
            'reset': [],
            'setup_timer_interrupt': [Type.INT16, Type.INT8, Type.INT8, Type.INT8],  # handler_addr, timer_val, match_val, speed
            'setup_keyboard_interrupt': [Type.INT16],  # handler_addr
            'clear_timer_interrupt': [],
            'clear_keyboard_interrupt': [],
            'software_interrupt': [Type.INT8],  # vector
            'random': [],  # no parameters
            'random_range': [Type.INT16, Type.INT16],  # min, max
            'vector': [Type.INT8],  # vector_number
            'memory.region': [Type.INT16, Type.INT16],  # start, size
            'hardware.reset': [],
            'memory.initialize_heap': [Type.INT16, Type.INT16],  # start, size
            'layer': [Type.INT8],  # layer_number
            'sprite': [Type.INT8],  # sprite_number
            'channel': [Type.INT8],  # channel_number
            'load_sample': [Type.INT16],  # address

            # String functions - missing signatures
            'strlen': [Type.STRING],  # string
            'strcpy': [Type.STRING, Type.STRING],  # dest, src
            'strcat': [Type.STRING, Type.STRING],  # dest, src
            'strcmp': [Type.STRING, Type.STRING],  # str1, str2
            'strchr': [Type.STRING, Type.CHAR],  # string, char
            'substr': [Type.STRING, Type.INT16, Type.INT16],  # string, start, length
            'print_string': [Type.STRING, Type.PIXEL, Type.PIXEL, Type.COLOR],  # string, x, y, color
            'char_at': [Type.STRING, Type.INT16],  # string, index
            'string_to_int': [Type.STRING],  # string
            'int_to_string': [Type.INT16],  # number
            'string_clear': [Type.STRING],  # string
            'string_fill': [Type.STRING, Type.CHAR, Type.INT16],  # string, char, count
        }

    def reset_state(self):
        """Reset analyzer state for new compilation."""
        # Reset to proper scope objects
        self.global_scope = Scope()
        self.current_scope = self.global_scope
        
        # Reset error lists
        self.errors = []
        self.warnings = []
        
        # Reset function context
        self.current_function = None
        
        logger.debug("Semantic analyzer state reset")

    def analyze(self, program: Program) -> None:
        """Analyze the program for semantic errors."""
        logger.debug("Starting semantic analysis")
        self.errors = []
        self.warnings = []
        self.current_scope = self.global_scope
        self.current_function = None

        try:
            # First pass: collect all global declarations
            self._collect_global_declarations(program)

            # Second pass: analyze all declarations
            program.accept(self)

            # Check for unused symbols
            self._check_unused_symbols()

            if self.errors:
                logger.error(f"Semantic analysis found {len(self.errors)} errors")
                for error in self.errors:
                    logger.error(f"  {error}")
            else:
                logger.debug("Semantic analysis completed successfully")

            if self.warnings:
                logger.warning(f"Semantic analysis found {len(self.warnings)} warnings")
                for warning in self.warnings:
                    logger.warning(f"  {warning}")

        except CompilerError as e:
            self.errors.append(str(e))
            logger.error(f"Semantic analysis failed: {e}")

    def _collect_global_declarations(self, program: Program) -> None:
        """Collect all global declarations in the symbol table."""
        for decl in program.declarations:
            if isinstance(decl, FunctionDeclaration):
                symbol = Symbol(decl.name, decl.return_type, 'function', decl.line, decl.column)
                self.global_scope.define(symbol)
            elif isinstance(decl, StructDeclaration):
                # Create proper struct type with field mapping
                field_map = {}
                for field in decl.fields:
                    field_map[field.name] = field.type
                struct_type = StructType(decl.name, field_map)
                symbol = Symbol(decl.name, struct_type, 'struct', decl.line, decl.column)
                self.global_scope.define(symbol)

    def _check_unused_symbols(self) -> None:
        """Check for unused symbols and generate warnings."""
        def check_scope(scope: Scope) -> None:
            for symbol in scope.symbols.values():
                if not symbol.used and symbol.kind in ('variable', 'parameter'):
                    self.warnings.append(
                        f"Unused {symbol.kind} '{symbol.name}' at line {symbol.line}"
                    )
            for child in scope.children:
                check_scope(child)

        check_scope(self.global_scope)

    def _enter_scope(self) -> None:
        """Enter a new scope."""
        new_scope = Scope(self.current_scope)
        self.current_scope.children.append(new_scope)
        self.current_scope = new_scope

    def _exit_scope(self) -> None:
        """Exit the current scope."""
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent

    def _type_compatible(self, left: DataType, right: DataType) -> bool:
        """Check if two types are compatible for assignment/operations."""
        if left == right:
            return True

        # Allow int8 to int16 promotion (both directions for operations)
        if left == Type.INT16 and right == Type.INT8:
            return True
        if left == Type.INT8 and right == Type.INT16:
            return True

        # Allow pixel operations with int8
        if left == Type.PIXEL and right == Type.INT8:
            return True
        if left == Type.INT8 and right == Type.PIXEL:
            return True

        # Allow color operations with int8 (for color literals)
        if left == Type.COLOR and right == Type.INT8:
            return True
        if left == Type.INT8 and right == Type.COLOR:
            return True

        # Allow color operations with int16 (color values are 16-bit)
        if left == Type.COLOR and right == Type.INT16:
            return True
        if left == Type.INT16 and right == Type.COLOR:
            return True

        # Allow hardware-specific types to be assigned from int8 literals
        hardware_types = [Type.SOUND, Type.LAYER, Type.SPRITE, Type.INTERRUPT, 
                         Type.INTERRUPT_VECTOR, Type.MEMORY_REGION]
        for hw_type in hardware_types:
            if left == hw_type and right == Type.INT8:
                return True
            if left == Type.INT8 and right == hw_type:
                return True

        # Allow uint types to be compatible with corresponding int types
        if left == Type.UINT8 and right == Type.INT8:
            return True
        if left == Type.INT8 and right == Type.UINT8:
            return True
        if left == Type.UINT16 and right == Type.INT16:
            return True
        if left == Type.INT16 and right == Type.UINT16:
            return True

        # Allow VOID to be compatible with any type (for function returns)
        if left == Type.VOID or right == Type.VOID:
            return True

        # Allow string assignment from string literals
        if left == Type.STRING and right == Type.STRING:
            return True

        # Allow char to int8 conversion
        if left == Type.CHAR and right == Type.INT8:
            return True
        if left == Type.INT8 and right == Type.CHAR:
            return True

        return False

    def _get_expression_type(self, expr: Expression) -> DataType:
        """Get the type of an expression."""
        if hasattr(expr, 'type') and expr.type is not None:
            return expr.type

        # For expressions without explicit type, infer from context
        if isinstance(expr, Literal):
            if isinstance(expr.value, int):
                # For now, default to int8 for integers
                # TODO: Context-aware type inference
                if 0 <= expr.value <= 255:
                    return Type.INT8
                else:
                    return Type.INT16
            elif isinstance(expr.value, str):
                return Type.STRING  # String literals as string type
            elif isinstance(expr.value, bool):
                return Type.INT8
        elif isinstance(expr, Variable):
            symbol = self.current_scope.resolve(expr.name)
            if symbol:
                return symbol.type
        elif isinstance(expr, BinaryOp):
            left_type = self._get_expression_type(expr.left)
            right_type = self._get_expression_type(expr.right)
            # Return the "wider" type
            if left_type == Type.INT16 or right_type == Type.INT16:
                return Type.INT16
            return left_type
        elif isinstance(expr, UnaryOp):
            # Unary operations preserve the operand type
            return self._get_expression_type(expr.operand)
        elif isinstance(expr, FunctionCall):
            # If we get here, the type wasn't set, so it's a user-defined function
            symbol = self.current_scope.resolve(expr.name)
            if symbol and symbol.kind == 'function':
                return symbol.type

        return Type.VOID  # Default fallback

    # Visitor methods

    def visit_program(self, node: Program) -> None:
        """Visit a program node."""
        for decl in node.declarations:
            decl.accept(self)

    def visit_struct_declaration(self, node: StructDeclaration) -> None:
        """Visit a struct declaration."""
        # Struct declarations are already collected in global scope
        pass

    def visit_function_declaration(self, node: FunctionDeclaration) -> None:
        """Visit a function declaration."""
        self.current_function = node

        # Enter function scope
        self._enter_scope()

        # Add parameters to scope
        for param in node.parameters:
            symbol = Symbol(param.name, param.type, 'parameter', node.line, node.column)
            self.current_scope.define(symbol)

        # Analyze function body
        for stmt in node.body:
            stmt.accept(self)

        # Exit function scope
        self._exit_scope()
        self.current_function = None

    def visit_variable_declaration(self, node: VariableDeclaration) -> None:
        """Visit a variable declaration."""
        # Check if variable already exists in current scope
        existing = self.current_scope.symbols.get(node.name)
        if existing:
            self.errors.append(
                f"Variable '{node.name}' already declared in this scope at line {existing.line}"
            )
            return

        # Create symbol
        symbol = Symbol(node.name, node.type, 'variable', node.line, node.column)
        self.current_scope.define(symbol)

        # Check initializer type compatibility
        if node.initializer:
            node.initializer.accept(self)  # Visit first to set types
            init_type = self._get_expression_type(node.initializer)
            if not self._type_compatible(node.type, init_type):
                self.errors.append(
                    f"Cannot assign {init_type} to variable of type {node.type} at line {node.line}"
                )

    def visit_assignment(self, node) -> None:
        """Visit an assignment."""
        # Analyze target and value first to set types
        node.target.accept(self)
        node.value.accept(self)

        # Then get types for checking
        target_type = self._get_expression_type(node.target)
        value_type = self._get_expression_type(node.value)

        # Check type compatibility
        if not self._type_compatible(target_type, value_type):
            self.errors.append(
                f"Cannot assign {value_type} to {target_type} at line {node.line}"
            )

    def visit_if_statement(self, node) -> None:
        """Visit an if statement."""
        # Condition must be convertible to boolean
        cond_type = self._get_expression_type(node.condition)
        if cond_type not in (Type.INT8, Type.INT16):
            self.errors.append(
                f"If condition must be numeric, got {cond_type} at line {node.line}"
            )

        node.condition.accept(self)

        # Enter then branch scope
        self._enter_scope()
        for stmt in node.then_branch:
            stmt.accept(self)
        self._exit_scope()

        # Enter else branch scope if present
        if node.else_branch:
            self._enter_scope()
            for stmt in node.else_branch:
                stmt.accept(self)
            self._exit_scope()

    def visit_while_statement(self, node) -> None:
        """Visit a while statement."""
        # Condition must be convertible to boolean
        cond_type = self._get_expression_type(node.condition)
        if cond_type not in (Type.INT8, Type.INT16):
            self.errors.append(
                f"While condition must be numeric, got {cond_type} at line {node.line}"
            )

        node.condition.accept(self)

        # Enter loop body scope
        self._enter_scope()
        for stmt in node.body:
            stmt.accept(self)
        self._exit_scope()

    def visit_for_statement(self, node) -> None:
        """Visit a for statement."""
        # Enter loop scope
        self._enter_scope()

        # Analyze initializer
        if node.initializer:
            node.initializer.accept(self)

        # Check condition type
        if node.condition:
            cond_type = self._get_expression_type(node.condition)
            if cond_type not in (Type.INT8, Type.INT16):
                self.errors.append(
                    f"For condition must be numeric, got {cond_type} at line {node.line}"
                )
            node.condition.accept(self)

        # Analyze increment
        if node.increment:
            node.increment.accept(self)

        # Analyze body
        for stmt in node.body:
            stmt.accept(self)

        self._exit_scope()

    def visit_switch_statement(self, node) -> None:
        """Visit a switch statement."""
        # Analyze switch expression
        node.expression.accept(self)
        switch_type = self._get_expression_type(node.expression)
        
        # Enter switch scope
        self._enter_scope()
        
        # Analyze all cases
        for case in node.cases:
            case.value.accept(self)
            case_type = self._get_expression_type(case.value)
            
            # Check case value type compatibility with switch expression
            if not self._type_compatible(switch_type, case_type):
                self.errors.append(
                    f"Case value type {case_type} incompatible with switch expression type {switch_type} at line {case.value.line}"
                )
            
            # Analyze case body
            for stmt in case.body:
                stmt.accept(self)
        
        # Analyze default case if present
        if node.default_case:
            for stmt in node.default_case:
                stmt.accept(self)
        
        self._exit_scope()

    def visit_break_statement(self, node) -> None:
        """Visit a break statement."""
        # For now, just accept break statements
        # TODO: Add context checking (must be in loop or switch)
        pass

    def visit_continue_statement(self, node) -> None:
        """Visit a continue statement."""
        # For now, just accept continue statements
        # TODO: Add context checking (must be in loop)
        pass

    def visit_return_statement(self, node) -> None:
        """Visit a return statement."""
        if not self.current_function:
            self.errors.append(f"Return statement outside function at line {node.line}")
            return

        if node.value:
            return_type = self._get_expression_type(node.value)
            if not self._type_compatible(self.current_function.return_type, return_type):
                self.errors.append(
                    f"Cannot return {return_type} from function returning {self.current_function.return_type} at line {node.line}"
                )
            node.value.accept(self)
        elif self.current_function.return_type != Type.VOID:
            self.errors.append(
                f"Function must return {self.current_function.return_type} at line {node.line}"
            )

    def visit_expression_statement(self, node) -> None:
        """Visit an expression statement."""
        node.expression.accept(self)

    def visit_block_statement(self, node) -> None:
        """Visit a block statement."""
        # Enter block scope
        self._enter_scope()
        for stmt in node.statements:
            stmt.accept(self)
        self._exit_scope()

    def visit_literal(self, node) -> None:
        """Visit a literal."""
        if node.type is None:
            # Infer type for literals that don't have explicit types
            if isinstance(node.value, int):
                if 0 <= node.value <= 255:
                    node.type = Type.INT8
                else:
                    node.type = Type.INT16
            elif isinstance(node.value, str):
                node.type = Type.STRING  # String literals as string type
            elif isinstance(node.value, bool):
                node.type = Type.INT8

    def visit_variable(self, node) -> None:
        """Visit a variable reference."""
        symbol = self.current_scope.resolve(node.name)
        if not symbol:
            self.errors.append(f"Undefined variable '{node.name}' at line {node.line}")
            return

        # Mark as used
        symbol.used = True
        node.type = symbol.type

    def visit_binary_op(self, node) -> None:
        """Visit a binary operation."""
        node.left.accept(self)
        node.right.accept(self)

        left_type = self._get_expression_type(node.left)
        right_type = self._get_expression_type(node.right)

        # Determine result type
        if left_type == Type.INT16 or right_type == Type.INT16:
            node.type = Type.INT16
        else:
            node.type = left_type

        # Type compatibility check
        if not self._type_compatible(left_type, right_type):
            self.errors.append(
                f"Type mismatch in binary operation: {left_type} {node.operator} {right_type} at line {node.line}"
            )

    def visit_unary_op(self, node) -> None:
        """Visit a unary operation."""
        node.operand.accept(self)
        node.type = self._get_expression_type(node.operand)

    def visit_ternary_op(self, node) -> None:
        """Visit a ternary conditional operation."""
        # Analyze all parts
        node.condition.accept(self)
        node.then_expr.accept(self)
        node.else_expr.accept(self)
        
        # Check condition type
        cond_type = self._get_expression_type(node.condition)
        if cond_type not in (Type.INT8, Type.INT16):
            self.errors.append(
                f"Ternary condition must be numeric, got {cond_type} at line {node.line}"
            )
        
        # Result type is the wider of the two branches
        then_type = self._get_expression_type(node.then_expr)
        else_type = self._get_expression_type(node.else_expr)
        
        # Type unification: choose the wider compatible type
        if self._type_compatible(then_type, else_type):
            if then_type == Type.INT16 or else_type == Type.INT16:
                node.type = Type.INT16
            else:
                node.type = then_type
        else:
            self.errors.append(
                f"Ternary branches have incompatible types: {then_type} and {else_type} at line {node.line}"
            )
            node.type = then_type  # Fallback to first branch

    def visit_function_call(self, node) -> None:
        """Visit a function call."""
        # Check if it's a built-in function
        if node.name in self.builtin_functions:
            node.type = self.builtin_functions[node.name]
            
            # Validate parameter types for builtin functions
            if node.name in self.builtin_signatures:
                expected_params = self.builtin_signatures[node.name]
                if len(node.arguments) != len(expected_params):
                    self.errors.append(
                        f"Function '{node.name}' expects {len(expected_params)} arguments, "
                        f"got {len(node.arguments)} at line {node.line}"
                    )
                else:
                    for i, (arg, expected_type) in enumerate(zip(node.arguments, expected_params)):
                        arg.accept(self)
                        arg_type = self._get_expression_type(arg)
                        
                        # Enhanced type compatibility for builtin functions
                        if not self._type_compatible(expected_type, arg_type):
                            # Special handling for different function classes
                            if (node.name == 'random_range' and 
                                arg_type == Type.INT8 and expected_type == Type.INT16):
                                # Allow INT8 literals to be used for INT16 parameters in random_range
                                pass
                            elif ((expected_type in [Type.PIXEL, Type.COLOR, Type.LAYER, Type.SPRITE]) and
                                  arg_type in [Type.INT8, Type.INT16]):
                                # Allow numeric types for hardware-specific types
                                if arg_type == Type.INT16 and expected_type in [Type.PIXEL, Type.COLOR]:
                                    self.warnings.append(
                                        f"Function '{node.name}' parameter {i+1} expects {expected_type.name} but got {arg_type.name}. "
                                        f"Value will be truncated at line {node.line}"
                                    )
                                # Otherwise allow the conversion silently
                            elif (arg_type in [Type.PIXEL, Type.COLOR, Type.LAYER, Type.SPRITE] and
                                  expected_type in [Type.INT8, Type.INT16]):
                                # Allow hardware types to be passed as numeric
                                pass
                            elif arg_type == Type.INT16 and expected_type == Type.INT8:
                                # Warn about potential truncation
                                self.warnings.append(
                                    f"Function '{node.name}' parameter {i+1} expects {expected_type.name} but got {arg_type.name}. "
                                    f"Value will be truncated at line {node.line}"
                                )
                            else:
                                self.errors.append(
                                    f"Function '{node.name}' parameter {i+1} expects {expected_type.name} "
                                    f"but got {arg_type.name} at line {node.line}"
                                )
        else:
            # Check user-defined function
            symbol = self.current_scope.resolve(node.name)
            if not symbol or symbol.kind != 'function':
                self.errors.append(f"Undefined function '{node.name}' at line {node.line}")
                return

            node.type = symbol.type

        # Analyze arguments (for non-builtin or after validation)
        for arg in node.arguments:
            arg.accept(self)

    def visit_member_access(self, node) -> None:
        """Visit a member access."""
        node.object.accept(self)

        # Get the object type first
        object_type = self._get_expression_type(node.object)
        
        # Handle struct member access
        if isinstance(object_type, StructType):
            if object_type.fields and node.member in object_type.fields:
                node.type = object_type.fields[node.member]
            else:
                # Look up the struct declaration in the symbol table
                struct_symbol = self.current_scope.resolve(object_type.name)
                if struct_symbol and struct_symbol.kind == 'struct':
                    struct_decl = struct_symbol.type
                    if hasattr(struct_decl, 'fields') and struct_decl.fields:
                        if node.member in struct_decl.fields:
                            node.type = struct_decl.fields[node.member]
                        else:
                            self.errors.append(
                                f"Struct '{object_type.name}' has no member '{node.member}' at line {node.line}"
                            )
                            node.type = Type.INT8  # Fallback
                    else:
                        self.errors.append(
                            f"Cannot access member '{node.member}' of incomplete struct '{object_type.name}' at line {node.line}"
                        )
                        node.type = Type.INT8  # Fallback
                else:
                    self.errors.append(
                        f"Cannot access member '{node.member}' of non-struct type '{object_type}' at line {node.line}"
                    )
                    node.type = Type.INT8  # Fallback
        else:
            self.errors.append(
                f"Cannot access member '{node.member}' of non-struct type '{object_type}' at line {node.line}"
            )
            node.type = Type.INT8  # Fallback

    def visit_array_access(self, node) -> None:
        """Visit an array access."""
        node.array.accept(self)
        node.index.accept(self)

        # Check index type
        index_type = self._get_expression_type(node.index)
        if index_type not in (Type.INT8, Type.INT16, Type.PIXEL):
            self.errors.append(f"Array index must be numeric, got {index_type} at line {node.line}")

        # Get the array type to determine element type
        array_type = self._get_expression_type(node.array)
        
        # Handle array types properly
        if hasattr(array_type, 'element_type'):
            # This is an ArrayType - get the element type
            node.type = array_type.element_type
        elif isinstance(array_type, Type):
            # This is a basic type, assume it's the element type
            node.type = array_type
        else:
            # Fallback - this indicates a bug in array declaration handling
            self.errors.append(f"Cannot determine array element type at line {node.line}")
            node.type = Type.INT8

    def reset_for_new_compilation(self):
        """Reset the analyzer state for a new compilation."""
        # Reset scopes
        self.global_scope = Scope()
        self.current_scope = self.global_scope
        
        # Clear any accumulated state
        self.errors.clear()
        self.warnings.clear()
        self.current_function = None
        
        # Scopes and builtin functions are already initialized in __init__

    def visit_hardware_access(self, node) -> None:
        """Visit a hardware access."""
        if node.register not in self.hardware_registers:
            self.errors.append(f"Unknown hardware register '{node.register}' at line {node.line}")
            return

        node.type = self.hardware_registers[node.register]
