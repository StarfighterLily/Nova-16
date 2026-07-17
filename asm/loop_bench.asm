; Simple loop benchmark for cache optimization
ORG 0x0000

    MOV R0, 0       ; Initialize counter
    MOV R1, 1      ; Constant 1

LOOP:
    ADD R0, R1     ; R0 += 1
    SUB R0, R1     ; R0 -= 1
    AND R0, R1     ; R0 &= 1
    OR R0, R1      ; R0 |= 1
    XOR R0, R1     ; R0 ^= 1
    MOV [0x2000], R0 ; Memory write
    MOV R2, [0x2000] ; Memory read
    JMP LOOP       ; Jump back to create loop

    HLT            ; Should never reach here