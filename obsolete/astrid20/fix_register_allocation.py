#!/usr/bin/env python3
"""
Fix register allocation to prevent conflicts between function-scope variables and caller variables.

The main issues to fix:
1. Functions use R2-R7 for parameters, but both caller and callee allocate these registers independently
2. No coordination between caller and callee register usage
3. Caller-save registers are preserved but allocation doesn't account for function call conventions

Solution:
1. Implement function-aware register allocation
2. Reserve parameter registers for functions that have parameters
3. Use different register allocation strategies for functions vs main code
4. Ensure proper caller-save vs callee-save register usage
"""

import os
import sys

# Add paths for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from typing import Dict, List, Set
from astrid2.optimizer.register_allocator import GraphColoringRegisterAllocator, InterferenceGraph
from astrid2.ir.builder import IRModule, IRFunction
from astrid2.utils.logger import get_logger

logger = get_logger(__name__)

class ImprovedRegisterAllocator(GraphColoringRegisterAllocator):
    """Improved register allocator that handles function calling conventions properly."""
    
    def __init__(self):
        super().__init__()
        
        # Define parameter passing registers (R2-R7 for parameters)
        self.parameter_registers = ['R2', 'R3', 'R4', 'R5', 'R6', 'R7']
        
        # Define different register sets for different contexts
        self.main_function_registers = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']
        self.user_function_registers = ['R0', 'R1', 'R8', 'R9']  # Avoid parameter registers for local vars
        self.return_value_register = 'R0'  # Functions return values in R0
        
        # P register allocation
        self.main_p_registers = ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7']
        self.user_p_registers = ['P5', 'P6', 'P7']  # Local variables use these
        
        # Track function calling information
        self.function_signatures = {}  # function_name -> parameter_count
        self.functions_with_calls = set()  # functions that make calls
        
    def allocate_registers(self, ir_module: IRModule) -> Dict[str, str]:
        """Perform function-aware register allocation."""
        logger.info("Starting improved function-aware register allocation")
        
        # Step 1: Analyze all functions to understand their signatures and call patterns
        self._analyze_function_signatures(ir_module)
        self._analyze_function_calls(ir_module)
        
        # Step 2: Allocate registers for each function with context awareness
        for function in ir_module.functions:
            self._allocate_function_registers_improved(function)
            
        logger.info(f"Improved allocation completed. Allocated: {len(self.allocation)}, Spilled: {len(self.spilled_vars)}")
        return self.allocation
        
    def _analyze_function_signatures(self, ir_module: IRModule):
        """Analyze function signatures to understand parameter requirements."""
        for function in ir_module.functions:
            param_count = len(function.parameters) if function.parameters else 0
            self.function_signatures[function.name] = param_count
            logger.debug(f"Function {function.name} has {param_count} parameters")
            
    def _analyze_function_calls(self, ir_module: IRModule):
        """Identify which functions make calls to other functions."""
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
                
    def _allocate_function_registers_improved(self, function: IRFunction):
        """Allocate registers for a function with calling convention awareness."""
        logger.debug(f"Allocating registers for function: {function.name}")
        
        # Determine allocation strategy based on function type
        is_main = function.name == 'main'
        has_parameters = len(function.parameters) > 0 if function.parameters else False
        makes_calls = function.name in self.functions_with_calls
        
        # Build interference graph
        interference_graph = self._build_interference_graph(function)
        
        # Choose appropriate register sets
        if is_main:
            # Main function can use all registers since it's the entry point
            r_regs = self.main_function_registers.copy()
            p_regs = self.main_p_registers.copy()
            
            # If main makes calls, avoid using caller-save registers for long-lived variables
            if makes_calls:
                # Prioritize callee-save registers for variables that span across calls
                r_regs = ['R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R0', 'R1', 'R8', 'R9']
                
        else:
            # User-defined functions need to respect calling conventions
            r_regs = self.user_function_registers.copy()
            p_regs = self.user_p_registers.copy()
            
            # For functions with parameters, handle parameter register allocation specially
            if has_parameters:
                self._allocate_parameter_registers(function, interference_graph)
                # Remove parameter registers from general allocation pool
                param_count = len(function.parameters)
                used_param_regs = self.parameter_registers[:param_count]
                r_regs = [r for r in r_regs if r not in used_param_regs]
        
        # Color the graphs with appropriate register sets
        self._color_graph(interference_graph, 'int8', r_regs)
        self._color_graph(interference_graph, 'int16', p_regs)
        
    def _allocate_parameter_registers(self, function: IRFunction, graph: InterferenceGraph):
        """Allocate specific registers for function parameters."""
        if not function.parameters:
            return
            
        for i, param in enumerate(function.parameters):
            if i < len(self.parameter_registers):
                param_reg = self.parameter_registers[i]
                param_name = param['name']
                
                # Map parameter directly to its designated register
                self.allocation[param_name] = param_reg
                logger.debug(f"Allocated parameter {param_name} to {param_reg}")
                
                # Add this parameter to the graph if it's not already there
                param_type = self._map_type_to_register_class(param['type'])
                if param_name not in graph.nodes:
                    graph.add_variable(param_name, param_type)
    
    def _color_graph(self, graph: InterferenceGraph, var_type: str, available_registers: List[str]):
        """Enhanced graph coloring with better conflict resolution."""
        variables = graph.get_variables_by_type(var_type)
        
        if not variables:
            return
            
        logger.debug(f"Coloring {len(variables)} {var_type} variables with {len(available_registers)} registers")
        
        # Separate already-allocated variables (like parameters) from unallocated ones
        allocated_vars = [var for var in variables if var in self.allocation]
        unallocated_vars = [var for var in variables if var not in self.allocation]
        
        logger.debug(f"Pre-allocated: {len(allocated_vars)}, Unallocated: {len(unallocated_vars)}")
        
        # Remove registers already used by pre-allocated variables
        used_registers = {self.allocation[var] for var in allocated_vars if self.allocation[var] in available_registers}
        remaining_registers = [reg for reg in available_registers if reg not in used_registers]
        
        logger.debug(f"Used registers: {used_registers}, Remaining: {len(remaining_registers)}")
        
        # Sort unallocated variables by degree (highest degree first)
        unallocated_vars.sort(key=lambda v: graph.degree(v), reverse=True)
        
        # Allocate remaining variables
        var_colors = {}  # variable -> color index
        
        for var in unallocated_vars:
            # Find colors used by neighbors (both pre-allocated and newly allocated)
            used_colors = set()
            neighbor_info = []
            
            for neighbor in graph.get_neighbors(var):
                if neighbor in self.allocation:
                    # Neighbor is already allocated
                    neighbor_reg = self.allocation[neighbor]
                    if neighbor_reg in remaining_registers:
                        color = remaining_registers.index(neighbor_reg)
                        used_colors.add(color)
                        neighbor_info.append(f"{neighbor}:{neighbor_reg}")
                elif neighbor in var_colors:
                    # Neighbor was allocated in this round
                    used_colors.add(var_colors[neighbor])
                    neighbor_info.append(f"{neighbor}:{remaining_registers[var_colors[neighbor]]}")
            
            # Find first available color
            color = 0
            while color in used_colors and color < len(remaining_registers):
                color += 1
                
            if color < len(remaining_registers):
                var_colors[var] = color
                register = remaining_registers[color]
                self.allocation[var] = register
                logger.debug(f"Allocated {register} to {var} (neighbors: {neighbor_info})")
            else:
                # Spill to memory
                self.spilled_vars.add(var)
                logger.debug(f"Spilled {var} to memory (neighbors: {neighbor_info})")
        
        # Verify no conflicts
        self._verify_no_register_conflicts(variables, graph)
        
    def _verify_no_register_conflicts(self, variables: List[str], graph: InterferenceGraph):
        """Verify that there are no register allocation conflicts."""
        conflicts = []
        
        for var1 in variables:
            if var1 in self.allocation:
                for var2 in variables:
                    if (var2 in self.allocation and var1 != var2 and 
                        self.allocation[var1] == self.allocation[var2] and
                        var2 in graph.get_neighbors(var1)):
                        conflicts.append((var1, var2, self.allocation[var1]))
        
        if conflicts:
            logger.error(f"Register allocation conflicts detected: {conflicts}")
            # Resolve by spilling the second variable in each conflict
            for var1, var2, reg in conflicts:
                logger.warning(f"Resolving conflict: spilling {var2} (conflicts with {var1} on {reg})")
                del self.allocation[var2]
                self.spilled_vars.add(var2)
        else:
            logger.debug("No register conflicts detected")

def test_improved_allocator():
    """Test the improved register allocator."""
    print("=== TESTING IMPROVED REGISTER ALLOCATOR ===")
    
    from astrid2.main import AstridCompiler
    
    # Test case: function with parameters
    test_code = """
int8 add(int8 x, int8 y) {
    int8 temp = x + y;
    return temp;
}

void main() {
    int8 a = 10;
    int8 b = 20;
    int8 result = add(a, b);
    halt();
}
"""
    
    print("Test code:")
    print(test_code)
    print()
    
    compiler = AstridCompiler()
    
    # Compile with original allocator
    try:
        print("=== ORIGINAL ALLOCATOR ===")
        assembly_orig = compiler.compile(test_code, "test_improved.ast")
        print("Generated Assembly:")
        print(assembly_orig)
        print()
    except Exception as e:
        print(f"Original compilation failed: {e}")
    
    # Now test with improved allocator (would need integration)
    print("=== ANALYSIS ===")
    print("Expected improvements:")
    print("1. Function parameters (x, y) should be allocated to R2, R3")
    print("2. Local variables in 'add' should avoid R2, R3")
    print("3. Variables in 'main' should be allocated efficiently")
    print("4. No register conflicts between caller and callee")

if __name__ == "__main__":
    test_improved_allocator()
