; Comprehensive test suite for ENTER, LEAVE, CALLZ, CALLNZ, RETN, LOOPZ, WHILE
; Tests stack frame management and control flow instructions

; Test 1: ENTER instruction - create stack frame
; Expected: SP decreased by (2 + frame_size), FP updated
TEST_ENTER:
    MOV P0, 16          ; Frame size = 16 bytes
    MOV P8, 0xFFF0     ; Set SP to known value
    MOV P9, 0x8000     ; Set FP to known value (will be pushed)
    
    ENTER P0            ; Create frame (push old FP, allocate locals)
    
    ; Verify: SP should be 0xFFF0 - 2 - 16 = 0xFFD8
    ; FP should be 0xFFF0 - 2 = 0xFFEE
    ; Old FP (0x8000) should be on stack at 0xFFEE
    
    ; Store results for verification
    MOV P1, P8          ; P1 = final SP
    MOV P2, P9          ; P2 = final FP
    
    ; Read old FP from stack
    MOV P3, P9
    READ P9             ; Read word at P9
    MOV P4, P9          ; P4 = old FP from stack
    
    HLT

; Test 2: LEAVE instruction - destroy stack frame
TEST_LEAVE:
    MOV P8, 0xFFF0     ; Set SP
    MOV P9, 0xFFEE     ; Set FP
    
    ; Put old FP on stack
    MOV P0, 0x8000     ; Old FP value
    WRITE P9            ; Write at FP address (will be restored)
    
    LEAVE               ; Restore FP, adjust SP
    
    ; Verify: SP should be 0xFFF0 (SP == FP)
    ; FP should be 0x8000 (restored from stack)
    
    MOV P1, P8          ; P1 = final SP
    MOV P2, P9          ; P2 = final FP
    
    HLT

; Test 3: CALLZ - call when zero flag is set
TEST_CALLZ_YES:
    MOV P0, 0           ; P0 = 0
    CMP P0, 0           ; Compare with 0 - sets Z flag
    
    ; PC should be here; SP should be initial 0xFFFF
    MOV P8, 0xFFFF      ; Store initial SP
    
    CALLZ SUBROUTINE_A  ; Call if Z (should call)
    
    ; If we get here, call worked and returned
    MOV P1, 0x0001      ; Mark success
    HLT

TEST_CALLZ_NO:
    MOV P0, 1           ; P0 = 1
    CMP P0, 0           ; Compare with 0 - clears Z flag
    
    CALLZ SUBROUTINE_B  ; Call if Z (should NOT call)
    
    ; Should jump directly here
    MOV P1, 0x0002      ; Mark that we skipped the call
    HLT

; Test 4: CALLNZ - call when zero flag is NOT set
TEST_CALLNZ_YES:
    MOV P0, 1           ; P0 = 1
    CMP P0, 0           ; Compare with 0 - clears Z flag
    
    CALLNZ SUBROUTINE_C ; Call if NZ (should call)
    
    ; If we get here, call worked and returned
    MOV P2, 0x0003      ; Mark success
    HLT

TEST_CALLNZ_NO:
    MOV P0, 0           ; P0 = 0
    CMP P0, 0           ; Compare with 0 - sets Z flag
    
    CALLNZ SUBROUTINE_D ; Call if NZ (should NOT call)
    
    ; Should jump directly here
    MOV P2, 0x0004      ; Mark that we skipped the call
    HLT

; Test 5: RETN - return with value
TEST_RETN:
    CALL SUBROUTINE_E   ; Call subroutine that uses RETN
    
    ; Should return here with R0 = 0x42
    MOV P3, R0          ; P3 = return value
    
    HLT

; Test 6: LOOPZ - loop while counter != 0 and Z flag set
TEST_LOOPZ:
    MOV P0, 5           ; Counter = 5
    MOV P1, 0           ; Accumulator = 0
    
LOOP_START:
    CMP P0, 0           ; Set Z flag based on P0
    ADD P1, 1           ; P1++
    LOOPZ P0, LOOP_START ; Decrement P0, loop if P0 != 0 and Z flag set
    
    ; After loop: P0 = 0, P1 = 5
    MOV P4, P0          ; P4 = final counter
    MOV P5, P1          ; P5 = final accumulator
    
    HLT

; Test 7: LOOPZ - should exit immediately if Z flag not set
TEST_LOOPZ_NO_Z:
    MOV P0, 5           ; Counter = 5
    MOV P1, 0           ; Accumulator = 0
    
    ; Don't set Z flag
    MOV P2, 1
    CMP P2, P0          ; P2 != P0, so Z flag is clear
    
LOOP_START_2:
    ADD P1, 1           ; P1++
    LOOPZ P0, LOOP_START_2 ; Should not loop (Z flag clear)
    
    ; After: P0 = 5 (unchanged), P1 = 1
    MOV P4, P0          ; P4 = final counter
    MOV P5, P1          ; P5 = final accumulator
    
    HLT

; Test 8: WHILE - basic condition check
TEST_WHILE:
    MOV P0, 5           ; Condition value
    MOV P1, 0           ; Accumulator
    
WHILE_START:
    WHILE P0            ; Check condition (sets flags based on P0)
    ADD P1, 1           ; P1++
    DEC P0              ; P0--
    CMP P0, 0           ; Check if P0 == 0
    JNZ WHILE_START     ; If not zero, loop back
    
    ; After: P0 = 0, P1 = 5
    MOV P6, P0          ; P6 = final condition
    MOV P7, P1          ; P7 = final accumulator
    
    HLT

; Subroutines
SUBROUTINE_A:
    MOV P0, 0xAAAA      ; Mark that subroutine was called
    RET

SUBROUTINE_B:
    MOV P0, 0xBBBB      ; Should not be called
    RET

SUBROUTINE_C:
    MOV P0, 0xCCCC      ; Mark that subroutine was called
    RET

SUBROUTINE_D:
    MOV P0, 0xDDDD      ; Should not be called
    RET

SUBROUTINE_E:
    MOV R0, 0x42        ; Return value = 0x42
    RETN R0             ; Return with value in R0

; Alternative: Test ENTER/LEAVE together
TEST_ENTER_LEAVE:
    MOV P0, 20          ; Frame size
    MOV P8, 0xFFE0      ; Initial SP
    MOV P9, 0x5000      ; Initial FP
    
    ENTER P0            ; Create frame
    
    ; Do some work with local variables
    MOV R0, 0x11        ; Use a local (on stack)
    
    LEAVE               ; Destroy frame
    
    ; Verify: SP and FP restored
    MOV PA, P8          ; PA = final SP
    MOV PB, P9          ; PB = final FP
    
    HLT

ORG 0x0000
