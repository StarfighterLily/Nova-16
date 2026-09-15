# Nova-16

A custom 16-bit CPU emulator with integrated graphics, sound, and I/O capabilities, written in Python.
Now mostly complete and mostly used for development/testing to run on the 16MHz [compiled version](nova16.exe) now included for Windows.

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
- Mouse input (2-button)
- Timer/counter system with programmable interrupts

### Development Tools
These may not work fully.
- **Assembler** (`nova_assembler.py`): Converts assembly code to machine code
- **Disassembler** (`nova_disassembler.py`): Converts machine code back to assembly
- **Debugger** (`nova_debugger.py`): Step-through debugging with register inspection
- **Profilers**: CPU profiler, GPU profiler, and memory profiler for performance analysis
- **GUI** (`nova_gui.py`): Visual interface for running programs
- **Graphics Monitor** (`nova_graphics_monitor.py`): Real-time graphics debugging

## Binary Format (default: NOMF)

The assembler's **default output is NOMF** (`nova/nomf.py`) — a single-file,
versioned, CRC-protected container that replaces the loose `.bin` + `.org` +
`.sym` sidecar trio:

| Artifact | Meaning |
|----------|---------|
| `.nex`   | NOMF executable: absolute load segments, **explicit entry point**, symbol table, link map |
| `.nobj`  | NOMF relocatable object: section-relative symbols + relocation records (for the future linker) |
| `.nlib`  | NOMF archive of objects (reserved) |

The legacy `.bin`/`.org`/`.sym` files are still emitted for compatibility and
still load, but the loader **prefers NOMF automatically** (detected by the
`NOMF` magic, not the extension):

```bash
# Assemble: produces program.nex (primary) plus legacy program.bin/.org/.sym
py -3.13 nova_assembler.py asm/program.asm

# Run — loads the .nex (explicit entry point, integrity-checked) or the .bin
py -3.13 nova_main.py --headless asm/program.nex --cycles 10000
```

NOMF benefits: no orphaned sidecars (segments, entry, symbols travel
together), no silent misloads (CRC + explicit entry chunk), code/data section
typing, and the section/symbol/relocation model needed for building objects
and linking programs.

## High Level Programming Languages

NoBASIC is a high-level programming language inspired by TI-BASIC, designed specifically for the Nova-16 emulator. It provides a simple, calculator-like syntax that compiles to Nova-16 assembly code, making it easier to develop programs without directly writing assembly.

Astrid is a C-like language designed for allowing access to the underlying system and likewise compiles.

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
python nova_main.py <program.asm>
```

**Headless Mode (for testing):**
```bash
python nova_main.py <program.asm> --headless --max-cycles 10000
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
Check asm/progs, astrid/progs, and nobasic/progs for hand-written code examples

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
Documentation may be stale due to design drift over the course of development.

- [CPU Specification](docs/CPU%20Specification.md) - Complete ISA documentation
- [VRAM Specification](docs/VRAM%20Specification.md) - Graphics memory layout
- [Sound System](docs/SOUND_SYSTEM.md) - Audio subsystem documentation
- [Keyboard Implementation](docs/Keyboard%20Implementation.md) - Input handling
- [Sprite System](docs/SPRITE_SYSTEM.md) - Sprite rendering system
- [Stack Addressing Syntax](docs/STACK_ADDRESSING_SYNTAX.md) - Stack operations
- [Instruction Reference](docs/nova16_instruction_reference.md) - Complete(-ish?) instruction list

## Development

### Project Status
The Nova-16 is an active project with ongoing development. See `docs/TODO` for planned features and improvements.
It is currently nearing the end of expansion.

### Contributing
This is a personal project, but feedback and suggestions are welcome. Fork it, hack it, develop for it, spread it.

## License

This project is free to install, use, share, break, fix, hack, remove, or otherwise engage with in any legal manner.
This project CANNOT be sold with my permission. This is for fun and education.

## Author

Created by StarfighterLily

## AI Disclaimer

As I am but a humble hedge-wizard with far too little time or social skills, I have used AI
for implementation, testing, bug hunting, and fixing this project and the languages (ESPECIALLY the languages).
Please, get some human eyes and hands on this.

---

**De Nova Stella** - "Of the New Star"
