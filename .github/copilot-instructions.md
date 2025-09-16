# NOVA-16 Development Guidelines
Follow the nova16.chatmode.md for response style and convention. Utilize the debugging tools available in the astrid directory:
```nova.py --headless program.bin [--cycles N]```: runs the program for N cycles without GUI, useful for automated testing.

```nova_debugger.py [<program>.bin]```: launches an interactive debugger for step-by-step execution and inspection.
```
Commands:
  step, s           Step one instruction
  step <n>, s <n>   Step <n> instructions
  regs, r           Show CPU registers
  mem <addr>        Show memory at <addr>
  stack             Show stack contents
  load <file>       Load a binary file into memory
  quit, q, exit     Exit debugger
  help, h, ?        Show this help
```

```nova_assembler.py program.asm```: assembles assembly code into binary format.

```nova_disassembler.py program.bin```: disassembles binary back into assembly code.

```nova_graphics_monitor.py program.bin```: visualizes graphics output of a binary program. Produces a lot of output, so pipe to a file and use search patterns to find relevant sections and data patterns. Use options to filter output. Consult the GRAPHICS_MONITOR_USAGE.md for details.
```
usage: nova_graphics_monitor.py [-h] [--regions REGIONS [REGIONS ...]] [--layers LAYERS [LAYERS ...]] [--cycles CYCLES] [--interval INTERVAL] [--quiet][--export EXPORT] [--config CONFIG] program
```

```astrid2.0/run_astrid.py program.ast```: compiles high-level Astrid code into assembly.

```astrid_debug_tool.py program.ast [--cycles N]```: automates compilation, assembly, execution, and graphics analysis of Astrid programs.


## Core Architecture
NOVA-16 is a custom 16-bit CPU emulator with Princeton architecture featuring 64KB unified memory. All components (CPU, graphics, sound, keyboard) share a single memory reference for tight integration.

**Key Components:**
- `nova_cpu.py` - CPU core with register management (R0-R9: 8-bit, P0-P9: 16-bit)
- `nova_memory.py` - 64KB unified memory system
- `nova_gfx.py` - 8-layer graphics with sprites and blending
- `nova_sound.py` - Multi-channel programmable sound
- `nova_keyboard.py` - Circular buffer input system

## Development Workflows

### Assembly Development (Primary)
```powershell
# Assemble .asm to .bin
python .\nova_assembler.py program.asm

# Test headlessly (no GUI)
python .\nova.py --headless program.bin --cycles 10000

# Run with GUI
python .\nova.py program.bin
```

### Astrid 2.0 High-Level Development
```powershell
# Compile .ast to .asm
cd astrid2.0
python run_astrid.py program.ast

# Then assemble to .bin
python ..\nova_assembler.py program.asm
```

### Debugging
```powershell
# Interactive debugger
python nova_debugger.py

# Common commands: s/step, r/regs, mem <addr>, stack
```

## Critical Patterns

### Register Usage
- **R0-R9**: 8-bit general purpose registers
- **P0-P9**: 16-bit general purpose registers
- **Special**: VX/VY (graphics coords), VM (video mode), VL (video layer)
- **Sound**: SA (address), SF (frequency), SV (volume), SW (waveform)
- **Timer**: TT (timer), TM (match), TC (control), TS (speed)
- **Byte Access**: P registers can have individual bytes accessed through the use of the ```:``` operator. 0xBEEF in P0, ```:P0``` would access the low byte (0xEF) and ```P0:``` would access the high byte (0xBE).

### Hardware Access Patterns
```asm
; Graphics system
MOV VM, 0           ; Coordinate mode (VX,VY = x,y coords)
MOV VL, 1           ; Active layer (1-8)
MOV VX, 100         ; X coordinate
MOV VY, 120         ; Y coordinate
SWRITE 0x1F         ; Write pixel/color

; Sound system
MOV SA, 0x2000      ; Sound address
MOV SF, 220         ; Frequency (Hz)
MOV SV, 128         ; Volume (0-255)
MOV SW, 1           ; Waveform (0-3)
SPLAY               ; Start playback

; Keyboard input
KEYIN R0            ; Read key into R0
KEYSTAT R0          ; Check if key available
```

### Memory Layout
- **0x0000-0x00FF**: Zero page (fast access)
- **0x0100-0x011F**: Interrupt vectors (8 vectors × 4 bytes)
- **0x0120-0xFFFF**: General memory (64KB total)
- **0xF000-0xF0FF**: Sprite control blocks (16 sprites × 16 bytes)

## Component Integration

### Shared Memory Pattern
```python
# All components share memory reference
cpu = CPU(memory, gfx, keyboard, sound)
memory.load(program_path)  # Programs loaded into shared memory
```

### Graphics Layer System
- **Layer 0**: Main screen buffer
- **Layers 1-4**: Background layers
- **Layers 5-8**: Sprite layers
- **Video Modes**: VM=0 (coordinate), VM=1 (memory addressing)

## Project Conventions

### File Organization
- `*.asm` - Assembly source files
- `*.ast` - Astrid 2.0 high-level source
- `*.bin` - Compiled binary programs
- `asm\` - Assembly examples and tests
- `astrid2.0\` - High-level compiler and tools

### Code Generation Pipeline
1. **Astrid** (.ast) → **Assembly** (.asm) via `astrid_compiler.py`
2. **Assembly** (.asm) → **Binary** (.bin) via `nova_assembler.py`
3. **Binary** (.bin) → **Execution** via `nova.py`

### Error Handling
```python
try:
    proc.step()
except Exception as e:
    print(f"Error at PC: 0x{proc.pc:04X}: {e}")
```

## Dependencies & Environment
- **Python 3.8+** with numpy, pygame
- **Windows PowerShell** for all commands
- **Windows 10** development platform

## Testing & Validation

### Headless Testing Pattern
```python
# Run for fixed cycles to validate behavior
run_headless(program_path, max_cycles=10000)
print(f"Final PC: 0x{proc.pc:04X}")
print(f"Graphics pixels: {non_zero_pixels}")
```

### Register State Validation
```python
# Check final register states after execution
print(f"R0-R9: {[f'0x{r:04X}' for r in proc.Rregisters[:10]]}")
print(f"P0-P9: {[f'0x{r:04X}' for r in proc.Pregisters[:10]]}")
```

<parameter name="filePath">e:\Storage\Scripts\Nova\.github\copilot-instructions.md