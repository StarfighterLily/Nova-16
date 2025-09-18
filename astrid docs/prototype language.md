# Astrid: Prototype Language for Nova-16

Astrid is a Python-inspired, compiled high-level language designed specifically for the Nova-16 16-bit CPU emulator. It aims to provide a clean, expressive syntax while tightly integrating with Nova-16's hardware features, reducing boilerplate and cognitive overhead for developers targeting this architecture.

## Core Principles

- **Python-Inspired Syntax**: Familiar indentation-based structure, dynamic typing, and concise expressions to lower the barrier for Python developers.
- **Hardware Integration**: Reserved variables directly map to Nova-16 hardware registers (VM, VL, VX, VY, SA, SF, SV, SW, TT, TM, TC, TS), allowing seamless access to graphics, sound, timers, and more without explicit memory operations.
- **Reduced Line Noise**: Minimize syntactic clutter; focus on intent and readability. No semicolons, explicit types, or verbose declarations where possible.
- **Functional First**: Emphasize immutability, higher-order functions, and composability, with object-oriented features as a secondary paradigm.
- **Stylish and Quirky**: Incorporate unique features that make programming fun and expressive, drawing from functional languages, metaprogramming, and domain-specific optimizations for embedded systems.
- **Compiled Target**: Translates to Nova-16 assembly (.asm) via the Astrid compiler, then assembles to binary (.bin) for execution.

## Language Design Overview

### Syntax Basics
- **Indentation-Based**: Like Python, blocks are defined by indentation.
- **Dynamic Typing**: Variables are inferred; no explicit type declarations.
- **Expressions Over Statements**: Everything is an expression where possible.

### Data Types and Structures
- **Primitives**: Integers (8-bit and 16-bit, auto-handled), floats (if supported), booleans.
- **Collections**: Lists (dynamic arrays), tuples (immutable), dictionaries (key-value maps).
- **Strings**: Unicode-aware, with hardware-accelerated operations where possible.
- **Hardware Types**: Direct access to memory regions (e.g., for graphics buffers).

### Functions and Lambdas
- **Function Definition**: `def func_name(params): body`
- **Lambdas**: `lambda x: x + 1`
- **Higher-Order**: Functions as first-class citizens, closures supported.
- **Currying**: Automatic or optional for multi-argument functions.

### Object-Oriented Features
- **Classes**: `class ClassName: methods`
- **Inheritance**: Single inheritance with mixins for composition.
- **Methods**: Instance and class methods, with `self` implicit.
- **Polymorphism**: Duck typing, with optional interfaces.

### Functional Programming
- **Immutability**: Encourage immutable data structures.
- **Pattern Matching**: For tuples, lists, and custom types.
- **Recursion**: Optimized for tail recursion.
- **Monads/Effects**: Lightweight effect system for side effects (e.g., hardware I/O).

### Ownership and Borrowing
Inspired by Rust's ownership model, Astrid incorporates compile-time and runtime checks to ensure memory safety and prevent common errors like use-after-free, double-free, and data races. Since Astrid is dynamically typed, these checks are enforced through static analysis and optional runtime verification.

- **Ownership Rules**: Every value has a single owner responsible for its lifecycle. When the owner goes out of scope, the value is automatically deallocated. Ownership can be transferred via assignment or function calls.
- **Borrowing**: References can temporarily borrow ownership with strict rules:
  - Multiple immutable borrows are allowed simultaneously.
  - Only one mutable borrow is permitted at a time.
  - No mutable borrows while immutable borrows exist.
- **Lifetimes**: The compiler tracks reference lifetimes to ensure borrowed values outlive their borrowers. Lifetimes are inferred automatically but can be annotated explicitly for complex cases.
- **Move Semantics**: Values can be "moved" to transfer ownership without copying, optimizing performance for large data structures.
- **Smart Pointers**: Built-in smart pointers (e.g., `Rc` for reference counting, `Box` for heap allocation) provide flexible ownership patterns while maintaining safety.
- **Runtime Safety**: For cases where compile-time analysis is insufficient, optional runtime checks validate ownership at execution time, with configurable error handling (panic or exception).

This system provides Rust-like safety guarantees in a dynamic language, preventing memory corruption while maintaining high performance on Nova-16's constrained resources.

### Unique/Obscure Features
Drawing from languages like Haskell, Lisp, and ML for metaprogramming and expressiveness:
- **Macros**: Compile-time code generation for domain-specific optimizations (e.g., inline assembly snippets).
- **Operator Overloading**: Custom operators including ++/-- increment/decrement for hardware registers or math.
- **Type Classes**: Ad-hoc polymorphism for generic functions (e.g., equality, serialization).
- **Metaprogramming**: Reflection and code-as-data for runtime code generation, useful for dynamic graphics or sound.
- **Lazy Evaluation**: For infinite sequences or performance-critical loops.
- **Embedded DSLs**: Syntax for graphics commands, sound synthesis, etc., that compile to efficient register operations.

### Hardware Integration
Astrid is designed as a seamless extension of Nova-16's architecture, with deep awareness of its 16-bit design, unified memory model, and specialized registers. The language provides direct, efficient access to hardware features while optimizing compilation for Nova-16's unique characteristics.

#### Register Integration
- **Direct Hardware Register Access**: Reserved variables map directly to Nova-16 registers:
  - Graphics: `VM` (video mode), `VL` (layer), `VX`/`VY` (coordinates)
  - Sound: `SA` (address), `SF` (frequency), `SV` (volume), `SW` (waveform)
  - Timer: `TT` (timer), `TM` (match), `TC` (control), `TS` (speed)
  - Stack: `SP` (P8), `FP` (P9)
- **Byte-Level Operations**: Leverage Nova-16's high/low byte access:
  - `P0:` accesses high byte of P0 register
  - `:P0` accesses low byte of P0 register
  - Automatic optimization for 8-bit vs 16-bit operations
- **Register Allocation Strategy**: Compiler prioritizes registers based on Nova-16's architecture:
  - R0-R9 for byte operations and temporary values
  - P0-P9 for addresses and 16-bit calculations
  - Hardware registers reserved for their specific purposes

#### Memory and Addressing
- **Zero-Page Awareness**: Compiler automatically places frequently accessed variables in 0x0000-0x00FF for single-byte addressing
- **Unified Memory Model**: Direct manipulation of Nova-16's 64KB address space with hardware-accelerated operations
- **Custom Addressing Modes**: 
  - Indexed addressing for arrays: `arr[i]` compiles to efficient Nova-16 indexed loads
  - Indirect addressing for pointers: `*ptr` maps to Nova-16's indirect modes
  - Stack-relative addressing for local variables
- **Memory Layout Optimization**: Data structures arranged to minimize page crossings and maximize cache efficiency

#### Stack Management
- **Hardware Stack Integration**: Stack grows downward from 0xFFFF, with SP (P8) and FP (P9) managed automatically
- **Efficient Function Calls**: Tail recursion elimination and register-based parameter passing
- **Interrupt-Safe Stacks**: Compiler generates interrupt-aware code that preserves stack integrity

#### Interrupt and Event Handling
- **Vector Integration**: Direct access to interrupt vectors at 0x0100-0x011F
- **Event-Driven Programming**: High-level event handlers that compile to efficient interrupt service routines
- **Priority Management**: Automatic handling of interrupt priorities (Timer > Keyboard > User)

#### Performance Optimizations
- **Hardware-Accelerated Operations**: Built-in functions map directly to Nova-16 opcodes:
  - `draw_pixel(x, y, color)` → SWRITE instruction
  - `play_sound(freq, vol)` → SA, SF, SV, SW registers + SPLAY
  - `key_read()` → KEYIN instruction
- **Batch Operations**: Group hardware operations to minimize register switching
- **Inline Assembly**: Seamless mixing of Astrid code with Nova-16 assembly for ultimate control
- **Memory Access Patterns**: Optimize for Nova-16's unified memory with prefetching hints

#### Graphics and Sound DSLs
- **Embedded Graphics DSL**: Syntax like `pixel(x, y) = color` compiles to optimal register sequences
- **Sound Synthesis DSL**: Functional composition of waveforms with hardware-accelerated playback
- **Real-Time Constraints**: Compiler ensures timing-critical code meets Nova-16's real-time requirements

This deep integration makes Astrid feel like a natural extension of Nova-16, providing high-level expressiveness while compiling to highly optimized, hardware-aware assembly code.

### Compilation and Execution
- **Pipeline**: Astrid source (.ast) → Assembly (.asm) via `astrid_compiler.py` → Binary (.bin) via `nova_assembler.py`.
- **Optimizations**: Tail recursion, constant folding, and intelligent register allocation.
- **Debugging**: Source-level debugging with mapping back to assembly.

#### Register Allocation

Astrid employs a prioritized intelligent register allocation system to optimize performance on the Nova-16 architecture:

- **Prioritized Allocation**: Speed-critical operations (graphics rendering, tight loops, real-time audio processing) are allocated the fastest available resources first. This includes preferring R registers (8-bit) for byte operations and P registers (16-bit) for address calculations, with hardware registers (VM, VL, VX, VY, etc.) reserved for their specific purposes. Non-critical operations receive remaining resources, ensuring optimal performance where it matters most.

- **Variable Lifetime Tracking**: The compiler performs static analysis to track the lifetime of each variable throughout its scope. Registers, stack frames, or memory locations are marked as occupied during the variable's active period. Upon reaching the end of the variable's lifetime (when it goes out of scope or is no longer referenced), the allocated resource is immediately freed for reuse. This minimizes resource contention, reduces memory pressure, and enables more efficient code generation by allowing overlapping allocations.

This allocation strategy ensures that performance-critical code paths receive optimal resource assignment while maintaining efficient memory usage for less critical operations, directly contributing to the high performance expected from Nova-16 applications.

### Example Code Snippets

#### Hello World with Graphics
```
def main():
    VM = 0        # Coordinate mode
    VL = 1        # Layer 1
    for x in range(256):
        for y in range(256):
            draw_pixel(x, y, (x + y) % 256)
```

#### Graphics API
```
def draw_pixel(x: int, y: int, color: int):
    """Draw a pixel at coordinates (x,y) with the specified color (0-255)"""
    VX = x
    VY = y
    SWRITE(color)
```

#### Functional Sound Synthesis
```
def sine_wave(freq):
    return {"freq": freq, "wave_func": lambda t: sin(2 * pi * freq * t)}

def play_sound(wave_data, duration):
    SA = 0x2000
    SF = wave_data["freq"]
    SV = 128
    SW = 1  # Sine
    SPLAY()
    wait(duration)

play_sound(sine_wave(440), 1.0)  # Play A4 for 1 second
```

#### Class with Polymorphism
```
class Sprite:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        update_sprite(self)

class Player(Sprite):
    def move(self, dx, dy):
        super().move(dx, dy)
        check_collision(self)
```

## Production Process Details

### Important Implementation Notes

1. **Dynamic Typing**: Core feature - all variables are dynamically typed. Type inference at compile time, runtime type checks.

2. **Indentation-Based Syntax**: Strict indentation rules. Use 4 spaces consistently. No tabs allowed.

3. **Hardware Integration**: Reserved variables (VM, VL, VX, VY, etc.) map directly to Nova-16 registers. Case-sensitive.

4. **Memory Constraints**: Design for 64KB total memory. Encourage efficient data structures.

5. **Functional First**: Prefer immutable data and functional patterns. Mutable state should be explicit.

6. **Error Handling**: Runtime errors with descriptive messages. Compile-time checks where possible.

7. **Performance**: Optimize for Nova-16's 16-bit architecture. Efficient register usage and memory access.

### Implementation Status

**Completed Features**:
- [ ] Basic syntax (indentation, expressions, statements)
- [ ] Dynamic typing with inference
- [ ] Function definitions and calls
- [ ] Hardware register access
- [ ] Basic control flow (if, for, while)

**Planned Features**:
- [ ] Classes and inheritance
- [ ] Lambda expressions
- [ ] List comprehensions
- [ ] Pattern matching
- [ ] Advanced functional constructs

### Testing Strategy

- **Unit Tests**: Test language features individually
- **Integration Tests**: Compile and run complete programs
- **Hardware Tests**: Validate Nova-16 integration
- **Performance Tests**: Benchmark compilation and execution
- **Compatibility Tests**: Ensure backward compatibility

### Language Evolution

**Version 1.0 Goals**:
- Complete basic language features
- Stable hardware integration
- Comprehensive standard library
- Good error messages
- Performance optimization

**Future Versions**:
- Advanced functional features
- Metaprogramming capabilities
- Enhanced type system
- Additional hardware support

### Common Pitfalls

1. **Indentation Errors**: Most common syntax errors. Use consistent spacing.
2. **Hardware Register Confusion**: Remember register names are case-sensitive and reserved.
3. **Memory Limits**: Be aware of 64KB constraint. Design for efficiency.
4. **Dynamic Typing Gotchas**: Type errors caught at runtime, not compile time.
5. **Performance Expectations**: Nova-16 is not high-performance hardware. Optimize carefully.

This design balances high-level expressiveness with low-level control, making Astrid ideal for Nova-16 development. Open for review and iteration!

