# NoBASIC Proposal

This directory contains a proposal for a new TI-BASIC inspired programming language for the Nova-16 emulator.

## What is NoBASIC?

NoBASIC is designed to capture the nostalgic feel of programming on a TI-83+ graphing calculator in math class, while leveraging Nova-16's enhanced 16-bit hardware. It eliminates line numbers in favor of structured, readable code that feels like the calculator programs you shared with friends.

## Key Features

- **No Line Numbers**: Clean, structured code like modern languages
- **TI-BASIC Familiarity**: Commands like `Disp`, `Input`, `ClrHome` that evoke nostalgia
- **Block Structure**: Clear `If/Then/End`, `For/End` blocks
- **Keyboard-Friendly Store**: Use `->` instead of special arrow characters
- **Hardware Integration**: Direct access to Nova-16's graphics, sound, and memory
- **Community Focus**: Easy to share, modify, and learn from others' programs

## Example Program

```
ClrHome
Disp "HELLO WORLD"
Disp "NoBASIC"

Input "ENTER YOUR NAME: ",Str1
Disp "HELLO ",Str1

randInt(1,100) -> N
For(I,1,10)
  Disp I
End

Pause
```


## Why This Language?

The original Nova-16 BASIC was traditional line-numbered BASIC. While functional, it didn't capture the magic of calculator programming. NoBASIC aims to:

1. **Evoke Nostalgia**: Feel like coding in math class
2. **Build Community**: Easy sharing and collaboration
3. **Leverage Hardware**: Use Nova-16's advanced features
4. **Modern Structure**: No line numbers, clear blocks

## Implementation Status

This is currently a **proposal**. The existing BASIC interpreter implements traditional BASIC. To implement NoBASIC, we'd need:

1. New parser for TI-style syntax
2. Runtime adapted for block structure
3. Hardware integration layer
4. Testing and examples

## Getting Started

To experiment with the concept:

1. Read `nobasic_proposal.md` for full specification
2. Look at the example programs
3. Imagine the community that could build around this!

The goal is to create a language that's as fun to program in as it was discovering TI-BASIC games on your calculator.