# Nova-16 Modern Assembler

A clean, efficient, and modern assembler for the Nova-16 CPU architecture.

## Features

- **Prefixed Operand Architecture**: Supports the Nova-16's advanced instruction encoding
- **Complete Instruction Set**: All Nova-16 instructions including graphics, sound, and advanced operations
- **Modern Python**: Uses dataclasses, type hints, and clean modular design
- **Full Directive Support**: ORG, EQU, DB, DW, DEFSTR directives
- **Advanced Addressing**: Register direct, indirect, indexed, and direct memory addressing
- **Symbol Resolution**: Two-pass assembly with proper forward reference resolution
- **Error Handling**: Comprehensive error reporting with line numbers

## Usage

```bash
python assembler.py <input.asm>
```

This will generate:
- `<input>.bin` - The compiled binary
- `<input>.org` - ORG segment information
- `<input>.sym` - Symbol table

## Architecture

The assembler is built with a clean modular architecture:

- `InstructionSet`: Manages opcodes and register mappings
- `Parser`: Parses assembly source into structured data
- `OperandClassifier`: Classifies operands into types
- `CodeGenerator`: Generates machine code from parsed instructions
- `DataGenerator`: Handles assembler directives
- `Assembler`: Main orchestrator with two-pass assembly

## Supported Features

### Instructions
All Nova-16 instructions are supported, including:
- Arithmetic: ADD, SUB, MUL, DIV, etc.
- Logic: AND, OR, XOR, NOT
- Control flow: JMP, JZ, CALL, RET
- Graphics: SWRITE, SREAD, SBLIT, etc.
- Sound: SPLAY, SSTOP, etc.
- Memory: MEMCPY, MEMSET, etc.

### Addressing Modes
- Register direct: `R0`, `P0`, `VX`, etc.
- Register indirect: `[R0]`, `[P1]`
- Register indexed: `[P0 + R1]`, `[FP - 4]`
- Direct memory: `[0x1000]`
- High/low byte access: `P0:`, `:P0`

### Directives
- `ORG <address>`: Set location counter
- `EQU <value>`: Define symbol
- `DB <values>`: Define bytes
- `DW <values>`: Define words (16-bit)
- `DEFSTR "string"`: Define null-terminated string

### Operands
- Hexadecimal: `0xFF`, `0x1234`
- Decimal: `255`, `1234`
- Character literals: `'A'`, `'\n'`
- Symbols and labels
- String literals with escape sequences

## Example

See `gfxtest.asm` for a complete example that demonstrates graphics, sound, and text operations.