# Phase 2: Core Implementation Tasks

## Overview
Implement the core changes to opcodes, assembler, CPU, and disassembler. The endpoint is a working prototype that can assemble and execute new orthogonal instructions.

## Detailed Steps
1. **Update opcodes.py**
   - Remove all variant opcodes (e.g., MOV reg imm8, etc.).
   - Add core opcodes with mode support.
   - Update size calculations to account for mode byte + variable operand data.
   - Test opcode definitions for conflicts.
   - Output: Revised `opcodes.py` with ~50 core opcodes.

2. **Modify nova_assembler.py**
   - Add parsing for mode-prefixed syntax (e.g., distinguish imm8 vs imm16).
   - Implement mode byte encoding logic.
   - Update instruction size calculation based on modes.
   - Handle register encoding as numbers (0-19).
   - Output: Assembler that generates new-format binaries.

3. **Revamp nova_cpu.py**
   - Update instruction decoder to parse mode byte.
   - Implement dynamic operand fetching based on modes.
   - Ensure full 16-bit immediate support.
   - Maintain compatibility with legacy opcodes via flag.
   - Output: CPU that executes new instructions correctly.

4. **Update nova_disassembler.py**
   - Add mode byte decoding for disassembly output.
   - Display operands with modes (e.g., "MOV R0, #0xBEEF (imm16)").
   - Handle variable instruction lengths.
   - Output: Disassembler that reads new binaries.

## Risk Mitigation
- Incremental commits after each file update.
- Test with simple programs before proceeding.

## Timeline
3-5 days.

## Endpoint Verification
- Assembler compiles new syntax without errors.
- CPU executes sample new instructions.
- Disassembler correctly decodes new binaries.