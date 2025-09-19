; Simple rotate test
MOV R0, 0xAAAA
MOV R1, 1
ROL R0, R1
; Expected: R0 = 0x5555

MOV R2, 0x5555
MOV R3, 2
ROR R2, R3
; Expected: R2 = 0x5555

HLT