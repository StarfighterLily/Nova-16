# Nova-16 VRAM and Graphics System Specification

## Overview
The Nova-16 VRAM module provides a comprehensive 2D graphics system with a 256×256 pixel display, dual memory buffers, extensive color palette support, and built-in text rendering capabilities. The system is designed for both high-performance graphics operations and ease of programming.

## Graphics Architecture

### Display Specifications
- **Resolution**: 256×256 pixels (65,536 total pixels)
- **Color Depth**: 8-bit per pixel (256 simultaneous colors)
- **Memory Layout**: Big-endian addressing with row-major pixel storage
- **Coordinate System**: Origin (0,0) at top-left, X increases right, Y increases down
- **Refresh Rate**: Software-controlled with VBlank/HBlank simulation

### Memory Architecture

#### Dual Buffer System
The graphics system maintains two separate 64KB memory regions:

**VRAM Buffer**
- **Purpose**: Off-screen graphics composition and manipulation
- **Size**: 256×256 bytes (65,536 bytes total)
- **Transfer**: Copy screen to VRAM with VBLIT
- **Access**: CPU can read/write through VREAD/VWRITE instructions

**Screen Buffer** 
- **Purpose**: Active display memory shown to user
- **Size**: 256×256 bytes (65,536 bytes total)
- **Usage**: Contains the actual displayed image
- **Transfer**: Contents updated from VRAM using SBLIT operation
- **Access**: Draw directly to screen with SREAD/SWRITE

### Graphics Registers

#### V-Registers (VX, VY)
Two 8-bit registers used for all graphics addressing operations:

| Register | Purpose | Value Range |
|----------|---------|-------------|
| VX | X-coordinate or high address byte | 0x00-0xFF |
| VY | Y-coordinate or low address byte | 0x00-0xFF |
| VM | Coord/Memory mode | 0-1 |
| VC | Pen color | 0-255 |

#### Graphics Flags Register
3-bit status register indicating graphics system state:

| Bit | Flag | Name | Description |
|-----|------|------|-------------|
| 2 | M | VMode | Graphics addressing mode (0=Coordinate, 1=Memory) |
| 1 | V | VBlank | Vertical blanking period active |
| 0 | H | HBlank | Horizontal blanking period active |

## Addressing Modes

### Coordinate Mode (VM = 0)
Direct pixel addressing using X,Y coordinates.

**Register Usage**:
- VX = X coordinate (0-255)
- VY = Y coordinate (0-255)

**Address Calculation**: PIXEL = VRAM[Y][X]

**Example**:
```assembly
MOV VM, 0      ; Set coordinate mode
MOV VX, 128    ; X = 128 (center)
MOV VY, 64     ; Y = 64 (upper center)
SWRITE 0x0F     ; Write white pixel at (128,64)
```

### Memory Mode (VM = 1)
Linear memory addressing treating display as 64KB memory region.

**Register Usage**:
- VX = High byte of address (0x00-0xFF)
- VY = Low byte of address (0x00-0xFF)

**Address Calculation**: ADDRESS = (VX << 8) | VY

**Example**:
```assembly
MOV VM, 1      ; Set memory mode
MOV VX, 0x10   ; High byte = 0x10
MOV VY, 0x80   ; Low byte = 0x80
SREAD R0       ; Read pixel at address 0x1080
```

### Address Translation
Memory addresses map to screen coordinates as follows:
- **ADDRESS** = Y × 256 + X
- **X** = ADDRESS % 256  
- **Y** = ADDRESS ÷ 256

## Color System

### Color Palette Organization
The Nova-16 uses an indexed color system with a sophisticated 256-color palette organized into themed color ramps:

| Range | Colors | Description |
|-------|--------|-------------|
| 0x00-0x0F | Grayscale | 16-level grayscale from black to white |
| 0x10-0x1F | Red | 16-level red intensity ramp |
| 0x20-0x2F | Green | 16-level green intensity ramp |
| 0x30-0x3F | Blue | 16-level blue intensity ramp |
| 0x40-0x4F | Yellow | 16-level yellow intensity ramp |
| 0x50-0x5F | Magenta | 16-level magenta intensity ramp |
| 0x60-0x6F | Cyan | 16-level cyan intensity ramp |
| 0x70-0x7F | Orange | 16-level orange intensity ramp |
| 0x80-0x8F | Purple | 16-level purple intensity ramp |
| 0x90-0x9F | Lime | 16-level lime intensity ramp |
| 0xA0-0xAF | Pink | 16-level pink intensity ramp |
| 0xB0-0xBF | Teal | 16-level teal intensity ramp |
| 0xC0-0xCF | Brown | 16-level brown intensity ramp |
| 0xD0-0xDF | Light Blue | 16-level light blue ramp |
| 0xE0-0xEF | Light Green | 16-level light green ramp |
| 0xF0-0xFF | Light Red | 16-level light red ramp |

### Common Color Values
```assembly
; Useful color constants
BLACK       EQU 0x00    ; Pure black
WHITE       EQU 0x0F    ; Pure white  
RED         EQU 0x1F    ; Bright red
GREEN       EQU 0x2F    ; Bright green
BLUE        EQU 0x3F    ; Bright blue
YELLOW      EQU 0x4F    ; Bright yellow
MAGENTA     EQU 0x5F    ; Bright magenta
CYAN        EQU 0x6F    ; Bright cyan
```

## Text Rendering System

### Font Specifications
- **Character Set**: Full 8-bit character space (0x00-0xFF)
- **Font Size**: 8×8 pixels per character
- **Encoding**: 1-bit per pixel (foreground/background)
- **Storage**: Bitmap data stored as 8 bytes per character

#### Text Features
- **Automatic wrapping**: Text wraps to next line at screen edge
- **Byte-oriented rendering**: `CHAR` and `TEXT` consume raw 8-bit character codes
- **Special characters**: `0x09` tab, `0x0A` newline, `0x0D` carriage return
- **Color control**: Foreground and optional background colors
- **Spacing control**: Configurable character spacing

#### Text Semantics
- **Glyph lookup**: Character code `n` uses glyph slot `n` when a full 256-character font table is present
- **Legacy compatibility**: Older 224-glyph tables still map glyph slot `0` to character code `0x20`
- **Memory strings**: `TEXT` reads bytes from memory until a `0x00` terminator is encountered
- **Screen edges**: Partially visible characters are clipped to the viewport instead of being dropped entirely
- **Control bytes**: Only tab, newline, and carriage return have layout meaning; all other byte values render their glyphs directly

### Font Character Map
```
 !"#$%&'()*+,-./0123456789:;<=>?
@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_
`abcdefghijklmnopqrstuvwxyz{|}~
```

Printable ASCII remains the primary human-readable subset, but the renderer can also draw byte values `0x00-0x1F`, `0x7F`, and `0x80-0xFF` when glyphs exist in the active font table.

## Performance Optimization

### High-Performance Operations
The graphics system includes optimized functions for common operations:

**Fast Pixel Access**
```python
# Bounds-checked pixel access
set_screen_val(value)       # Standard pixel write with bounds checking
set_screen_val_fast(value)  # Optimized pixel write (no bounds checking)
```

**Rectangle Fill**
```python
# Optimized rectangle drawing using NumPy slicing
fill_rect_fast(x, y, width, height, color)
```

**Array Operations**
All screen manipulation operations (roll, shift, rotate) use optimized NumPy array operations for maximum performance.


This comprehensive specification covers all aspects of the Nova-16 VRAM and graphics system, providing both technical reference and practical programming guidance for effective graphics development.