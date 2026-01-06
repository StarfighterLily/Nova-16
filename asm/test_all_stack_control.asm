; Comprehensive integrated test of all stack/control flow instructions
; This test covers edge cases and interactions

ORG 0x0000

; Test counters and markers
    MOV P0, 0               ; Test counter
    MOV P1, 0               ; Success marker

; ==================== TEST 1: ENTER/LEAVE PAIR ====================
test_enter_leave:
    MOV P0, 1               ; Test 1
    
    ; Setup initial stack state
    MOV P8, 0xFF00          ; SP
    MOV P9, 0x5000          ; FP
    
    ; Create frame with 32 bytes of locals
    ENTER 32                ; Enter subroutine
    
    ; Verify frame created
    ; SP should be 0xFF00 - 2 - 32 = 0xFECE
    ; FP should be 0xFF00 - 2 = 0xFEFE
    MOV PA, P8              ; PA = current SP
    MOV PB, P9              ; PB = current FP
    
    ; Now leave the frame
    LEAVE                   ; Exit subroutine
    
    ; Verify restoration
    ; SP should be 0xFEFE (back to post-push position)
    ; FP should be 0x5000 (restored from stack)
    MOV PC, P8              ; PC = restored SP
    MOV PD, P9              ; PD = restored FP
    
    ; Check results
    CMP PA, 0xFECE          ; Check SP was decremented correctly
    JZ test_callz_yes       ; Pass to next test
    MOV P1, 0x0001          ; Mark ENTER failure
    JMP end_tests

; ==================== TEST 2: CALLZ WHEN ZERO ====================
test_callz_yes:
    MOV P0, 2               ; Test 2
    
    ; Set zero flag
    MOV P2, 0
    CMP P2, P2              ; 0 == 0, sets Z flag
    
    ; Call should execute
    CALLZ callz_sub         ; Call if Z flag set
    
    ; Verify call executed
    CMP P3, 0x1111
    JZ test_callz_no
    MOV P1, 0x0002          ; Mark CALLZ yes failure
    JMP end_tests

callz_sub:
    MOV P3, 0x1111          ; Mark that call was executed
    RET

; ==================== TEST 3: CALLZ WHEN NOT ZERO ====================
test_callz_no:
    MOV P0, 3               ; Test 3
    
    ; Clear zero flag
    MOV P2, 1
    CMP P2, 0               ; 1 != 0, clears Z flag
    
    ; Call should NOT execute
    CALLZ no_callz_sub      ; Call if Z (should skip)
    
    ; Verify we skipped the call
    MOV P3, 0x2222
    
    ; Continue to next test
    JMP test_callnz_yes

no_callz_sub:
    MOV P3, 0xDEAD          ; Should not reach here
    RET

; ==================== TEST 4: CALLNZ WHEN NOT ZERO ====================
test_callnz_yes:
    MOV P0, 4               ; Test 4
    
    ; Clear zero flag
    MOV P2, 1
    CMP P2, 0               ; 1 != 0, clears Z flag
    
    ; Call should execute
    CALLNZ callnz_sub       ; Call if NZ flag
    
    ; Verify call executed
    CMP P3, 0x3333
    JZ test_callnz_no
    MOV P1, 0x0004          ; Mark CALLNZ yes failure
    JMP end_tests

callnz_sub:
    MOV P3, 0x3333          ; Mark that call was executed
    RET

; ==================== TEST 5: CALLNZ WHEN ZERO ====================
test_callnz_no:
    MOV P0, 5               ; Test 5
    
    ; Set zero flag
    MOV P2, 0
    CMP P2, P2              ; 0 == 0, sets Z flag
    
    ; Call should NOT execute
    CALLNZ no_callnz_sub    ; Call if NZ (should skip)
    
    ; Verify we skipped the call
    MOV P3, 0x4444
    
    ; Continue to next test
    JMP test_retn

no_callnz_sub:
    MOV P3, 0xCAFE          ; Should not reach here
    RET

; ==================== TEST 6: RETN ====================
test_retn:
    MOV P0, 6               ; Test 6
    
    ; Call subroutine that returns with value
    CALL retn_sub
    
    ; R0 should contain return value
    MOV P3, R0              ; P3 = return value
    CMP R0, 0x77
    JZ test_loopz
    MOV P1, 0x0006          ; Mark RETN failure
    JMP end_tests

retn_sub:
    MOV R0, 0x77            ; Set return value
    RETN R0                 ; Return with value

; ==================== TEST 7: LOOPZ ====================
test_loopz:
    MOV P0, 7               ; Test 7
    
    MOV P4, 10              ; Counter = 10
    MOV P5, 0               ; Accumulator = 0

loopz_start:
    ; Set Z flag for LOOPZ to work
    CMP P4, P4              ; Always true
    
    ; Do work
    ADD P5, 1               ; P5++
    
    ; Loop
    LOOPZ P4, loopz_start   ; Decrement P4, loop if P4 != 0 and Z set
    
    ; Verify results
    CMP P4, 0               ; Counter should be 0
    JNZ loopz_fail
    CMP P5, 10              ; Accumulator should be 10
    JZ test_while
    
loopz_fail:
    MOV P1, 0x0007          ; Mark LOOPZ failure
    JMP end_tests

; ==================== TEST 8: WHILE ====================
test_while:
    MOV P0, 8               ; Test 8
    
    MOV P6, 5               ; Loop counter
    MOV P7, 0               ; Accumulator = 0

while_start:
    ; Check condition
    WHILE P6                ; Sets flags based on P6
    
    ; Loop body
    ADD P7, 1               ; P7++
    DEC P6                  ; P6--
    
    ; Check if should continue
    JNZ while_start         ; Jump if P6 != 0
    
    ; Verify results
    CMP P6, 0               ; Counter should be 0
    JNZ while_fail
    CMP P7, 5               ; Accumulator should be 5
    JZ test_success
    
while_fail:
    MOV P1, 0x0008          ; Mark WHILE failure
    JMP end_tests

; ==================== SUCCESS ====================
test_success:
    MOV P1, 0xFFFF          ; Mark all tests passed
    
end_tests:
    HLT
