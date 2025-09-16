# Nova-16 Sprite System Implementation

The sprite system has been successfully implemented according to the specifications in the TODO file. Here's a comprehensive overview:

## Overview

The Nova-16 now features a **Hybrid Memory-Based Sprite System** that provides:
- Memory-mapped sprite control blocks
- Support for 16 sprites with arbitrary sizes
- Hardware transparency support
- Multiple sprite layers
- Minimal opcode usage (only 3 opcodes)

## Memory Layout

### Sprite Control Blocks: 0xF000-0xF0FF
- **16 sprites** × **16 bytes each** = 256 bytes total
- Each sprite has its own control block at `0xF000 + (sprite_id * 16)`

### Sprite Control Block Structure (per sprite):
```
Offset 0-1: Data address (16-bit, big-endian)
Offset 2:   X position (8-bit)
Offset 3:   Y position (8-bit) 
Offset 4:   Width (8-bit)
Offset 5:   Height (8-bit)
Offset 6:   Flags (8-bit)
            - Bit 0: Active (1 = sprite is active)
            - Bit 1: Transparency enabled (1 = transparency on)
            - Bit 7: Layer select (0 = sprite layer 5, 1 = sprite layer 6)
            - Bits 2-6, 8-15: Reserved for future use
Offset 7:   Transparency color (8-bit)
Offset 8-15: Reserved for future expansion
```

## Instructions

### SPBLIT reg/imm8 (Opcodes 0x94, 0x95)
Blits a specific sprite by ID (0-15).
- `SPBLIT R0` - Blit sprite with ID from register R0
- `SPBLIT 5` - Blit sprite 5 directly

### SPBLITALL (Opcode 0x96)
Blits all active sprites in order (0-15).
- Automatically clears sprite layers before rendering
- Only renders sprites with the active flag set (bit 0 = 1)

## Features

### Arbitrary Sprite Sizes
- Sprites can be any width and height (1-255 pixels each dimension)
- No fixed sprite size limitations
- Automatically clipped to screen boundaries

### Hardware Transparency
- Per-sprite transparency control via flags
- Configurable transparency color (0-255)
- Transparent pixels preserve background content

### Layer Support
- Sprites render to dedicated sprite layers (5 and 6)
- Layer selection via bit 7 of flags
- Integrates with existing graphics layer system

### Memory-Mapped Control
- Direct memory access to sprite parameters
- Real-time sprite manipulation
- Automatic dirty tracking for optimization

## Usage Examples

### Basic Sprite Setup (Assembly)
```assembly
; Setup sprite 0
MOV P0, 0xF000          ; Point to sprite 0 control block

; Set data address to 0x3000
MOV R0, 0x30
STOR P0, R0             ; High byte
INC P0
MOV R0, 0x00
STOR P0, R0             ; Low byte
INC P0

; Set position (100, 80)
MOV R0, 100
STOR P0, R0             ; X position
INC P0
MOV R0, 80
STOR P0, R0             ; Y position
INC P0

; Set size (16x16)
MOV R0, 16
STOR P0, R0             ; Width
INC P0
STOR P0, R0             ; Height
INC P0

; Set flags: active + transparency
MOV R0, 0x03
STOR P0, R0
INC P0

; Set transparency color (black)
MOV R0, 0x00
STOR P0, R0

; Render the sprite
SPBLIT 0
```

### Animation Loop
```assembly
ANIMATION_LOOP:
    ; Update sprite position
    MOV P0, 0xF002          ; Point to sprite 0 X position
    LOAD R0, P0             ; Load current X
    INC R0                  ; Move right
    STOR P0, R0             ; Store new X
    
    ; Re-render all sprites
    SPBLITALL
    
    ; Continue animation
    JMP ANIMATION_LOOP
```

## Implementation Details

### Files Modified
1. **opcodes.py** - Added sprite instruction definitions
2. **nova_gfx.py** - Added sprite rendering system
3. **nova_memory.py** - Added sprite memory dirty tracking
4. **instructions.py** - Added sprite instruction implementations
5. **nova_cpu.py** - Connected memory and graphics systems

### Performance Optimizations
- Dirty flag tracking to minimize unnecessary re-renders
- Boundary clipping to avoid out-of-bounds memory access
- Layer-based rendering for efficient compositing
- Vectorized pixel operations using NumPy

### Error Handling
- Invalid sprite IDs are automatically clamped (0-15)
- Out-of-bounds data addresses are validated
- Off-screen sprites are clipped appropriately
- Memory access errors are gracefully handled

## Testing

The sprite system has been thoroughly tested with:
- ✅ Sprite control block setup and reading
- ✅ Individual sprite blitting
- ✅ Bulk sprite rendering (SPBLITALL)
- ✅ Transparency functionality
- ✅ Layer support
- ✅ Instruction execution
- ✅ Memory dirty tracking
- ✅ Boundary clipping

## Compatibility

The sprite system is fully compatible with:
- Existing graphics layer system
- Memory management
- Instruction set architecture
- CPU execution model
- Assembly language syntax

## Benefits Achieved

✅ **Minimal opcodes** - Only 3 opcodes used (as specified)
✅ **Full functionality** - All requested features implemented
✅ **Future expandable** - Reserved bytes for additional features
✅ **Hardware acceleration** - Optimized rendering pipeline
✅ **Layer support** - Integrates with existing layer system
✅ **Arbitrary sizes** - No size limitations
✅ **Transparency** - Hardware transparency support

The Nova-16 sprite system is now complete and ready for use in games and graphics applications!
