# Nova-16 Stack Addressing and Indexed Memory Access Syntax Guide

## Overview

This document provides comprehensive syntax guidelines for stack pointer (SP) and frame pointer (FP) manipulation, along with indexed addressing modes in the Nova-16 assembly language. It details valid syntax patterns, common usage examples, and explicitly highlights unsupported or invalid syntax to prevent assembly errors.

## Table of Contents

1. [Register Overview](#register-overview)
2. [Valid Indexed Addressing Syntax](#valid-indexed-addressing-syntax)
3. [SP/FP Direct Manipulation](#spfp-direct-manipulation)
4. [Invalid Syntax Patterns](#invalid-syntax-patterns)
5. [Usage Examples](#usage-examples)
6. [Error Patterns and Solutions](#error-patterns-and-solutions)
7. [Best Practices](#best-practices)

---

## Register Overview

### Stack and Frame Pointer Registers
```asm
SP  ; Stack Pointer (P8) - 16-bit register, grows downward
FP  ; Frame Pointer (P9) - 16-bit register, used for function frames
```

### General Purpose Registers
```asm
R0-R9   ; 8-bit general purpose registers
P0-P9   ; 16-bit general purpose registers (P8=SP, P9=FP)
```

---

## Valid Indexed Addressing Syntax

### ✅ SP-Based Indexed Addressing

#### Positive Offsets
```asm
MOV R0, [SP+0]      ; Read from SP+0
MOV R1, [SP+1]      ; Read from SP+1  
MOV R2, [SP+127]    ; Read from SP+127 (maximum positive offset)
MOV [SP+5], R0      ; Write to SP+5
MOV [SP+10], 0x42   ; Write immediate to SP+10
```

#### Negative Offsets
```asm
MOV R0, [SP-1]      ; Read from SP-1
MOV R1, [SP-2]      ; Read from SP-2
MOV R2, [SP-128]    ; Read from SP-128 (maximum negative offset)
MOV [SP-1], R0      ; Write to SP-1
MOV [SP-5], 0xFF    ; Write immediate to SP-5
```

### ✅ FP-Based Indexed Addressing

#### Positive Offsets (Parameter Access)
```asm
MOV R0, [FP+4]      ; Read parameter 1 (typical function calling convention)
MOV R1, [FP+6]      ; Read parameter 2
MOV R2, [FP+8]      ; Read parameter 3
MOV [FP+4], R0      ; Write to parameter location
```

#### Negative Offsets (Local Variables)
```asm
MOV R0, [FP-1]      ; Read local variable 1
MOV R1, [FP-2]      ; Read local variable 2
MOV R2, [FP-8]      ; Read local variable at offset -8
MOV [FP-1], R0      ; Write to local variable
MOV [FP-4], 0x33    ; Write immediate to local variable
```

### ✅ General Register Indexed Addressing

#### P Register Indexing
```asm
MOV R0, [P0+5]      ; Read from P0+5
MOV R1, [P1-10]     ; Read from P1-10
MOV [P2+15], R0     ; Write to P2+15
MOV [P3-100], 0xAB  ; Write immediate to P3-100
```

#### R Register Indexing
```asm
MOV R0, [R5+3]      ; Read from R5+3 (using R5 as base address)
MOV R1, [R6-2]      ; Read from R6-2
MOV [R7+1], R0      ; Write to R7+1
```

### ✅ Mixed Data Size Operations
```asm
; 8-bit operations
MOV R0, [SP+5]      ; Read 8-bit value
MOV [FP-1], R0      ; Write 8-bit value

; 16-bit operations  
MOV P0, [SP+10]     ; Read 16-bit value (if supported by implementation)
MOV [FP-4], P1      ; Write 16-bit value
```

---

## SP/FP Direct Manipulation

### ✅ Valid Direct Operations

#### Register-to-Register
```asm
MOV SP, 0xF000      ; Set SP to absolute address
MOV FP, SP          ; Copy SP to FP
MOV P0, SP          ; Copy SP to P0
MOV SP, P0          ; Copy P0 to SP
```

#### Arithmetic Operations (Multi-Instruction)
```asm
; To subtract from SP:
SUB SP, 2           ; SP = SP - 2
SUB SP, 8           ; SP = SP - 8

; To add to SP:
ADD SP, 2           ; SP = SP + 2
ADD SP, 16          ; SP = SP + 16

; Using immediate values:
ADD SP, 0x10        ; SP = SP + 16
SUB SP, 0x04        ; SP = SP - 4
```

#### Increment/Decrement
```asm
INC SP              ; SP = SP + 1
DEC SP              ; SP = SP - 1
```

---

## Invalid Syntax Patterns

### ❌ Arithmetic Expressions in Operands

#### NOT SUPPORTED - Arithmetic in MOV operands
```asm
MOV SP, SP-2        ; ❌ INVALID - arithmetic expression
MOV SP, SP+8        ; ❌ INVALID - arithmetic expression  
MOV FP, FP-16       ; ❌ INVALID - arithmetic expression
MOV P0, SP-4        ; ❌ INVALID - arithmetic expression
```

**Solution**: Use separate arithmetic instructions
```asm
; Instead of: MOV SP, SP-2
SUB SP, 2           ; ✅ VALID

; Instead of: MOV FP, FP-16  
SUB FP, 16          ; ✅ VALID
```

### ❌ Invalid Offset Ranges

#### Offset Limits (Signed 8-bit: -128 to +127)
```asm
MOV R0, [SP+128]    ; ❌ INVALID - offset too large
MOV R0, [SP-129]    ; ❌ INVALID - offset too small  
MOV R0, [FP+200]    ; ❌ INVALID - offset too large
MOV R0, [P0-150]    ; ❌ INVALID - offset too small
```

### ❌ Direct Memory + Index Addressing

#### NOT SUPPORTED - Direct address + offset
```asm
MOV R0, [0x1000+5]  ; ❌ INVALID - direct memory + offset
MOV R0, [0x2000-2]  ; ❌ INVALID - direct memory + offset
```

**Solution**: Load address into register first
```asm
; Instead of: MOV R0, [0x1000+5]
MOV P0, 0x1000      ; Load base address
MOV R0, [P0+5]      ; ✅ VALID - register + offset
```

### ❌ Complex Arithmetic Expressions

#### NOT SUPPORTED - Multi-term expressions
```asm
MOV R0, [SP+FP+5]   ; ❌ INVALID - multiple registers
MOV R0, [SP*2+1]    ; ❌ INVALID - multiplication
MOV R0, [SP+(R0*2)] ; ❌ INVALID - complex expression
```

### ❌ Invalid Register Combinations

#### NOT SUPPORTED - Invalid register names
```asm
MOV R0, [SP0+5]     ; ❌ INVALID - SP0 is not a register
MOV R0, [FP1-2]     ; ❌ INVALID - FP1 is not a register
MOV R0, [R10+3]     ; ❌ INVALID - R10 doesn't exist (only R0-R9)
MOV R0, [P10-1]     ; ❌ INVALID - P10 doesn't exist (only P0-P9)
```

---

## Usage Examples

### Function Call Setup
```asm
; Function prologue
PUSH FP             ; Save caller's frame pointer
MOV FP, SP          ; Set new frame pointer
SUB SP, 8           ; Allocate 8 bytes for local variables

; Access parameters (passed on stack)
MOV R0, [FP+4]      ; Get parameter 1
MOV R1, [FP+6]      ; Get parameter 2

; Use local variables
MOV [FP-1], R0      ; Store to local var 1
MOV [FP-2], R1      ; Store to local var 2

; Function epilogue
MOV SP, FP          ; Restore stack pointer
POP FP              ; Restore caller's frame pointer
RET                 ; Return to caller
```

### Array Access with Base Register
```asm
MOV P0, array_base  ; Load array base address
MOV R0, [P0+0]      ; array[0]
MOV R1, [P0+1]      ; array[1]  
MOV R2, [P0+2]      ; array[2]

; Write to array
MOV [P0+3], 0x42    ; array[3] = 0x42
MOV [P0+4], R5      ; array[4] = R5
```

### Stack-Based Local Array
```asm
SUB SP, 10          ; Allocate 10 bytes on stack

; Access elements using SP indexing
MOV [SP+0], 0x11    ; local_array[0] = 0x11
MOV [SP+1], 0x22    ; local_array[1] = 0x22
MOV [SP+2], 0x33    ; local_array[2] = 0x33

; Read back values
MOV R0, [SP+0]      ; R0 = local_array[0]
MOV R1, [SP+1]      ; R1 = local_array[1]

ADD SP, 10          ; Deallocate local array
```

---

## Error Patterns and Solutions

### Common Assembly Errors

#### Error: "Unknown operand: SP-2"
```asm
MOV SP, SP-2        ; ❌ CAUSES ERROR
```
**Solution**:
```asm
SUB SP, 2           ; ✅ CORRECT
```

#### Error: "Unknown operand: [SP+200]"
```asm
MOV R0, [SP+200]    ; ❌ OFFSET TOO LARGE
```
**Solution**:
```asm
MOV P0, SP          ; Copy SP to P0
ADD P0, 200         ; Add large offset
MOV R0, [P0]        ; Read from calculated address
```

#### Error: "Direct indexed memory access not supported"
```asm
MOV R0, [0x1000+R1] ; ❌ NOT SUPPORTED
```
**Solution**:
```asm
MOV P0, 0x1000      ; Load base address
ADD P0, R1          ; Add index
MOV R0, [P0]        ; Read from calculated address
```

---

## Best Practices

### 1. Offset Range Management
- Keep offsets within -128 to +127 range for single-instruction access
- For larger offsets, use register arithmetic
- Document offset meanings with comments

### 2. Function Calling Conventions
```asm
; Recommended parameter layout:
; [FP+4]  - Parameter 1 (first parameter)
; [FP+6]  - Parameter 2 (second parameter)
; [FP+8]  - Parameter 3 (third parameter)
; [FP+0]  - Saved FP
; [FP-1]  - Local variable 1
; [FP-2]  - Local variable 2
; [FP-4]  - Local variable 3 (16-bit)
```

### 3. Stack Safety
```asm
; Always check stack bounds before large allocations
; Use consistent allocation/deallocation patterns
SUB SP, bytes       ; Allocate
; ... use stack space ...
ADD SP, bytes       ; Deallocate (same amount)
```

### 4. Register Usage
```asm
; Use P registers for base addresses in indexed operations
MOV P0, base_addr   ; P registers are 16-bit, ideal for addresses
MOV R0, [P0+offset] ; Efficient indexed access

; Use R registers for 8-bit data and offsets
MOV R1, 5           ; R registers for small values
ADD P0, R1          ; Add R register to P register
```

### 5. Code Clarity
```asm
; Use meaningful comments for stack layout
SUB SP, 6           ; Allocate: [SP+0]=temp1, [SP+2]=temp2, [SP+4]=counter

; Document parameter meanings
MOV R0, [FP+4]      ; R0 = array_length parameter
MOV R1, [FP+6]      ; R1 = array_base_addr parameter
```

---

## Implementation Notes

### Assembler Support Status
- ✅ **SP Offset Patterns**: `[SP±offset]` fully supported
- ✅ **FP Offset Patterns**: `[FP±offset]` fully supported  
- ✅ **General Register Offsets**: `[P0±offset]`, `[R0±offset]` supported
- ✅ **Data Directives**: `DB`, `DW`, `DEFSTR` with proper indentation
- ❌ **Arithmetic Expressions**: `SP-2` as operands not supported
- ❌ **Direct Indexed**: `[0x1000+offset]` not supported

### Opcode Encoding
```
SP Indexed: 0xFB + signed_offset_byte
FP Indexed: 0xFC + signed_offset_byte  
P0-P9 Indexed: 0xF3-0xFC + signed_offset_byte
R0-R9 Indexed: 0xE9-0xF2 + signed_offset_byte
```

### Signed Offset Conversion
```
Positive: 0-127 → 0x00-0x7F
Negative: -1 to -128 → 0xFF-0x80 (two's complement)
```

This syntax guide provides complete coverage of supported and unsupported patterns in Nova-16 stack addressing, enabling efficient and error-free assembly programming.
