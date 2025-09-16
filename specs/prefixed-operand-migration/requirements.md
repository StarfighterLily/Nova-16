# Prefixed Operand Migration Requirements

## Functional Requirements
- **Orthogonal Operations**: All instructions must support uniform operand modes (register, immediate 8/16-bit, indirect) without separate opcodes.
- **Full Operand Range**: Maintain 8-bit (0-255) and 16-bit (0-65535) immediate values.
- **Backward Compatibility**: Support legacy binaries via a version flag in the binary header.
- **Performance**: No significant slowdown in CPU execution; mode parsing should be efficient.
- **Assembler Support**: nova_assembler.py must parse mode-prefixed syntax and generate correct binaries.
- **Debugger Integration**: nova_debugger.py should display mode bytes and decoded operands.

## Non-Functional Requirements
- **Maintainability**: Reduce opcode table size by 50-70% for easier updates.
- **Extensibility**: Framework for adding new modes (e.g., indexed, scaled) without code changes.
- **Testing Coverage**: 100% test coverage for new decoder logic; validate with existing asm/ programs.
- **Documentation**: Update docs/ with new instruction format; provide migration guide.
- **Error Handling**: Clear error messages for invalid mode combinations in assembler/CPU.

## Technical Requirements
- **Opcode Table**: Redefine opcodes.py with core operations only (remove variants).
- **Assembler Changes**: Add mode encoding logic; support syntax like "MOV R0, 42" (imm8) vs "MOV R0, 0xBEEF" (imm16).
- **CPU Decoder**: Update nova_cpu.py to parse mode byte and fetch operands dynamically.
- **Memory Layout**: Ensure unified 64KB memory handles new instruction sizes.
- **Tools Update**: Modify nova_disassembler.py to decode mode bytes; update graphics/sound tools if affected.

## Dependencies
- Python 3.8+ with numpy, pygame (unchanged).
- No new external libraries.
- Existing hardware models (nova_gfx.py, nova_sound.py) remain compatible.

## Acceptance Criteria
- New orthogonal programs execute with same performance.
- Opcode count reduced to <100.
- Migration documented and tested.