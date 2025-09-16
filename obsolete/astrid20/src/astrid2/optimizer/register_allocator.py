"""
Astrid 2.0 Graph Coloring Register Allocator
Implements advanced register allocation using graph coloring algorithm.
"""

from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque

from ..utils.logger import get_logger
from ..ir.builder import IRModule, IRFunction, IRBasicBlock, IRInstruction

logger = get_logger(__name__)


class InterferenceGraph:
    """Interference graph for register allocation."""

    def __init__(self):
        self.nodes = set()  # Set of variables
        self.edges = defaultdict(set)  # variable -> set of interfering variables
        self.node_types = {}  # variable -> type (int8 or int16)
        self.live_ranges = {}  # variable -> (start, end) instruction indices

    def add_variable(self, var: str, var_type: str):
        """Add a variable to the interference graph."""
        self.nodes.add(var)
        self.node_types[var] = var_type

    def add_interference(self, var1: str, var2: str):
        """Add an interference edge between two variables."""
        if var1 != var2:
            self.edges[var1].add(var2)
            self.edges[var2].add(var1)

    def get_neighbors(self, var: str) -> Set[str]:
        """Get neighbors of a variable in the interference graph."""
        return self.edges[var].copy()

    def get_variables_by_type(self, var_type: str) -> List[str]:
        """Get all variables of a specific type."""
        return [var for var, vtype in self.node_types.items() if vtype == var_type]

    def degree(self, var: str) -> int:
        """Get degree of a variable in the graph."""
        return len(self.edges[var])


class GraphColoringRegisterAllocator:
    """Graph coloring register allocator for Astrid 2.0."""

    def __init__(self):
        # Available registers by type (P8=SP, P9=FP are reserved)
        # Reorder to separate caller-save vs callee-save for better allocation
        self.r_registers = ['R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R0', 'R1', 'R8', 'R9']  # Prioritize callee-save first
        self.p_registers = ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7']  # P8, P9 removed but keep order
        
        # Separate register sets for different contexts
        self.caller_save_r_registers = ['R0', 'R1', 'R8', 'R9']  # May be clobbered by function calls
        self.callee_save_r_registers = ['R2', 'R3', 'R4', 'R5', 'R6', 'R7']  # Preserved across function calls
        self.parameter_r_registers = ['R2', 'R3', 'R4', 'R5', 'R6', 'R7']  # Used for parameter passing
        
        # Define register classes for different purposes
        self.loop_protected_registers = ['P2', 'P3', 'P4']  # Protected registers for loop counters
        self.caller_save_registers = ['R0', 'R1', 'R8', 'R9', 'P0', 'P1']  # May be clobbered by function calls
        self.callee_save_registers = ['R2', 'R3', 'R4', 'R5', 'R6', 'R7']  # Preserved across function calls
        self.local_registers = ['P5', 'P6', 'P7']  # For local variables
        
        # Function calling convention registers
        self.parameter_registers = ['R2', 'R3', 'R4', 'R5', 'R6', 'R7']  # Function parameters passed in these
        self.return_register = 'R0'  # Function return values
        
        # Different register sets for different function types
        self.main_r_registers = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']  # Main can use all
        self.user_function_r_registers = ['R0', 'R1', 'R8', 'R9']  # User functions avoid param registers for locals
        self.user_function_p_registers = ['P5', 'P6', 'P7']  # User functions use local P registers

        # Register allocation results
        self.allocation = {}  # variable -> register
        self.spilled_vars = set()  # variables that need to be spilled to memory
        self.loop_variables = set()  # variables identified as loop counters
        
        # Function analysis results
        self.function_signatures = {}  # function_name -> parameter_count
        self.functions_with_calls = set()  # functions that make calls

    def allocate_registers(self, ir_module: IRModule) -> Dict[str, str]:
        """
        Perform graph coloring register allocation on the IR module.

        Returns:
            Dictionary mapping variables to allocated registers
        """
        logger.info("Starting graph coloring register allocation")

        # Step 1: Analyze function signatures and calling patterns
        self._analyze_function_signatures(ir_module)
        self._analyze_function_calls(ir_module)

        # Step 2: Build interference graph for each function
        for function in ir_module.functions:
            self._allocate_function_registers(function)

        logger.info(f"Register allocation completed. Allocated: {len(self.allocation)}, Spilled: {len(self.spilled_vars)}")
        return self.allocation

    def _analyze_function_signatures(self, ir_module: IRModule):
        """Analyze function signatures to understand parameter requirements."""
        self.function_signatures = {}
        for function in ir_module.functions:
            param_count = len(function.parameters) if function.parameters else 0
            self.function_signatures[function.name] = param_count
            logger.debug(f"Function {function.name} has {param_count} parameters")
            
    def _analyze_function_calls(self, ir_module: IRModule):
        """Identify which functions make calls to other functions."""
        self.functions_with_calls = set()
        for function in ir_module.functions:
            has_calls = False
            for block in function.blocks:
                for instruction in block.instructions:
                    if instruction.opcode == 'call':
                        has_calls = True
                        break
                if has_calls:
                    break
            
            if has_calls:
                self.functions_with_calls.add(function.name)
                logger.debug(f"Function {function.name} makes function calls")

    def _allocate_function_registers(self, function: IRFunction):
        """Allocate registers for a single function with calling convention awareness."""
        logger.debug(f"Allocating registers for function: {function.name}")

        # Determine function characteristics
        is_main = function.name == 'main'
        has_parameters = len(function.parameters) > 0 if function.parameters else False
        makes_calls = function.name in getattr(self, 'functions_with_calls', set())
        param_count = getattr(self, 'function_signatures', {}).get(function.name, 0)
        
        logger.debug(f"Function {function.name}: main={is_main}, params={param_count}, calls={makes_calls}")

        # First, detect loop variables that need protection
        self.loop_variables = self._detect_loop_variables(function)
        logger.debug(f"Detected loop variables: {self.loop_variables}")

        # Build interference graph
        interference_graph = self._build_interference_graph(function)

        # Choose register sets based on function type and characteristics
        if is_main:
            # Main function can use broader register set, but be careful with calls
            r_regs = self.r_registers.copy()
            p_regs = self.p_registers.copy()
            
            if makes_calls:
                # If main makes calls, prioritize callee-save registers for long-lived variables
                r_regs = ['R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R0', 'R1', 'R8', 'R9']
        else:
            # User-defined functions should use different approach
            # For functions with parameters, give priority to R2, R3, etc. for parameters
            if has_parameters and param_count > 0:
                # Allocate parameters to their conventional registers first
                param_registers = ['R2', 'R3', 'R4', 'R5', 'R6', 'R7'][:param_count]
                local_registers = ['R0', 'R1', 'R8', 'R9'] + ['R2', 'R3', 'R4', 'R5', 'R6', 'R7'][param_count:]
                r_regs = param_registers + local_registers
            else:
                # No parameters, use caller-save registers for locals
                r_regs = ['R0', 'R1', 'R8', 'R9', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7']
            
            p_regs = ['P5', 'P6', 'P7', 'P0', 'P1', 'P2', 'P3', 'P4']  # Local P registers first

        # Color the graph for int8 variables (R registers)
        self._color_graph(interference_graph, 'int8', r_regs)

        # Color the graph for int16 variables (P registers) with loop protection
        self._color_graph_with_loop_protection(interference_graph, 'int16', p_regs)

    def _build_interference_graph(self, function: IRFunction) -> InterferenceGraph:
        """Build interference graph for a function."""
        graph = InterferenceGraph()

        # Collect all variables and their types
        var_types = self._collect_variable_types(function)

        # Add all variables to graph
        for var, var_type in var_types.items():
            graph.add_variable(var, var_type)

        # Build live ranges and interference
        self._build_live_ranges_and_interference(function, graph)

        return graph

    def _collect_variable_types(self, function: IRFunction) -> Dict[str, str]:
        """Collect types of all variables in the function."""
        var_types = {}

        # Get types from IR module if available
        if hasattr(function, 'module') and hasattr(function.module, 'variable_types'):
            # Use type information from semantic analysis
            for ir_var, var_type in function.module.variable_types.items():
                var_types[ir_var] = var_type
        else:
            # Fallback to inference from instructions
            pass

        # From parameters
        for param in function.parameters:
            var_types[param['name']] = self._map_type_to_register_class(param['type'])

        # From instructions (for variables not in semantic info)
        for block in function.blocks:
            for instr in block.instructions:
                if instr.result and instr.result not in var_types:
                    # Infer type from instruction (simplified)
                    var_types[instr.result] = self._infer_variable_type(instr, function)

        return var_types

    def _map_type_to_register_class(self, ast_type) -> str:
        """Map AST type to register class (int8 or int16)."""
        if hasattr(ast_type, 'name'):
            type_name = ast_type.name
        else:
            type_name = str(ast_type).lower()

        # Map hardware types to register classes
        if type_name in ['int8', 'pixel', 'color', 'sound']:
            return 'int8'
        else:
            return 'int16'  # int16, layer, sprite, interrupt default to 16-bit

    def _infer_variable_type(self, instr: IRInstruction, function: IRFunction) -> str:
        """Infer variable type from instruction (simplified heuristic)."""
        # Look at operands to infer type
        for operand in instr.operands:
            if isinstance(operand, int):
                if 0 <= operand <= 255:
                    return 'int8'
                else:
                    return 'int16'
            elif isinstance(operand, str):
                # Check if operand is a variable with known type
                if operand in function.module.variable_types:
                    return self._map_type_to_register_class(function.module.variable_types[operand])
                # For now, assume int16 for unknown variables
                pass

        return 'int16'  # Default

    def _build_live_ranges_and_interference(self, function: IRFunction, graph: InterferenceGraph):
        """Build live ranges and interference edges using improved analysis."""
        
        # Collect all variables used in the function
        all_variables = set()
        
        for block in function.blocks:
            for instr in block.instructions:
                # Add result variable
                if instr.result and instr.result in graph.node_types:
                    all_variables.add(instr.result)
                
                # Add operand variables
                for operand in instr.operands:
                    if isinstance(operand, str) and operand in graph.node_types:
                        all_variables.add(operand)
        
        # Check if this function has loops (blocks with "for" in the name or back edges)
        has_loops = any("for_" in block.name or "loop_" in block.name or "while_" in block.name for block in function.blocks)
        is_complex = len(all_variables) > 20  # Consider functions with many variables as complex
        
        if has_loops and is_complex:
            # Improved conservative approach: Use block-level interference instead of function-wide
            # Group variables by the blocks they're used in
            block_variables = {}
            for block in function.blocks:
                block_vars = set()
                for instr in block.instructions:
                    if instr.result and instr.result in graph.node_types:
                        block_vars.add(instr.result)
                    for operand in instr.operands:
                        if isinstance(operand, str) and operand in graph.node_types:
                            block_vars.add(operand)
                block_variables[block.name] = block_vars
            
            # Variables used in the same block interfere with each other
            for block_name, vars_in_block in block_variables.items():
                vars_list = list(vars_in_block)
                for i in range(len(vars_list)):
                    for j in range(i + 1, len(vars_list)):
                        graph.add_interference(vars_list[i], vars_list[j])
            
            # Variables that span multiple blocks also interfere
            # Find variables used in multiple blocks
            var_blocks = {}
            for block_name, vars_in_block in block_variables.items():
                for var in vars_in_block:
                    if var not in var_blocks:
                        var_blocks[var] = []
                    var_blocks[var].append(block_name)
            
            # Variables that appear in multiple blocks interfere with each other
            multi_block_vars = [var for var, blocks in var_blocks.items() if len(blocks) > 1]
            for i in range(len(multi_block_vars)):
                for j in range(i + 1, len(multi_block_vars)):
                    graph.add_interference(multi_block_vars[i], multi_block_vars[j])
            
            logger.debug(f"Block-based conservative allocation: {len(all_variables)} total variables, {len(multi_block_vars)} span multiple blocks")
        elif has_loops:
            # For simple functions with loops but few variables, use per-block analysis
            self._simple_block_interference_analysis(function, graph, all_variables)
        else:
            # For functions without loops, use proper live variable analysis
            self._detailed_live_variable_analysis(function, graph, all_variables)
    
    def _simple_block_interference_analysis(self, function: IRFunction, graph: InterferenceGraph, all_variables: set):
        """Simple block-level interference for functions with loops but few variables."""
        for block in function.blocks:
            block_vars = set()
            for instr in block.instructions:
                if instr.result and instr.result in graph.node_types:
                    block_vars.add(instr.result)
                for operand in instr.operands:
                    if isinstance(operand, str) and operand in graph.node_types:
                        block_vars.add(operand)
            
            # Variables in the same block interfere
            vars_list = list(block_vars)
            for i in range(len(vars_list)):
                for j in range(i + 1, len(vars_list)):
                    graph.add_interference(vars_list[i], vars_list[j])
        
        logger.debug(f"Simple block interference: {len(all_variables)} variables in {len(function.blocks)} blocks")

    def _detailed_live_variable_analysis(self, function: IRFunction, graph: InterferenceGraph, all_variables: set):
        """Detailed live variable analysis for functions without complex control flow."""
        
        # Build control flow graph
        successors = self._build_control_flow_graph(function)
        
        # Simple analysis: variables are live from definition to last use
        for block in function.blocks:
            live_in_block = set()
            
            # Track variables defined and used in this block
            for instr in block.instructions:
                # Variables used by this instruction are live
                for operand in instr.operands:
                    if isinstance(operand, str) and operand in graph.node_types:
                        live_in_block.add(operand)
                
                # Result variable is also live (overlaps with usage)
                if instr.result and instr.result in graph.node_types:
                    live_in_block.add(instr.result)
            
            # All variables live in this block interfere with each other
            live_list = list(live_in_block)
            for i in range(len(live_list)):
                for j in range(i + 1, len(live_list)):
                    graph.add_interference(live_list[i], live_list[j])

    def _build_control_flow_graph(self, function: IRFunction) -> Dict[IRBasicBlock, List[IRBasicBlock]]:
        """Build control flow graph showing successors of each block."""
        successors = {}
        
        # Build name to block map
        name_to_block = {block.name: block for block in function.blocks}
        
        for i, block in enumerate(function.blocks):
            successors[block] = []
            
            # Check for control flow instructions
            if block.instructions:
                last_instr = block.instructions[-1]
                
                # Branch instructions
                if last_instr.opcode == 'jmp':
                    label = last_instr.operands[0]
                    if label in name_to_block:
                        successors[block].append(name_to_block[label])
                elif last_instr.opcode == 'br':
                    then_label = last_instr.operands[1]
                    else_label = last_instr.operands[2] if len(last_instr.operands) > 2 else None
                    if then_label in name_to_block:
                        successors[block].append(name_to_block[then_label])
                    if else_label and else_label in name_to_block:
                        successors[block].append(name_to_block[else_label])
                elif last_instr.opcode in ['ret', 'hlt']:
                    # No successors for return/halt
                    pass
                else:
                    # Fall through to next block
                    if i + 1 < len(function.blocks):
                        successors[block].append(function.blocks[i + 1])
            else:
                # Empty block falls through
                if i + 1 < len(function.blocks):
                    successors[block].append(function.blocks[i + 1])
        
        return successors

    def _color_graph(self, graph: InterferenceGraph, var_type: str, available_registers: List[str]):
        """Color the interference graph using greedy graph coloring algorithm with function awareness."""
        variables = graph.get_variables_by_type(var_type)

        if not variables:
            return

        logger.debug(f"Coloring {len(variables)} {var_type} variables with {len(available_registers)} registers")

        # Debug: Print interference information
        for var in variables:
            neighbors = graph.get_neighbors(var)
            logger.debug(f"Variable {var} interferes with: {neighbors}")

        # Separate variables by type and priority:
        # 1. Parameters should get priority for their designated registers
        # 2. Local variables get remaining registers
        # 3. Temporary variables use any available registers
        
        param_vars = []
        local_vars = []
        temp_vars = []
        
        for var in variables:
            if var.startswith('param_') or '_param' in var or var in ['x', 'y', 'a', 'b']:  # Parameter patterns
                param_vars.append(var)
            elif var.startswith('temp_') or var.startswith('t'):  # Temporary patterns
                temp_vars.append(var)
            else:
                local_vars.append(var)
        
        # Sort each category by degree (highest degree first) for better coloring
        param_vars.sort(key=lambda v: graph.degree(v), reverse=True)
        local_vars.sort(key=lambda v: graph.degree(v), reverse=True)  
        temp_vars.sort(key=lambda v: graph.degree(v), reverse=True)
        
        # Allocate in priority order: parameters first, then locals, then temps
        allocation_order = param_vars + local_vars + temp_vars

        # Track used colors (registers) for each variable
        var_colors = {}  # variable -> color (register index)

        for var in allocation_order:
            # Find available colors (registers) not used by neighbors
            used_colors = set()
            neighbor_regs = []
            for neighbor in graph.get_neighbors(var):
                if neighbor in var_colors:
                    used_colors.add(var_colors[neighbor])
                    neighbor_regs.append(f"{neighbor}:{available_registers[var_colors[neighbor]]}")

            # Find first available color
            color = 0
            while color in used_colors and color < len(available_registers):
                color += 1

            if color < len(available_registers):
                var_colors[var] = color
                register = available_registers[color]
                self.allocation[var] = register
                logger.debug(f"Allocated {register} to {var} (type: {'param' if var in param_vars else 'local' if var in local_vars else 'temp'}, neighbors: {neighbor_regs})")
            else:
                # Spill to memory
                self.spilled_vars.add(var)
                logger.debug(f"Spilled {var} to memory (neighbors: {neighbor_regs})")
                
        # Additional check: Verify no conflicts in final allocation
        conflicts = []
        for var1 in variables:
            if var1 in self.allocation:
                for var2 in variables:
                    if (var2 in self.allocation and var1 != var2 and 
                        self.allocation[var1] == self.allocation[var2] and
                        var2 in graph.get_neighbors(var1)):
                        conflicts.append((var1, var2, self.allocation[var1]))
        
        if conflicts:
            logger.error(f"Register allocation conflicts detected: {len(conflicts)} conflicts")
            # Resolve conflicts by spilling variables - FIX: check if variable exists before deletion
            resolved_conflicts = set()
            for var1, var2, reg in conflicts:
                conflict_key = tuple(sorted([var1, var2]))
                if conflict_key not in resolved_conflicts:
                    # Choose which variable to spill (prefer spilling var2 to maintain some consistency)
                    var_to_spill = var2
                    if var_to_spill in self.allocation:  # CRITICAL FIX: Check before deletion
                        logger.warning(f"Spilling {var_to_spill} due to conflict with {var1} on {reg}")
                        del self.allocation[var_to_spill]
                        self.spilled_vars.add(var_to_spill)
                        resolved_conflicts.add(conflict_key)
                    else:
                        logger.debug(f"Variable {var_to_spill} already spilled, skipping conflict resolution")

    def get_allocation(self) -> Dict[str, str]:
        """Get the register allocation mapping."""
        return self.allocation.copy()

    def get_spilled_variables(self) -> Set[str]:
        """Get variables that were spilled to memory."""
        return self.spilled_vars.copy()

    def _detect_loop_variables(self, function: IRFunction) -> Set[str]:
        """Detect variables that serve as loop counters and need protection."""
        loop_vars = set()
        
        # Look for patterns that indicate loop variables:
        # 1. Variables used in for_header blocks (comparisons)
        # 2. Variables modified in for_increment blocks
        # 3. Variables that appear in both patterns
        
        header_vars = set()
        increment_vars = set()
        
        for block in function.blocks:
            if "for_header" in block.name:
                # Variables used in loop condition checks
                for instr in block.instructions:
                    if instr.opcode in ['cmp', 'jc', 'jz', 'jnz']:
                        for operand in instr.operands:
                            if isinstance(operand, str) and operand.startswith('v'):
                                header_vars.add(operand)
            
            elif "for_increment" in block.name:
                # Variables modified in loop increment
                for instr in block.instructions:
                    if instr.opcode in ['add', 'inc', 'sub', 'dec']:
                        if instr.result and instr.result.startswith('v'):
                            increment_vars.add(instr.result)
                        for operand in instr.operands:
                            if isinstance(operand, str) and operand.startswith('v'):
                                increment_vars.add(operand)
        
        # Variables that appear in both header and increment are likely loop counters
        loop_vars = header_vars.intersection(increment_vars)
        
        # Also check for simple increment patterns like "i = i + 1"
        for block in function.blocks:
            if "for_increment" in block.name or "for_body" in block.name:
                for instr in block.instructions:
                    if instr.opcode == 'add' and len(instr.operands) >= 2:
                        if (instr.result and instr.result == instr.operands[0] and 
                            isinstance(instr.operands[1], int) and instr.operands[1] == 1):
                            loop_vars.add(instr.result)
        
        logger.debug(f"Loop detection: header_vars={header_vars}, increment_vars={increment_vars}, loop_vars={loop_vars}")
        return loop_vars

    def _color_graph_with_loop_protection(self, graph: InterferenceGraph, var_type: str, available_registers: List[str]):
        """Color the interference graph with special protection for loop variables."""
        variables = graph.get_variables_by_type(var_type)

        if not variables:
            return

        logger.debug(f"Coloring {len(variables)} {var_type} variables with loop protection")

        # Separate loop variables from regular variables
        loop_vars = [var for var in variables if var in self.loop_variables]
        regular_vars = [var for var in variables if var not in self.loop_variables]
        
        # Allocate loop variables to protected registers first
        if loop_vars:
            logger.debug(f"Allocating {len(loop_vars)} loop variables to protected registers")
            protected_regs = self.loop_protected_registers.copy()
            self._allocate_variables_to_registers(graph, loop_vars, protected_regs)
        
        # Allocate remaining variables to remaining registers
        if regular_vars:
            remaining_regs = [reg for reg in available_registers if reg not in self.allocation.values()]
            logger.debug(f"Allocating {len(regular_vars)} regular variables to {len(remaining_regs)} remaining registers")
            self._allocate_variables_to_registers(graph, regular_vars, remaining_regs)

    def _allocate_variables_to_registers(self, graph: InterferenceGraph, variables: List[str], available_registers: List[str]):
        """Allocate a list of variables to a list of available registers using graph coloring."""
        if not variables:
            return

        # Sort variables by degree (highest degree first) for better coloring
        variables.sort(key=lambda v: graph.degree(v), reverse=True)

        # Track used colors (registers) for each variable
        var_colors = {}  # variable -> color (register index)

        for var in variables:
            # Find available colors (registers) not used by neighbors
            used_colors = set()
            neighbor_regs = []
            for neighbor in graph.get_neighbors(var):
                if neighbor in var_colors:
                    used_colors.add(var_colors[neighbor])
                    neighbor_regs.append(f"{neighbor}:{available_registers[var_colors[neighbor]]}")

            # Find first available color
            color = 0
            while color in used_colors and color < len(available_registers):
                color += 1

            if color < len(available_registers):
                var_colors[var] = color
                register = available_registers[color]
                self.allocation[var] = register
                logger.debug(f"Allocated {register} to {var} (neighbors: {neighbor_regs})")
            else:
                # Spill to memory
                self.spilled_vars.add(var)
                logger.debug(f"Spilled {var} to memory (neighbors: {neighbor_regs})")
