ORG 0x1000

; Initialize stack pointer
MOV P8,0xF000

; Set P0 = 20, P1 = 5
MOV P0,20
MOV P1,5

; Add P0 = P0 + P1 (should be 20 + 5 = 25)
ADD P0,P1

; Halt
HLT