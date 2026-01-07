; Test loading 16-bit value into 8-bit register
ORG 0x0200

; Store 0x0F01 at address 0x0300
MOV P0, 0x0300
MOV P1, 0x0F01
MOV [P0], P1

; Load into 8-bit register
MOV P0, 0x0300
MOV R0, [P0]    ; Should get 0x01 (low byte) or 0x0F01?

; Draw pixel with that value
MOV VX, 100
MOV VY, 100
MOV VC, R0
SWRITE VC

HLT
