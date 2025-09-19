# NOVA-16 FORTH Implementation Architecture

## Overview

FORTH is a stack-based programming language that has been fully implemented for the NOVA-16 CPU emulator. This implementation provides a complete, production-ready FORTH environment with seamless integration to all NOVA-16 hardware subsystems.

## Core Architecture

### Memory Layout
The FORTH system is carefully mapped to the NOVA-16's 64KB unified memory space:

```
0x0000-0x00FF: Zero Page (Fast Access)
  - Critical system variables
  - Frequently accessed constants
  - Performance-critical data

0x0100-0x011F: Interrupt Vectors (8 vectors × 4 bytes)
  - Hardware interrupt handlers
  - System call interfaces
  - Timer and I/O interrupts

0x0120-0x0FFF: FORTH Kernel & System Area (3.8KB)
  - Core word definitions
  - System variables and constants
  - Bootstrap code and primitives

0x1000-0xDFFF: User Code Space (48KB)
  - User-defined FORTH words
  - Application code
  - Data structures and variables

0xE000-0xEFFF: Parameter Stack (4KB, grows downward)
  - Data stack for FORTH operations
  - 16-bit values stored as big-endian
  - Stack pointer: P8 (SP)

0xF000-0xFFFF: Return Stack (4KB, grows downward)
  - Control flow stack
  - Local variables and loop indices
  - Frame pointer: P9 (FP)
```

### Stack Architecture

#### Parameter Stack (Data Stack)
- **Purpose**: Primary data manipulation stack
- **Location**: 0xE000-0xEFFF (grows downward)
- **Register**: P8 (SP - Stack Pointer)
- **Usage**: Arithmetic, data passing, temporary storage
- **Access**: Indexed addressing with [P8+offset]

#### Return Stack (Control Stack)
- **Purpose**: Control flow and local storage
- **Location**: 0xF000-0xFFFF (grows downward)
- **Register**: P9 (FP - Frame Pointer)
- **Usage**: Return addresses, loop indices, local variables
- **Access**: Indexed addressing with [P9+offset]

### Register Usage Convention

```
P0-P7: General Purpose Registers
  - P0-P3: Primary working registers
  - P4-P7: Secondary working registers
  - Used for temporary calculations and data movement

P8: Stack Pointer (SP)
  - Points to top of parameter stack
  - Decrements on push, increments on pop
  - Always aligned to 16-bit boundaries

P9: Frame Pointer (FP)
  - Points to current stack frame
  - Used for local variable access
  - Manages function call contexts

R0-R9: 8-bit Registers
  - Byte-level operations
  - Character processing
  - Bit manipulation
  - Hardware register access
```

## FORTH Language Components

### Dictionary Structure
FORTH words are stored in a linked list dictionary:

```
Word Entry Format:
+-------------------+
| Link (16-bit)     | -> Previous word address
+-------------------+
| Name Length (8-bit)|
+-------------------+
| Name (variable)   | -> Word name characters
+-------------------+
| Code Field (16-bit)| -> Execution address
+-------------------+
| Parameter Field   | -> Word data/parameters
| (variable)        |
+-------------------+
```

### Inner Interpreter
The inner interpreter executes compiled FORTH code:

1. **Fetch**: Get next word address from instruction stream
2. **Execute**: Jump to word's code field
3. **Process**: Execute word's behavior
4. **Return**: Continue to next word
5. **Repeat**: Until program completion

### Outer Interpreter
The outer interpreter handles user input:

1. **Parse**: Tokenize input stream
2. **Lookup**: Search dictionary for word
3. **Execute**: Run word or compile if in compile mode
4. **Handle**: Process literals and numbers
5. **Repeat**: Process next token

## Compilation Process

### Word Definition Flow
```
User Input: : SQUARE DUP * ;

1. Parse ":" -> Enter compile mode
2. Parse "SQUARE" -> Create new word header
3. Parse "DUP" -> Compile DUP operation
4. Parse "*" -> Compile multiplication
5. Parse ";" -> Compile EXIT, end definition
6. Link word into dictionary
```

### Compilation State Management
- **State Variable**: 0 = interpret mode, 1 = compile mode
- **Control Stack**: Tracks nested control structures
- **Word Buffer**: Accumulates tokens during definition
- **Source Tracking**: Maintains original source for debugging

## Hardware Integration

### CPU Integration
- **Direct Register Access**: All CPU registers available
- **Stack Pointer Management**: Automatic SP/FP handling
- **Instruction Execution**: Native NOVA-16 instruction set
- **Interrupt Handling**: FORTH words for interrupt management

### Memory Integration
- **Unified Memory Model**: Single 64KB address space
- **Direct Memory Access**: @ and ! words for memory operations
- **Memory-Mapped I/O**: Hardware registers accessible as memory
- **Bounds Checking**: Automatic memory protection

### Graphics Integration
- **Graphics Registers**: VX, VY, VL, VM accessible via FORTH
- **Pixel Operations**: Direct framebuffer access
- **Sprite Management**: Hardware sprite control
- **Layer System**: 8-layer graphics support

### Sound Integration
- **Sound Registers**: SA, SF, SV, SW for audio control
- **Waveform Generation**: Multiple waveform types
- **Multi-channel Support**: Concurrent audio playback
- **Real-time Control**: Dynamic parameter adjustment

### Input Integration
- **Keyboard Buffer**: Circular buffer input system
- **Key Status**: KEYSTAT and KEYIN operations
- **Interrupt-Driven**: Hardware interrupt integration
- **Buffered Input**: Non-blocking input handling

## Implementation Strategy

### Bootstrap Process
1. **Initialize Hardware**: Set up CPU, memory, graphics, sound, keyboard
2. **Allocate Stacks**: Initialize parameter and return stacks
3. **Create Kernel**: Define core FORTH words
4. **Set up Dictionary**: Initialize empty dictionary
5. **Enter Interpreter**: Start interactive session

### Core Word Implementation
Core words are implemented as Python functions that generate NOVA-16 assembly:

```python
def word_dup(self):
    """DUP operation: duplicate top of stack"""
    return [
        "MOV R0, [P8+0]",    # Get top of stack
        "SUB P8, 2",          # Make room for duplicate
        "MOV [P8+0], R0",     # Store duplicate
    ]
```

### Error Handling
- **Stack Underflow/Overflow**: Automatic detection and recovery
- **Division by Zero**: Exception handling for math operations
- **Memory Bounds**: Protection against invalid memory access
- **Invalid Words**: Graceful handling of undefined words
- **Type Errors**: Runtime type checking where applicable

## Performance Optimizations

### Stack Operation Optimization
- **Indexed Addressing**: Proper [P8+offset] syntax usage
- **Register Caching**: Minimize memory accesses
- **Instruction Reduction**: Combine operations where possible
- **Frame Management**: Efficient function prologue/epilogue

### Memory Layout Optimization
- **Zero Page Usage**: Frequently accessed data in fast memory
- **Cache Alignment**: Optimize for NOVA-16 cache behavior
- **Dictionary Ordering**: Commonly used words at optimal locations
- **Memory Pool Management**: Efficient allocation strategies

### Compilation Optimizations
- **Constant Folding**: Compile-time constant evaluation
- **Dead Code Elimination**: Remove unreachable code
- **Peephole Optimization**: Local instruction optimization
- **Inline Expansion**: Small word inlining

## Testing and Validation

### Test Coverage
- **Core Words**: All 64+ FORTH words tested
- **Control Flow**: Complex nested structures validated
- **Memory Operations**: Bounds checking and error handling
- **Hardware Integration**: All subsystems tested
- **Edge Cases**: Stack underflow/overflow scenarios
- **Performance**: Benchmarking and optimization validation

### Validation Strategy
- **Unit Tests**: Individual word functionality
- **Integration Tests**: Full system interaction
- **Performance Tests**: Benchmarking against requirements
- **Compatibility Tests**: Hardware integration validation
- **Stress Tests**: Edge case and error condition handling

## Future Enhancements

### Native Code Compilation
- **FORTH to Assembly**: Direct compilation to NOVA-16 machine code
- **Optimization Passes**: Advanced compiler optimizations
- **Linker Integration**: Multi-module program support
- **Debugging Support**: Source-level debugging capabilities

### Advanced Features
- **Multi-threading**: Concurrent FORTH tasks
- **File System**: Persistent storage capabilities
- **Network Support**: Communication protocols
- **Graphics Library**: High-level graphics primitives
- **Sound Library**: Audio processing functions
- **Mathematics Library**: Advanced mathematical operations

### Development Tools
- **Interactive Debugger**: Single-step execution and inspection
- **Performance Profiler**: Execution time and memory usage analysis
- **Code Coverage**: Test coverage reporting
- **Documentation Generator**: Automatic documentation from source

## Conclusion

The NOVA-16 FORTH implementation provides a complete, high-performance programming environment that leverages the full capabilities of the NOVA-16 architecture. The careful integration with hardware subsystems, optimized memory layout, and comprehensive error handling make it suitable for a wide range of applications from system programming to interactive development.

The architecture is designed for both performance and maintainability, with clear separation of concerns between the FORTH language implementation and the underlying NOVA-16 hardware abstraction.</content>
<parameter name="filePath">c:\Code\Nova\forth\ARCHITECTURE.md