# Nova-16 CPU Architecture Specification

## Overview
The Nova-16 is a custom 16-bit big-endian Princeton (von Neumann) architecture with a custom ISA. It features a comprehensive instruction set, built-in graphics capabilities, keyboard support, and a robust interrupt system designed for embedded and educational applications.

## Core Architecture

### Data Path and Word Size
- **16-bit architecture** with big-endian byte ordering
- Variable-length instructions (1-4 bytes)
- Support for both 8-bit and 16-bit data operations
- Princeton architecture (unified memory space for code and data)

### Register Set

#### General-Purpose Registers
- **R0-R9**: Ten 8-bit general-purpose registers (0x00-0xFF)
- **P0-P9**: Ten 16-bit general-purpose registers (0x0000-0xFFFF)
- **VX, VY**: Two 8-bit graphics registers for coordinate operations

#### Special Registers
- **PC (Program Counter)**: 16-bit register pointing to the next instruction
- **SP (Stack Pointer)**: 16-bit register (P8) pointing to top of stack in memory, initialized to 0xFFFF
- **FP (Frame Pointer)**: 16-bit register (P9) for function frame management, initialized to 0xFFFF
- **TT, TM, TC, TS**: Timer control registers
- **SA, SF, SV, SW**: Sound registers
- **VM**: Video mode register
- **VL**: Graphics layer register

#### Register Access Modes
- **Direct access**: R0-R9, P0-P9, VX, VY
- **High-byte access**: P0: through P9: (bits 15-8 of P registers)
- **Low-byte access**: :P0 through :P9 (bits 7-0 of P registers)
- **Indirect access**: [R0] through [R9], [P0] through [P9]
- **Indexed access**: [R0+offset] through [R9+offset], [P0+offset] through [P9+offset]

### Status Flags Register
The CPU maintains a 12-bit flags register with the following flags:

| Bit | Flag | Name | Description |
|-----|------|------|-------------|
| 11 | E | Hacker | User-defined flag (not modified by CPU) |
| 10 | A | BCD Carry | Set if BCD operation result > 9 |
| 9 | H | Direction | Set for high-to-low execution mode | unimplemented
| 8 | P | Parity | Set if result has even number of 1-bits |
| 7 | Z | Zero | Set if operation result is zero |
| 6 | C | Carry | Set if operation produces carry/borrow |
| 5 | I | Interrupt | Set if interrupts are enabled |
| 4 | D | Decimal | Set if BCD arithmetic mode is enabled |
| 3 | B | Break | Set if breakpoint is encountered | unimplemented
| 2 | O | Overflow | Set if signed arithmetic overflow occurs |
| 1 | S | Sign | Set if result is negative (MSB = 1) |
| 0 | T | Trap | Set to enable single-step mode | unimplemented

### Memory Architecture
- **64KB unified address space** (0x0000 - 0xFFFF)
- **Memory-mapped I/O** for peripheral access
- **Interrupt vector table** at 0x0100-0x011F (8 vectors × 4 bytes each)
- **Hardware stack**: Memory-based stack using SP register, grows downward from 0xFFFF
- **Big-endian byte ordering**: MSB stored at lower address

### Stack Implementation
- **Stack Pointer (SP)**: P8 register points to the top of the stack
- **Frame Pointer (FP)**: P9 register used for function frame management
- **Stack Direction**: Grows downward (SP decreases on push operations)
- **Initial SP Value**: 0xFFFF (top of memory)
- **Data Storage**: All stack entries stored as 16-bit values
- **Stack Operations**: PUSH/POP instructions automatically manage SP
- **Function Calls**: CALL instruction pushes return address, RET pops it
- **Interrupts**: Automatic context saving (PC + flags) to stack

### Interrupt System

#### Interrupt Vectors and Priorities
The Nova-16 supports 8 interrupt levels with hardware prioritization:

| Vector | Address | Priority | Type | Description |
|--------|---------|----------|------|-------------|
| 0 | 0x0100 | Highest | Timer | Timer/counter overflow |
| 1 | 0x0104 | High | Serial | Serial I/O completion | unimplemented
| 2 | 0x0108 | Medium | Keyboard | Keyboard input available |
| 3 | 0x010C | Low | User 1 | User-defined interrupt 1 |
| 4 | 0x0110 | Low | User 2 | User-defined interrupt 2 |
| 5-7 | 0x0114-0x011C | Lowest | Reserved | Future expansion |

#### Interrupt Handling
- **Automatic context saving**: PC and flags pushed to stack
- **Interrupt disable**: I flag cleared during interrupt processing
- **Vectored interrupts**: Jump to handler address from vector table
- **IRET instruction**: Restores context and re-enables interrupts
- **Software interrupts**: INT instruction for system calls

#### Peripheral Interrupt Sources

**Timer Interrupt (Vector 0)**
- 4-byte control structure: Counter, Modulo, Control, Speed
- Programmable timer with overflow interrupt capability

**Serial Interrupt (Vector 1) unimplemented**
- 2-byte control structure: Data register, Control register
- Interrupt on transmission complete or data received

**Keyboard Interrupt (Vector 2)**
- 4-byte control structure: Data, Status, Control, Buffer count
- 16-key circular buffer with overflow protection
- Status flags: Key available, Buffer full, Interrupt pending

## Instruction Set Architecture

### Instruction Format and Encoding
- **Prefixed operand instructions**: All instructions use a consistent format
- **Opcode**: 1 byte (defines core operation)
- **Mode byte**: 1 byte (defines operand addressing modes)
- **Operands**: Variable length based on mode byte (0-6 bytes)
- **Big-endian encoding**: Multi-byte values stored MSB first

#### New Instruction Format
```
Instruction: [Opcode] [Mode Byte] [Operand Data...]

Mode Byte Format:
Bits 0-1: Operand 1 addressing mode
Bits 2-3: Operand 2 addressing mode  
Bits 4-5: Operand 3 addressing mode
Bit 6: Indexed addressing flag
Bit 7: Direct addressing flag

Addressing Modes:
00: Register direct
01: Immediate 8-bit
10: Immediate 16-bit
11: Memory reference (direct/indirect/indexed)
```

#### Example Instructions
```
MOV R0, 0x1234
06 08 A9 12 34
 |  |  |  |  |
 |  |  |  |  +- 0x34 (low byte of 0x1234)
 |  |  |  +---- 0x12 (high byte of 0x1234)  
 |  |  +------- 0xA9 (R0 register encoding)
 |  +---------- 0x08 (mode: op1=reg, op2=imm16)
 +------------- 0x06 (MOV opcode)

PUSH P0
2E 00 B3
 |  |  |
 |  |  +- 0xB3 (P0 register encoding)
 |  +---- 0x00 (mode: op1=reg)
 +------- 0x2E (PUSH opcode)
```

### Register Encoding
The CPU uses specific byte codes to identify registers in the new prefixed operand format:

| Register | Encoding | Type | Description |
|----------|----------|------|-------------|
| R0-R9 | 0xA9-0xB2 | 8-bit | General purpose registers |
| P0-P9 | 0xB3-0xBC | 16-bit | General purpose registers |
| VX | 0xBD | 8-bit | Graphics X coordinate |
| VY | 0xBE | 8-bit | Graphics Y coordinate |
| VM | 0x5F | 8-bit | Video mode register |
| VL | 0x60 | 8-bit | Video layer register |
| TT | 0x61 | 16-bit | Timer counter |
| TM | 0x62 | 16-bit | Timer match value |
| TC | 0x63 | 8-bit | Timer control |
| TS | 0x64 | 8-bit | Timer speed |
| SP | 0xBB | 16-bit | Stack pointer (P8) |
| FP | 0xBC | 16-bit | Frame pointer (P9) |

#### Memory Addressing Encodings
| Addressing Mode | Encoding Format | Example |
|----------------|-----------------|---------|
| Direct | [0xHHHH] | [0x1000] = 0x10 0x00 |
| Register Indirect | [reg] | [P0] = 0xB3 |
| Register Indexed | [reg+offset] | [P0+4] = 0xB3 0x04 |


## Instruction Set Reference

### Stack Operations
The Nova-16 provides comprehensive stack support through dedicated hardware registers and memory-based operations:

| Instruction | Syntax | Description | Operation |
|-------------|--------|-------------|-----------|
| PUSH | `PUSH reg` | Push register onto stack | SP -= 2; memory[SP] = reg |
| POP | `POP reg` | Pop value from stack to register | reg = memory[SP]; SP += 2 |
| PUSHA | `PUSHA` | Push all registers onto stack | Push R0-R9, P0-P9, flags |
| POPA | `POPA` | Pop all registers from stack | Pop flags, P9-P0, R9-R0 |
| PUSHF | `PUSHF` | Push flags register onto stack | SP -= 2; memory[SP] = flags |
| POPF | `POPF` | Pop flags register from stack | flags = memory[SP]; SP += 2 |
| CALL | `CALL addr` | Call subroutine | SP -= 2; memory[SP] = PC; PC = addr |
| RET | `RET` | Return from subroutine | PC = memory[SP]; SP += 2 |
| INT | `INT vector` | Software interrupt | SP -= 2; memory[SP] = PC; SP -= 2; memory[SP] = flags; PC = vector_table[vector] |
| IRET | `IRET` | Return from interrupt | flags = memory[SP]; SP += 2; PC = memory[SP]; SP += 2 |

### Stack Usage Examples

**Function Call Convention:**
```asm
; Function call
CALL my_function

; Function implementation
my_function:
    PUSH FP        ; Save old frame pointer
    MOV FP, SP     ; Set new frame pointer
    ; Function body...
    MOV SP, FP     ; Restore stack pointer
    POP FP         ; Restore frame pointer
    RET            ; Return to caller
```

**Interrupt Handler:**
```asm
; Timer interrupt handler at 0x0100
    PUSH R0        ; Save working registers
    ; Handle timer...
    POP R0         ; Restore registers
    IRET           ; Return from interrupt
```

### Key Architectural Notes

- **Stack Direction**: Grows downward from 0xFFFF toward lower addresses
- **SP Management**: All stack instructions automatically update SP register
- **FP Usage**: Conventionally used for function frame management (local variables)
- **Interrupt Context**: PC and flags automatically saved/restored by INT/IRET
- **16-bit Operations**: All stack entries are stored as 16-bit values
- **Big-endian Storage**: Multi-byte values stored MSB first in memory

This completes the comprehensive Nova-16 CPU specification. The architecture provides a rich instruction set suitable for educational purposes, embedded applications, and graphics programming while maintaining simplicity and clarity in its design.