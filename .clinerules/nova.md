
# Nova-16 AI Agent Coding Guidelines

## Core Principles
- **Never assume implementation details**—always check code and patterns in the repo before making changes.
- **Work incrementally**: Make small, testable changes and validate frequently.
- **Double-check all edits**: Even minor mistakes can cause major issues in this emulator.
- **Use project-specific workflows and patterns**—see below for concrete examples.

## Required Agent Behaviors
- Reference and follow patterns from these files:
    - [nova_cpu.py]: CPU core, register/flag handling
    - [nova_memory.py]: Memory layout, caching
    - [nova_gfx.py]: Graphics system, sprite control
    - [nova_assembler.py]: Assembly pipeline
    - [nova_mcp_server.py]: MCP tool integration

## Key Project Patterns
- **Register/flag access**: Use explicit register names (R0–R9, P0–P9, etc.) and follow byte-access conventions (`P0:`, `:P0`).
- **Memory layout**: Respect zero page, interrupt vectors, and sprite control block regions.
- **Component integration**: All subsystems share a single memory reference (see `initialize_system` in [nova.py]).
- **Testing**: Use pytest markers (`unit`, `integration`, `cpu`, etc.) and validate register/flag state after execution.
- **Assembly workflow**: Always assemble `.asm` to `.bin` before running or debugging. Use `.sym` files for symbol lookup.
- **Error handling**: Print PC and error details on exceptions (see example in this file).

## Example MCP Tool Usage
```powershell
# Assemble and run a program
py -3.13 nova_assembler.py asm/test_add.asm
py -3.13 nova.py test_add.bin --headless --cycles 10000

# Start MCP server for agent control
py -3.13 nova_mcp_server.py
```

## File/Directory Conventions
- `asm/` — Assembly source and test programs
- `NoBASIC/` — High-level language compiler and examples
- `tests/` — All test code (unit, integration, fixtures)
- `docs/` — Architecture and specification docs

**For more details, see the comments and docstrings in each key file.**

## Core Architecture
NOVA-16 is a custom 16-bit CPU emulator with Princeton architecture (unified memory) featuring 64KB shared memory. All components (CPU, graphics, sound, keyboard, timers) share a single memory reference for tight integration. The architecture emphasizes simplicity and efficiency.

**Key Components:**
- [nova_cpu.py](nova_cpu.py) - CPU core with registers (R0-R9: 8-bit, P0-P9: 16-bit), 12 flags, 8 interrupt vectors
- [nova_memory.py](nova_memory.py) - 64KB unified memory with zero-page caching and LRU cache for performance
- [nova_gfx.py](nova_gfx.py) - 8-layer graphics system (256×256) with sprite control, blending modes
- [nova_sound.py](nova_sound.py) - Programmable sound with waveforms and frequency control
- [nova_keyboard.py](nova_keyboard.py) - Circular key buffer input system
- [nova_assembler.py](nova_assembler.py) - Modern 2-pass assembler with comprehensive operand support
- [nova_mcp_server.py](nova_mcp_server.py) - MCP server for LLM-driven development

## Development Workflows

### Assembly Development (Primary)
```powershell
# Assemble .asm to .bin (creates .bin and optional .sym symbol table)
py -3.13 ..\nova_assembler.py program.asm

# Test headlessly (no GUI)
py -3.13 ..\nova.py --headless program.bin --cycles 10000

# Run with GUI
py -3.13 ..\nova.py program.bin

# Disassemble binary for inspection
py -3.13 ..\nova_disassembler.py program.bin
```

### MCP Server (LLM Integration)
```powershell
# Start MCP server (enables Claude/AI agent control)
py -3.13 .\nova_mcp_server.py

# Server provides 40+ tools for assembly, debugging, graphics, memory, sound
# Tools can be used via MCP clients (VS Code Copilot, Claude, etc.)
```

### NoBASIC Development (High-level Language)
```powershell
# Compile NoBASIC to Nova-16 assembly
cd NoBASIC
py -3.13 nobasic_compiler.py program.nb --output program.asm

# Then assemble normally
cd ..
py -3.13 .\nova_assembler.py NoBASIC/program.asm
```

### Debugging & Analysis
```powershell
# Interactive debugger (step, breakpoints, inspect)
py -3.13 nova_debugger.py program.bin

# Graphics system analysis (detailed output on rendering)
py -3.13 ..\nova_graphics_monitor.py program.bin --cycles 1000 --export debug_output

# Profiling (CPU, memory, performance)
py -3.13 ..\nova_profiler.py program.bin
py -3.13 ..\nova_memory_profiler.py program.bin
```

### Testing
```powershell
# Run test suite (pytest with markers)
pytest                           # All tests
pytest -m unit                   # Unit tests only
pytest -m integration            # Integration tests
pytest tests/unit/test_cpu.py    # Specific test file

# Test markers: unit, integration, slow, assembler, graphics, sound, memory, cpu
```

## Critical Patterns

### Register Usage
- **R0-R9**: 8-bit general purpose registers
- **P0-P9**: 16-bit general purpose registers
- **Special**: VX/VY (graphics coords), VM (video mode), VL (video layer), VC (video color)
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
MOV VL, 0           ; Active layer (0-8)
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

### Conditional Jumps and Comparisons
```asm
; Comparison operations set flags for conditional jumps
CMP R0, R1          ; Compare R0 with R1, set flags

; Signed comparisons (use overflow flag)
JLT label           ; Jump if less than (signed)
JGE label           ; Jump if greater or equal (signed)
JGT label           ; Jump if greater than (signed)  
JLE label           ; Jump if less or equal (signed)

; Unsigned comparisons (use carry flag)
JC label            ; Jump if carry (unsigned less than)
JNC label           ; Jump if no carry (unsigned greater or equal)

; Other conditions
JZ label            ; Jump if zero (equal)
JNZ label           ; Jump if not zero (not equal)
JS label            ; Jump if sign (negative)
JNS label           ; Jump if no sign (positive/zero)
```

### Flag Setting in Comparisons
- **CMP op1, op2** performs `result = op1 - op2` and sets flags
- **Zero (Z)**: Set if result = 0 (op1 == op2)
- **Sign (S)**: Set if result negative (op1 < op2 in signed)
- **Carry (C)**: Set if borrow occurred (op1 < op2 in unsigned)
- **Overflow (O)**: Set if signed overflow occurred
- **JLT**: Jumps when O ⊕ S = 1 (signed less than)

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

### Component Initialization (from nova.py)
```python
def initialize_system(enable_sound=True):
    mem = ram.Memory()
    gfx = gpu.GFX()
    kbd = keyboard.NovaKeyboard()
    snd = sound.NovaSound() if enable_sound else None
    
    proc = cpu.CPU(mem, gfx, kbd, snd)
    
    # Critical: keyboard and graphics must be connected
    kbd.cpu = proc
    mem.gfx_system = gfx
    
    return proc, mem, gfx, kbd, snd
```

### Memory Caching System
- **Zero page cache** (0x0000-0x00FF): Fast access for frequently used variables
- **Interrupt vector cache** (0x0100-0x011F): Pre-loaded interrupt vectors
- **LRU cache**: Up to 512 recently accessed bytes for hot locations
- **Auto-sync**: Caches sync with main memory on load and dirty flag updates

### Interrupt System
- **8 vectors** at 0x0100-0x011F (4 bytes each)
- **Priorities**: Timer (highest) → Keyboard → User interrupts
- **Automatic context save**: PC + flags pushed on interrupt
- **IRET** restores context and re-enables interrupts
- **Flag positions**: T(0), S(1), O(2), B(3), D(4), I(5), C(6), Z(7), P(8), H(9), A(10), E(11)

## Project Conventions

### File Organization
- `*.asm` - Assembly source files
- `*.bin` - Compiled binary programs
- `*.sym` - Symbol tables (optional, generated by assembler)
- `asm/` - Assembly examples and tests
- `NoBASIC/` - High-level language compiler and examples
- `tests/` - Test suite (unit, integration, fixtures)
- `docs/` - Specifications and detailed documentation
- `forth/` - FORTH interpreter (if available)

### Code Generation Pipeline
1. **Assembly** (.asm) → **Binary** (.bin) via [nova_assembler.py](nova_assembler.py)
2. **NoBASIC** (.nb) → **Assembly** (.asm) → **Binary** (.bin)
3. **FORTH** (interactive) → **Execution** via FORTH interpreter

### Assembler Features
- 2-pass assembly (labels resolved in pass 2)
- Comprehensive operand types: immediate, register, indirect, indexed
- Symbol table export (.sym) for debugger integration
- ORG directive sets program entry point
- P register byte access: `P0:` (high byte), `:P0` (low byte)

### Error Handling
```python
try:
    proc.step()
except Exception as e:
    print(f"Error at PC: 0x{proc.pc:04X}: {e}")
```

### Register State Inspection Pattern
When testing or debugging, always capture final state:
```python
print(f"R0-R9: {[f'0x{r:02X}' for r in proc.Rregisters[:10]]}")
print(f"P0-P9: {[f'0x{r:04X}' for r in proc.Pregisters[:10]]}")
print(f"Flags: Z={proc.flags[7]}, C={proc.flags[6]}, S={proc.flags[1]}, O={proc.flags[2]}")
```

## Dependencies & Environment
- **py -3.13** with numpy, pygame. Invoke with `py -3.13` to access correct version.
- **Windows PowerShell** for all commands
- **Windows 10** development platform
- **MCP package** (optional): `pip install mcp` for LLM integration
- **Pytest** (optional): `pip install pytest` for test execution

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

### Test Markers Reference
- `@pytest.mark.unit` - Fast, isolated tests (< 1s)
- `@pytest.mark.integration` - Component interaction tests
- `@pytest.mark.cpu` - CPU instruction tests
- `@pytest.mark.assembler` - Assembler pipeline tests
- `@pytest.mark.graphics` - Graphics rendering tests
- `@pytest.mark.sound` - Audio system tests
- `@pytest.mark.memory` - Memory access and caching tests
- `@pytest.mark.slow` - Slow-running tests (> 5s)