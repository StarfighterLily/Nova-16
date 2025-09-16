# NOVA-16 Development Guidelines

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

### FORTH Development
```powershell
# Interactive FORTH interpreter
cd forth
python forth_interpreter.py
```

### Debugging
```powershell
# Interactive debugger
python nova_debugger.py program.bin

# Graphics analysis (produces detailed output)
python nova_graphics_monitor.py program.bin --cycles 1000 --export debug_output

# Disassemble binary back to assembly
python nova_disassembler.py program.bin
```

## Critical Patterns

### Register Usage
- **R0-R9**: 8-bit general purpose registers
- **P0-P9**: 16-bit general purpose registers
- **Special**: VX/VY (graphics coords), VM (video mode), VL (video layer)
- **Sound**: SA (address), SF (frequency), SV (volume), SW (waveform)
- **Timer**: TT (timer), TM (match), TC (control), TS (speed)
- **Stack**: SP (P8), FP (P9) - stack grows downward from 0xFFFF
- **Byte Access**: P registers accessible as high/low bytes with `P0:` and `:P0` syntax

### Memory Layout
- **0x0000-0x00FF**: Zero page (fast access)
- **0x0100-0x011F**: Interrupt vectors (8 vectors × 4 bytes)
- **0x0120-0xFFFF**: General memory (64KB total)
- **0xF000-0xF0FF**: Sprite control blocks (16 sprites × 16 bytes)

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
KEYSTAT R0          ; Check if key available (0=no key, 1=key ready)
```

### Stack Operations
- **Grows downward** from 0xFFFF (SP decreases on push)
- **PUSH/POP** instructions auto-manage SP (P8)
- **CALL/RET** use stack for return addresses
- **Interrupts** save PC + flags to stack

## Component Integration

### Shared Memory Pattern
```python
# All components share memory reference
cpu = CPU(memory, gfx, keyboard, sound)
memory.load(program_path)  # Programs loaded into shared memory
```

### Interrupt System
- **8 vectors** at 0x0100-0x011F (4 bytes each)
- **Priorities**: Timer (highest) → Keyboard → User interrupts
- **Automatic context save**: PC + flags pushed on interrupt
- **IRET** restores context and re-enables interrupts

## Project Conventions

### File Organization
- `*.asm` - Assembly source files
- `*.bin` - Compiled binary programs
- `forth/` - FORTH interpreter and examples
- `asm/` - Assembly examples and tests
- `docs/` - Specifications and documentation

### Code Generation Pipeline
1. **Assembly** (.asm) → **Binary** (.bin) via `nova_assembler.py`
2. **FORTH** (interactive) → **Execution** via `forth_interpreter.py`

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
print(f"R0-R9: {[f'0x{r:02X}' for r in proc.Rregisters[:10]]}")
print(f"P0-P9: {[f'0x{r:04X}' for r in proc.Pregisters[:10]]}")
```