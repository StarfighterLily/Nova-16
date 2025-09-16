"""
Astrid Intermediate Representation Builder
"""

from typing import Dict, List, Any, Optional
from ..utils.logger import get_logger
from ..parser.ast import (
    Program, FunctionDeclaration, VariableDeclaration, Assignment,
    IfStatement, WhileStatement, ReturnStatement, BinaryOp, UnaryOp, TernaryOp,
    FunctionCall, Variable, Literal, Type, DataType, ASTVisitor, ArrayAccess,
    SwitchStatement, SwitchCase, BreakStatement, ContinueStatement
)

logger = get_logger(__name__)


class IRInstruction:
    """Base class for IR instructions."""
    def __init__(self, opcode: str, operands: List[Any] = None, result: str = None):
        self.opcode = opcode
        self.operands = operands or []
        self.result = result

    def __repr__(self):
        if self.result:
            return f"{self.result} = {self.opcode} {', '.join(str(op) for op in self.operands)}"
        else:
            return f"{self.opcode} {', '.join(str(op) for op in self.operands)}"


class IRBasicBlock:
    """Basic block in IR."""
    def __init__(self, name: str):
        self.name = name
        self.instructions: List[IRInstruction] = []
        self.predecessors: List['IRBasicBlock'] = []
        self.successors: List['IRBasicBlock'] = []

    def add_instruction(self, instruction: IRInstruction):
        self.instructions.append(instruction)


class IRFunction:
    """Function in IR."""
    def __init__(self, name: str, return_type: DataType):
        self.name = name
        self.return_type = return_type
        self.parameters: List[Dict[str, Any]] = []
        self.parameter_ir_vars: List[str] = []  # IR variables for parameters
        self.blocks: List[IRBasicBlock] = []
        self.entry_block = None
        self.module = None  # Reference to parent module

    def add_block(self, block: IRBasicBlock):
        self.blocks.append(block)
        if not self.entry_block:
            self.entry_block = block


class IRModule:
    """Top-level IR module."""
    def __init__(self):
        self.functions: List[IRFunction] = []
        self.globals: Dict[str, Any] = {}
        self.variable_types: Dict[str, str] = {}  # IR variable -> type (int8, int16, etc.)
        self.variable_map: Dict[str, str] = {}  # AST variable name -> IR variable name

    def add_function(self, function: IRFunction):
        self.functions.append(function)
        function.module = self  # Set reference to parent module


class IRBuilder(ASTVisitor):
    """IR builder for Astrid."""

    def __init__(self, semantic_analyzer=None):
        self.module = IRModule()
        self.current_function: Optional[IRFunction] = None
        self.current_block: Optional[IRBasicBlock] = None
        self.variable_counter = 0
        self.block_counter = 0
        self.variable_map: Dict[str, str] = {}  # AST variable name -> IR variable name
        self.semantic_analyzer = semantic_analyzer
        self.constant_map: Dict[Any, str] = {}  # Constant value -> IR variable name (for optimization)

    def build(self, program: Program, semantic_analyzer=None) -> IRModule:
        """Build IR from AST."""
        logger.debug("Starting IR generation")
        self.module = IRModule()
        self.semantic_analyzer = semantic_analyzer
        program.accept(self)
        logger.debug("IR generation completed")
        return self.module

    def visit_program(self, node: Program) -> None:
        """Visit program node."""
        for decl in node.declarations:
            decl.accept(self)

    def visit_function_declaration(self, node: FunctionDeclaration) -> None:
        """Visit function declaration."""
        # Create IR function
        ir_function = IRFunction(node.name, node.return_type)
        self.current_function = ir_function

        # Add parameters
        param_ir_vars = []
        for param in node.parameters:
            ir_function.parameters.append({
                'name': param.name,
                'type': param.type
            })
            # Map parameter to IR variable
            ir_var = self._new_variable()
            self.variable_map[param.name] = ir_var
            param_ir_vars.append(ir_var)
            
            # Record parameter location for code generation
            # Parameters will be mapped to stack locations in the code generator
            self.module.variable_types[ir_var] = self._get_type_name(param.type)
        
        # Store parameter IR variables for code generation
        ir_function.parameter_ir_vars = param_ir_vars

        # Create entry block
        entry_block = IRBasicBlock("entry")
        ir_function.add_block(entry_block)
        self.current_block = entry_block

        # Visit function body
        for stmt in node.body:
            stmt.accept(self)

        # Add function to module
        self.module.add_function(ir_function)
        
        # Store variable map for this function in the module
        # Use function name as key to store per-function variable maps
        if not hasattr(self.module, 'function_variable_maps'):
            self.module.function_variable_maps = {}
        self.module.function_variable_maps[ir_function.name] = self.variable_map.copy()
        
        # Clear per-function state
        self.current_function = None
        self.current_block = None
        self.variable_map.clear()
        self.constant_map.clear()  # Clear constants for each function

    def visit_variable_declaration(self, node: VariableDeclaration) -> None:
        """Visit variable declaration."""
        if node.initializer:
            # Evaluate initializer
            init_var = self._visit_expression(node.initializer)
            # Map variable name to IR variable
            ir_var = self._new_variable()
            self.variable_map[node.name] = ir_var
            
            # Record variable type from AST node
            type_name = self._get_type_name(node.type)
            self.module.variable_types[ir_var] = type_name
            
            # Only generate assignment if we have a current block (not global)
            if self.current_block:
                self.current_block.add_instruction(
                    IRInstruction("assign", [init_var], ir_var)
                )
        else:
            # Just allocate variable
            ir_var = self._new_variable()
            self.variable_map[node.name] = ir_var
            
            # Record variable type from AST node
            type_name = self._get_type_name(node.type)
            self.module.variable_types[ir_var] = type_name

    def visit_assignment(self, node: Assignment) -> None:
        """Visit assignment."""
        # Evaluate right-hand side
        rhs_var = self._visit_expression(node.value)
        
        # Handle different types of assignment targets
        if isinstance(node.target, Variable):
            # Simple variable assignment
            target_var = self.variable_map.get(node.target.name)
            if not target_var:
                target_var = self._new_variable()
                self.variable_map[node.target.name] = target_var
            # Generate assignment
            self.current_block.add_instruction(
                IRInstruction("assign", [rhs_var], target_var)
            )
        elif isinstance(node.target, ArrayAccess):
            # Array element assignment: array[index] = value
            array_var = self._visit_expression(node.target.array)
            index_var = self._visit_expression(node.target.index)
            # Generate array set instruction
            self.current_block.add_instruction(
                IRInstruction("array_set", [array_var, index_var, rhs_var])
            )
        else:
            # TODO: Handle other assignment targets (member access, etc.)
            pass

    def visit_return_statement(self, node: ReturnStatement) -> None:
        """Visit return statement."""
        if node.value:
            ret_var = self._visit_expression(node.value)
            self.current_block.add_instruction(
                IRInstruction("return", [ret_var])
            )
        else:
            self.current_block.add_instruction(
                IRInstruction("return", [])
            )

    def visit_expression_statement(self, node) -> None:
        """Visit expression statement."""
        # For expression statements, we need to evaluate the expression
        # This is crucial for expressions with side effects like increment/decrement
        self._visit_expression(node.expression)

    def visit_block_statement(self, node) -> None:
        """Visit block statement."""
        for stmt in node.statements:
            stmt.accept(self)

    def visit_if_statement(self, node: IfStatement) -> None:
        """Visit if statement."""
        # Evaluate condition
        cond_var = self._visit_expression(node.condition)

        # Create blocks
        then_block = IRBasicBlock(f"if_then_{self.block_counter}")
        self.block_counter += 1
        else_block = IRBasicBlock(f"if_else_{self.block_counter}") if node.else_branch else None
        self.block_counter += 1
        merge_block = IRBasicBlock(f"if_merge_{self.block_counter}")
        self.block_counter += 1

        # Add conditional branch
        self.current_block.add_instruction(
            IRInstruction("br", [cond_var, then_block.name, (else_block.name if else_block else merge_block.name)])
        )

        # Set up predecessors/successors
        then_block.predecessors.append(self.current_block)
        self.current_block.successors.append(then_block)
        if else_block:
            else_block.predecessors.append(self.current_block)
            self.current_block.successors.append(else_block)
        else:
            merge_block.predecessors.append(self.current_block)
            self.current_block.successors.append(merge_block)

        # Add blocks to function
        self.current_function.add_block(then_block)
        if else_block:
            self.current_function.add_block(else_block)
        self.current_function.add_block(merge_block)

        # Visit then branch
        old_block = self.current_block
        self.current_block = then_block
        for stmt in node.then_branch:
            stmt.accept(self)
        # Jump to merge
        self.current_block.add_instruction(
            IRInstruction("jmp", [merge_block.name])
        )
        merge_block.predecessors.append(self.current_block)
        self.current_block.successors.append(merge_block)

        # Visit else branch if present
        if node.else_branch:
            self.current_block = else_block
            for stmt in node.else_branch:
                stmt.accept(self)
            # Jump to merge
            self.current_block.add_instruction(
                IRInstruction("jmp", [merge_block.name])
            )
            merge_block.predecessors.append(self.current_block)
            self.current_block.successors.append(merge_block)

        # Continue with merge block
        self.current_block = merge_block

    def visit_while_statement(self, node) -> None:
        """Visit while statement."""
        # Create blocks
        loop_header = IRBasicBlock(f"while_header_{self.block_counter}")
        self.block_counter += 1
        loop_body = IRBasicBlock(f"while_body_{self.block_counter}")
        self.block_counter += 1
        loop_exit = IRBasicBlock(f"while_exit_{self.block_counter}")
        self.block_counter += 1

        # Jump to loop header
        self.current_block.add_instruction(
            IRInstruction("jmp", [loop_header.name])
        )
        loop_header.predecessors.append(self.current_block)
        self.current_block.successors.append(loop_header)

        # Set up loop header
        self.current_function.add_block(loop_header)
        self.current_function.add_block(loop_body)
        self.current_function.add_block(loop_exit)

        # Visit condition in loop header block
        old_block = self.current_block
        self.current_block = loop_header
        cond_var = self._visit_expression(node.condition)
        # Branch to body or exit
        self.current_block.add_instruction(
            IRInstruction("br", [cond_var, loop_body.name, loop_exit.name])
        )
        loop_body.predecessors.append(self.current_block)
        loop_exit.predecessors.append(self.current_block)
        self.current_block.successors.extend([loop_body, loop_exit])
        self.current_block = old_block

        # Visit loop body
        old_block = self.current_block
        self.current_block = loop_body
        for stmt in node.body:
            stmt.accept(self)

        # Jump back to header
        self.current_block.add_instruction(
            IRInstruction("jmp", [loop_header.name])
        )
        loop_header.predecessors.append(self.current_block)
        self.current_block.successors.append(loop_header)

        # Continue with exit block
        self.current_block = loop_exit

    def visit_for_statement(self, node) -> None:
        """Visit for statement."""
        # Create blocks
        loop_header = IRBasicBlock(f"for_header_{self.block_counter}")
        self.block_counter += 1
        loop_body = IRBasicBlock(f"for_body_{self.block_counter}")
        self.block_counter += 1
        loop_exit = IRBasicBlock(f"for_exit_{self.block_counter}")
        self.block_counter += 1

        # Visit initializer (if present) BEFORE jumping to loop
        # This ensures initializer is in current context, not inside loop
        if node.initializer:
            node.initializer.accept(self)

        # Jump to loop header AFTER initialization
        self.current_block.add_instruction(
            IRInstruction("jmp", [loop_header.name])
        )
        loop_header.predecessors.append(self.current_block)
        self.current_block.successors.append(loop_header)

        # Create a separate block for increment and jump back
        increment_block = IRBasicBlock(f"for_increment_{self.block_counter}")
        self.block_counter += 1

        # Set up loop header - ADD BLOCKS IN CORRECT ORDER
        self.current_function.add_block(loop_header)
        self.current_function.add_block(loop_body)
        self.current_function.add_block(increment_block)  # ADD INCREMENT BEFORE EXIT
        self.current_function.add_block(loop_exit)

        # Visit condition (if present) - must be done in loop header block
        old_block = self.current_block
        self.current_block = loop_header
        if node.condition:
            cond_var = self._visit_expression(node.condition)
            # Branch to body or exit
            self.current_block.add_instruction(
                IRInstruction("br", [cond_var, loop_body.name, loop_exit.name])
            )
            loop_body.predecessors.append(self.current_block)
            loop_exit.predecessors.append(self.current_block)
            self.current_block.successors.extend([loop_body, loop_exit])
        else:
            # No condition - always enter loop
            self.current_block.add_instruction(
                IRInstruction("jmp", [loop_body.name])
            )
            loop_body.predecessors.append(self.current_block)
            self.current_block.successors.append(loop_body)
        self.current_block = old_block

        # Visit loop body
        old_block = self.current_block

        self.current_block = loop_body
        for stmt in node.body:
            stmt.accept(self)

        # Jump to increment block from loop body
        self.current_block.add_instruction(IRInstruction("jmp", [increment_block.name]))
        increment_block.predecessors.append(self.current_block)
        self.current_block.successors.append(increment_block)

        # Visit increment (if present) in the increment block
        old_block = self.current_block
        self.current_block = increment_block
        if node.increment:
            # Handle increment as an assignment if it's of the form var = expression
            if isinstance(node.increment, Assignment):
                # This is an assignment, visit it normally
                node.increment.accept(self)
            else:
                # This is just an expression, evaluate it
                self._visit_expression(node.increment)

        # Jump back to header
        self.current_block.add_instruction(
            IRInstruction("jmp", [loop_header.name])
        )
        loop_header.predecessors.append(self.current_block)
        self.current_block.successors.append(loop_header)

        # Continue after the loop - set current block to loop_exit
        # This allows subsequent statements to be added after the loop
        self.current_block = loop_exit

    def _visit_expression(self, expr) -> str:
        """Visit expression and return IR variable name."""
        if isinstance(expr, Literal):
            # Check if we already have this constant
            if expr.value in self.constant_map:
                return self.constant_map[expr.value]
            
            # Create new variable for this constant
            ir_var = self._new_variable()
            
            # Set the type for the constant variable
            if hasattr(expr, 'type') and expr.type:
                type_name = self._get_type_name(expr.type)
                self.module.variable_types[ir_var] = type_name
            
            self.current_block.add_instruction(
                IRInstruction("const", [expr.value], ir_var)
            )
            
            # Cache this constant for reuse
            self.constant_map[expr.value] = ir_var
            return ir_var
        elif isinstance(expr, Variable):
            return self.variable_map.get(expr.name, expr.name)
        elif isinstance(expr, BinaryOp):
            left_var = self._visit_expression(expr.left)
            right_var = self._visit_expression(expr.right)
            result_var = self._new_variable()
            # Set the type for the result variable based on the expression type
            if hasattr(expr, 'type') and expr.type:
                type_name = self._get_type_name(expr.type)
                self.module.variable_types[result_var] = type_name
            self.current_block.add_instruction(
                IRInstruction(expr.operator, [left_var, right_var], result_var)
            )
            return result_var
        elif isinstance(expr, UnaryOp):
            operand_var = self._visit_expression(expr.operand)
            
            # Handle increment/decrement operations specially - they modify the original variable
            if expr.operator in ['++', '--']:
                # For increment/decrement, we want to modify the original variable
                # Check if the operand is a simple variable
                if isinstance(expr.operand, Variable):
                    original_var = self.variable_map.get(expr.operand.name, expr.operand.name)
                    # Generate increment instruction that modifies the original variable
                    self.current_block.add_instruction(
                        IRInstruction(f"u{expr.operator}", [original_var], original_var)
                    )
                    return original_var
                else:
                    # For complex expressions, still create a new variable
                    result_var = self._new_variable()
                    if hasattr(expr, 'type') and expr.type:
                        type_name = self._get_type_name(expr.type)
                        self.module.variable_types[result_var] = type_name
                    self.current_block.add_instruction(
                        IRInstruction(f"u{expr.operator}", [operand_var], result_var)
                    )
                    return result_var
            else:
                # For other unary operations, create a new variable
                result_var = self._new_variable()
                # Set the type for the result variable based on the expression type
                if hasattr(expr, 'type') and expr.type:
                    type_name = self._get_type_name(expr.type)
                    self.module.variable_types[result_var] = type_name
                self.current_block.add_instruction(
                    IRInstruction(f"u{expr.operator}", [operand_var], result_var)
                )
                return result_var
        elif isinstance(expr, TernaryOp):
            # Handle ternary operator by delegating to visit_ternary_op
            return self.visit_ternary_op(expr)
        elif isinstance(expr, ArrayAccess):
            # Handle array access
            array_var = self._visit_expression(expr.array)
            index_var = self._visit_expression(expr.index)
            result_var = self._new_variable()
            # Set the type for the result variable based on the expression type
            if hasattr(expr, 'type') and expr.type:
                type_name = self._get_type_name(expr.type)
                self.module.variable_types[result_var] = type_name
            self.current_block.add_instruction(
                IRInstruction("array_get", [array_var, index_var], result_var)
            )
            return result_var
        elif hasattr(expr, 'accept'):  # FunctionCall or other AST nodes
            return expr.accept(self)
        else:
            # For other expression types, return a placeholder
            return "unknown"

    def visit_function_call(self, node: FunctionCall) -> str:
        """Visit function call."""
        # Evaluate arguments
        arg_vars = []
        for arg in node.arguments:
            arg_var = self._visit_expression(arg)
            arg_vars.append(arg_var)

        # Create IR instruction for function call
        result_var = self._new_variable()
        self.current_block.add_instruction(
            IRInstruction("call", [node.name] + arg_vars, result_var)
        )

        return result_var

    def visit_ternary_op(self, node) -> str:
        """Visit ternary conditional operation."""
        # Evaluate condition
        cond_var = self._visit_expression(node.condition)
        
        # Create blocks for then and else branches, and merge block
        then_block = IRBasicBlock(f"ternary_then_{self.block_counter}")
        else_block = IRBasicBlock(f"ternary_else_{self.block_counter}")
        merge_block = IRBasicBlock(f"ternary_merge_{self.block_counter}")
        self.block_counter += 1

        # Create result variable
        result_var = self._new_variable()
        if hasattr(node, 'type') and node.type:
            type_name = self._get_type_name(node.type)
            self.module.variable_types[result_var] = type_name

        # Branch on condition
        self.current_block.add_instruction(
            IRInstruction("branch_if", [cond_var, then_block.name, else_block.name])
        )

        # Add blocks to function
        self.current_function.add_block(then_block)
        self.current_function.add_block(else_block)
        self.current_function.add_block(merge_block)

        # Generate then branch
        self.current_block = then_block
        then_var = self._visit_expression(node.then_expr)
        then_block.add_instruction(
            IRInstruction("assign", [then_var], result_var)
        )
        then_block.add_instruction(
            IRInstruction("jmp", [merge_block.name])
        )

        # Generate else branch
        self.current_block = else_block
        else_var = self._visit_expression(node.else_expr)
        else_block.add_instruction(
            IRInstruction("assign", [else_var], result_var)
        )
        else_block.add_instruction(
            IRInstruction("jmp", [merge_block.name])
        )

        # Continue with merge block
        self.current_block = merge_block
        return result_var

    def visit_switch_statement(self, node) -> None:
        """Visit switch statement."""
        # Evaluate switch expression
        switch_var = self._visit_expression(node.expression)
        
        # Create blocks for each case, default, and end
        case_blocks = []
        case_values = []
        
        for i, case in enumerate(node.cases):
            block_name = f"switch_case_{self.block_counter}_{i}"
            case_block = IRBasicBlock(block_name)
            self.current_function.add_block(case_block)
            case_blocks.append(case_block)
            
            # Evaluate case value
            case_value_var = self._visit_expression(case.value)
            case_values.append(case_value_var)
        
        default_block = None
        if node.default_case:
            default_block = IRBasicBlock(f"switch_default_{self.block_counter}")
            self.current_function.add_block(default_block)
        
        end_block = IRBasicBlock(f"switch_end_{self.block_counter}")
        self.current_function.add_block(end_block)
        self.block_counter += 1
        
        # Store break target for break statements
        old_break_target = getattr(self, '_break_target', None)
        self._break_target = end_block.name
        
        # Generate comparison chain
        for i, (case_value_var, case_block) in enumerate(zip(case_values, case_blocks)):
            next_test_block = IRBasicBlock(f"switch_test_{self.block_counter}_{i}")
            self.current_function.add_block(next_test_block)
            
            # Compare switch value with case value
            cmp_var = self._new_variable()
            self.current_block.add_instruction(
                IRInstruction("eq", [switch_var, case_value_var], cmp_var)
            )
            
            # Branch to case if equal, otherwise continue to next test
            self.current_block.add_instruction(
                IRInstruction("branch_if", [cmp_var, case_block.name, next_test_block.name])
            )
            
            self.current_block = next_test_block
        
        # After all case tests, jump to default or end
        if default_block:
            self.current_block.add_instruction(
                IRInstruction("jmp", [default_block.name])
            )
        else:
            self.current_block.add_instruction(
                IRInstruction("jmp", [end_block.name])
            )
        
        # Generate case bodies
        for i, (case, case_block) in enumerate(zip(node.cases, case_blocks)):
            self.current_block = case_block
            for stmt in case.body:
                stmt.accept(self)
            # If no explicit break, fall through to next case
            if (not case.body or 
                not isinstance(case.body[-1], BreakStatement)):
                if i + 1 < len(case_blocks):
                    # Fall through to next case
                    case_block.add_instruction(
                        IRInstruction("jmp", [case_blocks[i + 1].name])
                    )
                elif default_block:
                    # Fall through to default
                    case_block.add_instruction(
                        IRInstruction("jmp", [default_block.name])
                    )
                else:
                    # Fall through to end
                    case_block.add_instruction(
                        IRInstruction("jmp", [end_block.name])
                    )
        
        # Generate default case if present
        if default_block and node.default_case:
            self.current_block = default_block
            for stmt in node.default_case:
                stmt.accept(self)
            # Jump to end if no explicit break
            if (not node.default_case or 
                not isinstance(node.default_case[-1], BreakStatement)):
                default_block.add_instruction(
                    IRInstruction("jmp", [end_block.name])
                )
        
        # Restore break target
        self._break_target = old_break_target
        
        # Continue with end block
        self.current_block = end_block

    def visit_break_statement(self, node) -> None:
        """Visit break statement."""
        if hasattr(self, '_break_target') and self._break_target:
            self.current_block.add_instruction(
                IRInstruction("jmp", [self._break_target])
            )
        else:
            # Error: break outside loop/switch
            # This should be caught by semantic analysis
            pass

    def visit_continue_statement(self, node) -> None:
        """Visit continue statement."""
        if hasattr(self, '_continue_target') and self._continue_target:
            self.current_block.add_instruction(
                IRInstruction("jmp", [self._continue_target])
            )
        else:
            # Error: continue outside loop
            # This should be caught by semantic analysis
            pass

    def visit_binary_op(self, node) -> str:
        """Visit binary operation and return result variable."""
        left_var = self._visit_expression(node.left)
        right_var = self._visit_expression(node.right)
        result_var = self._new_variable()
        
        op_map = {
            '+': 'add', '-': 'sub', '*': 'mul', '/': 'div', '%': 'mod',
            '==': 'eq', '!=': 'ne', '<': 'lt', '<=': 'le', '>': 'gt', '>=': 'ge',
            '&&': 'and', '||': 'or', '&': 'bitand', '|': 'bitor', '^': 'bitxor',
            '<<': 'shl', '>>': 'shr'
        }
        
        if node.operator in op_map:
            self.current_block.add_instruction(
                IRInstruction(op_map[node.operator], [left_var, right_var], result_var)
            )
        else:
            logger.warning(f"Unknown binary operator: {node.operator}")
            
        return result_var

    def visit_unary_op(self, node) -> str:
        """Visit unary operation and return result variable."""
        operand_var = self._visit_expression(node.operand)
        result_var = self._new_variable()
        
        op_map = {
            '-': 'neg', '!': 'not', '~': 'bitnot',
            '++': 'inc', '--': 'dec'
        }
        
        if node.operator in op_map:
            self.current_block.add_instruction(
                IRInstruction(op_map[node.operator], [operand_var], result_var)
            )
        else:
            logger.warning(f"Unknown unary operator: {node.operator}")
            
        return result_var

    def visit_literal(self, node) -> str:
        """Visit literal and return result variable."""
        result_var = self._new_variable()
        self.current_block.add_instruction(
            IRInstruction("const", [node.value], result_var)
        )
        return result_var

    def visit_variable(self, node) -> str:
        """Visit variable reference and return result variable."""
        # Map AST variable name to IR variable name
        if node.name in self.variable_map:
            return self.variable_map[node.name]
        else:
            # This might be a parameter or global
            return node.name

    def visit_array_access(self, node) -> str:
        """Visit array access and return result variable."""
        array_var = self._visit_expression(node.array)
        index_var = self._visit_expression(node.index)
        result_var = self._new_variable()
        
        self.current_block.add_instruction(
            IRInstruction("array_load", [array_var, index_var], result_var)
        )
        return result_var

    def visit_member_access(self, node) -> str:
        """Visit member access and return result variable."""
        object_var = self._visit_expression(node.object)
        result_var = self._new_variable()
        
        self.current_block.add_instruction(
            IRInstruction("member_load", [object_var, node.member], result_var)
        )
        return result_var

    def visit_hardware_access(self, node) -> str:
        """Visit hardware access and return result variable."""
        result_var = self._new_variable()
        self.current_block.add_instruction(
            IRInstruction("hw_read", [node.register], result_var)
        )
        return result_var

    def visit_struct_declaration(self, node) -> None:
        """Visit struct declaration."""
        # Add struct to module globals
        self.module.globals[node.name] = {
            'type': 'struct',
            'fields': {field.name: field.type for field in node.fields}
        }

    def visit_declaration(self, node) -> None:
        """Visit generic declaration."""
        # Dispatch to specific declaration visitor
        if hasattr(node, 'accept'):
            node.accept(self)

    def visit_statement(self, node) -> None:
        """Visit generic statement."""
        # Dispatch to specific statement visitor
        if hasattr(node, 'accept'):
            node.accept(self)

    def visit_expression(self, node) -> str:
        """Visit generic expression."""
        # Dispatch to specific expression visitor
        return self._visit_expression(node)

    def _new_variable(self, var_type: str = None) -> str:
        """Generate a new IR variable name."""
        var_name = f"v{self.variable_counter}"
        self.variable_counter += 1
        if var_type:
            self.module.variable_types[var_name] = var_type
        return var_name

    def _get_type_name(self, data_type) -> str:
        """Convert DataType to string representation."""
        if hasattr(data_type, 'name'):
            return data_type.name.lower()
        else:
            return str(data_type).lower()
