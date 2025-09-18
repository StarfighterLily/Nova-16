# Astrid Compiler Design Document

## Executive Summary

This document outlines the design and implementation of the Astrid compiler for the Nova-16 16-bit CPU emulator. The Astrid language is a Python-inspired, dynamically-typed language optimized for embedded systems development on retro hardware. The compiler targets efficient Nova-16 assembly generation while providing high-level language features including functional programming constructs, hardware integration, and memory safety guarantees.

**Key Design Principles:**
- **Hardware-Aware**: Deep integration with Nova-16's register architecture and specialized hardware
- **Memory-Efficient**: Optimized for 64KB unified memory with lightweight memory management
- **Performance-Focused**: Intelligent register allocation and optimization for real-time applications
- **Safety-First**: Runtime bounds checking and type safety for embedded reliability

## Architecture Overview

### Nova-16 Target Architecture

The Nova-16 CPU features:
- **Register Set**: 10 × 8-bit registers (R0-R9), 10 × 16-bit registers (P0-P9)
- **Memory**: 64KB unified address space with big-endian byte ordering
- **Stack**: Hardware stack growing downward from 0xFFFF (SP = P8, FP = P9)
- **Special Registers**: Hardware registers for graphics (VM, VL, VX, VY), sound (SA, SF, SV, SW), and timer (TT, TM, TC, TS)
- **Instruction Set**: RISC-like with specialized graphics/sound operations

### Compiler Pipeline

```
Astrid Source (.ast)
       ↓
   ┌─────────────┐
   │   Lexer     │  → Token Stream
   └─────────────┘
       ↓
   ┌─────────────┐
   │   Parser    │  → Abstract Syntax Tree (AST)
   └─────────────┘
       ↓
   ┌─────────────┐
   │  Semantic   │  → Annotated AST + Symbol Table
   │  Analyzer   │
   └─────────────┘
       ↓
   ┌─────────────┐
   │     IR      │  → Intermediate Representation
   │  Builder    │
   └─────────────┘
       ↓
   ┌─────────────┐
   │ Code Gen    │  → Nova-16 Assembly (.asm)
   └─────────────┘
       ↓
   ┌─────────────┐
   │Assembler & │  → Binary Executable (.bin)
   │   Linker    │
   └─────────────┘
```

## Design Decisions and Rationale

### Register-Centric Hybrid Approach

**Decision**: Implement a hybrid register allocation strategy that balances register utilization with intelligent stack management, rather than pure stack-centric or pure register-centric approaches.

**Rationale**:
- **Pure Stack-Centric**: Simple but inefficient, creates excessive temporaries and memory traffic
- **Pure Register-Centric**: Optimal for performance but complex register allocation increases compilation time and may not handle dynamic language features well
- **Hybrid Approach**: Leverages Nova-16's rich register set while using stack for spilling and complex expressions

**Implementation**:
- **Hot Path Optimization**: Frequently accessed variables allocated to registers
- **Spill Strategy**: Least Recently Used (LRU) register spilling to stack
- **Register Classes**: R registers for 8-bit values, P registers for 16-bit/addresses
- **Hardware Reservation**: VM, VL, VX, VY, SA, SF, SV, SW, TT, TM, TC, TS reserved for hardware access

### Memory Management Strategy

**Decision**: Implement a lightweight, pool-based memory management system with reference counting for dynamic objects.

**Rationale**:
- **No General Heap**: Traditional malloc/free too complex for 64KB memory
- **Fixed Pools**: Predictable allocation, fast deallocation, bounds checking
- **Reference Counting**: Handles dynamic typing and functional programming patterns without complex GC

**Memory Layout**:
```
0x0000-0x00FF: Zero Page (fast access, frequently used globals)
0x0100-0x011F: Interrupt Vectors (8 vectors × 4 bytes)
0x0120-0xDFFF: General Memory Pool
0xE000-0xEFFF: String Pool (4KB)
0xF000-0xF0FF: Sprite Control Blocks (16 sprites × 16 bytes)
0xF100-0xFFFE: Object Pool (≈ 3.9KB)
0xFFFF: Stack Base (grows downward)
```

**Pool Management**:
- **String Pool**: Bump allocator with reference counting
- **Object Pool**: Free list allocator with reference counting
- **Stack**: Hardware-managed with overflow detection

### Type System Design

**Decision**: Dynamic typing with compile-time inference and runtime type tags.

**Rationale**:
- **Python-Inspired**: Matches Astrid's design goals
- **Memory Efficient**: Type information stored in object headers, not variables
- **Performance**: Type inference reduces runtime checks where possible

**Type Representation**:
```python
# Tagged Union for Values
class Value:
    TYPE_INT = 0x00    # 16-bit integer
    TYPE_FLOAT = 0x01  # 16-bit float (if supported)
    TYPE_BOOL = 0x02   # Boolean
    TYPE_STRING = 0x03 # String handle
    TYPE_OBJECT = 0x04 # Object handle
    TYPE_ARRAY = 0x05  # Array handle
    TYPE_NONE = 0x06   # None/Null

    def __init__(self, type_tag, data):
        self.type_tag = type_tag
        self.data = data  # 16-bit value (direct or handle)
```

### Function Calling Convention

**Decision**: Register-based calling convention with stack overflow for variadic arguments.

**Rationale**:
- **Register-First**: Minimizes stack traffic for common cases
- **Hardware-Aligned**: Leverages Nova-16's register architecture
- **Stack Fallback**: Handles arbitrary argument counts

**Calling Convention**:
- **Arguments**: First 4 args in R0-R3 (8-bit) or P0-P3 (16-bit) based on type
- **Return Value**: R0/R1 or P0 based on type
- **Stack Frame**: FP-relative addressing for locals
- **Caller Cleanup**: Efficient for functional programming patterns

## Component Architecture

### Lexer and Parser

**Indentation-Aware Parsing**:
- **Token Types**: Keywords, identifiers, literals, operators, indentation
- **Indentation Tracking**: Maintain indentation stack for block structure
- **Error Recovery**: Meaningful error messages for indentation errors

**Grammar Example**:
```
program     → statement*
statement   → assignment | function_def | if_stmt | for_stmt | expr_stmt
function_def → 'def' IDENTIFIER '(' params? ')' ':' block
block       → NEWLINE INDENT statement+ DEDENT
```

### Semantic Analyzer

**Symbol Table Management**:
- **Scopes**: Global, function, block-level scoping
- **Symbol Types**: Variables, functions, types, hardware registers
- **Type Inference**: Bottom-up type propagation
- **Hardware Validation**: Ensure proper use of reserved registers

**Type Inference Algorithm**:
```python
def infer_type(node, symbol_table):
    if isinstance(node, Literal):
        return node.type
    elif isinstance(node, BinaryOp):
        left_type = infer_type(node.left, symbol_table)
        right_type = infer_type(node.right, symbol_table)
        return type_combine(left_type, right_type, node.op)
    elif isinstance(node, Variable):
        return symbol_table.lookup(node.name).type
    # ... additional cases
```

### Intermediate Representation (IR)

**SSA-Based IR**:
- **Instructions**: Register-based operations with phi nodes
- **Blocks**: Basic blocks with control flow
- **Metadata**: Type information, register hints, optimization flags

**IR Example**:
```
function main():
    %x = load R0
    %y = load R1
    %result = add %x, %y
    store %result, R2
    ret
```

### Code Generator

**Register Allocation**:
- **Graph Coloring**: Interference graph with register constraints
- **Live Range Analysis**: Variable lifetime tracking
- **Spilling**: LRU-based register spilling to stack slots

**Instruction Selection**:
- **Pattern Matching**: Template-based instruction selection
- **Hardware Integration**: Direct mapping to Nova-16 opcodes
- **Optimization**: Peephole optimization and constant folding

## Implementation Details

### Register Allocation Algorithm

**Priority-Based Allocation**:
```python
class RegisterAllocator:
    def __init__(self):
        # Available registers (R0-R9 for 8-bit, P0-P9 for 16-bit)
        self.available_r = set(range(10))  # R0-R9
        self.available_p = set(range(10))  # P0-P9
        
        # Reserved P registers (cannot be allocated for general use)
        self.reserved_p = {8, 9}  # P8=SP (Stack Pointer), P9=FP (Frame Pointer)
        
        # Hardware registers (never allocated, accessed directly)
        self.hardware_reserved = {'VM', 'VL', 'VX', 'VY', 'SA', 'SF', 'SV', 'SW', 'TT', 'TM', 'TC', 'TS'}

    def allocate(self, var_type, priority=HIGH):
        if var_type == TYPE_8BIT and self.available_r:
            return f"R{self.available_r.pop()}"
        elif var_type == TYPE_16BIT and self.available_p:
            reg_num = self.available_p.pop()
            if reg_num not in self.reserved_p:
                return f"P{reg_num}"
        return self.spill_to_stack()
```

### Memory Management Implementation

**Reference Counting**:
```python
class MemoryManager:
    def alloc_string(self, content):
        handle = self.string_pool.allocate(len(content) + 1)
        self.string_pool.write(handle, content)
        self.ref_counts[handle] = 1
        return handle

    def retain(self, handle):
        if handle in self.ref_counts:
            self.ref_counts[handle] += 1

    def release(self, handle):
        if handle in self.ref_counts:
            self.ref_counts[handle] -= 1
            if self.ref_counts[handle] == 0:
                self.deallocate(handle)
```

### Hardware Integration

**Reserved Variable Mapping**:
```python
HARDWARE_REGISTERS = {
    'VM': 'video_mode',
    'VL': 'video_layer',
    'VX': 'video_x',
    'VY': 'video_y',
    'SA': 'sound_address',
    'SF': 'sound_frequency',
    'SV': 'sound_volume',
    'SW': 'sound_waveform',
    'TT': 'timer_value',
    'TM': 'timer_match',
    'TC': 'timer_control',
    'TS': 'timer_speed'
}
```

**Hardware-Aware Code Generation**:
```python
def generate_hardware_access(var_name, value):
    if var_name in HARDWARE_REGISTERS:
        reg = HARDWARE_REGISTERS[var_name]
        return f"MOV {reg}, {value}"
    else:
        return generate_normal_assignment(var_name, value)
```

## Optimization Strategies

### Compile-Time Optimizations

**Constant Folding**:
- **Arithmetic**: Fold constant expressions at compile time
- **String Concatenation**: Combine literal strings
- **Dead Code Elimination**: Remove unreachable code

**Function Inlining**:
- **Small Functions**: Inline functions with < 10 instructions
- **Hardware Functions**: Always inline hardware access functions
- **Recursive Functions**: Tail recursion optimization

**Byte Access Optimization**:
- **P Register Utilization**: Use `P0:` and `:P0` syntax for 8-bit operations on 16-bit registers
- **Automatic Selection**: Compiler detects byte operations and selects optimal register access patterns
- **Performance Gains**: Reduces instruction count by 20-40% for byte-oriented algorithms
- **Memory Efficiency**: Minimizes register pressure by leveraging P register byte access

### Runtime Optimizations

**Register Allocation Hints**:
- **Loop Variables**: Prefer registers for loop counters
- **Hot Paths**: Analyze execution frequency for optimization
- **Variable Lifetime**: Optimize register reuse based on scope

**Memory Access Optimization**:
- **Zero Page**: Place frequently accessed variables in 0x0000-0x00FF
- **Cache Awareness**: Align data structures for efficient access
- **Batch Operations**: Group hardware register updates

## Testing and Validation

### Test Categories

**Unit Tests**:
- **Lexer**: Token recognition and error handling
- **Parser**: AST construction and error recovery
- **Semantic Analyzer**: Type inference and symbol resolution
- **Code Generator**: Assembly output validation

**Integration Tests**:
- **End-to-End**: Source to binary compilation
- **Hardware Integration**: Graphics, sound, and I/O functionality
- **Performance Benchmarks**: Validate efficiency targets

**Validation Tests**:
- **Memory Safety**: Bounds checking and leak detection
- **Type Safety**: Runtime type validation
- **Hardware Compatibility**: Nova-16 emulator validation

### Performance Benchmarks

**Key Metrics**:
- **Compilation Speed**: Lines per second
- **Code Size**: Bytes of generated assembly
- **Runtime Performance**: Instructions per second
- **Memory Usage**: Peak memory consumption

**Benchmark Suite**:
```python
def benchmark_gfx_demo():
    """Graphics rendering performance test"""
    start_time = time.time()
    compile_and_run("gfx_demo.ast")
    end_time = time.time()
    return end_time - start_time
```

## Future Considerations

### Extensibility

**Language Features**:
- **Macros**: Compile-time code generation
- **Generics**: Type-parametric functions
- **Modules**: Separate compilation and linking

**Optimization Enhancements**:
- **Profile-Guided Optimization**: Runtime profiling for optimization
- **Advanced Register Allocation**: Graph coloring with coalescing
- **Interprocedural Analysis**: Cross-function optimization

### Platform Evolution

**Hardware Extensions**:
- **Floating Point**: If added to Nova-16
- **Additional Memory**: Larger address spaces
- **DMA Operations**: Hardware-accelerated memory transfers

**Tooling Improvements**:
- **IDE Integration**: Syntax highlighting and error diagnostics
- **Debug Support**: Source-level debugging
- **Profiling Tools**: Performance analysis and optimization guidance

## Production Process Details

### Important Implementation Guidelines

1. **Modular Architecture**: Maintain clean separation between lexer, parser, semantic analyzer, IR, and code generator. Use well-defined interfaces.

2. **Hardware Awareness**: Every component must understand Nova-16's 64KB memory, register set, and instruction constraints.

3. **Performance Focus**: Optimize for compilation speed and code quality. Track metrics throughout development.

4. **Error Handling**: Implement comprehensive error reporting with actionable messages. Support error recovery where possible.

5. **Testing Strategy**: Comprehensive testing at unit, integration, and system levels. Include hardware validation.

6. **Documentation**: Keep specifications and implementation in sync. Update docs as code evolves.

7. **Extensibility**: Design for future language features and hardware extensions.

### Implementation Checklist

- [ ] Complete compiler pipeline implementation
- [ ] Hardware register integration
- [ ] Memory management system
- [ ] Type system with dynamic typing
- [ ] Function calling convention
- [ ] Optimization passes
- [ ] Comprehensive test suite
- [ ] Performance benchmarking
- [ ] Documentation and examples

### Quality Assurance

**Testing Categories**:
- **Unit Tests**: Individual component testing
- **Integration Tests**: Component interaction validation
- **System Tests**: End-to-end compilation testing
- **Hardware Tests**: Validation on Nova-16 emulator
- **Performance Tests**: Benchmarking against targets
- **Regression Tests**: Ensure no functionality breaks

**Code Quality**:
- **Coverage**: >90% test coverage
- **Linting**: Automated code quality checks
- **Reviews**: Code review for all changes
- **Documentation**: Complete API and user documentation

### Risk Management

**Technical Risks**:
- **Register Allocation Complexity**: Mitigate with simple initial implementation, enhance later
- **Hardware Integration**: Extensive testing with emulator
- **Performance**: Continuous monitoring and optimization

**Schedule Risks**:
- **Scope Creep**: Strict feature prioritization
- **Resource Constraints**: Regular progress assessment
- **Technical Challenges**: Prototyping for risky features

### Success Metrics

- **Functionality**: Compiles Astrid to working Nova-16 binaries
- **Performance**: Efficient code generation, fast compilation
- **Reliability**: Robust error handling, comprehensive testing
- **Usability**: Clear error messages, good documentation
- **Maintainability**: Clean, modular codebase

## Conclusion

The Astrid compiler design balances the constraints of the Nova-16 architecture with the expressiveness goals of a modern, Python-inspired language. By adopting a hybrid register-centric approach, lightweight memory management, and deep hardware integration, the compiler achieves efficient code generation while maintaining developer productivity and program safety.

The modular architecture ensures maintainability and extensibility, allowing for future enhancements while preserving the core design principles that make Astrid suitable for embedded development on retro hardware platforms.

---

**Document Version**: 1.0
**Date**: September 17, 2025
**Authors**: Astrid Compiler Design Team
**Status**: Implementation Ready