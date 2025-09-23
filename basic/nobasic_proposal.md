# NoBASIC Language Proposal

## Overview
NoBASIC is a TI-83+ TI-BASIC inspired programming language for the Nova-16 fantasy computer. It captures the nostalgic feel of coding on a graphing calculator in math class, with the community-driven gaming culture, while leveraging Nova-16's enhanced 16-bit hardware capabilities.

## Core Philosophy
- **No Line Numbers**: Programs are structured text files, not numbered lines
- **Calculator Feel**: Commands evoke TI-BASIC familiarity (Disp, Input, ClrHome)
- **Block Structure**: Clear Then/End blocks for control flow
- **Hardware Integration**: Direct access to Nova-16's graphics, sound, and memory
- **Community Spirit**: Easy to share, modify, and learn from others' programs

## Language Syntax

### Program Structure
Programs are plain text files with `.nob` extension. Statements are executed sequentially unless control flow changes execution.

### Variables
- **Numeric Variables**: `A` through `Z` (16-bit signed integers, -32768 to 32767)
- **Lists**: `L1` through `L6` (arrays of up to 999 elements)
- **Strings**: `Str1` through `Str9` (up to 255 characters each)
- **Matrices**: `[A]` through `[J]` (up to 10x10 matrices)
- **System Variables**:
  - `Xmin`, `Xmax`, `Ymin`, `Ymax`: Graphing window
  - `X`, `Y`: Current coordinates
  - `I%`: Loop counter (internal)

### Operators
- **Arithmetic**: `+`, `-`, `*`, `/`, `^` (power)
- **Comparison**: `=`, `!`, `<`, `>`, `<=`, `>=`
- **Logical**: `and`, `or`, `not`, `xor`

### Control Flow

#### Conditional Execution
```
If condition
Then
  statements
Else
  statements
End
```

#### Loops
```
For(variable, start, end[, step])
  statements
End

While condition
  statements
End

Repeat condition
  statements
End
```

#### Subroutines
```
Lbl label
  statements
Goto label

prgmSUBROUTINE
  statements
Return
```

### Input/Output Commands

#### Display
```
Disp [text/variable/list/matrix]
Output(row, col, text/variable)
ClrHome
ClrDraw
```

#### Input
```
Input [prompt,] variable
Prompt variable1, variable2, ...
GetCalc(variable)  // For inter-program communication
```

### Graphics Commands

#### Drawing
```
Pxl-On(x, y[, color])
Pxl-Off(x, y)
Pxl-Change(x, y[, color])
Line(x1, y1, x2, y2[, color])
Horizontal y
Vertical x
Circle(x, y, radius[, color])
Text(x, y, text)
```

#### Advanced Graphics (Nova-16 Enhanced)
```
Sprite-On(id, x, y)
Sprite-Off(id)
Layer(n)  // Set active layer 0-7
VMode(n)  // Set video mode
Rect(x1, y1, x2, y2, color[, fill])
```

### Sound Commands (Nova-16 Specific)
```
Tone(freq, duration[, vol, wave])
Play(freq, vol, wave)  // Continuous
StopSound
```

### Memory and System
```
value -> variable  // Store operation (keyboard-friendly)
variable -> {address}  // Memory poke
randInt(low, high) -> variable
getKey -> variable
```

### Math Functions
```
sin(, cos(, tan(, asin(, acos(, atan(
ln(, log(, 10^(
sqrt(, abs(, round(, iPart(, fPart(
min(, max(, mean(, median(, sum(
```

## Example Programs

### Hello World
```
ClrHome
Disp "HELLO WORLD"
Disp "NoBASIC"
Pause
ClrHome
```

### Simple Game Loop
```
ClrHome
0 -> S  // Score
While getKey != 21  // Not ENTER
  ClrDraw
  Text(0,0,"SCORE: ")
  Text(7,0,S)
  
  // Game logic here
  
  DispGraph
End
```

### Graphics Demo
```
FnOff
ClrDraw
AxesOff
GridOff
LabelOff

For(I,0,319)
  For(J,0,239)
    Pxl-On(I,J,(I+J) mod 256)
  End
End

Disp "RAINBOW SCREEN"
Pause
ClrDraw
```

### Sound Demo
```
ClrHome
Disp "SOUND TEST"

For(F,220,880,110)
  Tone(F,500)
End

Disp "DONE"
```

## Hardware Integration

### Memory Layout
- **0x0000-0x00FF**: System variables and TI-BASIC compatibility
- **0x0100-0x011F**: Interrupt vectors
- **0x0120-0x0FFF**: Program space and variables
- **0x1000-0xDFFF**: Lists, matrices, strings
- **0xE000-0xEFFF**: Graphics buffer
- **0xF000-0xFFFF**: Stack and runtime

### Performance
- **Interpreted**: Direct execution for simplicity
- **JIT Compilation**: Hot code paths compiled to assembly
- **Hardware Acceleration**: Graphics and sound operations use dedicated hardware

## Community Features

### Program Sharing
- Programs stored as text files for easy sharing
- Comments with // or /*
- Include other programs with #include

### Debugging
```
Pause  // Stop execution
Disp "DEBUG: X=",X
Trace  // Enable tracing
```

### Libraries
```
#lib "GAMES"
#lib "GRAPHICS"
```

## Implementation Plan

### Phase 1: Core Language
- Variables and expressions
- Disp/Input commands
- If/Then/End blocks
- For/End loops

### Phase 2: Graphics & Sound
- Pixel operations
- Drawing commands
- Tone/Play commands
- Layer management

### Phase 3: Advanced Features
- Lists and matrices
- Strings
- File I/O
- Subroutines

### Phase 4: Optimization
- JIT compilation
- Memory optimization
- Performance profiling

## Nostalgia Factors

### Calculator Feel
- Command names match TI-BASIC exactly where possible
- Same variable naming (A-Z, L1-L6, Str1-Str9)
- Familiar error messages and behavior

### Math Class Vibes
- Graphing calculator origins
- Educational focus on math functions
- Simple, learnable syntax

### Gaming Community
- Easy program sharing
- Competitive programming challenges
- User-created games and utilities

This proposal captures the essence of TI-BASIC while extending it for Nova-16's capabilities, creating a language that's both nostalgic and powerful.