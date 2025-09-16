# Phase 1: Planning & Design Tasks

## Overview
This phase focuses on analyzing the current system and designing the new prefixed operand architecture. The endpoint is a finalized design document and mode encoding scheme ready for implementation.

## Detailed Steps
1. **Review Current Opcode Table**
   - Read and analyze `opcodes.py` to list all current opcodes and their variants.
   - Identify redundant patterns (e.g., MOV variants for different operand types).
   - Document the total number of opcodes (~200) and categorize by operation type.
   - Output: A summary report of redundancies and potential savings.

2. **Finalize Mode Byte Encoding Scheme**
   - Define bit allocation in the mode byte (e.g., 2 bits per operand for mode).
   - Specify mode values: 00=register, 01=imm8, 10=imm16, 11=indirect.
   - Consider extensions for indexed or direct memory modes.
   - Test encoding/decoding logic on paper for sample instructions.
   - Output: Mode encoding specification with examples.

3. **Define Core Opcode List**
   - List essential operations (MOV, ADD, etc.) without variants.
   - Assign new hex values to core opcodes (aim for <50 total).
   - Ensure no conflicts with existing opcodes for compatibility.
   - Validate that all current functionality can be covered.
   - Output: Updated opcode table draft.

## Risk Mitigation
- Backup `opcodes.py` before any changes.
- Consult existing docs/ for hardware constraints.

## Timeline
1-2 days.

## Endpoint Verification
- Design.md updated with finalized mode scheme.
- Core opcode list defined and documented.