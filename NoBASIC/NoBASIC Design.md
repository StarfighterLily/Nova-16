# NoBASIC - A TI-BASIC Inspired Language for the Nova-16

NoBASIC is a high-level programming language designed for the Nova-16 custom 16-bit CPU emulator. It draws heavy inspiration from TI-83/84 BASIC, offering a nostalgic, easy-to-learn syntax reminiscent of programming on graphing calculators. However, NoBASIC removes the constraints of the original TI-BASIC, allowing full utilization of the Nova-16's powerful hardware features, including multi-layer graphics, programmable sound, keyboard input, and unified memory architecture.

With NoBASIC, developers can create interactive programs, games, and demos that leverage the Nova-16's 64KB unified memory, 8-layer graphics system, multi-channel sound, and real-time input handling. It's perfect for rapid prototyping, educational purposes, and reliving the thrill of coding in math class—without the limitations.

## Language Overview

NoBASIC programs are structured as a sequence of statements, executed line by line. Programs can be written in plain text files (`.nobasic`) and compiled to Nova-16 assembly (`.asm`) or directly to binary (`.bin`) for execution on the emulator.

### Syntax Basics

- **Case Insensitive**: Commands and keywords are not case-sensitive (e.g., `CLRDRAW`, `clrdraw`, or `ClrDraw` are equivalent).
- **Line-Based**: Each statement typically occupies one line, though multi-line constructs (like loops) use `End` to close blocks.
- **Comments**: Use `//` for single-line comments.
- **Statements**: End implicitly at the end of a line; no semicolons required.
- **Operators**: Standard arithmetic (`+`, `-`, `*`, `/`, `^`), comparison (`=`, `<>`, `<`, `>`, `<=`, `>=`), logical (`and`, `or`, `not`).

### Data Types and Variables

NoBASIC supports simple data types inspired by TI-BASIC:

- **Numbers**: Real numbers (floating-point like, but implemented as integers in Nova-16). Variables A-Z can hold numeric values.
- **Lists**: One-dimensional arrays, e.g., `L1`, `L2`, etc. Access elements with `L1(1)`, `L1(2)`.
- **Strings**: Text strings, e.g., `Str1`, `Str2`. Limited to 255 characters.
- **Matrices**: 2D arrays, e.g., `MatA`, `MatB`. Access with `MatA(1,1)`.
- **Variables**: Single-letter variables A-Z for numbers, plus lists, strings, and matrices. User-defined variables to come later.
- **Structs**: User-defined structs. Each field is 16-bit, max 10 fields.

Variables are global by default, and there's no explicit declaration—assigning a value creates the variable.

### Control Structures

NoBASIC includes familiar control flow from TI-BASIC:

- **Conditional Statements**:
  ```
  If condition Then
      statements
  Else
      statements
  End
  ```
  Smaller statements need no Then:
  ```
  If condition
    one line statement
  ```

- **Loops**:
  - For loops: `For variable = start To end [Step step] ... Next`
  - While loops: `While condition ... End`
  - Repeat loops: `Repeat condition ... End`

- **Jumps and Labels**: `Goto label`, `Label:`

### Graphics Commands

Leveraging the Nova-16's 8-layer graphics system:

- `ClrDraw`: Clear the current graphics layer.
- `PxlOn(x, y, color)`: Turn on a pixel at (x, y) with the specified color (0-255).
- `PxlOff(x, y)`: Turn off a pixel at (x, y).
- `Line(x1, y1, x2, y2, color)`: Draw a line from (x1, y1) to (x2, y2).
- `Circle(x, y, radius, color)`: Draw a circle centered at (x, y).
- `Text(x, y, "string", color)`: Display text at (x, y).
- `SetLayer(layer)`: Switch to a specific graphics layer (0-7).
- `SpriteOn(spriteId, x, y)`: Enable and position a sprite.
- `SpriteOff(spriteId)`: Disable a sprite.

Graphics coordinates range from 0 to 255 (256x256 resolution per layer).

### Sound Commands

Utilizing the Nova-16's programmable sound system:

- `PlayTone(frequency, duration, volume)`: Play a tone at the given frequency (Hz), duration (ms), and volume (0-255).
- `PlayWave(waveform, frequency, volume)`: Play a waveform (0-3) continuously.
- `StopSound`: Stop all sound playback.
- `SetChannel(channel)`: Select a sound channel (0-3) for multi-channel audio.

### Input and Output

- `GetKey`: Wait for and return a key press (returns key code).
- `Input(prompt, variable)`: Prompt the user for input and store in a variable.
- `Disp "text"`: Display on the first available line and move to next line.
- `Pause`: Pause execution until a key is pressed.

Keyboard input uses the Nova-16's circular buffer system for real-time responsiveness.

### Built-in Functions

Mathematical and utility functions:

- **Math**: `sin(x)`, `cos(x)`, `tan(x)`, `sqrt(x)`, `abs(x)`, `int(x)`, `round(x)`
- **Random**: `rand`: Generate a random number (0-1).
- **String**: `length(str)`, `sub(str, start, length)`, `concat(str1, str2)`
- **List/Matrix**: `dim(list)`, `sum(list)`, `mean(list)`, etc.
- **Hardware Access**: `MemRead(addr)`, `MemWrite(addr, value)` for direct memory manipulation.

### Program Structure and Execution

Programs start execution from the first line. No main function is required. Programs can call subroutines using `Goto` or structured loops.

NoBASIC programs are compiled to Nova-16 assembly using a dedicated compiler (e.g., `nobasic_compiler.py`), which generates optimized assembly code that interfaces directly with the Nova-16 hardware.

### Examples

#### Simple Graphics Demo
```
ClrDraw
For I = 0 To 255
    PxlOn(I, I, 31)  // Draw diagonal line
End
Pause
```

#### Interactive Input
```
Disp "Enter your name:"
Input "Name: ", Str1
Disp "Hello, " + Str1
Pause
```

#### Sound and Graphics
```
SetLayer(1)
Circle(128, 128, 50, 15)
PlayTone(440, 1000, 128)  // A4 note
Pause
StopSound
```

#### Game Loop Example
```
ClrDraw
X = 128
Y = 128
While 1
    K = GetKey
    If K = 24 Then Y = Y - 1  // Up
    If K = 25 Then Y = Y + 1  // Down
    If K = 26 Then X = X - 1  // Left
    If K = 26 Then X = X + 1  // Right
    ClrDraw
    PxlOn(X, Y, 31)
End
```

## Compilation and Running

1. Write your NoBASIC program in a `.nobasic` file.
2. Compile using: `python nobasic_compiler.py program.nobasic`
3. This generates `program.asm` and `program.bin`.
4. Run on Nova-16: `python nova.py program.bin`

NoBASIC aims to balance nostalgia with modern capabilities, making the Nova-16 accessible to beginners while powerful enough for advanced projects.

For more details, refer to the Nova-16 hardware specs and assembler documentation.