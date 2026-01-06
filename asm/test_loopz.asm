; Test LOOPZ - loop while counter != 0 and Z flag set

ORG 0x0000

    MOV P0, 5               ; Counter = 5
    MOV P1, 0               ; Accumulator = 0
    MOV P2, loop_start      ; Address of loop start

loop_start:
    ; Set Z flag
    CMP P0, P0              ; Always true
    
    ; Do work
    ADD P1, 1               ; P1++
    
    ; Loop
    LOOPZ P0, P2            ; Decrement P0, loop if P0 != 0 and Z set
    
    ; After: P0 = 0, P1 = 5
    MOV P3, P0              ; P3 = counter
    MOV P4, P1              ; P4 = accumulator
    
    HLT
