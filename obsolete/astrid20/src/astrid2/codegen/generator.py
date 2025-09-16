"""
Astrid 2.0 Code Generator
"""

from typing import List, Optional
from ..utils.logger import get_logger
from ..ir.builder import IRModule, IRFunction, IRBasicBlock, IRInstruction

logger = get_logger(__name__)


class CodeGenerator:
    """Code generator for Astrid 2.0."""

    def __init__(self):
        self.variable_locations = {}  # IR variable -> location (register, stack, or memory)
        self.next_memory_location = 0x2000  # Start allocating variables from 0x2000
        self.string_literals = {}  # String literal values -> memory addresses
        self.next_string_location = 0x3000  # Start allocating strings from 0x3000
        
        # Register allocation - prioritize stable registers for variables
        # Reserve R0-R1 and R8-R9 for temps, use R2-R7 for variables
        self.available_r_registers = ['R2', 'R3', 'R4', 'R5', 'R6', 'R7']  # Variables first  
        self.available_p_registers = ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7']  # Variables first
        self.allocated_registers = set()  # Currently allocated registers
        self.temp_allocated_registers = set()  # Temporarily allocated registers
        self.register_map = {}  # IR variable -> allocated register
        self.stack_map = {}  # IR variable -> stack offset from FP
        self.spilled_vars = set()  # Variables spilled to memory
        self.constant_map = {}  # IR variable -> constant value
        self.label_counter = 0  # For generating unique labels
        self.current_stack_offset = 0  # Current stack frame offset for local variables
        self.max_stack_offset = 0  # Maximum stack space needed for this function

    def generate(self, ir_module: IRModule) -> str:
        """Generate assembly code from IR."""
        logger.debug("Starting code generation")

        # Use register allocation from optimizer if available
        if hasattr(ir_module, 'register_allocation'):
            self.register_map = ir_module.register_allocation.copy()
            self.spilled_vars = getattr(ir_module, 'spilled_variables', set())
            self._has_optimized_allocation = True
            logger.debug(f"Using optimized register allocation: {len(self.register_map)} registers allocated")
            # Update available and allocated lists
            self.allocated_registers = set(self.register_map.values())
            self.available_r_registers = [r for r in ['R2', 'R3', 'R4', 'R5', 'R6', 'R7'] if r not in self.allocated_registers]
            self.available_p_registers = [p for p in ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7'] if p not in self.allocated_registers]
        else:
            # Fallback to simple allocation
            self.register_map = {}
            self.spilled_vars = set()
            self._has_optimized_allocation = False
            logger.debug("Using simple register allocation")
            self.allocated_registers.clear()
            self.available_r_registers = ['R2', 'R3', 'R4', 'R5', 'R6', 'R7']
            self.available_p_registers = ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7']  # P8=SP, P9=FP reserved
            self.available_r_registers = ['R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9', 'R0', 'R1']
            self.available_p_registers = ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7']  # P8=SP, P9=FP reserved

        assembly = []
        assembly.append("; Astrid 2.0 Generated Assembly")
        assembly.append("ORG 0x1000")
        assembly.append("STI")
        assembly.append("")
        
        # Initialize stack pointer for function calls
        assembly.append("; Initialize stack pointer")
        assembly.append("MOV P8, 0xFFFF")  # Set SP to top of stack (grows downward)
        
        # Check if main function makes calls - if so, set up proper stack initialization
        main_function = None
        for function in ir_module.functions:
            if function.name == "main":
                main_function = function
                break
        
        if main_function and self._function_has_calls(main_function):
            assembly.append("MOV P0, 0x0000")  # Load dummy return address
            assembly.append("PUSH P0")        # Initialize stack with dummy return address
            assembly.append("CALL main")      # Call main as a function
            assembly.append("HLT")            # Halt after main returns
        assembly.append("")

        # Generate code for each function
        for function in ir_module.functions:
            assembly.extend(self._generate_function(function))

        # Note: HLT is now handled in the main function's return statement
        assembly.append("")
        
        # Generate string literal data
        if self.string_literals:
            assembly.append("; String literal data")
            for string_value, address in self.string_literals.items():
                assembly.append(f"ORG 0x{address:04X}")
                assembly.append(f"string_literal_{address:04X}:")
                # Use DEFSTR directive for Nova assembler compatibility
                # Properly escape string for assembly
                escaped_string = (string_value
                    .replace('\\', '\\\\')  # Escape backslashes first
                    .replace('"', '\\"')    # Escape quotes
                    .replace('\n', '\\n')   # Escape newlines
                    .replace('\t', '\\t')   # Escape tabs
                    .replace('\r', '\\r'))  # Escape carriage returns
                assembly.append(f'DEFSTR "{escaped_string}"')
                assembly.append("")

        result = "\n".join(assembly)
        
        # CRITICAL: Perform variable resolution pass to replace v0, v1, etc. with actual registers
        result = self._resolve_variables(result)
        
        logger.debug("Code generation completed")
        return result

    def _allocate_register(self, var_type: str) -> str:
        """Allocate a register for a variable of the given type."""
        if var_type in ['int8', 'char', 'pixel', 'color']:
            # Use R registers for 8-bit types
            if self.available_r_registers:
                reg = self.available_r_registers.pop(0)
                self.allocated_registers.add(reg)
                return reg
        else:
            # Use P registers for 16-bit types and string pointers
            if self.available_p_registers:
                reg = self.available_p_registers.pop(0)
                self.allocated_registers.add(reg)
                return reg
        
        # No registers available
        return None

    def _allocate_stack_location(self, var_type: str) -> str:
        """Allocate a stack location for a variable."""
        # Allocate space on stack (growing downward from FP)
        var_size = 1 if var_type in ['int8', 'char', 'pixel', 'color'] else 2
        self.current_stack_offset += var_size
        self.max_stack_offset = max(self.max_stack_offset, self.current_stack_offset)
        
        # Return stack location as offset from frame pointer WITHOUT brackets
        # The brackets will be added when generating the actual instruction
        stack_location = f"FP-{self.current_stack_offset}"
        return stack_location

    def _allocate_memory_location(self, var_type: str) -> str:
        """Allocate a static memory location for a variable (last resort)."""
        location = f"0x{self.next_memory_location:04X}"
        self.next_memory_location += 2  # Always allocate 2 bytes for simplicity
        return location

    def _allocate_variable_location(self, var_name: str, var_type: str) -> str:
        """Allocate location for a variable using three-tier strategy:
        1. Try register first
        2. Use stack if registers exhausted
        3. Fall back to static memory as last resort
        """
        # First try to allocate a register
        reg = self._allocate_register(var_type)
        if reg:
            self.register_map[var_name] = reg
            logger.debug(f"Allocated register {reg} for variable {var_name} (type: {var_type})")
            return reg
        
        # If no registers available, try stack allocation
        stack_loc = self._allocate_stack_location(var_type)
        if stack_loc:
            self.stack_map[var_name] = stack_loc
            logger.debug(f"Allocated stack location {stack_loc} for variable {var_name} (type: {var_type})")
            return stack_loc
        
        # If both register and stack allocation fail, use memory as fallback
        memory_loc = self._allocate_memory_location(var_type)
        self.variable_locations[var_name] = memory_loc
        self.spilled_vars.add(var_name)
        logger.debug(f"Spilled variable {var_name} to memory location {memory_loc}")
        return memory_loc

    def _is_stack_location(self, location: str) -> bool:
        """Check if a location is a stack location."""
        if location is None:
            return False
        return ((location.startswith("FP-") or location.startswith("FP+")) and not location.startswith('[')) or \
               ((location.startswith("[FP-") or location.startswith("[FP+")) and location.endswith("]"))

    def _is_register(self, location: str) -> bool:
        """Check if a location is a register."""
        if location is None:
            return False
        return location.startswith(('R', 'P', 'V')) and not self._is_stack_location(location) and not location.startswith('[')

    def _is_memory_location(self, location: str) -> bool:
        """Check if a location is a memory location."""
        if location is None:
            return False
        return location.startswith('0x') or (location.startswith('[') and not self._is_stack_location(location))

    def _generate_load_from_location(self, location: str, dest_reg: str) -> list:
        """Generate assembly to load a value from any location (register, stack, or memory) to a register."""
        assembly = []
        if self._is_register(location):
            if location != dest_reg:
                assembly.append(f"MOV {dest_reg}, {location}")
        elif self._is_stack_location(location):
            assembly.extend(self._generate_load_from_stack(location, dest_reg))
        elif self._is_memory_location(location):
            assembly.append(f"MOV {dest_reg}, [{location}]")
        else:
            # Fallback for other cases - check if already bracketed to avoid double brackets
            if location.startswith('[') and location.endswith(']'):
                assembly.append(f"MOV {dest_reg}, {location}")
            else:
                assembly.append(f"MOV {dest_reg}, [{location}]")
        return assembly

    def _generate_store_to_location(self, location: str, source_reg: str) -> list:
        """Generate assembly to store a value from register to any location (register, stack, or memory)."""
        assembly = []
        if self._is_register(location):
            if location != source_reg:
                assembly.append(f"MOV {location}, {source_reg}")
        elif self._is_stack_location(location):
            assembly.extend(self._generate_store_to_stack(location, source_reg))
        elif self._is_memory_location(location):
            assembly.extend(self._generate_store_to_memory(location, source_reg))
        else:
            # Fallback for other cases - check if already bracketed to avoid double brackets
            if location.startswith('[') and location.endswith(']'):
                assembly.append(f"MOV {location}, {source_reg}")
            else:
                assembly.append(f"MOV [{location}], {source_reg}")
        return assembly

    def _generate_load_from_stack(self, stack_location: str, dest_reg: str) -> list:
        """Generate assembly to load a value from stack to register."""
        assembly = []
        # Handle both bracketed and non-bracketed stack locations
        if stack_location.startswith("[FP+") and stack_location.endswith("]"):
            # Extract offset from "[FP+4]" (parameter access)
            offset = stack_location[4:-1]  # Remove "[FP+" and "]"
            # Use a temporary register to calculate the address
            temp_reg = self._get_temp_register('P')
            assembly.append(f"MOV {temp_reg}, P9")  # P9 is FP
            assembly.append(f"ADD {temp_reg}, {offset}")
            assembly.append(f"MOV {dest_reg}, [{temp_reg}]")
            self._return_temp_register(temp_reg)
        elif stack_location.startswith("[FP-") and stack_location.endswith("]"):
            # Extract offset from "[FP-4]" (local variable access)
            offset = stack_location[4:-1]  # Remove "[FP-" and "]"
            # Use a temporary register to calculate the address
            temp_reg = self._get_temp_register('P')
            assembly.append(f"MOV {temp_reg}, P9")  # P9 is FP
            assembly.append(f"SUB {temp_reg}, {offset}")
            assembly.append(f"MOV {dest_reg}, [{temp_reg}]")
            self._return_temp_register(temp_reg)
        elif stack_location.startswith("FP+"):
            # Extract offset from "FP+4" (parameter access)
            offset = stack_location[3:]  # Remove "FP+"
            # Use a temporary register to calculate the address
            temp_reg = self._get_temp_register('P')
            assembly.append(f"MOV {temp_reg}, P9")  # P9 is FP
            assembly.append(f"ADD {temp_reg}, {offset}")
            assembly.append(f"MOV {dest_reg}, [{temp_reg}]")
            self._return_temp_register(temp_reg)
        elif stack_location.startswith("FP-"):
            # Extract offset from "FP-4" (local variable access)
            offset = stack_location[3:]  # Remove "FP-"
            # Use a temporary register to calculate the address
            temp_reg = self._get_temp_register('P')
            assembly.append(f"MOV {temp_reg}, P9")  # P9 is FP
            assembly.append(f"SUB {temp_reg}, {offset}")
            assembly.append(f"MOV {dest_reg}, [{temp_reg}]")
            self._return_temp_register(temp_reg)
        else:
            # Fallback for malformed stack locations
            assembly.append(f"MOV {dest_reg}, {stack_location}")
            
        return assembly

    def _generate_store_to_stack(self, stack_location: str, source_reg: str) -> list:
        """Generate assembly to store a value from register to stack."""
        assembly = []
        # Handle both bracketed and non-bracketed stack locations
        if stack_location.startswith("[FP+") and stack_location.endswith("]"):
            # Extract offset from "[FP+4]" (parameter access)
            offset = stack_location[4:-1]  # Remove "[FP+" and "]"
            # Use a temporary register to calculate the address
            temp_reg = self._get_temp_register('P')
            assembly.append(f"MOV {temp_reg}, P9")  # P9 is FP
            assembly.append(f"ADD {temp_reg}, {offset}")
            assembly.append(f"MOV [{temp_reg}], {source_reg}")
            self._return_temp_register(temp_reg)
        elif stack_location.startswith("[FP-") and stack_location.endswith("]"):
            # Extract offset from "[FP-4]" (local variable access)
            offset = stack_location[4:-1]  # Remove "[FP-" and "]"
            # Use a temporary register to calculate the address
            temp_reg = self._get_temp_register('P')
            assembly.append(f"MOV {temp_reg}, P9")  # P9 is FP
            assembly.append(f"SUB {temp_reg}, {offset}")
            assembly.append(f"MOV [{temp_reg}], {source_reg}")
            self._return_temp_register(temp_reg)
        elif stack_location.startswith("FP+"):
            # Extract offset from "FP+4" (parameter access)
            offset = stack_location[3:]  # Remove "FP+"
            # Use a temporary register to calculate the address
            temp_reg = self._get_temp_register('P')
            assembly.append(f"MOV {temp_reg}, P9")  # P9 is FP
            assembly.append(f"ADD {temp_reg}, {offset}")
            assembly.append(f"MOV [{temp_reg}], {source_reg}")
            self._return_temp_register(temp_reg)
        elif stack_location.startswith("FP-"):
            # Extract offset from "FP-4" (local variable access)
            offset = stack_location[3:]  # Remove "FP-"
            # Use a temporary register to calculate the address
            temp_reg = self._get_temp_register('P')
            assembly.append(f"MOV {temp_reg}, P9")  # P9 is FP
            assembly.append(f"SUB {temp_reg}, {offset}")
            assembly.append(f"MOV [{temp_reg}], {source_reg}")
            self._return_temp_register(temp_reg)
        else:
            # Fallback for malformed stack locations
            assembly.append(f"MOV {stack_location}, {source_reg}")
            
        return assembly

    def _get_temp_register(self, reg_type: str = 'P') -> str:
        """Get a temporary register that is not currently allocated to a variable."""
        if reg_type == 'R':
            # Define dedicated temp registers that won't be used for variables
            # Never use registers already allocated to variables
            exclude_allocated = set(self.register_map.values())
            # Prefer registers not used for variables - check spilled variables first
            temp_candidates = ['R8', 'R9', 'R1', 'R0']  # Ordered by preference
            
            for reg in temp_candidates:
                if (reg not in exclude_allocated and 
                    reg not in self.temp_allocated_registers):
                    self.temp_allocated_registers.add(reg)
                    return reg
            
            # If dedicated temps are taken, try any available R register but exclude allocated ones
            for reg in ['R8', 'R9', 'R1', 'R0', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7']:
                if (reg not in exclude_allocated and 
                    reg not in self.temp_allocated_registers):
                    self.temp_allocated_registers.add(reg)
                    return reg
            
            # Last resort: Find the least used variable register and temporarily use it
            # This is safer than printing warnings repeatedly
            for reg in ['R8', 'R9', 'R1', 'R0']:
                if reg not in exclude_allocated:
                    return reg
            # Ultimate fallback - use a register that might have a conflict but warn only once
            if not hasattr(self, '_temp_register_warning_shown'):
                print(f"WARNING: All R registers allocated, temporary register conflict may occur")
                self._temp_register_warning_shown = True
            return 'R9'
        else:
            # Define dedicated temp registers for P type (avoid P8=SP, P9=FP)
            exclude_allocated = set(self.register_map.values())
            temp_candidates = ['P6', 'P7', 'P1', 'P0']  # Safe temp registers
            
            for reg in temp_candidates:
                if (reg not in exclude_allocated and 
                    reg not in self.temp_allocated_registers):
                    self.temp_allocated_registers.add(reg)
                    return reg
            
            # If dedicated temps are taken, try any available P register but exclude allocated ones and reserved ones
            for reg in ['P6', 'P7', 'P1', 'P0', 'P2', 'P3', 'P4', 'P5']:  # Removed P8, P9
                if (reg not in exclude_allocated and 
                    reg not in self.temp_allocated_registers):
                    self.temp_allocated_registers.add(reg)
                    return reg
            
            # Last resort: Find the least used variable register
            for reg in ['P6', 'P7', 'P1', 'P0']:
                if reg not in exclude_allocated:
                    return reg
            # Ultimate fallback - but warn only once per type
            if not hasattr(self, '_temp_p_register_warning_shown'):
                print(f"WARNING: All P registers allocated, temporary register conflict may occur")
                self._temp_p_register_warning_shown = True
            return 'P7'

    def _return_temp_register(self, reg: str):
        """Return a temporary register to the available pool."""
        if reg in self.temp_allocated_registers:
            self.temp_allocated_registers.remove(reg)

    def _get_safe_temp_register(self, reg_type: str = 'P', exclude_registers: set = None) -> str:
        """Get a temporary register that doesn't conflict with existing allocations."""
        if exclude_registers is None:
            exclude_registers = set()
            
        if reg_type == 'R':
            # Use available registers first, but skip excluded ones
            for reg in self.available_r_registers[:]:  # Copy the list to avoid modification issues
                if reg not in exclude_registers:
                    self.available_r_registers.remove(reg)
                    self.temp_allocated_registers.add(reg)
                    return reg
            
            # Try to find an available R register not allocated to variables and not excluded
            for reg in ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']:
                if (reg not in self.allocated_registers and 
                    reg not in self.temp_allocated_registers and 
                    reg not in exclude_registers):
                    self.temp_allocated_registers.add(reg)
                    return reg
            
            # If all are allocated or excluded, try to find one not used as a variable register
            for reg in ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']:
                if (reg not in self.register_map.values() and 
                    reg not in self.temp_allocated_registers and 
                    reg not in exclude_registers):
                    self.temp_allocated_registers.add(reg)
                    return reg
            
            # Last resort: try to find any available register
            for reg in ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']:
                if reg not in self.temp_allocated_registers and reg not in exclude_registers:
                    self.temp_allocated_registers.add(reg)
                    return reg
            
            # If we still can't find one, this is a serious allocation problem
            raise Exception("Unable to allocate safe temporary register - all registers are in use or excluded")
        else:
            # Similar logic for P registers
            for reg in self.available_p_registers[:]:
                if reg not in exclude_registers:
                    self.available_p_registers.remove(reg)
                    self.temp_allocated_registers.add(reg)
                    return reg
            
            for reg in ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7']:  # Removed P8, P9
                if (reg not in self.allocated_registers and 
                    reg not in self.temp_allocated_registers and 
                    reg not in exclude_registers):
                    self.temp_allocated_registers.add(reg)
                    return reg
            
            for reg in ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7']:  # Removed P8, P9
                if (reg not in self.register_map.values() and 
                    reg not in self.temp_allocated_registers and 
                    reg not in exclude_registers):
                    self.temp_allocated_registers.add(reg)
                    return reg
            
            for reg in ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7']:  # Removed P8, P9
                if reg not in self.temp_allocated_registers and reg not in exclude_registers:
                    self.temp_allocated_registers.add(reg)
                    return reg
            
            raise Exception("Unable to allocate safe temporary P register - all registers are in use or excluded")

    def _return_temp_register(self, reg: str):
        """Return a temporary register to the available pool."""
        if reg in self.temp_allocated_registers:
            self.temp_allocated_registers.remove(reg)
            if reg.startswith('R'):
                self.available_r_registers.insert(0, reg)
            elif reg.startswith('P'):
                self.available_p_registers.insert(0, reg)

    def _preserve_live_caller_save_registers(self) -> list:
        """Preserve caller-save registers that contain live variables before function call."""
        preserved_info = []
        
        # Define caller-save registers (these may be clobbered by the callee)
        caller_save_registers = ['R0', 'R1', 'R8', 'R9', 'P0', 'P1']
        
        # Find variables currently allocated to caller-save registers
        for var_name, reg in self.register_map.items():
            if reg in caller_save_registers:
                # This variable needs to be preserved
                # Allocate a stack location for temporary storage
                stack_offset = self.current_stack_offset + 2  # Reserve 2 bytes
                self.current_stack_offset += 2
                self.max_stack_offset = max(self.max_stack_offset, self.current_stack_offset)
                stack_loc = f"FP-{stack_offset}"
                preserved_info.append((var_name, reg, stack_loc))
        
        return preserved_info

    def _generate_caller_save_preservation(self, preserved_info: list) -> list:
        """Generate assembly to save caller-save registers to stack."""
        assembly = []
        if preserved_info:
            assembly.append("; Preserve caller-save registers")
            for var_name, reg, stack_loc in preserved_info:
                assembly.extend(self._generate_store_to_stack(stack_loc, reg))
        return assembly

    def _generate_caller_save_restoration(self, preserved_info: list) -> list:
        """Generate assembly to restore caller-save registers from stack."""
        assembly = []
        if preserved_info:
            assembly.append("; Restore caller-save registers")
            for var_name, reg, stack_loc in preserved_info:
                assembly.extend(self._generate_load_from_stack(stack_loc, reg))
        return assembly

    def _get_variable_location(self, var_name: str, var_type: str = None) -> str:
        """Get location for a variable, allocating if necessary."""
        # Check if already allocated to register
        if var_name in self.register_map:
            return self.register_map[var_name]
        # Check if allocated to stack
        elif var_name in self.stack_map:
            return self.stack_map[var_name]
        # Check if allocated to memory
        elif var_name in self.variable_locations:
            return self.variable_locations[var_name]
        else:
            # Variable not yet allocated - allocate using three-tier strategy
            # Get variable type from IR module if not provided
            if var_type is None and hasattr(self, 'current_function') and self.current_function and hasattr(self.current_function, 'module'):
                # var_name is already an IR variable name
                if var_name in self.current_function.module.variable_types:
                    var_type = self.current_function.module.variable_types[var_name]
                else:
                    var_type = 'int16'  # Default fallback
            elif var_type is None:
                var_type = 'int16'  # Default fallback
            
            # Use new three-tier allocation strategy
            return self._allocate_variable_location(var_name, var_type)

    def _function_has_calls(self, function: IRFunction) -> bool:
        """Check if a function contains any function calls."""
        for block in function.blocks:
            for instruction in block.instructions:
                if instruction.opcode == 'call':
                    return True
        return False

    def _generate_function(self, function: IRFunction) -> list:
        """Generate assembly for a function."""
        # Set current function for return handling
        self.current_function = function
        
        # Reset allocation state for each function
        self.allocated_registers.clear()
        self.register_map.clear()
        self.stack_map.clear()
        self.variable_locations.clear()
        self.current_stack_offset = 0
        self.max_stack_offset = 0
        self.next_memory_location = 0x2000  # Reset memory allocation per function
        
        # Reset available registers (don't use P8, P9 as they are SP, FP)
        self.available_r_registers = ['R2', 'R3', 'R4', 'R5', 'R6', 'R7']  # Reserve R0, R1, R8, R9 for temps
        self.available_p_registers = ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7']  # Reserve P8, P9 for SP, FP
        
        assembly = []
        assembly.append(f"; Function {function.name}")
        assembly.append(f"{function.name}:")

        # Set up stack frame for non-main functions OR main functions that make calls
        main_has_calls = function.name == "main" and self._function_has_calls(function)
        needs_stack_frame = function.name != "main" or main_has_calls
        
        if needs_stack_frame:
            # Save frame pointer
            assembly.append("PUSH FP")
            # Set new frame pointer
            assembly.append("MOV FP, SP")
        
        # Re-map parameters to stack frame offsets instead of registers
        if needs_stack_frame and hasattr(function, 'parameter_ir_vars'):
            # Parameters are accessed from stack frame at FP+4, FP+6, FP+8, etc.
            # FP+0 = saved FP, FP+2 = return address, FP+4 = first parameter
            for i, param_ir_var in enumerate(function.parameter_ir_vars):
                stack_offset = 4 + (i * 2)  # Each parameter is 2 bytes
                stack_location = f"FP+{stack_offset}"  # Remove brackets here, they're added during access
                self.stack_map[param_ir_var] = stack_location
                logger.debug(f"Mapped parameter {param_ir_var} to stack location {stack_location}")

        # Process each basic block (this will trigger variable allocation)
        for block in function.blocks:
            assembly.extend(self._generate_block(block))

        # Allocate stack space if any variables were allocated to stack
        if self.max_stack_offset > 0:
            # Insert stack allocation after function prologue
            stack_alloc_instruction = f"SUB SP, {self.max_stack_offset}  ; Allocate stack space for local variables"
            # Find where to insert (after MOV FP, SP for functions with stack frames)
            if needs_stack_frame:
                # Insert after "MOV FP, SP"
                insert_pos = 3  # After function label, PUSH FP, MOV FP, SP
            else:
                # Insert frame pointer setup and stack allocation for main without calls
                insert_pos = 2  # After function label
            
            # Find the actual position by looking for the function label
            for i, line in enumerate(assembly):
                if line == f"{function.name}:":
                    if needs_stack_frame:
                        insert_pos = i + 3  # After label, PUSH FP, MOV FP, SP
                    else:
                        insert_pos = i + 1  # After label
                    break
            
            if not needs_stack_frame:
                # Add frame pointer setup for main function without calls
                assembly.insert(insert_pos, "MOV FP, SP")
                assembly.insert(insert_pos + 1, stack_alloc_instruction)
            else:
                assembly.insert(insert_pos, stack_alloc_instruction)

        # Clean up stack frame for non-main functions that set one up
        if needs_stack_frame and function.name != "main":
            # Restore stack pointer (this also deallocates local variables)
            assembly.append("MOV SP, FP")
            # Restore frame pointer
            assembly.append("POP FP")
            # Return (only for non-main functions)
            assembly.append("RET")

        # Add HLT for main function if it doesn't end with a return
        if function.name == "main":
            # Only add HLT at the very end if there isn't already one
            if not any(line.strip() == "HLT" for line in assembly):
                assembly.append("HLT")

        # Clean up stack frame for main functions that set one up (must be AFTER HLT insertion)
        if function.name == "main" and main_has_calls:
            # Insert cleanup before the last HLT
            for i in range(len(assembly) - 1, -1, -1):
                if assembly[i].strip() == "HLT":
                    assembly.insert(i, "POP FP")
                    assembly.insert(i, "MOV SP, FP")
                    break

        assembly.append("")
        return assembly

    def _generate_block(self, block: IRBasicBlock) -> list:
        """Generate assembly for a basic block."""
        assembly = []
        assembly.append(f"{block.name}:")

        for instruction in block.instructions:
            assembly.extend(self._generate_instruction(instruction))

        return assembly

    def _generate_instruction(self, instruction: IRInstruction) -> list:
        """Generate assembly for an instruction."""
        assembly = []

        if instruction.opcode == "const":
            # Load constant into a register/memory location
            value = instruction.operands[0]
            result_var = instruction.result
            
            # Track the constant value
            self.constant_map[result_var] = value
            
            # Check if this is a string literal
            if isinstance(value, str) and len(value) > 0 and not value.isdigit():
                # This is a string literal - allocate memory for it
                if value not in self.string_literals:
                    string_addr = self.next_string_location
                    self.string_literals[value] = string_addr
                    self.next_string_location += len(value) + 1  # +1 for null terminator
                
                # Store string address in the result variable location
                string_addr = self.string_literals[value]
                if result_var in self.register_map:
                    reg = self.register_map[result_var]
                    assembly.append(f"MOV {reg}, 0x{string_addr:04X}")
                # For string constants, store the address as the value
                self.constant_map[result_var] = f"0x{string_addr:04X}"
            else:
                # Regular constant (number)
                if result_var in self.register_map:
                    reg = self.register_map[result_var]
                    assembly.append(f"MOV {reg}, {value}")
                # For constants, don't allocate memory - keep them as immediate values
                # They will be used directly in operations or assignments

        elif instruction.opcode == "assign":
            # Copy value from one location to another
            source = instruction.operands[0]
            dest = instruction.result
            dest_location = self._get_variable_location(dest)
            
            # Check if source is a constant, but only if not already allocated
            if source in self.constant_map and source not in self.variable_locations and source not in self.register_map and source not in self.stack_map:
                source_value = str(self.constant_map[source])
                # Source is a constant - load it into dest location
                if self._is_register(dest_location):
                    assembly.append(f"MOV {dest_location}, {source_value}")
                elif self._is_stack_location(dest_location):
                    # Load constant to temp register then store to stack
                    temp_reg = self._get_temp_register('R')
                    assembly.append(f"MOV {temp_reg}, {source_value}")
                    assembly.extend(self._generate_store_to_stack(dest_location, temp_reg))
                    self._return_temp_register(temp_reg)
                else:
                    # Load to temp register then store to memory
                    temp_reg = self._get_temp_register('R')
                    assembly.append(f"MOV {temp_reg}, {source_value}")
                    assembly.extend(self._generate_store_to_memory(dest_location, temp_reg))
                    self._return_temp_register(temp_reg)
            elif source in self.variable_locations or source in self.register_map or source in self.stack_map:
                # Get source location (check all allocation maps)
                source_location = self.register_map.get(source) or self.stack_map.get(source) or self.variable_locations.get(source, source)
                
                # Handle different source->dest combinations
                if self._is_register(source_location):
                    # Source is in register
                    if self._is_register(dest_location):
                        # Register to register
                        if source_location != dest_location:
                            assembly.append(f"MOV {dest_location}, {source_location}")
                    elif self._is_stack_location(dest_location):
                        # Register to stack
                        assembly.extend(self._generate_store_to_stack(dest_location, source_location))
                    else:
                        # Register to memory
                        assembly.extend(self._generate_store_to_memory(dest_location, source_location))
                        
                elif self._is_stack_location(source_location):
                    # Source is on stack
                    if self._is_register(dest_location):
                        # Stack to register
                        assembly.extend(self._generate_load_from_stack(source_location, dest_location))
                    elif self._is_stack_location(dest_location):
                        # Stack to stack - use temp register
                        temp_reg = self._get_temp_register('R')
                        assembly.extend(self._generate_load_from_stack(source_location, temp_reg))
                        assembly.extend(self._generate_store_to_stack(dest_location, temp_reg))
                        self._return_temp_register(temp_reg)
                    else:
                        # Stack to memory - use temp register
                        temp_reg = self._get_temp_register('R')
                        assembly.extend(self._generate_load_from_stack(source_location, temp_reg))
                        assembly.extend(self._generate_store_to_memory(dest_location, temp_reg))
                        self._return_temp_register(temp_reg)
                        
                else:
                    # Source is in memory or stack location that was already resolved
                    # Check if source_location already has brackets to avoid double bracketing
                    source_operand = source_location
                    if not (source_location.startswith('[') and source_location.endswith(']')):
                        # Source is a plain memory address, add brackets
                        source_operand = f"[{source_location}]"
                    # else: source_location already has brackets (like [FP-4]), use as-is
                    
                    if self._is_register(dest_location):
                        # Memory to register
                        assembly.append(f"MOV {dest_location}, {source_operand}")
                    elif self._is_stack_location(dest_location):
                        # Memory to stack - use temp register
                        temp_reg = self._get_temp_register('R')
                        assembly.append(f"MOV {temp_reg}, {source_operand}")
                        assembly.extend(self._generate_store_to_stack(dest_location, temp_reg))
                        self._return_temp_register(temp_reg)
                    else:
                        # Memory to memory - use temp register
                        temp_reg = self._get_temp_register('R')
                        assembly.append(f"MOV {temp_reg}, {source_operand}")
                        assembly.extend(self._generate_store_to_memory(dest_location, temp_reg))
                        self._return_temp_register(temp_reg)
            else:
                # Source is a literal value - load it into dest location
                if self._is_immediate_value(source):
                    if self._is_register(dest_location):
                        assembly.append(f"MOV {dest_location}, {source}")
                    elif self._is_stack_location(dest_location):
                        temp_reg = self._get_temp_register('R')
                        assembly.append(f"MOV {temp_reg}, {source}")
                        assembly.extend(self._generate_store_to_stack(dest_location, temp_reg))
                        self._return_temp_register(temp_reg)
                    else:
                        temp_reg = self._get_temp_register('R')
                        assembly.append(f"MOV {temp_reg}, {source}")
                        assembly.extend(self._generate_store_to_memory(dest_location, temp_reg))
                        self._return_temp_register(temp_reg)
                else:
                    # Source is not a literal value - resolve its location
                    source_location = self._get_variable_location(source)
                    
                    if self._is_register(dest_location):
                        # Load source to destination register
                        assembly.extend(self._generate_load_from_location(source_location, dest_location))
                    elif self._is_stack_location(dest_location):
                        # Load source to temp register then store to stack
                        temp_reg = self._get_temp_register('R')
                        assembly.extend(self._generate_load_from_location(source_location, temp_reg))
                        assembly.extend(self._generate_store_to_stack(dest_location, temp_reg))
                        self._return_temp_register(temp_reg)
                    else:
                        # Load source to temp register then store to memory
                        temp_reg = self._get_temp_register('R')
                        assembly.extend(self._generate_load_from_location(source_location, temp_reg))
                        assembly.extend(self._generate_store_to_memory(dest_location, temp_reg))
                        self._return_temp_register(temp_reg)

        elif instruction.opcode in [">", "<", ">=", "<=", "==", "!=", "eq"]:
            # Comparison operations - simplified and correct implementation
            left = instruction.operands[0]
            right = instruction.operands[1]
            result = instruction.result

            if left in self.constant_map:
                left_loc = str(self.constant_map[left])
            else:
                left_loc = self.register_map.get(left) or self.stack_map.get(left) or self.variable_locations.get(left, left)
            if right in self.constant_map:
                right_loc = str(self.constant_map[right])
            else:
                right_loc = self.register_map.get(right) or self.stack_map.get(right) or self.variable_locations.get(right, right)
            
            # If operands are still IR variable names, resolve them to locations
            if not self._is_immediate_value(left_loc) and not self._is_register(left_loc) and not self._is_memory_address(left_loc) and not self._is_stack_location(left_loc):
                left_loc = self._get_variable_location(left)
            if not self._is_immediate_value(right_loc) and not self._is_register(right_loc) and not self._is_memory_address(right_loc) and not self._is_stack_location(right_loc):
                right_loc = self._get_variable_location(right)
            
            result_loc = self._get_variable_location(result)

            # Determine register type based on operand types
            left_type = None
            right_type = None
            
            # Try to get variable type for left operand
            if left in self.current_function.module.variable_types:
                left_type = self.current_function.module.variable_types[left]
            
            # Try to get variable type for right operand  
            if right in self.current_function.module.variable_types:
                right_type = self.current_function.module.variable_types[right]
            
            # Default to int16 if types unknown
            if left_type is None:
                left_type = 'int16'
            if right_type is None:
                right_type = 'int16'
                
            # Determine register type - use P registers for 16-bit operations
            if left_type == 'int16' or right_type == 'int16':
                reg_type = 'P'
            else:
                reg_type = 'R'

            # Use temp registers that don't conflict with allocated variables
            # For left operand: if it's already in a register, use it directly
            if self._is_register(left_loc):
                left_reg = left_loc
                left_needs_temp = False
            else:
                left_reg = self._get_temp_register(reg_type)
                left_needs_temp = True
            
            # Get a safe temp register for right operand
            right_reg = self._get_temp_register(reg_type)
            
            # Get a safe temp register for result
            result_temp_reg = self._get_temp_register('R')  # Result is always boolean (8-bit)
            
            # Load left operand
            if self._is_immediate_value(left_loc):
                assembly.append(f"MOV {left_reg}, {left_loc}")
            elif self._is_register(left_loc):
                # Already using the register directly, no need to load
                pass
            elif self._is_stack_location(left_loc):
                assembly.extend(self._generate_load_from_stack(left_loc, left_reg))
            elif self._is_memory_address(left_loc):
                temp_p_reg = self._get_temp_register('P')
                assembly.append(f"MOV {temp_p_reg}, {left_loc}")
                assembly.append(f"MOV {left_reg}, [{temp_p_reg}]")
                self._return_temp_register(temp_p_reg)
            else:
                assembly.append(f"MOV {left_reg}, [{left_loc}]")

            # Track special case: i < 256 becomes i <= 255
            is_special_256_case = False
            
            # Load right operand
            if self._is_immediate_value(right_loc):
                try:
                    val = int(right_loc, 0)
                    if reg_type == 'R' and 0 <= val <= 255:
                        # 8-bit comparison with small immediate
                        assembly.append(f"CMP {left_reg}, {right_loc}")
                    elif reg_type == 'P':
                        # 16-bit comparison - load immediate into P register
                        assembly.append(f"CMP {left_reg}, {right_loc}")
                    else:
                        # 8-bit comparison with large immediate value
                        if val == 256 and instruction.opcode == "<":
                            # For i < 256 where i is 8-bit, this is always true
                            # Compare against 255 and use <= logic instead
                            assembly.append(f"CMP {left_reg}, 255")
                            is_special_256_case = True
                        else:
                            # 8-bit register but large immediate - need to extract low byte
                            temp_p_reg = self._get_temp_register('P')
                            assembly.append(f"MOV {temp_p_reg}, {right_loc}")
                            assembly.append(f"MOV {right_reg}, :{temp_p_reg}")
                            assembly.append(f"CMP {left_reg}, {right_reg}")
                            self._return_temp_register(temp_p_reg)
                except ValueError:
                    if reg_type == 'P':
                        # 16-bit comparison with non-numeric immediate
                        assembly.append(f"CMP {left_reg}, {right_loc}")
                    else:
                        # 8-bit comparison with non-numeric immediate - extract low byte
                        temp_p_reg = self._get_temp_register('P')
                        assembly.append(f"MOV {temp_p_reg}, {right_loc}")
                        assembly.append(f"MOV {right_reg}, :{temp_p_reg}")
                        assembly.append(f"CMP {left_reg}, {right_reg}")
                        self._return_temp_register(temp_p_reg)
            elif self._is_register(right_loc):
                assembly.append(f"CMP {left_reg}, {right_loc}")
            elif self._is_stack_location(right_loc):
                assembly.extend(self._generate_load_from_stack(right_loc, right_reg))
                assembly.append(f"CMP {left_reg}, {right_reg}")
            elif self._is_memory_address(right_loc):
                temp_p_reg = self._get_temp_register('P')
                assembly.append(f"MOV {temp_p_reg}, {right_loc}")
                assembly.append(f"MOV {right_reg}, [{temp_p_reg}]")
                assembly.append(f"CMP {left_reg}, {right_reg}")
                self._return_temp_register(temp_p_reg)
            else:
                if self._is_stack_location(right_loc):
                    assembly.extend(self._generate_load_from_stack(right_loc, right_reg))
                else:
                    assembly.append(f"MOV {right_reg}, [{right_loc}]")
                assembly.append(f"CMP {left_reg}, {right_reg}")

            # Generate result based on comparison type
            label_true = f"cmp_true_{self.label_counter}"
            label_done = f"cmp_done_{self.label_counter}"
            self.label_counter += 1

            if instruction.opcode == "==" or instruction.opcode == "eq":
                assembly.append(f"JZ {label_true}")  # Jump if zero (equal)
            elif instruction.opcode == "!=":
                assembly.append(f"JNZ {label_true}")  # Jump if not zero (not equal)
            elif instruction.opcode == "<":
                if is_special_256_case:
                    # For i < 256 case, we compared with 255, so use <= logic
                    assembly.append(f"JC {label_true}")  # Jump if carry (less than)
                    assembly.append(f"JZ {label_true}")  # Jump if zero (equal)
                else:
                    assembly.append(f"JC {label_true}")  # Jump if carry (less than for unsigned)
            elif instruction.opcode == "<=":
                assembly.append(f"JC {label_true}")  # Jump if carry (less than)
                assembly.append(f"JZ {label_true}")  # Jump if zero (equal)
            elif instruction.opcode == ">":
                # Greater than: not carry and not zero
                assembly.append(f"JC {label_done}")  # If carry, skip to false
                assembly.append(f"JZ {label_done}")  # If zero, skip to false
                assembly.append(f"JMP {label_true}")  # Otherwise true
            elif instruction.opcode == ">=":
                # Greater or equal: not carry
                assembly.append(f"JC {label_done}")  # If carry, false
                assembly.append(f"JMP {label_true}")  # Otherwise true

            # Set result to false (0)
            assembly.append(f"MOV {result_temp_reg}, 0")
            assembly.append(f"JMP {label_done}")
            
            # Set result to true (1)
            assembly.append(f"{label_true}:")
            assembly.append(f"MOV {result_temp_reg}, 1")
            
            assembly.append(f"{label_done}:")
            
            # Store result
            assembly.extend(self._generate_store_to_location(result_loc, result_temp_reg))
            
            # Return temp registers
            if left_needs_temp:
                self._return_temp_register(left_reg)
            self._return_temp_register(right_reg)
            self._return_temp_register(result_temp_reg)

        elif instruction.opcode == "&&":
            # Logical AND operation
            left = instruction.operands[0]
            right = instruction.operands[1]
            result = instruction.result

            left_loc = self.register_map.get(left, self.variable_locations.get(left, left))
            right_loc = self.register_map.get(right, self.variable_locations.get(right, right))
            result_loc = self._get_variable_location(result)

            # Load left operand
            left_temp = self._get_temp_register('R')
            if self._is_immediate_value(left_loc):
                assembly.append(f"MOV {left_temp}, {left_loc}")
            elif self._is_register(left_loc):
                assembly.append(f"MOV {left_temp}, {left_loc}")
            else:
                assembly.append(f"MOV {left_temp}, [{left_loc}]")

            # Check if left is false (0)
            assembly.append(f"CMP {left_temp}, 0")
            assembly.append("JZ and_false")  # If left is 0, result is 0

            # Load right operand
            right_temp = self._get_temp_register('R')
            if self._is_immediate_value(right_loc):
                assembly.append(f"MOV {right_temp}, {right_loc}")
            elif self._is_register(right_loc):
                assembly.append(f"MOV {right_temp}, {right_loc}")
            else:
                assembly.append(f"MOV {right_temp}, [{right_loc}]")

            # Check if right is false (0)
            assembly.append(f"CMP {right_temp}, 0")
            assembly.append("JZ and_false")  # If right is 0, result is 0

            # Both are true
            assembly.append(f"MOV {left_temp}, 1")
            assembly.append("JMP and_done")

            # Result is false
            assembly.append("and_false:")
            assembly.append(f"MOV {left_temp}, 0")

            assembly.append("and_done:")

            # Store result
            if self._is_register(result_loc):
                assembly.append(f"MOV {result_loc}, {left_temp}")
            elif self._is_memory_address(result_loc):
                temp_p_reg = self._get_temp_register('P')
                assembly.append(f"MOV {temp_p_reg}, {result_loc}")
                assembly.append(f"MOV [{temp_p_reg}], {left_temp}")
                self._return_temp_register(temp_p_reg)
            else:
                assembly.extend(self._generate_store_to_location(result_loc, left_temp))

        elif instruction.opcode == "||":
            # Logical OR operation
            left = instruction.operands[0]
            right = instruction.operands[1]
            result = instruction.result

            left_loc = self.register_map.get(left, self.variable_locations.get(left, left))
            right_loc = self.register_map.get(right, self.variable_locations.get(right, right))
            result_loc = self._get_variable_location(result)

            # Load left operand
            left_temp = self._get_temp_register('R')
            if self._is_immediate_value(left_loc):
                assembly.append(f"MOV {left_temp}, {left_loc}")
            elif self._is_register(left_loc):
                assembly.append(f"MOV {left_temp}, {left_loc}")
            else:
                assembly.append(f"MOV {left_temp}, [{left_loc}]")

            # Check if left is true (non-zero)
            assembly.append(f"CMP {left_temp}, 0")
            assembly.append("JNZ or_true")  # If left is non-zero, result is 1

            # Load right operand
            right_temp = self._get_temp_register('R')
            if self._is_immediate_value(right_loc):
                assembly.append(f"MOV {right_temp}, {right_loc}")
            elif self._is_register(right_loc):
                assembly.append(f"MOV {right_temp}, {right_loc}")
            else:
                assembly.append(f"MOV {right_temp}, [{right_loc}]")

            # Check if right is true (non-zero)
            assembly.append(f"CMP {right_temp}, 0")
            assembly.append("JNZ or_true")  # If right is non-zero, result is 1

            # Both are false
            assembly.append(f"MOV {left_temp}, 0")
            assembly.append("JMP or_done")

            # Result is true
            assembly.append("or_true:")
            assembly.append(f"MOV {left_temp}, 1")

            assembly.append("or_done:")

            # Store result
            if self._is_register(result_loc):
                assembly.append(f"MOV {result_loc}, {left_temp}")
            elif self._is_memory_address(result_loc):
                temp_p_reg = self._get_temp_register('P')
                assembly.append(f"MOV {temp_p_reg}, {result_loc}")
                assembly.append(f"MOV [{temp_p_reg}], {left_temp}")
                self._return_temp_register(temp_p_reg)
            else:
                assembly.extend(self._generate_store_to_location(result_loc, left_temp))

        elif instruction.opcode in ["+", "-", "*", "/", "%"]:
            # Binary operations
            left = instruction.operands[0]
            right = instruction.operands[1]
            result = instruction.result

            left_loc = self.register_map.get(left, self.variable_locations.get(left, left))
            right_loc = self.register_map.get(right, self.variable_locations.get(right, right))
            
            # Check if operands are constants FIRST, before checking variable_locations
            if left in self.constant_map:
                left_loc = str(self.constant_map[left])
            if right in self.constant_map:
                right_loc = str(self.constant_map[right])
            
            # If operands are still IR variable names, resolve them to locations
            if not self._is_immediate_value(left_loc) and not self._is_register(left_loc) and not self._is_memory_address(left_loc):
                left_loc = self._get_variable_location(left)
            if not self._is_immediate_value(right_loc) and not self._is_register(right_loc) and not self._is_memory_address(right_loc):
                right_loc = self._get_variable_location(right)
            
            result_loc = self._get_variable_location(result)

            skip_operation = False  # Initialize flag
            skip_result_storage = False  # Initialize flag

            # Special case for increment: var = something + 1
            # Check this BEFORE constant resolution to work with IR variable names
            left_operand = instruction.operands[0]
            right_operand = instruction.operands[1]
            is_increment = (instruction.opcode == "+" and 
                           (str(right_operand) == '1' or 
                            (right_operand in self.constant_map and self.constant_map[right_operand] == 1) or
                            right_operand == 1))
            if is_increment:
                # For increment, we need to increment the value and store result
                left_loc = self.register_map.get(left_operand, self.variable_locations.get(left_operand, left_operand))
                if not self._is_immediate_value(left_loc) and not self._is_register(left_loc) and not self._is_memory_address(left_loc):
                    left_loc = self._get_variable_location(left_operand)
                result_loc = self._get_variable_location(result)
                
                if self._is_register(left_loc):
                    # Left in register
                    if self._is_register(result_loc):
                        # Both in registers
                        if left_loc != result_loc:
                            assembly.append(f"MOV {result_loc}, {left_loc}")
                        assembly.append(f"ADD {result_loc}, 1")
                    else:
                        # Result in memory/stack, left in register
                        temp_reg = self._get_temp_register('R')
                        assembly.append(f"MOV {temp_reg}, {left_loc}")
                        assembly.append(f"ADD {temp_reg}, 1")
                        assembly.extend(self._generate_store_to_location(result_loc, temp_reg))
                        self._return_temp_register(temp_reg)
                else:
                    # Left in memory/stack
                    if self._is_register(result_loc):
                        # Load, increment, store to register
                        temp_reg = self._get_temp_register('R')
                        assembly.extend(self._generate_load_from_location(left_loc, temp_reg))
                        assembly.append(f"ADD {temp_reg}, 1")
                        assembly.append(f"MOV {result_loc}, {temp_reg}")
                        self._return_temp_register(temp_reg)
                    else:
                        # Both in memory/stack
                        temp_reg = self._get_temp_register('R')
                        assembly.extend(self._generate_load_from_location(left_loc, temp_reg))
                        assembly.append(f"ADD {temp_reg}, 1")
                        assembly.extend(self._generate_store_to_location(result_loc, temp_reg))
                        self._return_temp_register(temp_reg)
                skip_operation = True
                skip_result_storage = True  # We already stored the result
            else:
                # Normal binary operation - resolve constants after increment check
                # Check if operands are constants FIRST, before checking variable_locations
                if left in self.constant_map:
                    left_loc = str(self.constant_map[left])
                if right in self.constant_map:
                    right_loc = str(self.constant_map[right])
                
                # Get available registers for the operation - use safe registers
                left_reg = None
                for reg in ['R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9', 'R1', 'R0']:
                    if (reg not in self.register_map.values() and 
                        reg not in self.temp_allocated_registers and
                        reg != left_loc and reg != right_loc and reg != result_loc):
                        left_reg = reg
                        self.temp_allocated_registers.add(reg)
                        break
                if left_reg is None:
                    left_reg = 'R9'  # fallback
                
                right_reg = None
                for reg in ['R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9', 'R1', 'R0']:
                    if (reg not in self.register_map.values() and 
                        reg not in self.temp_allocated_registers and
                        reg != left_loc and reg != right_loc and reg != result_loc and
                        reg != left_reg):
                        right_reg = reg
                        self.temp_allocated_registers.add(reg)
                        break
                if right_reg is None:
                    right_reg = 'R8'  # fallback
                
                # If we still can't get different registers, use a different approach
                if right_reg == left_reg:
                    # Handle the case where we can't get two different registers
                    # We'll load the left operand first, then handle the right operand specially
                    pass  # We'll handle this in the loading section below
                
                # Load left operand
                if self._is_immediate_value(left_loc):
                    assembly.append(f"MOV {left_reg}, {left_loc}")
                elif self._is_register(left_loc):
                    # Left operand is already in a register
                    if left_loc != left_reg:
                        assembly.append(f"MOV {left_reg}, {left_loc}")
                elif self._is_stack_location(left_loc):
                    # Left operand is on the stack - use proper stack access
                    assembly.extend(self._generate_load_from_stack(left_loc, left_reg))
                elif self._is_memory_address(left_loc):
                    # Load address into temp register then indirect access
                    temp_p_reg = self._get_temp_register('P')
                    assembly.append(f"MOV {temp_p_reg}, {left_loc}")
                    assembly.append(f"MOV {left_reg}, [{temp_p_reg}]")
                    self._return_temp_register(temp_p_reg)
                else:
                    if left_loc.startswith('P'):
                        assembly.append(f"MOV {left_reg}, :{left_loc}")  # For P registers, load low byte
                    else:
                        assembly.append(f"MOV {left_reg}, [{left_loc}]")

                # Load right operand
                if left_reg == right_reg:
                    # Special optimization for + 1
                    if instruction.opcode == "+" and (right_loc == '1' or str(right_loc) == '1'):
                        assembly.append(f"ADD {left_reg}, 1")
                        skip_operation = True
                    else:
                        # Find a different register for right operand
                        available_regs = [r for r in ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9'] if r != left_reg and r not in self.allocated_registers]
                        if available_regs:
                            actual_right_reg = available_regs[0]
                        else:
                            # Last resort: use any register, even if allocated (will cause issues but won't crash)
                            actual_right_reg = 'R1' if left_reg == 'R0' else 'R0'
                        
                        if self._is_immediate_value(right_loc):
                            assembly.append(f"MOV {actual_right_reg}, {right_loc}")
                        elif self._is_register(right_loc):
                            if right_loc != actual_right_reg:
                                assembly.append(f"MOV {actual_right_reg}, {right_loc}")
                        elif self._is_stack_location(right_loc):
                            # Right operand is on the stack - use proper stack access
                            assembly.extend(self._generate_load_from_stack(right_loc, actual_right_reg))
                        elif self._is_memory_address(right_loc):
                            temp_p_reg = self._get_temp_register('P')
                            assembly.append(f"MOV {temp_p_reg}, {right_loc}")
                            assembly.append(f"MOV {actual_right_reg}, [{temp_p_reg}]")
                            self._return_temp_register(temp_p_reg)
                        else:
                            if right_loc.startswith('P'):
                                assembly.append(f"MOV {actual_right_reg}, :{right_loc}")
                            else:
                                assembly.append(f"MOV {actual_right_reg}, [{right_loc}]")
                        
                        # Perform operation
                        if instruction.opcode == "+":
                            assembly.append(f"ADD {left_reg}, {actual_right_reg}")
                        elif instruction.opcode == "-":
                            assembly.append(f"SUB {left_reg}, {actual_right_reg}")
                        elif instruction.opcode == "*":
                            assembly.append(f"MUL {left_reg}, {actual_right_reg}")
                        elif instruction.opcode == "/":
                            assembly.append(f"DIV {left_reg}, {actual_right_reg}")
                        elif instruction.opcode == "%":
                            assembly.append(f"MOD {left_reg}, {actual_right_reg}")
                        
                        skip_operation = True
                else:
                    # Normal loading for different registers
                    # Special optimization for + 1
                    if instruction.opcode == "+" and (right_loc == '1' or str(right_loc) == '1'):
                        assembly.append(f"ADD {left_reg}, 1")
                        skip_operation = True
                    else:
                        if self._is_immediate_value(right_loc):
                            try:
                                val = int(right_loc, 0)
                                if 0 <= val <= 255:
                                    assembly.append(f"MOV {right_reg}, {right_loc}")
                                else:
                                    # For large constants, use temp register
                                    temp_p_reg = self._get_temp_register('P')
                                    assembly.append(f"MOV {temp_p_reg}, {right_loc}")
                                    assembly.append(f"MOV {right_reg}, :{temp_p_reg}")
                                    self._return_temp_register(temp_p_reg)
                            except ValueError:
                                assembly.append(f"MOV {right_reg}, {right_loc}")
                        elif self._is_register(right_loc):
                            # Right operand is already in a register
                            if right_loc != right_reg:
                                assembly.append(f"MOV {right_reg}, {right_loc}")
                        elif self._is_memory_address(right_loc):
                            # Load address into temp register then indirect access
                            temp_p_reg = self._get_temp_register('P')
                            assembly.append(f"MOV {temp_p_reg}, {right_loc}")
                            assembly.append(f"MOV {right_reg}, [{temp_p_reg}]")
                            self._return_temp_register(temp_p_reg)
                        else:
                            if self._is_stack_location(right_loc):
                                assembly.extend(self._generate_load_from_stack(right_loc, right_reg))
                            else:
                                assembly.append(f"MOV {right_reg}, [{right_loc}]")
                        
                        skip_operation = False

                # Perform operation
                if not skip_operation:
                    if instruction.opcode == "+":
                        assembly.append(f"ADD {left_reg}, {right_reg}")
                    elif instruction.opcode == "-":
                        assembly.append(f"SUB {left_reg}, {right_reg}")
                    elif instruction.opcode == "*":
                        assembly.append(f"MUL {left_reg}, {right_reg}")
                    elif instruction.opcode == "/":
                        assembly.append(f"DIV {left_reg}, {right_reg}")
                    elif instruction.opcode == "%":
                        assembly.append(f"MOD {left_reg}, {right_reg}")

                # Store result
                if not skip_result_storage:
                    if instruction.opcode == "+" and result_loc.startswith('P'):
                        # Handle carry for 16-bit addition - use unique labels per operation
                        carry_label = f"add_carry_{self.label_counter}"
                        done_label = f"add_done_{self.label_counter}"
                        self.label_counter += 1
                        
                        assembly.append(f"MOV :{result_loc}, {left_reg}")
                        assembly.append(f"JC {carry_label}")
                        assembly.append(f"JMP {done_label}")
                        assembly.append(f"{carry_label}:")
                        if left_loc.startswith('P'):
                            assembly.append(f"MOV {left_reg}, {left_loc}:")
                        else:
                            assembly.append(f"MOV {left_reg}, 0")  # If left was not P, high byte is 0
                        assembly.append(f"ADD {left_reg}, 1")  # Add carry
                        assembly.append(f"MOV {result_loc}:, {left_reg}")
                        assembly.append(f"{done_label}:")
                    elif self._is_register(result_loc):
                        if result_loc != left_reg:
                            assembly.append(f"MOV {result_loc}, {left_reg}")
                    elif result_loc.startswith('P'):
                        assembly.append(f"MOV :{result_loc}, {left_reg}")  # Store to low byte
                    else:
                        assembly.extend(self._generate_store_to_location(result_loc, left_reg))

        elif instruction.opcode == "u!":
            # Unary NOT operation (logical negation)
            operand = instruction.operands[0]
            result = instruction.result

            operand_loc = self.variable_locations.get(operand, self.register_map.get(operand, operand))
            result_loc = self._get_variable_location(result)

            # Load operand
            temp_reg = self._get_temp_register('R')
            if self._is_immediate_value(operand_loc):
                assembly.append(f"MOV {temp_reg}, {operand_loc}")
            elif self._is_register(operand_loc):
                assembly.append(f"MOV {temp_reg}, {operand_loc}")
            else:
                assembly.append(f"MOV {temp_reg}, [{operand_loc}]")

            # Logical NOT: if operand is 0, result is 1; otherwise result is 0
            assembly.append(f"CMP {temp_reg}, 0")
            assembly.append("JZ not_zero")  # If zero, result should be 1
            assembly.append(f"MOV {temp_reg}, 0")   # Non-zero becomes 0
            assembly.append("JMP not_done")
            assembly.append("not_zero:")
            assembly.append(f"MOV {temp_reg}, 1")   # Zero becomes 1
            assembly.append("not_done:")

            # Store result
            if self._is_register(result_loc):
                assembly.append(f"MOV {result_loc}, {temp_reg}")
            elif self._is_memory_address(result_loc):
                temp_p_reg = self._get_temp_register('P')
                assembly.append(f"MOV {temp_p_reg}, {result_loc}")
                assembly.append(f"MOV [{temp_p_reg}], {temp_reg}")
                self._return_temp_register(temp_p_reg)
            else:
                assembly.extend(self._generate_store_to_location(result_loc, temp_reg))

        elif instruction.opcode == "return":
            # Check if this is the main function
            if hasattr(self, 'current_function') and self.current_function and self.current_function.name == "main":
                # Main function should halt instead of return
                assembly.append("HLT")
            else:
                # For non-main functions, just set up return value if any
                if instruction.operands:
                    # Return with value - this will be handled by the function's RET
                    ret_val = instruction.operands[0]
                    # For now, just move to a standard return register
                    if ret_val in self.register_map:
                        assembly.append(f"MOV R0, {self.register_map[ret_val]}")
                    elif ret_val in self.variable_locations:
                        temp_reg = self._get_temp_register('R')
                        assembly.extend(self._generate_load_from_location(self.variable_locations[ret_val], temp_reg))
                        assembly.append(f"MOV R0, {temp_reg}")
                    else:
                        assembly.append(f"MOV R0, {ret_val}")
                # Don't generate RET here - it's at the end of the function

        elif instruction.opcode == "br":
            # Conditional branch
            cond = instruction.operands[0]
            then_label = instruction.operands[1]
            else_label = instruction.operands[2] if len(instruction.operands) > 2 else None

            # Check if condition is a constant first
            if cond in self.constant_map:
                # Condition is constant - can optimize
                try:
                    condition_value = int(self.constant_map[cond])
                    if condition_value != 0:
                        # Condition is true (non-zero) - always jump to then_label
                        assembly.append(f"JMP {then_label}")
                    else:
                        # Condition is false (zero) - jump to else_label if present
                        if else_label:
                            assembly.append(f"JMP {else_label}")
                except (ValueError, TypeError):
                    # Not a numeric constant, treat as regular variable
                    assembly.append(f"MOV R9, {self.constant_map[cond]}")
                    assembly.append("CMP R9, 0")
                    assembly.append(f"JNZ {then_label}")
                    if else_label:
                        assembly.append(f"JMP {else_label}")
            else:
                # Load condition into R9 (use a high register that's less likely to conflict)
                cond_loc = self.variable_locations.get(cond, self.register_map.get(cond, cond))
                if self._is_register(cond_loc):
                    assembly.append(f"MOV R9, {cond_loc}")
                elif self._is_memory_address(cond_loc):
                    # Load address into P0 then indirect access
                    assembly.append(f"MOV P0, {cond_loc}")
                    assembly.append(f"MOV R9, [P0]")
                elif self._is_immediate_value(cond_loc):
                    assembly.append(f"MOV R9, {cond_loc}")
                else:
                    # Fallback - try to load from memory
                    assembly.append(f"MOV R9, [{cond_loc}]")

                # Compare with 0 to set flags
                assembly.append("CMP R9, 0")

                # Jump if not zero
                assembly.append(f"JNZ {then_label}")
                if else_label:
                    assembly.append(f"JMP {else_label}")

        elif instruction.opcode == "branch_if":
            # Conditional branch with three operands: condition, then_label, else_label
            cond = instruction.operands[0]
            then_label = instruction.operands[1]
            else_label = instruction.operands[2]

            # Check if condition is a constant first
            if cond in self.constant_map:
                # Condition is constant - can optimize
                try:
                    condition_value = int(self.constant_map[cond])
                    if condition_value != 0:
                        # Condition is true (non-zero) - always jump to then_label
                        assembly.append(f"JMP {then_label}")
                    else:
                        # Condition is false (zero) - jump to else_label
                        assembly.append(f"JMP {else_label}")
                except (ValueError, TypeError):
                    # Not a numeric constant, treat as regular variable
                    assembly.append(f"MOV R9, {self.constant_map[cond]}")
                    assembly.append("CMP R9, 0")
                    assembly.append(f"JNZ {then_label}")
                    assembly.append(f"JMP {else_label}")
            else:
                # Load condition into R9 (use a high register that's less likely to conflict)
                cond_loc = self.variable_locations.get(cond, self.register_map.get(cond, cond))
                if self._is_register(cond_loc):
                    assembly.append(f"MOV R9, {cond_loc}")
                elif self._is_memory_address(cond_loc):
                    # Load address into P0 then indirect access
                    assembly.append(f"MOV P0, {cond_loc}")
                    assembly.append(f"MOV R9, [P0]")
                elif self._is_immediate_value(cond_loc):
                    assembly.append(f"MOV R9, {cond_loc}")
                else:
                    # Fallback - try to load from memory
                    assembly.append(f"MOV R9, [{cond_loc}]")

                # Compare with 0 to set flags
                assembly.append("CMP R9, 0")

                # Jump if not zero to then_label, otherwise fall through to else_label
                assembly.append(f"JNZ {then_label}")
                assembly.append(f"JMP {else_label}")

        elif instruction.opcode == "jmp":
            # Unconditional jump
            target = instruction.operands[0]
            assembly.append(f"JMP {target}")

        elif instruction.opcode == "call":
            # Function call
            func_name = instruction.operands[0]
            args = instruction.operands[1:]
            assembly.extend(self._generate_function_call(func_name, args, instruction.result))

        elif instruction.opcode == "u++":
            # Post-increment: result = operand, then operand++
            operand = instruction.operands[0]
            result = instruction.result
            
            operand_loc = self._get_variable_location(operand)
            result_loc = self._get_variable_location(result)
            
            # Check if result_loc conflicts with an existing variable's register
            result_conflicts = False
            if self._is_register(result_loc):
                for var_name, var_reg in self.register_map.items():
                    if var_reg == result_loc and var_name != result:
                        result_conflicts = True
                        break
            
            # For post-increment: first assign current value to result (if result is used)
            if not result_conflicts:
                if self._is_register(operand_loc) and self._is_register(result_loc):
                    # Both in registers
                    if operand_loc != result_loc:
                        assembly.append(f"MOV {result_loc}, {operand_loc}")
                    # Then increment the operand
                    assembly.append(f"INC {operand_loc}")
                elif self._is_register(operand_loc):
                    # Operand in register, result in memory or stack
                    if operand_loc != result_loc:
                        if self._is_register(result_loc):
                            assembly.append(f"MOV {result_loc}, {operand_loc}")
                        else:
                            # Result is in memory or stack - use proper store syntax
                            assembly.extend(self._generate_store_to_location(result_loc, operand_loc))
                    assembly.append(f"INC {operand_loc}")
                else:
                    # Operand in memory or stack
                    temp_reg = self._get_temp_register('R')
                    # Load from operand location (could be memory or stack)
                    assembly.extend(self._generate_load_from_location(operand_loc, temp_reg))
                    # Assign to result
                    if self._is_register(result_loc):
                        assembly.append(f"MOV {result_loc}, {temp_reg}")
                    else:
                        assembly.extend(self._generate_store_to_location(result_loc, temp_reg))
                    # Increment the value
                    assembly.append(f"INC {temp_reg}")
                    # Store back to operand location (could be memory or stack)
                    assembly.extend(self._generate_store_to_location(operand_loc, temp_reg))
                    self._return_temp_register(temp_reg)
            else:
                # Result conflicts with existing variable, just increment without storing result
                if self._is_register(operand_loc):
                    assembly.append(f"INC {operand_loc}")
                else:
                    temp_reg = self._get_temp_register('R')
                    # Load from operand location (could be memory or stack)
                    assembly.extend(self._generate_load_from_location(operand_loc, temp_reg))
                    assembly.append(f"INC {temp_reg}")
                    # Store back to operand location (could be memory or stack)
                    assembly.extend(self._generate_store_to_location(operand_loc, temp_reg))
                    self._return_temp_register(temp_reg)

        elif instruction.opcode == "u--":
            # Post-decrement: result = operand, then operand--
            operand = instruction.operands[0]
            result = instruction.result
            
            operand_loc = self._get_variable_location(operand)
            result_loc = self._get_variable_location(result)
            
            # Check if result_loc conflicts with an existing variable's register
            result_conflicts = False
            if self._is_register(result_loc):
                for var_name, var_reg in self.register_map.items():
                    if var_reg == result_loc and var_name != result:
                        result_conflicts = True
                        break
            
            # For post-decrement: first assign current value to result (if result is used)
            if not result_conflicts:
                if self._is_register(operand_loc) and self._is_register(result_loc):
                    # Both in registers
                    if operand_loc != result_loc:
                        assembly.append(f"MOV {result_loc}, {operand_loc}")
                    # Then decrement the operand
                    assembly.append(f"DEC {operand_loc}")
                elif self._is_register(operand_loc):
                    # Operand in register, result in memory or stack
                    if operand_loc != result_loc:
                        if self._is_register(result_loc):
                            assembly.append(f"MOV {result_loc}, {operand_loc}")
                        else:
                            # Result is in memory or stack - use proper store syntax
                            assembly.extend(self._generate_store_to_location(result_loc, operand_loc))
                    assembly.append(f"DEC {operand_loc}")
                else:
                    # Operand in memory or stack
                    temp_reg = self._get_temp_register('R')
                    # Load from operand location (could be memory or stack)
                    assembly.extend(self._generate_load_from_location(operand_loc, temp_reg))
                    # Assign to result
                    if self._is_register(result_loc):
                        assembly.append(f"MOV {result_loc}, {temp_reg}")
                    else:
                        assembly.extend(self._generate_store_to_location(result_loc, temp_reg))
                    # Decrement the value
                    assembly.append(f"DEC {temp_reg}")
                    # Store back to operand location (could be memory or stack)
                    assembly.extend(self._generate_store_to_location(operand_loc, temp_reg))
                    self._return_temp_register(temp_reg)
            else:
                # Result conflicts with existing variable, just decrement without storing result
                if self._is_register(operand_loc):
                    assembly.append(f"DEC {operand_loc}")
                else:
                    temp_reg = self._get_temp_register('R')
                    # Load from operand location (could be memory or stack)
                    assembly.extend(self._generate_load_from_location(operand_loc, temp_reg))
                    assembly.append(f"DEC {temp_reg}")
                    # Store back to operand location (could be memory or stack)
                    assembly.extend(self._generate_store_to_location(operand_loc, temp_reg))
                    self._return_temp_register(temp_reg)

        elif instruction.opcode == "array_get":
            # Array element access: result = array[index]
            array_var = instruction.operands[0]
            index_var = instruction.operands[1]
            result = instruction.result
            
            # Get array base address and index
            array_loc = self._get_variable_location(array_var)
            index_loc = self._get_variable_location(index_var)
            result_loc = self._get_variable_location(result)
            
            # For now, implement a simple array access
            # TODO: Implement proper array bounds checking and addressing
            
            # Load index into a register
            index_reg = self._get_temp_register('R')
            if index_var in self.constant_map:
                assembly.append(f"MOV {index_reg}, {self.constant_map[index_var]}")
            else:
                assembly.extend(self._generate_load_from_location(index_loc, index_reg))
            
            # For simplicity, treat array as base address + index
            # This is a basic implementation - real arrays would need proper memory layout
            base_reg = self._get_temp_register('P')
            if array_var in self.constant_map:
                assembly.append(f"MOV {base_reg}, {self.constant_map[array_var]}")
            else:
                assembly.extend(self._generate_load_from_location(array_loc, base_reg))
            
            # Calculate address: base + index
            assembly.append(f"ADD {base_reg}, {index_reg}")
            
            # Load value from calculated address
            value_reg = self._get_temp_register('R')
            assembly.append(f"MOV {value_reg}, [{base_reg}]")
            
            # Store result
            assembly.extend(self._generate_store_to_location(result_loc, value_reg))
            
            # Clean up temp registers
            self._return_temp_register(index_reg)
            self._return_temp_register(base_reg)
            self._return_temp_register(value_reg)

        elif instruction.opcode == "array_set":
            # Array element assignment: array[index] = value
            array_var = instruction.operands[0]
            index_var = instruction.operands[1]
            value_var = instruction.operands[2]
            
            # Get array base address, index, and value
            array_loc = self._get_variable_location(array_var)
            index_loc = self._get_variable_location(index_var)
            value_loc = self._get_variable_location(value_var)
            
            # Load index into a register
            index_reg = self._get_temp_register('R')
            if index_var in self.constant_map:
                assembly.append(f"MOV {index_reg}, {self.constant_map[index_var]}")
            else:
                assembly.extend(self._generate_load_from_location(index_loc, index_reg))
            
            # Load value into a register
            value_reg = self._get_temp_register('R')
            if value_var in self.constant_map:
                assembly.append(f"MOV {value_reg}, {self.constant_map[value_var]}")
            else:
                assembly.extend(self._generate_load_from_location(value_loc, value_reg))
            
            # Get array base address
            base_reg = self._get_temp_register('P')
            if array_var in self.constant_map:
                assembly.append(f"MOV {base_reg}, {self.constant_map[array_var]}")
            else:
                assembly.extend(self._generate_load_from_location(array_loc, base_reg))
            
            # Calculate address: base + index
            assembly.append(f"ADD {base_reg}, {index_reg}")
            
            # Store value at calculated address
            assembly.append(f"MOV [{base_reg}], {value_reg}")
            
            # Clean up temp registers
            self._return_temp_register(index_reg)
            self._return_temp_register(value_reg)
            self._return_temp_register(base_reg)

        else:
            assembly.append(f"; Unknown instruction: {instruction}")

        return assembly

    def _generate_function_call(self, func_name: str, args: List[str], result_var: str = None) -> list:
        """Generate assembly for a function call."""
        from ..builtin import graphics_builtins, sound_builtins, system_builtins, string_builtins

        assembly = []

        # Check if it's a built-in function
        graphics_functions = [
            'set_pixel', 'get_pixel', 'clear_screen', 'draw_line', 'draw_rect', 'fill_rect', 
            'set_layer', 'set_blend_mode', 'scroll_layer', 'roll_screen_x', 'roll_screen_y',
            'flip_screen_x', 'flip_screen_y', 'rotate_screen_left', 'rotate_screen_right',
            'shift_screen_x', 'shift_screen_y', 'set_sprite', 'move_sprite', 'show_sprite', 'hide_sprite'
        ]

        string_functions = [
            'strlen', 'strcpy', 'strcat', 'strcmp', 'strchr', 'substr', 'print_string', 
            'char_at', 'string_to_int', 'int_to_string', 'string_clear', 'string_fill'
        ]
        
        if func_name in graphics_functions:
            # Graphics builtin
            builtin_func = getattr(graphics_builtins, f'_{func_name}', None)
            if builtin_func:
                # Evaluate arguments to get their values
                arg_values = []
                for arg in args:
                    if arg in self.constant_map and arg not in self.variable_locations and arg not in self.register_map:
                        # Argument is a constant
                        arg_values.append(str(self.constant_map[arg]))
                    elif arg in self.register_map:
                        # Argument is in a register
                        arg_values.append(self.register_map[arg])
                    elif arg in self.stack_map:
                        # Argument is on the stack - need to load it to a temp register first
                        temp_reg = self._get_temp_register('P')
                        assembly.extend(self._generate_load_from_stack(self.stack_map[arg], temp_reg))
                        arg_values.append(temp_reg)
                    elif arg in self.variable_locations:
                        # Argument is in memory
                        arg_values.append(f"[{self.variable_locations[arg]}]")
                    elif self._is_immediate_value(arg):
                        # Argument is an immediate value
                        arg_values.append(arg)
                    else:
                        # Try to treat as a register or memory location
                        arg_values.append(arg)

                # Generate the builtin call
                try:
                    builtin_code = builtin_func(*arg_values)
                    assembly.extend(builtin_code.strip().split('\n'))
                    
                    # Handle result assignment for graphics builtin functions that return values
                    if result_var:
                        if func_name in ['get_pixel']:
                            # These functions return result in R0
                            result_location = self._get_variable_location(result_var)
                            if result_location != 'R0':
                                assembly.extend(self._generate_store_to_location(result_location, 'R0'))
                    
                    # Return any temp registers that were allocated for stack arguments
                    for i, arg in enumerate(args):
                        if arg in self.stack_map and i < len(arg_values):
                            if arg_values[i].startswith(('P', 'R')) and arg_values[i] in self.temp_allocated_registers:
                                self._return_temp_register(arg_values[i])
                except Exception as e:
                    assembly.append(f"; Error generating builtin {func_name}: {e}")

        elif func_name in ['play_tone', 'stop_channel', 'set_volume', 'set_waveform', 'play_sample', 'set_master_volume', 'set_channel_pan']:
            # Sound builtin - handle specially for play_tone
            if func_name == 'play_tone':
                # play_tone(frequency, volume, channel)
                assembly.append("; Play tone builtin")
                freq_arg = args[0] if len(args) > 0 else '440'
                vol_arg = args[1] if len(args) > 1 else '128'
                chan_arg = args[2] if len(args) > 2 else '0'
                
                # Load frequency into SF
                if freq_arg in self.constant_map:
                    assembly.append(f"MOV SF, {self.constant_map[freq_arg]}")
                elif self._is_immediate_value(freq_arg):
                    assembly.append(f"MOV SF, {freq_arg}")
                else:
                    assembly.append(f"MOV SF, {freq_arg}")  # Will be resolved later
                
                # Load volume into SV
                if vol_arg in self.constant_map:
                    assembly.append(f"MOV SV, {self.constant_map[vol_arg]}")
                elif self._is_immediate_value(vol_arg):
                    assembly.append(f"MOV SV, {vol_arg}")
                else:
                    assembly.append(f"MOV SV, {vol_arg}")  # Will be resolved later
                
                # Calculate channel base address (channel * 8) and load into SA
                if chan_arg in self.constant_map:
                    chan_addr = self.constant_map[chan_arg] * 8
                    assembly.append(f"MOV SA, {chan_addr}")
                elif self._is_immediate_value(chan_arg):
                    chan_addr = int(chan_arg, 0) * 8
                    assembly.append(f"MOV SA, {chan_addr}")
                else:
                    # Need to calculate at runtime
                    assembly.append(f"MOV R9, {chan_arg}")  # Will be resolved later
                    assembly.append("MUL R9, 8")
                    assembly.append("MOV SA, R9")
                
                assembly.append("MOV SW, 0")  # Square wave
                assembly.append("SPLAY")
            else:
                # Other sound builtin
                builtin_func = getattr(sound_builtins, f'_{func_name}', None)
                if builtin_func:
                    arg_values = []
                    for arg in args:
                        if arg in self.register_map:
                            arg_values.append(self.register_map[arg])
                        elif arg in self.stack_map:
                            # Argument is on the stack - need to load it to a temp register first
                            temp_reg = self._get_temp_register('P')
                            assembly.extend(self._generate_load_from_stack(self.stack_map[arg], temp_reg))
                            arg_values.append(temp_reg)
                        elif arg in self.variable_locations:
                            arg_values.append(f"[{self.variable_locations[arg]}]")
                        elif arg in self.constant_map:
                            arg_values.append(self.constant_map[arg])
                        elif self._is_immediate_value(arg):
                            arg_values.append(arg)
                        else:
                            arg_values.append(arg)

                    try:
                        builtin_code = builtin_func(*arg_values)
                        assembly.extend(builtin_code.strip().split('\n'))
                        
                        # Return any temp registers that were allocated for stack arguments
                        for i, arg in enumerate(args):
                            if arg in self.stack_map and i < len(arg_values):
                                if arg_values[i].startswith(('P', 'R')) and arg_values[i] in self.temp_allocated_registers:
                                    self._return_temp_register(arg_values[i])
                    except Exception as e:
                        assembly.append(f"; Error generating builtin {func_name}: {e}")

        elif func_name in string_functions:
            # String builtin
            builtin_func = getattr(string_builtins, f'_{func_name}', None)
            if builtin_func:
                arg_values = []
                for arg in args:
                    if arg in self.constant_map and arg not in self.variable_locations and arg not in self.register_map:
                        # Argument is a constant
                        arg_values.append(str(self.constant_map[arg]))
                    elif arg in self.register_map:
                        # Argument is in a register
                        arg_values.append(self.register_map[arg])
                    elif arg in self.stack_map:
                        # Argument is on the stack - need to load it to a temp register first
                        temp_reg = self._get_temp_register('P')
                        assembly.extend(self._generate_load_from_stack(self.stack_map[arg], temp_reg))
                        arg_values.append(temp_reg)
                    elif arg in self.variable_locations:
                        # Argument is in memory
                        arg_values.append(f"[{self.variable_locations[arg]}]")
                    elif self._is_immediate_value(arg):
                        # Argument is an immediate value
                        arg_values.append(arg)
                    else:
                        # For string literals, check if it's a string address
                        if arg.startswith('0x'):
                            arg_values.append(arg)
                        else:
                            arg_values.append(arg)

                try:
                    builtin_code = builtin_func(*arg_values)
                    assembly.extend(builtin_code.strip().split('\n'))
                    
                    # Handle result assignment for string builtin functions that return values
                    if result_var:
                        if func_name in ['strlen', 'strcmp', 'strchr', 'char_at', 'string_to_int']:
                            # These functions return result in R0
                            result_location = self._get_variable_location(result_var)
                            if result_location != 'R0':
                                assembly.extend(self._generate_store_to_location(result_location, 'R0'))
                        elif func_name in ['substr', 'int_to_string']:
                            # These functions return result in P0 (string address)
                            result_location = self._get_variable_location(result_var)
                            if result_location != 'P0':
                                assembly.extend(self._generate_store_to_location(result_location, 'P0'))
                    
                    # Return any temp registers that were allocated for stack arguments
                    for i, arg in enumerate(args):
                        if arg in self.stack_map and i < len(arg_values):
                            if arg_values[i].startswith(('P', 'R')) and arg_values[i] in self.temp_allocated_registers:
                                self._return_temp_register(arg_values[i])
                except Exception as e:
                    assembly.append(f"; Error generating builtin {func_name}: {e}")

        elif func_name in ['enable_interrupts', 'disable_interrupts', 'set_interrupt_handler', 'configure_timer', 'read_keyboard', 'clear_keyboard_buffer', 'get_timer_value', 'set_timer_match', 'memory_read', 'memory_write', 'halt', 'reset', 'vector', 'memory.region', 'hardware.reset', 'memory.initialize_heap', 'setup_timer_interrupt', 'setup_keyboard_interrupt', 'clear_timer_interrupt', 'clear_keyboard_interrupt', 'software_interrupt', 'random', 'random_range']:
            # System builtin - handle specially for functions that need integer arguments
            if func_name in ['memory_read', 'memory_write']:
                # Memory functions need special handling
                assembly.append(f"; {func_name} builtin")
                if func_name == 'memory_write':
                    # memory_write(address, value)
                    addr_arg = args[0] if len(args) > 0 else '0'
                    value_arg = args[1] if len(args) > 1 else '0'
                    
                    # Load address into P0
                    if addr_arg in self.constant_map:
                        assembly.append(f"MOV P0, {self.constant_map[addr_arg]}")
                    elif self._is_immediate_value(addr_arg):
                        assembly.append(f"MOV P0, {addr_arg}")
                    else:
                        assembly.append(f"MOV P0, {addr_arg}")  # Will be resolved later
                    
                    # Load value into R0
                    if value_arg in self.constant_map:
                        assembly.append(f"MOV R0, {self.constant_map[value_arg]}")
                    elif self._is_immediate_value(value_arg):
                        assembly.append(f"MOV R0, {value_arg}")
                    else:
                        assembly.append(f"MOV R0, {value_arg}")  # Will be resolved later
                    
                    assembly.append("MOV [P0], R0")
                    
                elif func_name == 'memory_read':
                    # memory_read(address)
                    addr_arg = args[0] if len(args) > 0 else '0'
                    
                    # Load address into P0
                    if addr_arg in self.constant_map:
                        assembly.append(f"MOV P0, {self.constant_map[addr_arg]}")
                    elif self._is_immediate_value(addr_arg):
                        assembly.append(f"MOV P0, {addr_arg}")
                    else:
                        assembly.append(f"MOV P0, {addr_arg}")  # Will be resolved later
                    
                    assembly.append("MOV R0, [P0]")
                    
            elif func_name == 'play_tone':
                # play_tone(frequency, volume, channel)
                assembly.append("; Play tone builtin")
                freq_arg = args[0] if len(args) > 0 else '440'
                vol_arg = args[1] if len(args) > 1 else '128'
                chan_arg = args[2] if len(args) > 2 else '0'
                
                # Load frequency into SF
                if freq_arg in self.constant_map:
                    assembly.append(f"MOV SF, {self.constant_map[freq_arg]}")
                elif self._is_immediate_value(freq_arg):
                    assembly.append(f"MOV SF, {freq_arg}")
                else:
                    assembly.append(f"MOV SF, {freq_arg}")  # Will be resolved later
                
                # Load volume into SV
                if vol_arg in self.constant_map:
                    assembly.append(f"MOV SV, {self.constant_map[vol_arg]}")
                elif self._is_immediate_value(vol_arg):
                    assembly.append(f"MOV SV, {vol_arg}")
                else:
                    assembly.append(f"MOV SV, {vol_arg}")  # Will be resolved later
                
                # Calculate channel base address (channel * 8) and load into SA
                if chan_arg in self.constant_map:
                    chan_addr = self.constant_map[chan_arg] * 8
                    assembly.append(f"MOV SA, {chan_addr}")
                elif self._is_immediate_value(chan_arg):
                    chan_addr = int(chan_arg, 0) * 8
                    assembly.append(f"MOV SA, {chan_addr}")
                else:
                    # Need to calculate at runtime
                    assembly.append(f"MOV R9, {chan_arg}")  # Will be resolved later
                    assembly.append("MUL R9, 8")
                    assembly.append("MOV SA, R9")
                
                assembly.append("MOV SW, 0")  # Square wave
                assembly.append("SPLAY")
                
            else:
                # Other system builtin
                builtin_func = getattr(system_builtins, f'_{func_name}', None)
                if builtin_func:
                    arg_values = []
                    for arg in args:
                        if arg in self.register_map:
                            # Argument is in a register
                            arg_values.append(self.register_map[arg])
                        elif arg in self.stack_map:
                            # Argument is on the stack - need to load it to a temp register first
                            temp_reg = self._get_temp_register('P')
                            assembly.extend(self._generate_load_from_stack(self.stack_map[arg], temp_reg))
                            arg_values.append(temp_reg)
                            # Note: temp register will be returned after builtin code generation
                        elif arg in self.variable_locations:
                            # Argument is in memory
                            arg_values.append(f"[{self.variable_locations[arg]}]")
                        elif arg in self.constant_map:
                            # Argument is a constant value
                            arg_values.append(self.constant_map[arg])
                        elif self._is_immediate_value(arg):
                            # Argument is an immediate value
                            arg_values.append(arg)
                        else:
                            # Variable not yet allocated - defer to runtime resolution
                            arg_values.append(arg)

                    try:
                        builtin_code = builtin_func(*arg_values)
                        assembly.extend(builtin_code.strip().split('\n'))
                        
                        # Handle result assignment for builtin functions
                        if result_var:
                            if func_name in ['random', 'random_range']:
                                # These functions return result in P0
                                result_location = self._get_variable_location(result_var)
                                if result_location != 'P0':
                                    assembly.extend(self._generate_store_to_location(result_location, 'P0'))
                            elif func_name in ['memory_read', 'get_timer_value']:
                                # These functions return result in R0
                                result_location = self._get_variable_location(result_var)
                                if result_location != 'R0':
                                    assembly.extend(self._generate_store_to_location(result_location, 'R0'))
                        
                        # Return any temp registers that were allocated for stack arguments
                        for i, arg in enumerate(args):
                            if arg in self.stack_map and i < len(arg_values):
                                if arg_values[i].startswith(('P', 'R')) and arg_values[i] in self.temp_allocated_registers:
                                    self._return_temp_register(arg_values[i])
                    except Exception as e:
                        assembly.append(f"; Error generating builtin {func_name}: {e}")

        else:
            # User-defined function call - use stack-based calling convention for proper parameter access
            assembly.append(f"; Call user function: {func_name}")
            
            # Step 1: Push arguments onto stack in reverse order (last argument first)
            # This ensures the first argument is at FP+4, second at FP+6, etc.
            for arg in reversed(args):
                temp_reg = self._get_temp_register('R')
                
                if arg in self.constant_map and arg not in self.register_map and arg not in self.variable_locations and arg not in self.stack_map:
                    # Argument is a constant
                    assembly.append(f"MOV {temp_reg}, {self.constant_map[arg]}")
                elif arg in self.register_map:
                    # Argument is in a register
                    assembly.append(f"MOV {temp_reg}, {self.register_map[arg]}")
                elif arg in self.stack_map:
                    # Argument is on the stack - need to load it first
                    assembly.extend(self._generate_load_from_stack(self.stack_map[arg], temp_reg))
                elif arg in self.variable_locations:
                    # Argument is in memory
                    assembly.extend(self._generate_load_from_location(self.variable_locations[arg], temp_reg))
                elif self._is_immediate_value(arg):
                    # Argument is an immediate value
                    assembly.append(f"MOV {temp_reg}, {arg}")
                else:
                    # Try to resolve as variable location
                    arg_location = self._get_variable_location(arg)
                    assembly.extend(self._generate_load_from_location(arg_location, temp_reg))
                
                # Push the argument onto the stack
                assembly.append(f"PUSH {temp_reg}")
                self._return_temp_register(temp_reg)
            
            # Step 2: Call the function
            assembly.append(f"CALL {func_name}")
            
            # Step 3: Clean up parameters from stack
            if args:
                param_count = len(args)
                # Each parameter is 2 bytes (16-bit), so multiply by 2
                stack_cleanup = param_count * 2
                assembly.append(f"ADD SP, {stack_cleanup}         ; Clean up {param_count} parameters")
            
            # Step 4: Function result is in R0
            if result_var:
                result_location = self._get_variable_location(result_var)
                if result_location != 'R0':
                    assembly.extend(self._generate_store_to_location(result_location, 'R0'))

        return assembly

    def _is_register(self, location: str) -> bool:
        """Check if a location is a register."""
        return location in ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9',
                           'P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9']

    def _allocate_variable(self, var_name: str) -> str:
        """Allocate memory location for a variable (fallback method)."""
        if var_name not in self.variable_locations:
            self.variable_locations[var_name] = f"0x{self.next_memory_location:04X}"
            self.next_memory_location += 2  # Allocate 2 bytes for each variable
        return self.variable_locations[var_name]

    def _is_memory_address(self, value: str) -> bool:
        """Check if a value is a memory address (allocated variable location)."""
        if value is None:
            return False
        return value.startswith("0x") and len(value) == 6  # Format: 0xXXXX

    def _generate_store_to_memory(self, location: str, register: str) -> list:
        """Generate code to store a register value to a memory location."""
        assembly = []
        if self._is_memory_address(location):
            # For memory address in format 0xXXXX, use direct indirect addressing
            assembly.append(f"MOV [{location}], {register}")
        else:
            # For register indirect, use direct syntax
            assembly.append(f"MOV [{location}], {register}")
        return assembly

    def _get_high_byte(self, loc: str) -> str:
        """Get the high byte of a location (register or immediate)."""
        if self._is_immediate_value(loc):
            val = int(loc, 0)
            return str(val >> 8)
        else:
            return f"{loc}:"

    def _get_low_byte(self, loc: str) -> str:
        """Get the low byte of a location (register or immediate)."""
        if self._is_immediate_value(loc):
            val = int(loc, 0)
            return str(val & 0xFF)
        else:
            return f":{loc}"

    def _is_immediate_value(self, value: str) -> bool:
        """Check if a value is an immediate (constant) value."""
        if not value:
            return False
        if self._is_memory_address(value):
            return False  # Memory addresses should be dereferenced
        try:
            int(value, 0)  # Try to parse as integer (handles 0x, 0b, decimal)
            return True
        except ValueError:
            return False

    def _resolve_variables(self, assembly_code: str) -> str:
        """
        Critical variable resolution pass that replaces v0, v1, v2... placeholders 
        with actual register allocations.
        
        This fixes the bug where IR variables like v0, v8, v9 are not being 
        properly substituted with allocated registers.
        """
        logger.debug(f"Starting variable resolution. Register map: {self.register_map}")
        logger.debug(f"Stack map: {self.stack_map}")
        logger.debug(f"Variable locations: {self.variable_locations}")
        
        lines = assembly_code.split('\n')
        resolved_lines = []
        
        for line_num, line in enumerate(lines):
            original_line = line
            
            # Skip comments and labels
            if line.strip().startswith(';') or line.strip().endswith(':') or not line.strip():
                resolved_lines.append(line)
                continue
            
            # Find all variable references in this line (v followed by digits)
            import re
            var_pattern = r'\bv(\d+)\b'
            variables_in_line = re.findall(var_pattern, line)
            
            for var_num in variables_in_line:
                var_name = f"v{var_num}"
                replacement = None
                
                # Try to find the variable in our allocation maps
                if var_name in self.register_map:
                    replacement = self.register_map[var_name]
                elif var_name in self.stack_map:
                    # For stack locations, we need to generate proper access code inline
                    # This is complex, so for now let's use a temporary register approach
                    stack_location = self.stack_map[var_name]
                    logger.debug(f"Stack variable {var_name} at {stack_location} needs access code generation")
                    # For this resolution pass, we'll substitute the stack location directly
                    # The actual access code generation happens during instruction generation
                    replacement = stack_location
                elif var_name in self.variable_locations:
                    replacement = self.variable_locations[var_name]
                elif var_name in self.constant_map:
                    replacement = str(self.constant_map[var_name])
                else:
                    # Variable not allocated - this indicates the register allocator didn't handle it
                    # OR it was spilled to memory - check if it's in the spilled set
                    if hasattr(self, '_has_optimized_allocation') and self._has_optimized_allocation and var_name in self.spilled_vars:
                        # This variable was spilled by the optimizer - allocate memory for it
                        replacement = self._allocate_spilled_memory(var_name)
                        logger.debug(f"Allocated memory for spilled variable {var_name} -> {replacement}")
                    else:
                        # Variable not pre-allocated - use emergency allocation
                        logger.info(f"Variable {var_name} not pre-allocated, using emergency allocation (line {line_num})")
                        replacement = self._emergency_allocate_variable(var_name)
                
                if replacement:
                    # For stack locations, avoid double bracket issues
                    if (replacement.startswith('FP+') or replacement.startswith('FP-')) and '[' in line:
                        # The instruction already has brackets, so we need to expand the stack access
                        # This is a complex case that needs full instruction rewriting
                        # For now, let's detect and handle specific patterns
                        if f'[{var_name}]' in line:
                            # Replace [vN] with the stack access pattern
                            if replacement.startswith('FP+'):
                                offset = replacement[3:]  # Remove "FP+"
                                temp_reg = 'P6'  # Use a consistent temp register
                                stack_access = f'{temp_reg}, P9\nADD {temp_reg}, {offset}\nMOV R3, [{temp_reg}]'
                                # This is getting complex, let's use simpler approach for now
                                line = line.replace(f'[{var_name}]', f'[{replacement}]')
                            elif replacement.startswith('FP-'):
                                offset = replacement[3:]  # Remove "FP-"
                                line = line.replace(f'[{var_name}]', f'[{replacement}]')
                        else:
                            # Simple variable name replacement
                            line = re.sub(rf'\b{var_name}\b', replacement, line)
                    else:
                        # Replace the variable with its allocation
                        line = re.sub(rf'\b{var_name}\b', replacement, line)
                    logger.debug(f"Resolved {var_name} -> {replacement}")
                else:
                    logger.warning(f"Failed to resolve variable {var_name} in line: {line}")
            
            resolved_lines.append(line)
            
            # Log significant changes
            if line != original_line:
                logger.debug(f"Line {line_num}: '{original_line}' -> '{line}'")
        
        resolved_code = '\n'.join(resolved_lines)
        logger.debug("Variable resolution completed")
        return resolved_code
    
    def _emergency_allocate_variable(self, var_name: str) -> str:
        """
        Emergency variable allocation when the register allocator didn't handle a variable.
        This is a normal fallback mechanism, not an error condition.
        """
        logger.debug(f"Emergency allocation for variable {var_name}")
        
        # Try to allocate a register first
        reg = self._allocate_register('int16')  # Default to int16
        if reg:
            self.register_map[var_name] = reg
            logger.debug(f"Emergency allocated register {reg} for {var_name}")
            return reg
        
        # If no registers, try stack
        stack_loc = self._allocate_stack_location('int16')
        self.stack_map[var_name] = stack_loc
        logger.debug(f"Emergency allocated stack location {stack_loc} for {var_name}")
        return stack_loc
    
    def _generate_store_to_memory(self, location: str, source_reg: str) -> list:
        """Generate assembly to store a value to memory location."""
        assembly = []
        if location.startswith('0x'):
            # Direct memory address
            assembly.append(f"MOV [{location}], {source_reg}")
        else:
            # Check if already bracketed to avoid double brackets
            if location.startswith('[') and location.endswith(']'):
                assembly.append(f"MOV {location}, {source_reg}")
            else:
                assembly.append(f"MOV [{location}], {source_reg}")
        return assembly
    
    def _allocate_spilled_memory(self, var_name: str) -> str:
        """Allocate memory location for a spilled variable."""
        # Use static memory allocation for spilled variables
        location = f"0x{self.next_memory_location:04X}"
        self.next_memory_location += 2  # Always allocate 2 bytes for simplicity
        self.variable_locations[var_name] = location
        logger.debug(f"Allocated memory {location} for spilled variable {var_name}")
        return location
