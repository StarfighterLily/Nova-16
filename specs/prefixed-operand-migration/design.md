# Prefixed Operand Instruction Set Design

## Overview
This design proposes migrating Nova-16's instruction set from a variant-heavy, opcode-prefixed system to an orthogonal, operand-prefixed architecture. The goal is to reduce opcode redundancy, improve flexibility, and maintain full 16-bit operand support while simplifying assembler and CPU logic.

## Current System Issues
- **Non-Orthogonality**: Each operation (e.g., MOV, ADD) has multiple opcodes for different operand types (reg, imm8, imm16, indirect, indexed), leading to ~200 opcodes.
- **Redundancy**: Variants like "MOV reg reg" and "MOV reg imm16" duplicate logic.
- **Maintenance Burden**: Assembler (nova_assembler.py) and CPU decoder (nova_cpu.py) must handle each variant separately.
- **Limited Flexibility**: Adding new addressing modes requires new opcodes.

## Proposed System: Operand-Prefixed Orthogonality

### Instruction Structure
Each instruction follows this format:
1. **Opcode** (1 byte): Core operation (e.g., MOV = 0x05).
2. **Mode Byte** (1 byte): Encodes addressing modes for operands using bit fields.
3. **Operand Data** (1-2 bytes per operand): Actual values, with full 16-bit support.

### Mode Byte Encoding
- **Bits 0-1**: Operand 1 mode
- **Bits 2-3**: Operand 2 mode (if applicable)
- **Bits 4-5**: Operand 3 mode (for 3-operand instructions)
- **Bits 6-7**: Reserved for extensions (e.g., flags)

Mode values:
- 00: Register direct (R0-R9, P0-P9, specials)
- 01: Immediate 8-bit (1 data byte)
- 10: Immediate 16-bit (2 data bytes)
- 11: Register indirect ([reg])

For indexed or direct memory, extend with sub-modes in data bytes.

### Example Instructions
- **MOV R0, 42** (imm8):
  - Opcode: 0x05
  - Mode: 0x01 (op1: reg, op2: imm8)
  - Data: 0x00 (R0), 0x2A (42)

- **MOV R0, 0xBEEF** (imm16):
  - Opcode: 0x05
  - Mode: 0x02 (op1: reg, op2: imm16)
  - Data: 0x00 (R0), 0xBE 0xEF

- **ADD R0, [P1]** (reg + indirect):
  - Opcode: 0x14
  - Mode: 0x0C (op1: reg, op2: indirect)
  - Data: 0x00 (R0), 0x0B (P1)

### Register Handling
- Registers encoded as numbers (0-19: R0-R9=0-9, P0-P9=10-19, specials like VX=20).
- No separate opcodes for registers; handled via mode + data.

### Benefits
- **Reduced Opcodes**: Core operations drop from ~10 variants to 1-2.
- **Full Range**: Immediates remain 8/16-bit without capping.
- **Extensibility**: New modes added via mode byte without new opcodes.
- **Simpler Parsing**: Assembler calculates sizes dynamically.

### Drawbacks & Mitigations
- **Increased Instruction Length**: +1 byte per instruction; mitigated by fewer total opcodes.
- **Decoder Complexity**: CPU needs mode parsing; update nova_cpu.py accordingly.
- **Backward Compatibility**: Legacy binaries need reassembly

### Implementation Scope
- Update opcodes.py to define core opcodes only.
- Modify nova_assembler.py for mode encoding.
- Revamp nova_cpu.py instruction decoder.