; Cache benchmark program
ORG 0x0000

MAIN:
    MOV R0, 0       ; Initialize counter
    MOV R1, 1       ; Constant 1
    
LOOP:
    ADD R0, R1      ; Increment counter
    SUB R0, R1      ; Decrement counter
    AND R0, R1      ; Bitwise AND
    OR R0, R1       ; Bitwise OR
    XOR R0, R1      ; Bitwise XOR
    MOV [0x2000], R0 ; Memory write
    MOV R2, [0x2000] ; Memory read
    JMP LOOP        ; Loop back (sequential)

    HLT             ; Should not reach here