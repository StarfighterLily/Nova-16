
# Nova-16 Fantasy Computer: Python Implementation Design

## Overview
Nova-16 is a custom fantasy 16-bit CPU and hardware platform, implemented in Python for maximum hackability and educational value. The system emulates a tightly integrated retro computer with unified memory, multi-layer graphics, programmable sound, and direct hardware access. All hardware modules share a single memory reference, enabling true side effects and hardware integration.


## Core Architecture
- **CPU:** 16-bit Princeton architecture, single unified 64KB memory for code, data, graphics, sound, and input.
- **Registers:**
  - R0-R9: 8-bit general purpose
  - P0-P9: 16-bit general purpose (byte access via `:P0`/`P0:`)
  - VX/VY: Graphics coordinates
  - VM: Video mode (0=coordinate, 1=memory)
  - VL: Video layer (0-7)
  - Sound: SA (address), SF (frequency), SV (volume), SW (waveform)
  - Timer: TT, TM, TC, TS


## Memory Map
- 0x0000-0x00FF: Zero page (fastest access)
- 0x0100-0x011F: Interrupt vectors (manual setup required)
- 0x0120-0xEFFF: General RAM
- 0xF000-0xF0FF: Sprite control blocks (16 sprites × 16 bytes)


## Graphics System
- 8 layers: 0 (main), 1-4 (background), 5-7 (sprites)
- VM=0: Coordinate mode (VX/VY)
- VM=1: Direct memory addressing
- SWRITE: Write pixel/color
- Sprite blending and control via shared memory


## Sound System
- Multi-channel programmable sound
- SPLAY: Start playback
- Waveforms: 0-3
- Sound registers are memory-mapped and can be manipulated mid-playback


## Keyboard Input
- Circular buffer
- KEYIN/KEYSTAT instructions for polling and reading


## Python Implementation Details
- **Modules:**
    - `nova_cpu.py`: CPU core, register management, instruction set
    - `nova_memory.py`: 64KB unified memory
    - `nova_gfx.py`: Graphics layers, sprites, blending
    - `nova_sound.py`: Sound channels, waveforms
    - `nova_keyboard.py`: Input buffer
    - `nova.py`: Main emulator, integrates all components
- **Shared Memory:** All hardware modules reference the same memory object for true side effects and hardware integration.
- **Assembler/Disassembler:**
    - `nova_assembler.py`: Assembles `.asm` to `.bin`
    - `nova_disassembler.py`: Disassembles `.bin` to `.asm`
- **Debugger:** `nova_debugger.py` for interactive inspection (step, regs, mem, stack)


## Development Workflow
1. Write assembly (`.asm`) or Astrid high-level code (`.ast`)
2. Assemble to binary (`.bin`)
3. Run in emulator (`nova.py`) or headless mode for automated testing
4. Debug with `nova_debugger.py` as needed


## Quirks & Features
- Unified memory: All hardware shares the same address space
- Register byte access: Use `:P0`/`P0:` for low/high byte
- No hardware stack pointer: Must be managed in software
- Sprite system: Direct memory manipulation for control
- Zero page: Fastest access, ideal for hot variables
- Layered graphics: Priority and blending by layer number
- Interrupts: Vectors are fixed, manual setup required
- Assembler quirks: Labels are case-sensitive, comments use `;`


## Error Handling
- Exceptions print PC and error details for rapid debugging


## Testing & Validation
- Headless mode: Run for fixed cycles to validate behavior
- Register state validation after execution


## File Organization
- `asm/`: Assembly examples
- `astrid/`: High-level compiler/tools
- `docs/`: Hardware and software specs


## Environment
- Python 3.8+, numpy, pygame
- Windows 10, PowerShell


---
For more details, see the docs folder and the assembler/CPU source files. This design enables rapid prototyping, deep hardware hacking, and educational exploration of fantasy computer architecture.