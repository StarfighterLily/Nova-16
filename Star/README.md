# Star - NoBASIC Interpreter

Star is a direct interpreter for NoBASIC programs that translates NoBASIC code into Python calls, providing graphics output without the overhead of the full Nova-16 emulator.

## Features

- **Direct Execution**: NoBASIC programs are parsed and executed directly in Python
- **Graphics Support**: Full graphics capabilities using a simplified GFX system
- **No Emulator Overhead**: Runs NoBASIC programs without simulating the Nova-16 CPU
- **Real-time Display**: Uses Pygame for graphics display

## Usage

```bash
python star_interpreter.py <program.nobasic> [--verbose]
```

## Supported NoBASIC Features

- Graphics: ClrDraw, PxlOn, PxlOff, Line, Circle, Text
- Variables and expressions
- Control flow: If/Then/Else, For/Next, While/End, Repeat/Until
- Display: Disp statements (output to console)
- Pause: Built-in pause functionality

## Architecture

- `star_interpreter.py`: Main interpreter that parses NoBASIC and executes statements
- `star_gfx.py`: Simplified graphics system for drawing operations
- `font.py`: Font data for text rendering

## Dependencies

- Python 3.8+
- numpy
- pygame
- NoBASIC compiler (for parsing)

## Example

```nobasic
ClrDraw
PxlOn(100, 100, 255)
Line(50, 50, 150, 150, 128)
Text(10, 10, "Hello Star!", 255)
Pause
```

This will clear the screen, draw a white pixel, a gray line, display text, and pause.