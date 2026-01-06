; Test WHILE - basic condition check

ORG 0x0000

    MOV P0, 10              ; Loop counter
    MOV P1, 0               ; Accumulator
    MOV P2, loop_start      ; Address of loop

loop_start:
    ; Check condition
    WHILE P0                ; Set flags based on P0
    
    ; Do work
    ADD P1, 1               ; P1++
    
    ; Decrement
    DEC P0                  ; P0--
    
    ; Check if continue
    JNZ P2                  ; Jump if P0 != 0
    
    ; After: P0 = 0, P1 = 10
    MOV P3, P0              ; P3 = counter
    MOV P4, P1              ; P4 = accumulator
    
    HLT
