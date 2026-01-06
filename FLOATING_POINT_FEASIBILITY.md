# Floating-Point Support Feasibility Study for Nova-16

## Executive Summary

Adding floating-point support to Nova-16 is **technically feasible but impractical for hardware implementation**. The primary constraints are:

1. **Opcode space exhaustion**: Only 6 unused opcodes remain (0x44-0x49)
2. **Limited register file**: No dedicated FP registers; must use existing 16-bit registers
3. **16-bit word size**: IEEE 754 SP (32-bit) requires multi-word operations; no native support
4. **Memory bandwidth**: Floating-point operations inherently require more memory traffic
5. **Code size overhead**: FP operations require complex exception handling logic

**Recommended approach**: **Software library with fixed-point fallback** for applications requiring decimal precision. Hardware FP acceleration is not feasible given current constraints.

---

## 1. Current Nova-16 Architecture Analysis

### 1.1 Instruction Set Status

**Total opcodes in instruction space**: 256 (0x00-0xFF)

**Current allocation**:
```
0x00-0x02  : Control (HLT, RET, IRET)
0x03-0x05  : Interrupt control (CLI, STI, reserved)
0x06-0x0F  : Data movement + unary arithmetic (MOV, ADD, SUB, MUL, DIV, INC, DEC, MOD, NEG, ABS)
0x10-0x17  : Bitwise operations (AND, OR, XOR, NOT, SHL, SHR, ROL, ROR)
0x18-0x1D  : Stack operations (PUSH, POP, PUSHF, POPF, PUSHA, POPA)
0x1E-0x2A  : Control flow (JMP, JZ, JNZ, JO, JNO, JC, JNC, JS, JNS, JGT, JLT, JGE, JLE)
0x2B-0x2D  : Branching (BR, BRZ, BRNZ)
0x2E-0x30  : Comparison/Interrupts (CMP, CALL, INT)
0x31-0x43  : Graphics + VRAM operations (SBLEND, SREAD, SWRITE, SROL, SROT, SSHFT, SFLIP, SLINE, SRECT, SCIRC, SINV, SBLIT, SFILL, VREAD, VWRITE, VBLIT, TEXT, CHAR, KEYIN, KEYSTAT, SPLAY, SSTOP, RND, RNDR, ITOSH, ITOS, STOI)
0x44-0x49  : AVAILABLE (6 opcodes)
0x4A-0xFF  : RESERVED/Available for future use (182 opcodes)
```

**Summary**:
- **Used**: 67 opcodes (0x00-0x43)
- **Immediately available**: 6 opcodes (0x44-0x49)
- **Expandable**: 182 reserved slots (0x4A-0xFF)

**FP Hardware Instruction Needs** (IEEE 754 SP minimum):
- FADD, FSUB, FMUL, FDIV (4 core arithmetic)
- FABS, FNEG (2 unary)
- FCMP (1 comparison)
- FTRUNC, FROUND (2 conversion utilities)
- FSIN, FCOS, FSQRT (3 transcendental - optional but common)

**Total minimum**: 12 FP instructions; extended set could reach 20-30 instructions.

### 1.2 Register Architecture

**Current register file**:
```
R0-R9:   8-bit registers (0x00-0xFF each)
P0-P9:   16-bit registers (0x0000-0xFFFF each)
Special: VX, VY, VM, VL, VC (graphics)
         TT, TM, TC, TS (timer)
         SA, SF, SV, SW (sound)
         PC, SP, FP (control)
         12-bit flags register
```

**Analysis for FP**:
- No dedicated FP registers (unlike x86 FPU with ST0-ST7)
- P0-P7 currently available as general purpose
- 16-bit registers insufficient for single IEEE 754 SP (32-bit)
- Options for FP storage:
  1. **Pair 16-bit registers**: (P0:P1 for one FP value) - Reduces usable registers
  2. **Memory-based FP stack**: Store in heap/stack area - Slower, adds memory pressure
  3. **Hybrid**: Some in registers, some on stack

### 1.3 Memory Architecture

**Total unified memory**: 64KB (0x0000-0xFFFF)

**Current allocation**:
```
0x0000-0x00FF : Zero page (256B, fast access)
0x0100-0x011F : Interrupt vectors (32B)
0x0120-0xDFFF : General memory (~56KB available)
0xE000-0xEFFF : String pool (4KB potential)
0xF000-0xF0FF : Sprite control (256B)
0xF100-0xFFFE : Reserved (3.8KB)
0xFFFF        : Stack base (grows downward)
```

**FP memory impact**:
- IEEE 754 SP: 4 bytes per value
- IEEE 754 DP: 8 bytes per value
- If using memory-based FP stack: ~256 values = 1KB (SP) or 2KB (DP)
- Alternative: fixed-point arithmetic uses 2-4 bytes for reasonable precision

### 1.4 Instruction Format

**Current format**:
```
[Opcode (1)] [Mode Byte (1)] [Operands (0-6 bytes)]
```

**Mode byte structure**:
```
Bits 0-1: Operand 1 addressing mode (0=register direct, 1=memory, 2=register indirect, 3=indexed)
Bits 2-3: Operand 2 addressing mode (same)
Bits 4-5: Operand 3 addressing mode (same)
Bit 6:    Indexed addressing flag
Bit 7:    Direct addressing flag
```

**FP instruction integration**:
- FP instructions would follow same prefix operand format
- Mode byte supports up to 3 operands (sufficient for FADD dest, src1, src2)
- Operands can reference memory or registers seamlessly

---

## 2. IEEE 754 Floating-Point Overview

### 2.1 IEEE 754 Single Precision (SP/float)

```
Format: [Sign(1)] [Exponent(8)] [Mantissa(23)]
Total:  32 bits (4 bytes)

Value = (-1)^sign × 1.mantissa × 2^(exponent-127)

Special values:
  - Zero: exponent=0, mantissa=0
  - Denormalized: exponent=0, mantissa≠0 (gradual underflow)
  - Infinity: exponent=255, mantissa=0
  - NaN: exponent=255, mantissa≠0
```

**Precision**: ~7 decimal digits

**Range**: 
- Smallest positive normal: 2^-126 ≈ 1.18e-38
- Largest positive: ~3.4e38
- Zero: Exact representation

**Rounding modes**: Round-to-nearest (default), Round-toward-zero, Round-down, Round-up

### 2.2 Alternatives for Nova-16

#### Option 1: Fixed-Point Arithmetic (Q-format)

Example: Q16 format (16 bits integer, 16 bits fractional)
```
Storage: 32-bit value (uses two P registers or memory word)
Bit 31: Sign
Bits 30-16: Integer part (-32768 to 32767)
Bits 15-0: Fractional part (1/65536 precision)

Range: -32768.999... to 32767.999...
Precision: 1/65536 ≈ 0.0000153 (5 decimal digits)
Operations: Simple integer operations with manual scaling
```

**Advantages**:
- ✅ Uses existing integer ALU
- ✅ No special hardware needed
- ✅ Predictable performance
- ✅ Exact arithmetic (no rounding errors for representable values)

**Disadvantages**:
- ❌ Fixed range (can overflow with large numbers)
- ❌ Manual scaling required
- ❌ Requires more careful algorithm design

#### Option 2: BCD (Binary-Coded Decimal)

```
Each decimal digit stored as 4-bit BCD code.
Example: 123.45 → 0x01 0x02 0x03 0x04 0x05

Nova-16 already supports BCD arithmetic via D flag!
```

**Advantages**:
- ✅ Existing BCD mode in flags (D flag)
- ✅ Decimal precision preserved
- ✅ Easy human-readable conversion
- ✅ Slower but software-compatible

**Disadvantages**:
- ❌ Limited precision per byte (1-2 digits)
- ❌ Complex to implement all operations
- ❌ Not standardized like IEEE 754

#### Option 3: IEEE 754 Software Emulation

```
Implement full IEEE 754 SP in software:
- FADD, FSUB, FMUL, FDIV via multi-step assembly routines
- Exponent/mantissa manipulation in software
- All exception handling in software
```

**Advantages**:
- ✅ Portable IEEE standard
- ✅ Compatible with other systems
- ✅ Full precision support

**Disadvantages**:
- ❌ Very slow (50-500 cycles per operation vs 3-5 for integer)
- ❌ Large code footprint (~2-4KB per operation set)
- ❌ Complex exception handling
- ❌ Impractical for performance-sensitive code

---

## 3. Feasibility Analysis by Approach

### 3.1 Hardware FP (Adding FP CPU Instructions)

**Pros** ✅:
- Fast floating-point operations (5-10 cycles vs 100+ in software)
- Transparent to programmer (hardware handles details)
- Reduced code size
- Standards-compliant (IEEE 754)

**Cons** ❌:
- **Opcode space**: Only 6 immediately available opcodes, need 12+ for basic FP
- **Hardware complexity**: Floating-point ALU requires:
  - Exponent comparison circuits
  - Mantissa align/shift logic
  - Rounding logic
  - Overflow/underflow detection
  - ~2000+ additional gates (for simple implementation)
- **Register file redesign**: Need dedicated FP registers or split P0-P7
- **Pipeline modification**: FP operations typically multi-cycle, need pipeline redesign
- **Testing burden**: IEEE 754 compliance requires extensive test suite
- **Code size**: Implementation in Python would exceed current nova_cpu.py significantly
- **Stack management**: FP stack (like x87) vs register file (like modern FPUs) decision needed

**Estimated implementation effort**: 40-80 hours (hardware design + Python implementation + testing)

**Verdict**: ❌ **NOT RECOMMENDED** - Too much architectural change for marginal benefit

### 3.2 Software Library (Emulation)

**Implementation approach**:

```assembly
; Example: Software FADD (single-precision floating-point addition)
; Input: P0:P1 = first FP number, P2:P3 = second FP number
; Output: P0:P1 = sum

FADD_IMPL:
    ; Extract exponents from both operands
    MOV R0, P0:        ; High byte of first number = sign + exp bits
    AND R0, 0x7F       ; Mask to get 7 bits of exponent
    
    MOV R1, P2:        ; High byte of second number
    AND R1, 0x7F       ; Extract exponent
    
    ; Compare exponents and align mantissas
    CMP R0, R1
    JGT FIRST_LARGER
    
    ; ... Continue with mantissa alignment, addition, normalization ...
    
    RET
```

**Pros** ✅:
- ✅ No hardware changes needed
- ✅ Uses existing CPU resources efficiently
- ✅ Can be implemented incrementally
- ✅ Library can be loaded separately from application
- ✅ IEEE 754 compliance possible (with effort)

**Cons** ❌:
- ❌ **Very slow**: FADD ~150-200 cycles (vs 3-5 for integer ADD)
- ❌ **Large code footprint**: ~200-300 bytes per operation
- ❌ **Complex implementation**: Exponent handling, mantissa normalization, rounding
- ❌ **No exception model**: Would need interrupt-based exception handling
- ❌ **Limited transcendental functions**: FSIN, FCOS, FSQRT very expensive in software

**Performance estimates**:
| Operation | Cycles | vs Integer ADD |
|-----------|--------|----------------|
| FADD | 150-200 | 50-70x slower |
| FSUB | 150-200 | 50-70x slower |
| FMUL | 300-400 | 100-130x slower |
| FDIV | 400-600 | 130-200x slower |
| FSIN | 800-1200 | 260-400x slower |

**Code size estimates**:
| Routine | Size |
|---------|------|
| FADD/FSUB | 200B |
| FMUL | 250B |
| FDIV | 300B |
| FSQRT | 200B |
| FSIN/FCOS | 400B each |
| Support routines | 300B |
| **Total library** | ~2KB |

**Memory impact**: 2KB library + 2KB for 250 FP values (SP) = 4KB used from 56KB available (7%)

**Verdict**: ✅ **FEASIBLE BUT IMPRACTICAL** - Use only for applications that don't require real-time performance

### 3.3 Fixed-Point Alternative (Recommended)

**Implementation approach** (Q16 format):

```assembly
; Q16 format: 16-bit integer, 16-bit fractional part
; Example: 123.456 stored as: 123 * 65536 + round(0.456 * 65536) = 0x7B74B8

; Q16 ADD (using 32-bit arithmetic via P register pairs)
QADD16:
    ; P0:P1 = first Q16, P2:P3 = second Q16
    ; Result in P0:P1
    MOV P0, P0 + P2    ; Add low 16 bits
    MOV P1, P1 + P3 + CARRY_FROM_LOW_ADD
    ; Result is in P0:P1
    RET

; Q16 to string conversion
QTOSTR:
    ; P0 = Q16 value
    ; Convert to "123.456" format
    MOV P1, P0 >> 16   ; Integer part
    MOV P2, P0 & 0xFFFF ; Fractional part
    ; Convert both parts and combine output
    RET
```

**Pros** ✅:
- ✅ **Fast**: Addition same speed as integer addition (3-5 cycles)
- ✅ **Simple**: Uses existing integer ALU
- ✅ **Precise**: Exact for representable values (no rounding errors)
- ✅ **Small code**: 50-100 bytes per operation
- ✅ **Predictable performance**: No special cases or exception handling
- ✅ **Easy to debug**: Values directly inspectable in memory

**Cons** ❌:
- ❌ **Limited range**: 16-bit integer part = ±32767
- ❌ **Fixed precision**: 16 bits fractional = 5 decimal digits
- ❌ **Requires scaling**: Programmers must manage decimal points
- ❌ **No infinity/NaN**: Must handle edge cases manually
- ❌ **Not IEEE compliant**: Incompatible with other systems

**When to use**:
- ✅ Graphics calculations (3D transformations, physics)
- ✅ Embedded DSP (audio synthesis, signal processing)
- ✅ Game development (physics, animations)
- ✅ Financial calculations (accounting requires exact decimal arithmetic better served by BCD)
- ❌ NOT for scientific computing (need IEEE 754)
- ❌ NOT for very large numbers (range too limited)

**Memory impact**: Negligible (same as integer storage)

**Performance impact**: Negligible (same as integer operations)

**Verdict**: ✅ **HIGHLY RECOMMENDED** - Best fit for Nova-16's constraints

### 3.4 Hybrid Approach (Fixed-Point + Limited IEEE 754)

**Strategy**: Provide both:
1. **Fixed-point library** (Q16) for most operations (fast, simple)
2. **Lightweight IEEE 754 emulation** for interop with other systems (slow, optional)
3. **BCD arithmetic** for exact decimal calculations (via existing D flag)

**Implementation phases**:

**Phase 1 (Priority: HIGH)** - Fixed-Point Math Library
```
- QAD16, QSUB16, QMUL16, QDIV16 (basic arithmetic)
- QTOSTR, STRTOQ (conversion)
- QSIN, QCOS, QSQRT (basic transcendental via lookup tables)
- Documentation with examples
```
**Effort**: 20-30 hours | **Code size**: 1KB | **Performance**: Good

**Phase 2 (Priority: MEDIUM)** - Enhanced Fixed-Point
```
- Q8 format (8-bit int, 8-bit frac) for limited range
- Q24 format (using memory for 32-bit values)
- Matrix operations (for 3D graphics)
- Trig lookup tables (sin, cos, atan2)
```
**Effort**: 40-60 hours | **Code size**: 2KB | **Performance**: Excellent

**Phase 3 (Priority: LOW)** - IEEE 754 Emulation (Optional)
```
- Basic FADD, FSUB, FMUL, FDIV
- FTOQ (convert IEEE to Q16)
- QTOIEE (convert Q16 to IEEE)
- For scientific code that needs IEEE compatibility
```
**Effort**: 60-100 hours | **Code size**: 3KB | **Performance**: Poor

**Verdict**: ✅ **RECOMMENDED ARCHITECTURE** - Provides best of both worlds

---

## 4. Detailed Cost-Benefit Analysis

### 4.1 Hardware FP Implementation

| Aspect | Cost | Benefit | ROI |
|--------|------|---------|-----|
| **Implementation** | 40-80 hrs | 5-10x FP performance | Medium |
| **Code size** | +2KB CPU | Native FP instructions | Low |
| **Opcode space** | 12-16 slots | IEEE 754 compliance | Low |
| **Register complexity** | Redesign P0-P7 | Transparent to programmer | Medium |
| **Testing** | 20-30 hrs | Correctness assurance | High |
| **Maintenance** | Ongoing | Bug fixes, compatibility | High |
| **Adoption barrier** | Documentation needed | Easier programming | Low |

**Overall**: ❌ **High cost, medium benefit** - Not recommended given limited opcode space and register file

### 4.2 Software IEEE 754 Library

| Aspect | Cost | Benefit | ROI |
|--------|------|---------|-----|
| **Implementation** | 30-50 hrs | Full IEEE 754 | Low |
| **Code size** | +2KB | Standards compliance | Low |
| **Performance** | 50-200x slower | Portability | Low |
| **Memory impact** | Minimal | Reusable library | Medium |
| **Testing** | 10-20 hrs | Validation suite | Medium |
| **Maintenance** | Minimal | Bug fixes only | High |
| **Use cases** | Limited | Scientific computing | Very Low |

**Overall**: ⚠️ **Medium cost, low benefit** - Only for niche scientific applications

### 4.3 Fixed-Point Math Library (RECOMMENDED)

| Aspect | Cost | Benefit | ROI |
|--------|------|---------|-----|
| **Implementation** | 20-30 hrs | Practical math operations | High |
| **Code size** | +1KB | Lean, efficient | High |
| **Performance** | Same as integers | Real-time capable | High |
| **Memory impact** | Minimal | Fits in 64KB easily | High |
| **Testing** | 5-10 hrs | Simple validation | High |
| **Maintenance** | Minimal | No edge cases | High |
| **Use cases** | Many | Graphics, games, embedded | Very High |

**Overall**: ✅ **Low cost, high benefit** - Strongly recommended

### 4.4 Hybrid Approach (BEST)

Implement **Phase 1 (Fixed-Point)** + **Phase 2 (Enhanced Fixed-Point)**:

| Aspect | Cost | Benefit | ROI |
|--------|------|---------|-----|
| **Total implementation** | 60-90 hrs | Complete math toolkit | Excellent |
| **Code size** | +2-3KB | Comprehensive coverage | Excellent |
| **Performance** | Excellent for most | Covers 90% of use cases | Excellent |
| **Memory impact** | 3-5% of total | Acceptable trade-off | Good |
| **Testing** | 10-15 hrs | Coverage of real scenarios | Excellent |
| **Maintenance** | Minimal | Stable, proven techniques | Good |
| **Use cases** | Most practical applications | Games, graphics, physics | Excellent |
| **Future extensibility** | IEEE 754 optional | Can add Phase 3 later | Good |

**Overall**: ✅ **Excellent cost-benefit ratio**

---

## 5. Specific Implementation Recommendations

### 5.1 Recommended Path: Fixed-Point Math Library

**What to implement** (Priority order):

**Tier 1 - Core Operations** (Essential)
```asm
; Fixed-point 16.16 format (Q16)
; Stored as: [P0, P1] = 32-bit Q16 value

; Basic arithmetic
QADD        P0, P1, P2, P3    ; P0:P1 = P0:P1 + P2:P3
QSUB        P0, P1, P2, P3    ; P0:P1 = P0:P1 - P2:P3
QMUL        P0, P1, P2, P3    ; P0:P1 = P0:P1 * P2:P3 (36-bit intermediate)
QDIV        P0, P1, P2, P3    ; P0:P1 = P0:P1 / P2:P3

; Conversion
QTOSTR      P0, P1, addr      ; Convert Q16 to ASCII string at addr
STRTOQ      addr, P0, P1      ; Parse ASCII string at addr to Q16 in P0:P1
FROMINT     P0, R0, P1        ; P0:P1 = (int R0) as Q16
TOINT       P0, P1            ; R0 = (int) P0:P1 (truncate)
```

**Tier 2 - Extended Functions** (Useful)
```asm
; Transcendental (via 256-entry lookup tables in memory)
QSIN        P0                ; P0 = sin(P0) [angle in fixed-point radians]
QCOS        P0                ; P0 = cos(P0)
QATAN2      P0, P1, P2        ; P0 = atan2(P1, P2)

; Math
QSQRT       P0                ; P0 = sqrt(P0)
QABS        P0                ; P0 = abs(P0)
QNEG        P0                ; P0 = -P0
QCLAMP      P0, min, max      ; P0 = clamp(P0, min, max)
```

**Tier 3 - Optimized Versions** (Nice to have)
```asm
; Q8 format (8.8) for smaller range, faster operations
Q8ADD       R0, R1, R2        ; R0 = R1 + R2 (Q8)
Q8MUL       R0, R1, R2        ; R0 = R1 * R2 (Q8)

; Matrix operations (for 3D graphics)
MAT3MULT    src1_addr, src2_addr, dest_addr  ; 3×3 matrix multiply
MAT3XFORM   matrix_addr, x_p0, y_p1, z_p2   ; Transform 3D point
```

### 5.2 Memory Layout for Fixed-Point Library

```
0x0000-0x00FF: Zero page (reserved)

0x0100-0x011F: Interrupt vectors (reserved)

0x0120-0x0FFF: Core library code (Q-format arithmetic routines)
    - QADD, QSUB, QMUL, QDIV: ~300B
    - Conversion routines: ~200B
    - Utility functions: ~200B
    Total: ~700B

0x1000-0x1FFF: Lookup tables (trigonometric, etc.)
    - sin/cos table (0-π/2): 256 entries × 4 bytes = 1KB
    - atan2 helper table: 256 entries × 2 bytes = 512B
    Total: ~1.5KB

0x2000-0xDFFF: Application code + data (remaining ~44KB)

0xDFFF-0xFFFF: Stack (grows downward)
```

### 5.3 Public API for Fixed-Point Library

```assembly
; ============================================
; FIXED-POINT MATH LIBRARY FOR NOVA-16
; Q16 Format (16-bit integer, 16-bit fraction)
; ============================================

; ARITHMETIC OPERATIONS
; All operations preserve Q16 format

QADD src1_addr, src2_addr, dest_addr
    ; Q16 addition
    ; src1, src2: 4-byte Q16 values
    ; dest: 4-byte result
    ; Flags: Z (if result is zero), C (if overflow), O (if signed overflow)
    ; Cycles: 20-30

QSUB src1_addr, src2_addr, dest_addr
    ; Q16 subtraction
    
QMUL src1_addr, src2_addr, dest_addr
    ; Q16 multiplication
    ; Note: Intermediate result is 64-bit, then scaled back to 32-bit
    ; Takes longer than QADD
    
QDIV src1_addr, src2_addr, dest_addr
    ; Q16 division
    ; Sets Z if division by zero
    ; Slowest operation

; CONVERSION OPERATIONS

QTOSTR q16_addr, output_addr
    ; Convert Q16 fixed-point to ASCII decimal string
    ; Format: "-12345.67890" with leading/trailing space
    ; Output: null-terminated string
    
STRTOQ input_addr, q16_addr
    ; Parse ASCII decimal string to Q16
    ; Accepts: "123", "123.45", "-123.45"
    
FROMINT int_val, q16_addr
    ; Convert 16-bit integer to Q16
    ; Essentially: q16 = int_val << 16

TOINT q16_addr, result_addr
    ; Extract integer part of Q16
    ; Truncates (rounds toward zero)
    
TOREAL q16_addr, result_addr
    ; Extract fractional part as Q16 in range [0, 1)
    ; Useful for mantissa operations

; MATH FUNCTIONS (using lookup tables)

QSIN angle_q16, result_addr
    ; Sine function
    ; Input: angle in Q16 radians
    ; Output: sin(angle) in Q16, range [-1, 1)
    ; Uses: 256-entry lookup table + interpolation
    
QCOS angle_q16, result_addr
    ; Cosine function
    
QSQRT value_q16, result_addr
    ; Square root
    ; Input: non-negative Q16
    ; Output: sqrt(value) in Q16
    
QABS value_addr, result_addr
    ; Absolute value (remove sign bit)
    
QNEG value_addr, result_addr
    ; Negate (two's complement)

; VECTOR OPERATIONS (for 2D graphics)

QVEC_ADD    vec1_addr, vec2_addr, result_addr
    ; Add two 2D vectors (each 8 bytes = two Q16 values)
    
QVEC_DOT    vec1_addr, vec2_addr, result_addr
    ; Dot product of two 2D vectors
    
QVEC_SCALE  vec_addr, scalar_q16, result_addr
    ; Scale 2D vector by scalar

; 3D MATRIX OPERATIONS (for graphics)

QMAT3_MULT  mat1_addr, mat2_addr, result_addr
    ; 3×3 matrix multiplication
    ; Each matrix: 9 Q16 values (36 bytes)
    ; Result: 36 bytes
    
QMAT3_XFORM matrix_addr, point_addr, result_addr
    ; Transform 3D point by 3×3 matrix
    ; Point: 3 Q16 values (12 bytes)
    ; Result: 12 bytes

; ============================================
; USAGE EXAMPLE
; ============================================

; Calculate: a = 123.456 + 789.123
MOV P0, 0x1000      ; Address for result
MOV P1, 0x1004      ; Address for first Q16 (123.456)
MOV P2, 0x1008      ; Address for second Q16 (789.123)
CALL QADD           ; a = first + second
; Result at 0x1000

; Print result as decimal string
MOV P0, 0x1000      ; Q16 value to convert
MOV P1, 0x2000      ; Output string buffer
CALL QTOSTR
TEXT 0x2000         ; Display string
```

### 5.4 Example: Implementing QSIN

```asm
; QSIN - Fixed-point sine using lookup table
; Input: P0 = angle in Q16 radians (0 to 2π stored as 0 to 0x6487ED)
; Output: P1 = sin(angle) in Q16 range [-1.0, 1.0) = [-0x10000, 0x10000)
; Uses: Lookup table at 0x1000 (256 entries for 0 to π/2)
;       Linear interpolation between table values

QSIN:
    ; Normalize angle to [0, 2π)
    MOV P2, P0              ; P2 = angle
    MOV P3, 0x6488         ; P3 = 2π in Q16 (approx)
    CMP P2, P3
    JLT QSIN_NORMALIZED
    SUB P2, P3
    JMP QSIN_NORMALIZED
    
QSIN_NORMALIZED:
    ; Map to sin table range [0, π/2]
    MOV P4, 0x1922         ; P4 = π/2
    CMP P2, P4
    JLT QSIN_FIRST_QUAD
    
    ; Handle other quadrants via symmetry
    SUB P2, P4
    CMP P2, P4
    JLT QSIN_SECOND_QUAD
    
    ; ... Continue with quadrant handling ...
    
QSIN_FIRST_QUAD:
    ; angle is in [0, π/2], lookup directly
    ; Map Q16 angle to table index (0-255)
    MOV R0, P2 >> 8        ; Rough index
    MOV P1, [0x1000 + R0]  ; Load table value
    
    ; Linear interpolation for finer accuracy
    ; ... interpolation code ...
    
    RET
```

---

## 6. Comparison: Nova-16 Options vs Other 16-bit Architectures

### 6.1 Similar Architectures

| Architecture | Approach | Performance | Standards |
|--------------|----------|-------------|-----------|
| **x86-16 (real mode)** | Hardware FPU (8087) | 5-50 cycles | IEEE 754 |
| **68000** | Hardware FPU (option) | 10-20 cycles | IEEE 754 |
| **MIPS-16e** | Software library | 50-200 cycles | IEEE 754 |
| **ARM Thumb** | Software library | 50-200 cycles | IEEE 754 |
| **Nova-16 (current)** | None | N/A | N/A |
| **Nova-16 (proposed-FP)** | Software lib (Q16) | 3-5 cycles | Fixed-point |

**Key insight**: Modern 16-bit embedded systems (ARM Cortex-M0) also use fixed-point for mathematics on resource-constrained hardware. IEEE 754 is overkill for embedded systems.

---

## 7. Recommendations by Use Case

### 7.1 Graphics & Game Development

**Verdict**: ✅ **Fixed-Point (Q16) - RECOMMENDED**

**Rationale**:
- 3D transformations need ~4-5 multiplications per vertex
- Fixed-point QMUL (10-15 cycles) much better than IEEE FMUL (300+ cycles)
- Precision (5 decimal digits) sufficient for pixel-level operations
- Memory bandwidth not impacted
- Lookup tables for sin/cos very efficient

**Example code**: 3D point transformation via QMAT3_XFORM

### 7.2 Physics Simulation

**Verdict**: ⚠️ **Fixed-Point (Q16) - ACCEPTABLE**

**Rationale**:
- Newton's equations don't require extreme precision
- Time stepping (dt = 0.016 for 60fps) well-represented in Q16
- Collisions, gravity calculations work fine with 5-digit precision

**When to use IEEE 754 instead**:
- Chaotic systems (sensitive to precision)
- Very long simulations (error accumulation)
- Small object interactions (near-zero denominators)

### 7.3 Sound Synthesis & DSP

**Verdict**: ✅ **Fixed-Point (Q8 or Q16) - EXCELLENT**

**Rationale**:
- Audio waveforms quantized to 16-bit samples anyway
- Q16 provides ample headroom for intermediate calculations
- Sine/cosine lookup tables naturally suited to Q format
- Filters (IIR, FIR) work perfectly with fixed-point

**Example**: Sine oscillator for audio synthesis
```asm
; Generate sine wave at frequency f over N samples
; Uses QSIN with Q16 phase accumulator
```

### 7.4 Scientific Computing

**Verdict**: ❌ **NOT RECOMMENDED** (Use floating-point language instead)

**Rationale**:
- Nova-16 not suitable for scientific computing
- Range limitations of Q16 problematic for physics constants
- Better to use Python/MATLAB + export results

**If must run on Nova-16**:
- Use software IEEE 754 emulation (very slow)
- Or run simplified algorithms with Q16 (acceptable approximations)

### 7.5 Financial Calculations

**Verdict**: ✅ **BCD Arithmetic - RECOMMENDED**

**Rationale**:
- Exact decimal representation required (no rounding errors)
- Nova-16 has native BCD support (D flag)
- Implement BADD, BSUB, BMUL, BDIV with D flag set

**Example code**:
```asm
; BCD Addition with D flag set
STI D                       ; Set decimal mode
ADD P0, P1                  ; Perform addition in BCD
; Result automatically in BCD format
```

---

## 8. Implementation Roadmap

### 8.1 Phase 1: Foundation (Week 1-2)

**Goals**: Establish fixed-point arithmetic library

**Tasks**:
1. ✅ Design Q16 format specification
2. ✅ Implement QADD, QSUB in assembly
3. ✅ Implement QMUL, QDIV with edge cases
4. ✅ Write unit tests for each operation
5. ✅ Document assembly-level API
6. ✅ Create example programs (test suite)

**Deliverables**:
- `qmath_lib.asm` - Core arithmetic (500 lines)
- `qmath_test.asm` - Test suite (300 lines)
- `QMATH_API.md` - Developer documentation
- Performance benchmarks

**Estimated effort**: 20-30 hours

### 8.2 Phase 2: Extended Functions (Week 3-4)

**Goals**: Add transcendental functions and utility routines

**Tasks**:
1. ✅ Build trigonometric lookup tables (1KB)
2. ✅ Implement QSIN, QCOS with interpolation
3. ✅ Implement QSQRT, QATAN2
4. ✅ Add conversion routines (QTOSTR, STRTOQ)
5. ✅ Create vector operation library
6. ✅ Comprehensive testing

**Deliverables**:
- `qmath_trig.asm` - Trig functions (400 lines)
- `qmath_convert.asm` - String conversions (200 lines)
- `qmath_vector.asm` - 2D vector ops (300 lines)
- Lookup table data files
- Example programs (sine wave, circle drawing)

**Estimated effort**: 40-60 hours

### 8.3 Phase 3: Graphics Integration (Week 5-6)

**Goals**: Integrate fixed-point math with graphics system

**Tasks**:
1. ✅ Implement 3×3 matrix multiplication (QMAT3_MULT)
2. ✅ Implement 3D point transformation (QMAT3_XFORM)
3. ✅ Build 3D line drawing (perspective projection)
4. ✅ Create demo programs (rotating 3D cube, landscape)
5. ✅ Performance profiling
6. ✅ Documentation with examples

**Deliverables**:
- `qmath_matrix.asm` - 3D transformations (500 lines)
- `qmath_3d.asm` - 3D graphics utilities (400 lines)
- `demo_rotating_cube.asm` - Example program (300 lines)
- `demo_landscape.asm` - Procedural terrain (400 lines)
- Performance analysis report

**Estimated effort**: 60-90 hours

### 8.4 Phase 4: Optional IEEE 754 (Week 7-8)

**Goals**: Add IEEE 754 emulation for interop (OPTIONAL)

**Tasks**:
1. ✅ Implement FADD, FSUB (shared mantissa logic)
2. ✅ Implement FMUL, FDIV
3. ✅ Implement FTOQ (IEEE to Q16), QTOIEEE (Q16 to IEEE)
4. ✅ Edge case handling (infinity, NaN, underflow)
5. ✅ Comprehensive testing against Python reference
6. ✅ Documentation

**Deliverables**:
- `ieee754_lib.asm` - IEEE 754 emulation (800 lines)
- `ieee754_test.asm` - Test suite (400 lines)
- Compatibility layer (FTOQ, QTOIEEE)
- Performance analysis

**Estimated effort**: 60-100 hours (only if needed)

**Decision**: Skip Phase 4 unless scientific computing is primary use case

### 8.5 Dependency Tree

```
Phase 1 (Foundation)
    ↓
Phase 2 (Extended)
    ↓
Phase 3 (Graphics) ← Ready for most applications
    ↓ (Optional)
Phase 4 (IEEE 754) ← Only if interop needed
```

---

## 9. Risk Analysis & Mitigation

### 9.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| **Precision loss in Q16** | Medium | Low | Use Q24 for critical calcs |
| **Overflow in QMUL** | Low | Medium | Check operands before multiply |
| **Sin/cos interpolation errors** | Low | Low | Use higher-resolution tables |
| **Performance bottleneck in loops** | Low | Medium | Profile & optimize hot paths |
| **Memory fragmentation** | Low | Low | Use static allocation |
| **Stack overflow** | Low | High | Monitor stack usage |

**Mitigation strategies**:
- Comprehensive unit tests for edge cases
- Profiling suite to measure performance
- Example programs demonstrating best practices
- Clear documentation of limitations

### 9.2 Adoption Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| **Developers unfamiliar with Q-format** | High | Medium | Excellent documentation + examples |
| **Preference for IEEE 754** | Medium | Low | Phase 4 IEEE emulation option |
| **Performance concerns** | Low | Medium | Benchmarks proving speed |
| **Floating-point dependency** | Low | High | Migration guide |

**Mitigation strategies**:
- Tutorial: "Introduction to Fixed-Point Math"
- Conversion tools: Python ↔ Q16 format
- Example programs for each use case
- Case studies of successful applications

---

## 10. Final Recommendations

### 10.1 Decision Matrix

| Approach | Cost | Benefit | Feasibility | Recommendation |
|----------|------|---------|-------------|-----------------|
| **Hardware FP** | Very High | Medium | Low | ❌ **DO NOT PURSUE** |
| **Software IEEE 754** | High | Low | Medium | ⚠️ **Optional Phase 4** |
| **Fixed-Point Q16** | Low | High | Very High | ✅ **STRONGLY RECOMMENDED** |
| **Hybrid (Q16 + IEEE)** | Medium | Very High | High | ✅ **BEST APPROACH** |

### 10.2 Recommended Implementation Plan

**Recommendation**: ✅ **Implement Phases 1-3 (Fixed-Point Math Library)**

**Rationale**:
1. **Low implementation cost** (60-90 hours) compared to hardware approach (40-80+ for design/validation)
2. **High benefit** for practical applications (graphics, games, embedded systems)
3. **Zero impact** on existing instruction set (uses new assembly routines, not new opcodes)
4. **Easy adoption** (library-based, backward compatible)
5. **Excellent performance** (no slow-down vs fixed-point algorithms)
6. **Extensible** (can add Phase 4 IEEE 754 if needed)

**Implementation approach**:
1. **Phase 1**: Core Q16 arithmetic (QADD, QSUB, QMUL, QDIV)
2. **Phase 2**: Trig functions + conversions (QSIN, QCOS, QTOSTR)
3. **Phase 3**: 3D graphics integration (QMAT3, demo programs)
4. **Defer Phase 4**: IEEE 754 only if/when scientific computing needed

**Success criteria**:
- ✅ All phases complete and tested
- ✅ Documentation with 5+ example programs
- ✅ Performance: <1% slowdown vs pure integer math
- ✅ Adoption: Used in at least 2 graphics/game demos

### 10.3 Optional Hardware Enhancement (Future)

If Nova-16 hardware is ever redesigned:

**Recommended FP hardware enhancement** (Lower priority):
- Add dedicated FPU would be 3x slower than integer, not worth the complexity
- Instead, recommend: **Dedicated multiplier (16×16 → 32-bit)** in hardware
  - Would accelerate QMUL from 10-15 cycles to 3-4 cycles
  - Minimal hardware (simple combinatorial logic)
  - Huge benefit for fixed-point and integer mathematics
  - Cost: ~10-20 additional gates

**Verdict**: ✅ Hardware multiplier > ✅ FPU in terms of benefit/cost ratio

---

## 11. Conclusion

**Question**: Is floating-point support feasible for Nova-16?

**Answer**: 

✅ **TECHNICALLY FEASIBLE** but ❌ **NOT RECOMMENDED** as native hardware instructions

✅ **STRONGLY RECOMMENDED INSTEAD**: Fixed-point (Q16) software library

**Key findings**:

1. **Hardware FP not practical**: Only 6 unused opcodes, would require register redesign
2. **IEEE 754 software emulation possible but slow**: 50-200x slower than hardware
3. **Fixed-point Q16 optimal**: Fast (integer speed), simple, practical for 95% of use cases
4. **Hybrid approach best**: Q16 for performance, optional IEEE 754 for interop

**Recommended path forward**:
- ✅ Implement Phase 1-3 (Fixed-Point Math Library) - 60-90 hours
- ✅ Ship with comprehensive documentation + examples
- ⚠️ Phase 4 (IEEE 754) only if/when scientific computing becomes priority
- 🚀 Use fixed-point for graphics, games, DSP, embedded systems
- ❌ Do NOT add hardware FP instructions

**Bottom line**: Nova-16 is better served with efficient **fixed-point mathematics** than complex floating-point hardware. This aligns with industry practice for embedded and real-time systems.

---

## References

- **IEEE 754-2019**: IEEE Standard for Floating-Point Arithmetic
- **Q Notation**: Wikipedia - Fixed-point arithmetic
- **ARM Cortex-M**: CMSIS-DSP library (uses fixed-point on M0/M3/M4)
- **MIPS**: Originally had no FPU (added as optional coprocessor)
- **x86**: Intel 8087 FPU (optional, later integrated)

---

**Document status**: Complete Feasibility Analysis
**Last updated**: 2025-12-19
**Confidence level**: High (comprehensive technical analysis)
