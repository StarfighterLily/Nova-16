; Test LOOPZ - verify it doesn't loop when Z flag is clear

ORG 0x0000

    MOV P0, 5               ; Counter = 5
    MOV P1, 0               ; Accumulator = 0
    MOV P2, 1               ; Compare value
    MOV P3, loop_start      ; Address of loop
    
    ; Clear Z flag
    CMP P0, P2              ; 5 != 1
    
    ; Do one iteration
    ADD P1, 1               ; P1++
    
    ; LOOPZ should not jump
    LOOPZ P0, P3            ; Should not loop
    
    ; Continue here
    MOV P4, P0              ; P4 = counter (should be 5)
    MOV P5, P1              ; P5 = accumulator (should be 1)
    JMP done

loop_start:
    ADD P1, 1               ; Should not reach
    RET

done:
    HLT
