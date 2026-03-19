# Nova-16

A custom 16-bit CPU emulator with integrated graphics, sound, and I/O capabilities, written in Python.

## Overview

Nova-16 is a complete 16-bit computer system emulator featuring a custom instruction set architecture (ISA) with Princeton (von Neumann) architecture. The system includes a comprehensive CPU, memory management, graphics subsystem, keyboard input, sound generation, and development tools including an assembler, disassembler, and debugger.

## Core Features

### CPU Architecture
- **16-bit big-endian architecture** with variable-length instructions (1-4 bytes)
- **10 x 8-bit general-purpose registers** (R0-R9)
- **10 x 16-bit general-purpose registers** (P0-P9)
- **64KB unified address space** with memory-mapped I/O
- **12-bit status flags register** supporting comprehensive flag operations
- **Hardware stack** with dedicated Stack Pointer (SP/P8) and Frame Pointer (FP/P9)
- **Interrupt system** with 8 vectored interrupts and priority handling
- **Custom prefixed operand encoding** supporting multiple addressing modes

### Graphics System (GFX)
- Multiple rendering layers (0-8) with compositing
- Text rendering with custom font support
- Sprite system with 8x8 and 16x16 sprite support
- Video RAM (VRAM) with screen memory
- Screen scrolling and fill operations
- Coordinate and linear addressing modes
- Graphics profiler for performance analysis

### Sound System
- Multi-channel audio synthesis
- Multiple waveforms: sine, square, triangle, sawtooth, and noise
- Sound effects: beep, rising tone, falling tone, coin, explosion, laser, and jump sounds
- Volume and frequency control
- Real-time audio playback using PyAudio

### Input/Output
- Keyboard input with interrupt support
- 16-key circular buffer for keyboard events
- Memory-mapped keyboard control registers
- Timer/counter system with programmable interrupts

### Development Tools
- **Assembler** (`nova_assembler.py`): Converts assembly code to machine code
- **Disassembler** (`nova_disassembler.py`): Converts machine code back to assembly
- **Debugger** (`nova_debugger.py`): Step-through debugging with register inspection
- **Profilers**: CPU profiler, GPU profiler, and memory profiler for performance analysis
- **GUI** (`nova_gui.py`): Visual interface for running programs
- **Graphics Monitor** (`nova_graphics_monitor.py`): Real-time graphics debugging

## NoBASIC Programming Language

NoBASIC is a high-level programming language inspired by TI-BASIC, designed specifically for the Nova-16 emulator. It provides a simple, calculator-like syntax that compiles to Nova-16 assembly code, making it easier to develop programs without directly writing assembly.

### Key Features

- **Simple Syntax**: Case-insensitive, line-based statements with implicit variable declaration.
- **Data Types**: Support for numbers, lists, strings, matrices, and user-defined structs.
- **Control Structures**: Loops (For, While), conditionals (If-Then-Else), and subroutines.
- **Hardware Integration**: Built-in commands for graphics drawing, sprite manipulation, sound playback, and keyboard input.
- **Rapid Prototyping**: Ideal for games, demos, and educational programs.

### Compiling and Running NoBASIC Programs

1. Write your program in a `.nobasic` file.
2. Compile to assembly:
   ```bash
   python NoBASIC/nobasic_compiler.py <program.nobasic> --output <program.asm>
   ```
3. Assemble and run as with any assembly program:
   ```bash
   python nova_assembler.py <program.asm>
   python nova.py <program.bin>
   ```

### Example NoBASIC Program

```nobasic
// Simple starfield effect
ClrDraw
SetLayer(1)
For x = 0 to 25
    For y = 0 to 20
        PxlOn(rnd()+x, rnd()-y, rndr(0x01, 0x05))
    Next
Next
```

### Tools

- **Compiler** (`NoBASIC/nobasic_compiler.py`): Converts NoBASIC source to assembly.
- **Debugger** (`NoBASIC/nobasic_debugger.py`): Debug NoBASIC programs.
- **Profiler** (`NoBASIC/nobasic_profiler.py`): Performance analysis for NoBASIC code.

For detailed documentation, see [NoBASIC Design](NoBASIC/NoBASIC%20Design.md).

## Project Structure

```
Nova-16/
├── nova.py                      # Main entry point
├── nova_cpu.py                  # CPU emulator core
├── nova_memory.py               # Memory management
├── nova_gfx.py                  # Graphics subsystem
├── nova_sound.py                # Sound generation
├── nova_keyboard.py             # Keyboard input handling
├── nova_assembler.py            # Assembly language compiler
├── nova_disassembler.py         # Machine code to assembly converter
├── nova_debugger.py             # Interactive debugger
├── nova_gui.py                  # Graphical user interface
├── nova_profiler.py             # CPU profiling tools
├── nova_gpu_profiler.py         # Graphics profiling tools
├── nova_memory_profiler.py      # Memory usage analysis
├── instructions.py              # Instruction set implementation
├── opcodes.py                   # Opcode definitions
├── font.py                      # Font rendering system
├── asm/                         # Example assembly programs
│   ├── gfxtest.asm             # Graphics demonstration
│   ├── soundtest.asm           # Sound system test
│   ├── kbd_sprite.asm          # Keyboard-controlled sprite
│   ├── wordproc.asm            # Simple word processor
│   └── ...
├── docs/                        # Documentation
│   ├── CPU Specification.md     # Complete CPU architecture docs
│   ├── VRAM Specification.md    # Graphics memory layout
│   ├── SOUND_SYSTEM.md         # Audio system documentation
│   └── ...
└── tests/                       # Unit tests

```

## Installation

### Requirements
- Python 3.8 or higher
- NumPy
- Pygame
- PyAudio

### Install Dependencies

```bash
pip install numpy pygame pyaudio
```

## Usage

### Running Assembly Programs

**Graphical Mode:**
```bash
python nova.py <program.asm>
```

**Headless Mode (for testing):**
```bash
python nova.py <program.asm> --headless --max-cycles 10000
```

### Assembling Programs

```bash
python nova_assembler.py <input.asm> -o <output.bin>
```

### Disassembling Programs

```bash
python nova_disassembler.py <input.bin> -o <output.asm>
```

### Debugging Programs

```bash
python nova_debugger.py <program.bin>
```

## Example Programs

### Hello World (Text Display)
```assembly
ORG 0x1000

START:
    MOV VC, 0x1F    ; Set color to bright red
    MOV VX, 0       ; X coordinate
    MOV VY, 0       ; Y coordinate
    MOV VM, 0       ; Coordinate mode
    TEXT STR        ; Display string
    HLT

STR:
    DEFSTR "Hello, Nova-16!"
```

### Graphics Animation
```assembly
ORG 0x1000

SETUP:
    MOV VM, 1        ; Memory mode
    MOV VL, 1        ; Use layer 1
    MOV VC, 0        ; Starting color

LOOP:
    SWRITE VC        ; Write pixel
    INC VC           ; Change color
    JMP LOOP         ; Repeat
```

### Sound Test
```assembly
ORG 0x1000

MAIN:
    MOV SF, 128      ; Set frequency
    MOV SV, 128      ; Set volume
    MOV SW, 0x82     ; Sine wave + enabled
    SPLAY            ; Play sound
    HLT
```

## Instruction Set Highlights

The Nova-16 supports a comprehensive instruction set including:

- **Data Movement**: MOV, PUSH, POP, XCHG
- **Arithmetic**: ADD, SUB, MUL, DIV, INC, DEC
- **Logic**: AND, OR, XOR, NOT
- **Bit Operations**: SHL, SHR, ROL, ROR, BTST, BSET, BCLR
- **Control Flow**: JMP, JZ, JNZ, JC, JNC, JLT, JGE, JGT, JLE, CALL, RET
- **Stack Operations**: PUSH, POP, PUSHA, POPA, PUSHF, POPF
- **Graphics**: SWRITE, SREAD, SFILL, SROL, TEXT, SPBLIT
- **Sound**: SPLAY, SSTOP, STRIG
- **I/O**: KEYIN, KEYSTAT, KEYCTRL
- **System**: HLT, NOP, STI, CLI, INT, IRET

## Extras

### Profiling Tools
- **CPU Profiler**: Track instruction execution frequency and timing
- **GPU Profiler**: Monitor graphics operations and layer usage
- **Memory Profiler**: Analyze memory access patterns and hotspots

### MCP Server
The project includes an MCP (Model Context Protocol) server for AI integration:
```bash
python setup_mcp_server.py
# or
start_mcp_server.bat
```

### Font System
Custom bitmap font renderer with support for the full 8-bit character range (`0x00-0xFF`). `TEXT` reads null-terminated byte strings from memory, treating `0x09` as tab, `0x0A` as newline, and `0x0D` as carriage return; all other byte values render through the active font table. Font data can be edited using the font maker tool in the `font maker/` directory.

### Test Suite
Comprehensive test suite using pytest:
```bash
pytest tests/
```

## Documentation

Detailed documentation is available in the `docs/` directory:

- [CPU Specification](docs/CPU%20Specification.md) - Complete ISA documentation
- [VRAM Specification](docs/VRAM%20Specification.md) - Graphics memory layout
- [Sound System](docs/SOUND_SYSTEM.md) - Audio subsystem documentation
- [Keyboard Implementation](docs/Keyboard%20Implementation.md) - Input handling
- [Sprite System](docs/SPRITE_SYSTEM.md) - Sprite rendering system
- [Stack Addressing Syntax](docs/STACK_ADDRESSING_SYNTAX.md) - Stack operations
- [Instruction Reference](docs/nova16_instruction_reference.md) - Complete instruction list

## Development

### Project Status
The Nova-16 is an active project with ongoing development. See `docs/TODO` for planned features and improvements.

### Contributing
This is a personal project, but feedback and suggestions are welcome through GitHub issues.

## Technical Details

- **Byte Ordering**: Big-endian throughout
- **Memory Model**: Princeton architecture with unified 64KB address space
- **Interrupt Vectors**: Located at 0x0100-0x011F
- **Stack**: Grows downward from 0xFFFF
- **Keyboard Buffer**: 16-key circular buffer at memory-mapped location

## License

This project does not currently have a license specified. Please contact the author for usage permissions.

## Author

Created by StarfighterLily

---

**De Nova Stella** - "Of the New Star"
