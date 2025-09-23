ORG 0x1000

; Initialize stack pointer
MOV P8,0xF000

; Set P0 = 10, P1 = 20
MOV P0,10
MOV P1,20

; Multiply P0 = P0 * P1 (should be 10 * 20 = 200)
MUL P0,P1

; Halt
HLT