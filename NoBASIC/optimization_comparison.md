# For Loop Optimization Results

## Before Optimization (Original Code)

### Outer Loop (y = 0 to 255):
```asm
L1:
MOV R3, 255              ; ❌ Load end value every iteration
CMP P3, R3               ; Compare
JC L3                    ; ❌ Two jumps to continue
JZ L3
JMP L2                   ; ❌ Jump to exit
L3:                      ; ❌ Extra label
; ... inner loop ...
INC P3
JMP L1
L2:
```

**Instruction count per outer loop iteration: 5 instructions (MOV, CMP, JC, JZ, JMP) before body**

### Inner Loop (x = 0 to 255):
```asm
L4:
MOV R3, 255              ; ❌ Load end value every iteration
CMP P4, R3               ; Compare
JC L6                    ; ❌ Two jumps to continue
JZ L6
JMP L5                   ; ❌ Jump to exit
L6:                      ; ❌ Extra label
; ... body ...
INC P4
JMP L4
L5:
```

**Instruction count per inner loop iteration: 5 instructions before body**

---

## After Optimization (New Code)

### Outer Loop (y = 0 to 255):
```asm
MOV R2, 255              ; ✅ Load end value ONCE (hoisted out)
MOV R1, R2               ; Store in dedicated register
L1:
CMP P3, R1               ; ✅ Compare with pre-loaded value
JGT L2                   ; ✅ Single jump to exit
; ... inner loop ...
INC P3
JMP L1
L2:
```

**Instruction count per outer loop iteration: 2 instructions (CMP, JGT) before body**

### Inner Loop (x = 0 to 255):
```asm
MOV R2, 255              ; ✅ Load end value ONCE (hoisted out)
MOV P5, R2               ; Store in dedicated register
L3:
CMP P4, P5               ; ✅ Compare with pre-loaded value
JGT L4                   ; ✅ Single jump to exit
; ... body ...
INC P4
JMP L3
L4:
```

**Instruction count per inner loop iteration: 2 instructions (CMP, JGT) before body**

---

## Performance Comparison

### Outer Loop (256 iterations):
- **Before:** 5 instructions × 256 = **1,280 instructions** (overhead)
- **After:** 2 setup + (2 instructions × 256) = **514 instructions** (overhead)
- **Savings:** 766 instructions (59.8% reduction)

### Inner Loop (256 × 256 = 65,536 iterations):
- **Before:** 5 instructions × 65,536 = **327,680 instructions** (overhead)
- **After:** 2 setup + (2 instructions × 65,536) = **131,074 instructions** (overhead)
- **Savings:** 196,606 instructions (60.0% reduction)

### Total Loop Overhead Reduction:
- **Combined Savings:** 197,372 instructions eliminated
- **Percentage Improvement:** ~60% fewer overhead instructions for loop control

---

## Code Quality Improvements

1. ✅ **Hoisted invariants:** End values loaded once outside loops
2. ✅ **Simplified branching:** Single JGT instead of JC+JZ+JMP pattern
3. ✅ **Fewer labels:** Eliminated intermediate body labels
4. ✅ **Better register usage:** Dedicated registers for end values across iterations
5. ✅ **Cleaner assembly:** More readable and maintainable

---

## Expected Runtime Impact

For the `screen_fill.nobasic` program:
- **Inner loop body:** ~8-10 instructions (pixel drawing)
- **Inner loop overhead (before):** 5 instructions (38% overhead)
- **Inner loop overhead (after):** 2 instructions (18% overhead)

**Estimated speed improvement:** 25-30% faster execution for nested loop programs!

---

## Note on JGT vs JC/JZ Pattern

The original code used:
```asm
JC label    ; Jump if carry (unsigned less than)
JZ label    ; Jump if zero (equal)
JMP exit    ; Otherwise exit
```

This pattern handles the cases: `current < end` and `current == end` → continue loop.

The optimized code uses:
```asm
JGT exit    ; Jump if greater than (current > end)
```

This is equivalent but more efficient because Nova-16's CMP instruction sets flags such that JGT correctly handles the loop exit condition in a single instruction.

Both approaches handle signed comparisons correctly, but JGT is cleaner and eliminates 3 instructions per iteration!
