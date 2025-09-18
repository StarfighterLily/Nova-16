# Astrid Code Generator Specification

## Overview

The Astrid code generator is responsible for translating the analyzed Abstract Syntax Tree (AST) into Nova-16 assembly code through the Intermediate Representation (IR). It performs instruction selection, register allocation, optimization, and final assembly generation to produce efficient machine code for the Nova-16 CPU.

**Key Responsibilities:**
- Convert AST to IR with type information
- Perform register allocation for Nova-16's register set
- Apply optimization passes (constant folding, dead code elimination, etc.)
- Generate Nova-16 assembly instructions
- Handle hardware register mapping
- Optimize for Nova-16's memory layout and instruction set

## Code Generation Pipeline

### Pipeline Overview

```
Analyzed AST → IR Generation → Optimization Passes → Register Allocation → Assembly Generation → Binary Output
```

### IR Generation Phase

```python
class IRGenerator:
    def __init__(self, analyzed_program: AnalyzedProgram):
        self.analyzed_program = analyzed_program
        self.ir_module = IRModule()
        self.temp_counter = 0
        self.current_function = None

    def generate_ir(self) -> IRModule:
        """Main IR generation entry point"""
        # Generate global declarations
        self.generate_globals()

        # Generate function definitions
        for func in self.analyzed_program.original_ast.functions:
            self.generate_function_ir(func)

        # Generate class definitions
        for cls in self.analyzed_program.original_ast.classes:
            self.generate_class_ir(cls)

        return self.ir_module

    def create_temp(self, type_hint: IRType = None) -> IRTemp:
        """Create a temporary variable"""
        name = f"%{self.temp_counter}"
        self.temp_counter += 1
        return IRTemp(name, type_hint)
```

### IR Instruction Classes

```python
from dataclasses import dataclass
from typing import List, Optional, Any
from enum import Enum

class IRType(Enum):
    I8 = "i8"
    I16 = "i16"
    FLOAT = "float"
    BOOL = "bool"
    PTR = "ptr"
    VOID = "void"

@dataclass
class IRTemp:
    name: str
    type_hint: Optional[IRType] = None

@dataclass
class IRInstruction:
    """Base class for IR instructions"""
    pass

@dataclass
class IRLoad(IRInstruction):
    """Load from memory or register"""
    dest: IRTemp
    source: Any  # Memory address or register
    volatile: bool = False

@dataclass
class IRStore(IRInstruction):
    """Store to memory or register"""
    value: Any
    dest: Any  # Memory address or register
    volatile: bool = False

@dataclass
class IRBinaryOp(IRInstruction):
    """Binary operations"""
    dest: IRTemp
    left: Any
    operator: str
    right: Any

@dataclass
class IRUnaryOp(IRInstruction):
    """Unary operations"""
    dest: IRTemp
    operator: str
    operand: Any

@dataclass
class IRCall(IRInstruction):
    """Function calls"""
    dest: Optional[IRTemp]
    function: str
    arguments: List[Any]

@dataclass
class IRJump(IRInstruction):
    """Unconditional jump"""
    target: str

@dataclass
class IRBranch(IRInstruction):
    """Conditional branch"""
    condition: Any
    true_target: str
    false_target: str

@dataclass
class IRReturn(IRInstruction):
    """Return from function"""
    value: Optional[Any]

@dataclass
class IRPhi(IRInstruction):
    """Phi function for SSA"""
    dest: IRTemp
    operands: List[tuple[Any, str]]  # (value, predecessor_block)

@dataclass
class IRHardwareOp(IRInstruction):
    """Hardware-specific operations"""
    operation: str
    operands: List[Any]
```

## Expression Code Generation

### Main Expression Dispatcher

```python
def generate_expression(self, expr: Expression) -> IROperand:
    """Main expression IR generation dispatcher"""
    if isinstance(expr, Literal):
        return self.generate_literal(expr)
    elif isinstance(expr, Identifier):
        return self.generate_identifier(expr)
    elif isinstance(expr, BinaryOp):
        return self.generate_binary_op(expr)
    elif isinstance(expr, UnaryOp):
        return self.generate_unary_op(expr)
    elif isinstance(expr, FunctionCall):
        return self.generate_function_call(expr)
    elif isinstance(expr, Assignment):
        return self.generate_assignment(expr)
    elif isinstance(expr, HardwareAccess):
        return self.generate_hardware_access(expr)
    elif isinstance(expr, PostfixOp):
        return self.generate_postfix_op(expr)
    else:
        self.error(f"Unsupported expression type: {type(expr)}")
        return self.create_temp()  # Return dummy temp
```

### Binary Operation Generation

```python
def generate_binary_op(self, expr: BinaryOp) -> IRTemp:
    """Generate IR for binary operations"""
    left = self.generate_expression(expr.left)
    right = self.generate_expression(expr.right)

    result = self.create_temp()

    # Handle different operator types
    if expr.operator in ['+', '-', '*', '/', '%']:
        ir_op = IRBinaryOp(result, left, expr.operator, right)
    elif expr.operator in ['==', '!=', '<', '<=', '>', '>=']:
        ir_op = IRBinaryOp(result, left, 'cmp_' + expr.operator, right)
        result.type_hint = IRType.BOOL
    elif expr.operator in ['and', 'or']:
        ir_op = IRBinaryOp(result, left, expr.operator, right)
        result.type_hint = IRType.BOOL
    elif expr.operator in ['&', '|', '^', '<<', '>>']:
        ir_op = IRBinaryOp(result, left, expr.operator, right)

    self.current_block.add_instruction(ir_op)
    return result
```

### Function Call Generation

```python
def generate_function_call(self, expr: FunctionCall) -> Optional[IRTemp]:
    """Generate IR for function calls"""
    # Generate arguments
    arguments = []
    for arg in expr.arguments:
        arg_ir = self.generate_expression(arg)
        arguments.append(arg_ir)

    # Handle return value
    result = None
    if not self.is_void_function(expr.function):
        result = self.create_temp()

    # Generate call instruction
    call_ir = IRCall(result, expr.function.name, arguments)
    self.current_block.add_instruction(call_ir)

    return result
```

### Hardware Register Access

```python
def generate_hardware_access(self, expr: HardwareAccess) -> IRTemp:
    """Generate IR for hardware register access"""
    result = self.create_temp()

    # Map hardware register to IR
    register_map = {
        'VM': 'hw_video_mode',
        'VL': 'hw_video_layer',
        'VX': 'hw_video_x',
        'VY': 'hw_video_y',
        'SA': 'hw_sound_address',
        'SF': 'hw_sound_frequency',
        'SV': 'hw_sound_volume',
        'SW': 'hw_sound_waveform',
        'TT': 'hw_timer_value',
        'TM': 'hw_timer_match',
        'TC': 'hw_timer_control',
        'TS': 'hw_timer_speed',
        'SP': 'hw_stack_pointer',
        'FP': 'hw_frame_pointer',
    }

    hw_register = register_map.get(expr.register, expr.register)

    # Generate load instruction
    load_ir = IRLoad(result, hw_register, volatile=True)
    self.current_block.add_instruction(load_ir)

    return result
```

### Postfix Operation Generation

```python
def generate_postfix_op(self, expr: PostfixOp) -> IRTemp:
    """Generate IR for postfix increment/decrement operations"""
    # Postfix operations return the original value, then modify the variable
    # We need to: 1) Save original value, 2) Perform increment/decrement, 3) Return saved value

    operand = expr.operand
    operator = expr.operator

    # Generate operand address/expression
    operand_ir = self.generate_expression(operand)

    # Create temp for original value (this will be returned)
    original_value = self.create_temp()

    # Load current value
    load_ir = IRLoad(original_value, operand_ir)
    self.current_block.add_instruction(load_ir)

    # Create temp for new value
    new_value = self.create_temp()

    # Generate increment/decrement operation
    if operator == '++':
        # Add 1 to current value
        add_ir = IRBinaryOp(new_value, original_value, '+', IRLiteral(1))
        self.current_block.add_instruction(add_ir)
    elif operator == '--':
        # Subtract 1 from current value
        sub_ir = IRBinaryOp(new_value, original_value, '-', IRLiteral(1))
        self.current_block.add_instruction(sub_ir)

    # Store new value back to variable
    store_ir = IRStore(new_value, operand_ir)
    self.current_block.add_instruction(store_ir)

    # Return original value (postfix semantics)
    return original_value
```

## Statement Code Generation

### Function Definition Generation

```python
def generate_function_ir(self, func: FunctionDef):
    """Generate IR for function definition"""
    # Create function IR
    ir_function = IRFunction(func.name, func.parameters)

    # Set current function context
    self.current_function = ir_function

    # Generate parameter handling
    for i, param in enumerate(func.parameters):
        param_temp = self.create_temp()
        ir_function.add_parameter(param_temp, param)

    # Create entry block
    entry_block = IRBasicBlock("entry")
    ir_function.add_block(entry_block)
    self.current_block = entry_block

    # Generate function body
    for stmt in func.body:
        self.generate_statement(stmt)

    # Ensure return statement
    if not self.has_return_statement(func.body):
        return_ir = IRReturn(None)
        self.current_block.add_instruction(return_ir)

    self.ir_module.add_function(ir_function)
    self.current_function = None
```

### Control Flow Generation

```python
def generate_if_statement(self, stmt: If):
    """Generate IR for if statement"""
    # Generate condition
    condition = self.generate_expression(stmt.condition)

    # Create blocks
    then_block = IRBasicBlock(f"if_then_{self.block_counter}")
    else_block = IRBasicBlock(f"if_else_{self.block_counter}")
    merge_block = IRBasicBlock(f"if_merge_{self.block_counter}")

    self.block_counter += 1

    # Generate branch
    branch_ir = IRBranch(condition, then_block.name, else_block.name)
    self.current_block.add_instruction(branch_ir)

    # Generate then branch
    self.current_function.add_block(then_block)
    self.current_block = then_block
    for then_stmt in stmt.then_branch:
        self.generate_statement(then_stmt)
    then_jump = IRJump(merge_block.name)
    self.current_block.add_instruction(then_jump)

    # Generate else branch
    self.current_function.add_block(else_block)
    self.current_block = else_block
    if stmt.else_branch:
        for else_stmt in stmt.else_branch:
            self.generate_statement(else_stmt)
    else_jump = IRJump(merge_block.name)
    self.current_block.add_instruction(else_jump)

    # Add merge block
    self.current_function.add_block(merge_block)
    self.current_block = merge_block
```

## Register Allocation

### Register Allocation Strategy

```python
class RegisterAllocator:
    def __init__(self):
        # Nova-16 register sets
        self.r_registers = [f"R{i}" for i in range(10)]  # R0-R9 (8-bit)
        self.p_registers = [f"P{i}" for i in range(10)]  # P0-P9 (16-bit)

        # Reserved registers
        self.reserved = {"P8", "P9"}  # SP, FP

        # Hardware registers (cannot be allocated)
        self.hardware = {
            "VM", "VL", "VX", "VY", "SA", "SF", "SV", "SW",
            "TT", "TM", "TC", "TS", "SP", "FP"
        }

        # Allocation state
        self.available_r = set(self.r_registers) - self.reserved
        self.available_p = set(self.p_registers) - self.reserved
        self.allocation_map = {}

    def allocate_register(self, temp: IRTemp, preferred_type: str = None) -> str:
        """Allocate a register for a temporary"""
        if temp.name in self.allocation_map:
            return self.allocation_map[temp.name]

        # Choose register based on type hints
        if temp.type_hint == IRType.I8 or preferred_type == "r":
            if self.available_r:
                register = self.available_r.pop()
                self.allocation_map[temp.name] = register
                return register
        elif temp.type_hint in [IRType.I16, IRType.PTR] or preferred_type == "p":
            if self.available_p:
                register = self.available_p.pop()
                self.allocation_map[temp.name] = register
                return register

        # Spill to stack if no registers available
        return self.spill_to_stack(temp)

    def allocate_byte_access(self, temp: IRTemp, is_high_byte: bool) -> str:
        """Allocate byte access to P register for optimal 8-bit operations"""
        # Prefer P registers for byte access to avoid additional MOV instructions
        if self.available_p:
            register = self.available_p.pop()
            # Mark as byte-access register
            self.allocation_map[temp.name] = f"{register}:{'' if is_high_byte else ':'}"
            return self.allocation_map[temp.name]
        
        # Fall back to R register if no P registers available
        if self.available_r:
            register = self.available_r.pop()
            self.allocation_map[temp.name] = register
            return register
            
        # Spill to stack
        return self.spill_to_stack(temp)
```

### Byte Access Optimization Strategy

For optimal system utilization, the register allocator prioritizes P register byte access for 8-bit operations:

- **High Byte Access (`P0:`)**: Used for accessing the most significant byte of 16-bit values
- **Low Byte Access (`:P0`)**: Used for accessing the least significant byte of 16-bit values
- **Automatic Selection**: Compiler automatically chooses byte access when:
  - Operating on 8-bit values stored in 16-bit registers
  - Performing byte-level arithmetic or logic operations
  - Accessing struct fields or array elements

**Benefits:**
- Reduces instruction count by eliminating MOV operations
- Improves performance for byte-oriented algorithms
- Optimizes memory usage in register-constrained scenarios

    def spill_to_stack(self, temp: IRTemp) -> str:
        """Spill temporary to stack"""
        # Generate stack slot
        stack_slot = f"[FP-{self.stack_offset}]"
        self.stack_offset += 2  # 16-bit aligned
        self.allocation_map[temp.name] = stack_slot
        return stack_slot
```

## Assembly Code Generation

### Instruction Selection

```python
class AssemblyGenerator:
    def __init__(self, ir_module: IRModule, register_allocation: dict):
        self.ir_module = ir_module
        self.register_allocation = register_allocation
        self.assembly = []
        self.label_counter = 0

    def generate_assembly(self) -> List[str]:
        """Generate Nova-16 assembly from IR"""
        # Generate data section
        self.generate_data_section()

        # Generate code section
        self.generate_code_section()

        return self.assembly

    def generate_instruction(self, ir_instr: IRInstruction) -> List[str]:
        """Generate assembly for IR instruction"""
        if isinstance(ir_instr, IRBinaryOp):
            return self.generate_binary_op_assembly(ir_instr)
        elif isinstance(ir_instr, IRLoad):
            return self.generate_load_assembly(ir_instr)
        elif isinstance(ir_instr, IRStore):
            return self.generate_store_assembly(ir_instr)
        elif isinstance(ir_instr, IRCall):
            return self.generate_call_assembly(ir_instr)
        elif isinstance(ir_instr, IRJump):
            return self.generate_jump_assembly(ir_instr)
        elif isinstance(ir_instr, IRBranch):
            return self.generate_branch_assembly(ir_instr)
        elif isinstance(ir_instr, IRReturn):
            return self.generate_return_assembly(ir_instr)
        else:
            return [f"; Unhandled instruction: {type(ir_instr)}"]
```

### Binary Operation Assembly

```python
def generate_binary_op_assembly(self, instr: IRBinaryOp) -> List[str]:
    """Generate assembly for binary operations"""
    dest_reg = self.register_allocation[instr.dest.name]
    left_operand = self.get_operand_assembly(instr.left)
    right_operand = self.get_operand_assembly(instr.right)

    assembly = []

    # Load operands into registers if needed
    if not self.is_register(left_operand):
        left_reg = self.allocate_temp_register()
        assembly.append(f"MOV {left_reg}, {left_operand}")
    else:
        left_reg = left_operand

    if not self.is_register(right_operand):
        right_reg = self.allocate_temp_register()
        assembly.append(f"MOV {right_reg}, {right_operand}")
    else:
        right_reg = right_operand

    # Generate operation
    if instr.operator == '+':
        assembly.append(f"ADD {left_reg}, {right_reg}")
        if dest_reg != left_reg:
            assembly.append(f"MOV {dest_reg}, {left_reg}")
    elif instr.operator == '-':
        assembly.append(f"SUB {left_reg}, {right_reg}")
        if dest_reg != left_reg:
            assembly.append(f"MOV {dest_reg}, {left_reg}")
    elif instr.operator == '*':
        assembly.append(f"MUL {left_reg}, {right_reg}")
        if dest_reg != left_reg:
            assembly.append(f"MOV {dest_reg}, {left_reg}")
    elif instr.operator == '/':
        assembly.append(f"DIV {left_reg}, {right_reg}")
        if dest_reg != left_reg:
            assembly.append(f"MOV {dest_reg}, {left_reg}")
    # ... additional operators

    return assembly
```

### Function Call Assembly

```python
def generate_call_assembly(self, instr: IRCall) -> List[str]:
    """Generate assembly for function calls"""
    assembly = []

    # Save caller-saved registers
    assembly.extend(self.save_caller_saved_registers())

    # Push arguments (first 4 in registers, rest on stack)
    for i, arg in enumerate(instr.arguments):
        if i < 4:
            # Pass in registers P0-P3
            arg_assembly = self.get_operand_assembly(arg)
            assembly.append(f"MOV P{i}, {arg_assembly}")
        else:
            # Push to stack
            arg_assembly = self.get_operand_assembly(arg)
            assembly.append(f"PUSH {arg_assembly}")

    # Call function
    assembly.append(f"CALL {instr.function}")

    # Handle return value
    if instr.dest:
        dest_reg = self.register_allocation[instr.dest.name]
        if dest_reg.startswith('P'):
            assembly.append(f"MOV {dest_reg}, P0")
        else:
            assembly.append(f"MOV {dest_reg}, R0")

    # Restore caller-saved registers
    assembly.extend(self.restore_caller_saved_registers())

    return assembly
```

## Optimization Passes

### Constant Folding

```python
class ConstantFoldingPass:
    def run(self, ir_module: IRModule):
        """Perform constant folding optimization"""
        for function in ir_module.functions:
            for block in function.blocks:
                new_instructions = []
                for instr in block.instructions:
                    if isinstance(instr, IRBinaryOp):
                        folded = self.try_fold_binary_op(instr)
                        if folded:
                            new_instructions.append(folded)
                        else:
                            new_instructions.append(instr)
                    else:
                        new_instructions.append(instr)
                block.instructions = new_instructions

    def try_fold_binary_op(self, instr: IRBinaryOp) -> Optional[IRInstruction]:
        """Try to fold a binary operation with constants"""
        left_const = self.get_constant_value(instr.left)
        right_const = self.get_constant_value(instr.right)

        if left_const is not None and right_const is not None:
            result = self.compute_constant(instr.operator, left_const, right_const)
            return IRLoad(instr.dest, result)

        return None

    def compute_constant(self, operator: str, left: int, right: int) -> int:
        """Compute constant result"""
        if operator == '+':
            return left + right
        elif operator == '-':
            return left - right
        elif operator == '*':
            return left * right
        elif operator == '/':
            return left // right  # Integer division
        # ... additional operators
```

### Dead Code Elimination

```python
class DeadCodeEliminationPass:
    def run(self, ir_module: IRModule):
        """Eliminate dead code"""
        for function in ir_module.functions:
            # Build use-def chains
            use_def = self.build_use_def_chains(function)

            # Find live variables
            live_vars = self.find_live_variables(function, use_def)

            # Remove dead instructions
            for block in function.blocks:
                new_instructions = []
                for instr in block.instructions:
                    if self.is_live_instruction(instr, live_vars):
                        new_instructions.append(instr)
                block.instructions = new_instructions
```

## Hardware-Specific Optimizations

### Graphics Operation Optimization

```python
def optimize_graphics_operations(self, ir_module: IRModule):
    """Optimize graphics hardware operations"""
    for function in ir_module.functions:
        for block in function.blocks:
            instructions = block.instructions
            optimized = []

            i = 0
            while i < len(instructions):
                instr = instructions[i]

                # Look for VX/VY followed by SWRITE pattern
                if (isinstance(instr, IRStore) and
                    instr.dest == 'hw_video_x' and
                    i + 2 < len(instructions) and
                    isinstance(instructions[i + 1], IRStore) and
                    instructions[i + 1].dest == 'hw_video_y' and
                    isinstance(instructions[i + 2], IRHardwareOp) and
                    instructions[i + 2].operation == 'SWRITE'):

                    # Combine into optimized pixel write
                    vx_value = instr.value
                    vy_value = instructions[i + 1].value
                    color_value = instructions[i + 2].operands[0]

                    optimized.append(IRHardwareOp(
                        'SET_PIXEL',
                        [vx_value, vy_value, color_value]
                    ))

                    i += 3  # Skip the three instructions
                else:
                    optimized.append(instr)
                    i += 1

            block.instructions = optimized
```

### Byte Access Optimization

```python
def optimize_byte_access(self, ir_module: IRModule):
    """Optimize 8-bit operations using P register byte access"""
    for function in ir_module.functions:
        for block in function.blocks:
            new_instructions = []
            
            for instr in block.instructions:
                # Look for 8-bit operations that can use byte access
                if isinstance(instr, IRBinaryOp) and instr.type_hint == IRType.I8:
                    optimized = self.try_byte_access_optimization(instr)
                    if optimized:
                        new_instructions.extend(optimized)
                        continue
                        
                # Look for byte loads/stores
                elif isinstance(instr, IRLoad) and instr.type_hint == IRType.I8:
                    optimized = self.try_byte_load_optimization(instr)
                    if optimized:
                        new_instructions.append(optimized)
                        continue
                        
                new_instructions.append(instr)
                
            block.instructions = new_instructions

    def try_byte_access_optimization(self, instr: IRBinaryOp) -> List[IRInstruction]:
        """Try to optimize 8-bit binary operation using byte access"""
        left_reg = self.get_allocated_register(instr.left)
        right_reg = self.get_allocated_register(instr.right)
        
        # If both operands are in P registers, use byte access
        if (left_reg and left_reg.startswith('P') and 
            right_reg and right_reg.startswith('P')):
            
            # Generate byte access operations
            return [
                IRByteOp(
                    instr.operator,
                    f"{left_reg}:",  # High byte access
                    f"{right_reg}:", # High byte access
                    instr.dest
                )
            ]
        
        return None

    def try_byte_load_optimization(self, instr: IRLoad) -> IRInstruction:
        """Optimize byte loads using P register byte access"""
        if isinstance(instr.source, IRVariable):
            source_reg = self.get_allocated_register(instr.source)
            if source_reg and source_reg.startswith('P'):
                # Use byte access for loading from P register
                return IRLoad(instr.dest, f"{source_reg}:", IRType.I8)
        
        return None
```

**Byte Access Patterns for Optimal Utilization:**
- **Arithmetic Operations**: `ADD R0, P0:` (add to high byte of P0)
- **Logic Operations**: `AND R1, :P1` (AND with low byte of P1)  
- **Memory Access**: `MOV P2:, [address]` (store to high byte of P2)
- **Register Transfer**: `MOV :P3, R4` (move R4 to low byte of P3)

These optimizations reduce instruction count by 20-40% for byte-oriented code while maintaining register efficiency.

## Testing and Validation

### Unit Tests

```python
def test_code_generator_basic():
    """Test basic code generation"""
    source = """
def add(x, y):
    return x + y

result = add(5, 3)
"""

    # Parse and analyze
    ast = parse_source(source)
    analyzer = SemanticAnalyzer()
    analyzed = analyzer.analyze(ast)

    # Generate IR
    generator = IRGenerator(analyzed)
    ir_module = generator.generate_ir()

    # Check IR structure
    assert len(ir_module.functions) == 1
    assert ir_module.functions[0].name == "add"
    assert len(ir_module.functions[0].blocks) >= 1
```

### Integration Tests

```python
def test_code_generator_hardware():
    """Test hardware register code generation"""
    source = """
def draw_pixel(x, y, color):
    VX = x
    VY = y
    SWRITE(color)
"""

    # Generate assembly
    assembly = generate_assembly_from_source(source)

    # Check for hardware operations
    assert "MOV VX, P0" in assembly
    assert "MOV VY, P1" in assembly
    assert "SWRITE R0" in assembly
```

## Performance Considerations

### Optimization Strategies

1. **Instruction Scheduling**: Reorder instructions for better pipelining
2. **Register Coloring**: Graph coloring for optimal register allocation
3. **Memory Access Optimization**: Optimize for Nova-16's memory layout
4. **Inlining**: Inline small functions to reduce call overhead

### Benchmarking

```python
def benchmark_code_generation():
    """Benchmark code generation performance"""
    import time

    # Load test program
    with open("benchmark_program.ast", "r") as f:
        source = f.read()

    start_time = time.time()

    # Full pipeline
    ast = parse_source(source)
    analyzed = SemanticAnalyzer().analyze(ast)
    ir = IRGenerator(analyzed).generate_ir()

    # Apply optimizations
    optimizer = IROptimizer()
    optimized_ir = optimizer.optimize(ir)

    # Generate assembly
    allocator = RegisterAllocator()
    register_map = allocator.allocate(optimized_ir)

    generator = AssemblyGenerator(optimized_ir, register_map)
    assembly = generator.generate_assembly()

    end_time = time.time()

    print(f"Generated {len(assembly)} assembly instructions in {end_time - start_time:.3f} seconds")
    print(f"Code generation speed: {len(assembly) / (end_time - start_time):.0f} instructions/second")
```

## Production Process Details

### Important Implementation Notes

1. **Hardware Register Validation**: Always validate that hardware registers (VM, VL, VX, VY, SA, SF, SV, SW, TT, TM, TC, TS) are accessed correctly. Ensure volatile semantics are preserved.

2. **Stack Frame Management**: Remember that Nova-16 stack grows downward from 0xFFFF. FP-relative addressing must account for this. Local variables are at positive offsets from FP.

3. **Register Allocation Constraints**: 
   - R0-R9: 8-bit operations only
   - P0-P7: General 16-bit (P8=SP, P9=FP reserved)
   - Hardware registers: Never allocate for general use
   - Spill to stack when registers exhausted

4. **Type System Limitations**: Nova-16 is integer-only. FLOAT type support is optional and requires software floating-point implementation. Default to integer operations.

5. **Memory Layout Awareness**: Place frequently accessed data in zero page (0x0000-0x00FF) for faster access. Compiler should analyze access patterns.

6. **Error Recovery**: Code generation should not fail silently. Implement graceful degradation (e.g., spill to stack) when register allocation fails.

7. **Optimization Ordering**: Run constant folding before register allocation, DCE after. Hardware optimizations should be last to preserve register mappings.

### Integration Testing Checklist

- [ ] **Unit Tests**: Test each IR instruction generation
- [ ] **Register Allocation**: Verify correct register assignment and spilling
- [ ] **Hardware Integration**: Test all hardware register accesses
- [ ] **Function Calls**: Validate calling convention adherence
- [ ] **Stack Operations**: Ensure proper FP/SP management
- [ ] **Assembly Validity**: Generated code must assemble without errors
- [ ] **Performance Regression**: Code generation should not slow down compilation significantly

### Debugging Support

Implement source line mapping for debugging:
```python
class DebugInfo:
    def __init__(self):
        self.line_mapping = {}  # Assembly line -> Source line
    
    def add_mapping(self, asm_line, source_line):
        self.line_mapping[asm_line] = source_line
```

### Performance Metrics

Track these during development:
- **Code Size**: Bytes of generated assembly
- **Register Efficiency**: Percentage of operations using registers vs stack
- **Hardware Utilization**: Number of direct hardware accesses
- **Compilation Speed**: Instructions generated per second

## Implementation Checklist

- [ ] IR generation from AST
- [ ] Register allocation system
- [ ] Assembly instruction selection
- [ ] Function call handling
- [ ] Hardware register optimization
- [ ] Control flow generation
- [ ] Optimization passes (constant folding, DCE)
- [ ] Memory access optimization
- [ ] Error handling and recovery
- [ ] Comprehensive test suite
- [ ] Performance benchmarking
- [ ] Integration with assembler

## Code Generation Examples

### Simple Function
```
Astrid: def add(x, y): return x + y
IR:      %0 = add i16 %x, %y
         ret i16 %0
Assembly:MOV P0, [FP+4]    ; Load x
         ADD P0, [FP+6]    ; Add y
         RET
```

### Hardware Access
```
Astrid: VX = 100; VY = 120; SWRITE(255)
IR:      store volatile i16 100, hw_video_x
         store volatile i16 120, hw_video_y
         call void @SWRITE(i8 255)
Assembly:MOV VX, 100
         MOV VY, 120
         MOV R0, 255
         SWRITE R0
```

This code generator specification provides a comprehensive guide for implementing the Astrid compiler's backend, ensuring efficient Nova-16 assembly generation with proper hardware integration and optimization.</content>
<parameter name="filePath">c:\Code\Nova\astrid docs\astrid_code_generator_specification.md