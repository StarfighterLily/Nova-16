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
- **Usage**: All graphics drawing operations target VRAM by default
- **Access**: CPU can read/write through SREAD/SWRITE instructions

**Screen Buffer** 
- **Purpose**: Active display memory shown to user
- **Size**: 256×256 bytes (65,536 bytes total)
- **Usage**: Contains the actual displayed image
- **Transfer**: Contents updated from VRAM using SBLIT operation

#### Memory Transfer Operations
```assembly
; Transfer VRAM contents to visible screen
SBLIT    ; Sets VBlank/HBlank flags during transfer

```

### Graphics Registers

#### V-Registers (VX, VY)
Two 8-bit registers used for all graphics addressing operations:

| Register | Purpose | Value Range |
|----------|---------|-------------|
| VX | X-coordinate or high address byte | 0x00-0xFF |
| VY | Y-coordinate or low address byte | 0x00-0xFF |

#### Graphics Flags Register
3-bit status register indicating graphics system state:

| Bit | Flag | Name | Description |
|-----|------|------|-------------|
| 2 | M | VMode | Graphics addressing mode (0=Coordinate, 1=Memory) |
| 1 | V | VBlank | Vertical blanking period active |
| 0 | H | HBlank | Horizontal blanking period active |

## Addressing Modes

### Coordinate Mode (SMODE 0)
Direct pixel addressing using X,Y coordinates.

**Register Usage**:
- VX = X coordinate (0-255)
- VY = Y coordinate (0-255)

**Address Calculation**: PIXEL = VRAM[Y][X]

**Example**:
```assembly
SMODE 0        ; Set coordinate mode
MOV VX, 128    ; X = 128 (center)
MOV VY, 64     ; Y = 64 (upper center)
SWRITE 555     ; Write white pixel at (128,64)
```

### Memory Mode (SMODE 1)
Linear memory addressing treating display as 64KB memory region.

**Register Usage**:
- VX = High byte of address (0x00-0xFF)
- VY = Low byte of address (0x00-0xFF)

**Address Calculation**: ADDRESS = (VX << 8) | VY

**Example**:
```assembly
SMODE 1        ; Set memory mode
MOV VX, 0x10   ; High byte = 0x10
MOV VY, 0x80   ; Low byte = 0x80
SREAD R0        ; Read pixel at address 0x1080
```

### Address Translation
Memory addresses map to screen coordinates as follows:
- **ADDRESS** = Y × 256 + X
- **X** = ADDRESS % 256  
- **Y** = ADDRESS ÷ 256

## Graphics Instructions

### Mode Control

#### SMODE (Set Graphics Mode) - Opcodes: 0x80-0x81
```assembly
SMODE reg       ; Set mode from register value
SMODE imm      ; Set mode from immediate value
```
Sets the graphics addressing mode for subsequent operations.

**Modes**:
- **0**: Coordinate mode (VX=X, VY=Y)
- **1**: Memory mode (VX=high byte, VY=low byte)

**Effects**: Changes graphics addressing interpretation  
**Flags**: M flag updated to reflect current mode

### Data Access

#### SREAD (Screen Read) - Opcode: 0x82
```assembly
SREAD reg       ; Read pixel value into register
```
Reads pixel data from VRAM at current VX,VY position.

**Operation**: reg = VRAM[VY][VX] (coordinate mode) or VRAM[address] (memory mode)  
**Effects**: Loads pixel value into specified register  
**Flags**: None modified

#### SWRITE (Screen Write) - Opcodes: 0x83-0x84
```assembly
SWRITE reg      ; Write register value to pixel
SWRITE imm     ; Write immediate value to pixel
```
Writes pixel data to VRAM at current VX,VY position.

**Operation**: VRAM[VY][VX] = value (coordinate mode) or VRAM[address] = value (memory mode)  
**Effects**: Updates pixel in VRAM buffer  
**Flags**: None modified

### Screen Manipulation Operations

#### SROLL (Screen Roll Left) - Opcodes: 0x85-0x86
```assembly
SROLL reg       ; Roll left by register value
SROLL imm      ; Roll left by immediate value
```
Rolls entire screen content left, with pixels wrapping to right edge.

**Effects**: Pixels shifted left wrap around to right side  
**Performance**: Optimized using NumPy array operations

#### SROLR (Screen Roll Right) - Opcodes: 0x87-0x88
```assembly
SROLR reg       ; Roll right by register value  
SROLR imm      ; Roll right by immediate value
```
Rolls entire screen content right, with pixels wrapping to left edge.

#### SSHFTL (Screen Shift Left) - Opcodes: 0x89-0x8A
```assembly
SSHFTL reg      ; Shift left by register value
SSHFTL imm     ; Shift left by immediate value
```
Shifts screen content left, with rightmost pixels lost and leftmost filled with black (0).

#### SSHFTR (Screen Shift Right) - Opcodes: 0x8B-0x8C
```assembly
SSHFTR reg      ; Shift right by register value
SSHFTR imm     ; Shift right by immediate value  
```
Shifts screen content right, with leftmost pixels lost and rightmost filled with black (0).

#### SROTL (Screen Rotate Left) - Opcodes: 0x8D-0x8E
```assembly
SROTL reg       ; Rotate left by register value
SROTL imm      ; Rotate left by immediate value
```
Rotates entire screen 90 degrees counter-clockwise.

#### SROTR (Screen Rotate Right) - Opcodes: 0x8F-0x90
```assembly
SROTR reg       ; Rotate right by register value  
SROTR imm      ; Rotate right by immediate value
```
Rotates entire screen 90 degrees clockwise.

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

### Color Programming Examples
```assembly
; Draw a rainbow gradient
ORG 0x1000
RAINBOW:
    SMODE 0        ; Coordinate mode
    MOV R0, 0      ; Y coordinate
    MOV R1, 0      ; Color index

RAINBOW_LOOP:
    MOV VY, R0      ; Set Y position
    MOV R2, 0      ; X coordinate

LINE_LOOP:
    MOV VX, R2      ; Set X position
    SWRITE R1       ; Write current color
    INC R2          ; Next X
    CMP R2, 256    ; End of line?
    JNZ LINE_LOOP   ; Continue line

    INC R0          ; Next Y
    ADD R1, 1      ; Next color
    CMP R0, 256    ; End of screen?
    JNZ RAINBOW_LOOP

    HLT
```

## Text Rendering System

### Font Specifications
- **Character Set**: ASCII characters 32-127 (printable characters)
- **Font Size**: 8×8 pixels per character
- **Encoding**: 1-bit per pixel (foreground/background)
- **Storage**: Bitmap data stored as 8 bytes per character

### Text Rendering Functions

#### Character Rendering
```assembly
; Draw single character (pseudocode)
DRAW_CHAR:
    ; Input: Character in R0, X in VX, Y in VY, Color in R1
    ; Converts ASCII to font bitmap and renders to VRAM
```

#### String Rendering  
```assembly
; Draw text string (pseudocode)
DRAW_STRING:
    ; Input: String address in P0, X in VX, Y in VY, Color in R1
    ; Renders multiple characters with automatic positioning
```

#### Text Features
- **Automatic wrapping**: Text wraps to next line at screen edge
- **Special characters**: Support for newline (\n) and tab (\t)
- **Color control**: Foreground and optional background colors
- **Spacing control**: Configurable character spacing

### Font Character Map
```
 !"#$%&'()*+,-./0123456789:;<=>?
@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_
`abcdefghijklmnopqrstuvwxyz{|}~
```

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

### Programming Best Practices

#### Efficient Pixel Drawing
```assembly
; Use coordinate mode for individual pixels
SMODE 0
MOV VX, 100
MOV VY, 100  
SWRITE 0x1F    ; Red pixel

; Use memory mode for sequential access
SMODE 1
MOV P0, 0x0000 ; Start address
PIXEL_LOOP:
    MOV VX, P0:     ; High byte
    MOV VY, :P0     ; Low byte
    SWRITE 0x2F    ; Green pixel
    INC P0          ; Next address
    ; ... continue loop
```

#### Efficient Screen Updates
```assembly
; Work in VRAM, then transfer to screen
SMODE 0
; ... draw graphics to VRAM ...
SBLIT   ; Single transfer to display
```

## Advanced Graphics Programming


### Sprite System
```assembly
; Basic sprite drawing
DRAW_SPRITE:
    ; Input: Sprite data address in P0, X in R0, Y in R1
    SMODE 0
    MOV R2, 0      ; Row counter
    
SPRITE_ROW:
    MOV R3, 0      ; Column counter
    
SPRITE_COL:
    ; Calculate screen position
    MOV VX, R0
    ADD VX, R3
    MOV VY, R1  
    ADD VY, R2
    
    ; Read sprite pixel
    LOAD R4, [P0]
    INC P0
    
    ; Write if not transparent (0)
    CMP R4, 0
    JZ SKIP_PIXEL
    SWRITE R4
    
SKIP_PIXEL:
    INC R3
    CMP R3, 8      ; 8x8 sprite
    JNZ SPRITE_COL
    
    INC R2
    CMP R2, 8
    JNZ SPRITE_ROW
    
    RET
```

### Screen Effects
```assembly
; Scrolling background effect
SCROLL_EFFECT:
    SSHFTL 1       ; Shift screen left
    
    ; Draw new column on right
    SMODE 0
    MOV VX, 255    ; Rightmost column
    MOV R0, 0      ; Y counter
    
DRAW_COLUMN:
    MOV VY, R0
    ; Generate pattern based on Y position
    MOV R1, R0
    AND R1, 0x0F   ; Use low 4 bits for color
    ADD R1, 0x10   ; Add to red palette range
    SWRITE R1
    
    INC R0
    CMP R0, 256
    JNZ DRAW_COLUMN
    
    SBLIT
    RET
```


## Error Conditions and Debugging

### Common Error Conditions
- **Coordinate out of bounds**: X or Y ≥ 256 in coordinate mode
- **Invalid memory address**: Address ≥ 65536 in memory mode  
- **Invalid graphics mode**: SMODE value other than 0 or 1
- **Stack overflow**: Excessive use of graphics functions with deep call stacks

### Debugging Techniques
```assembly
; Bounds checking example
CHECK_BOUNDS:
    CMP VX, 256
    JC BOUNDS_ERROR
    CMP VY, 256  
    JC BOUNDS_ERROR
    ; Safe to proceed
    RET
    
BOUNDS_ERROR:
    ; Handle error condition
    HLT
```

### Performance Monitoring
- Monitor VBlank/HBlank flags for optimal transfer timing
- Use cycle counting for animation frame rate control
- Profile graphics operations to identify bottlenecks

This comprehensive specification covers all aspects of the Nova-16 VRAM and graphics system, providing both technical reference and practical programming guidance for effective graphics development.