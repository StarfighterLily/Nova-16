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

### Unique/Obscure Features
Drawing from languages like Haskell, Lisp, and ML for metaprogramming and expressiveness:
- **Macros**: Compile-time code generation for domain-specific optimizations (e.g., inline assembly snippets).
- **Operator Overloading**: Custom operators for hardware registers or math.
- **Type Classes**: Ad-hoc polymorphism for generic functions (e.g., equality, serialization).
- **Metaprogramming**: Reflection and code-as-data for runtime code generation, useful for dynamic graphics or sound.
- **Lazy Evaluation**: For infinite sequences or performance-critical loops.
- **Embedded DSLs**: Syntax for graphics commands, sound synthesis, etc., that compile to efficient register operations.

### Hardware Integration
- **Register Variables**: `VM = 0` directly sets the video mode register.
- **Memory Access**: `mem[addr] = value` for direct unified memory manipulation.
- **Interrupts and Events**: Event-driven programming for keyboard, timers.
- **Graphics/Sound Primitives**: Built-in functions like `draw_pixel(x, y, color)` that map to SWRITE, or `play_sound(freq, vol)`.

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
    VM = 0  # Coordinate mode
    VL = 1  # Layer 1
    for x in range(320):
        for y in range(240):
            draw_pixel(x, y, (x + y) % 256)
```

#### Functional Sound Synthesis
```
def sine_wave(freq):
    lambda t: sin(2 * pi * freq * t)

play_sound = lambda wave, duration: 
    SA = 0x2000
    SF = wave.freq
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

This design balances high-level expressiveness with low-level control, making Astrid ideal for Nova-16 development. Open for review and iteration!

