ORG 0x0200
MOV SP, 0xFFFF
MOV FP, SP
MOV VX, 0
MOV VY, 0
MOV VC, 15
TEXT STR0
MOV R0, 8192
MOV R2, 42
; MEMWRITE - Write to memory
MOV P1, R0
MOV [P1], R2
MOV P1, R2
; Free R2 (last use)
MOV P2, P1
MOV R2, 8192
; MEMREAD - Read from memory
MOV P1, R2
MOV R1, [P1]
; Free P1 (last use)
MOV P2, R1
MOV VX, 0
MOV VY, 0
MOV VC, 15
TEXT STR1
; SpriteOn - Enable and position sprite
XOR R3, R3
MOV R4, 100
MOV R5, 100
MOV P2, R3
SHL P2, P2
SHL P2, P2
SHL P2, P2
SHL P2, P2
MOV P3, 0xF000  ; Sprite memory base
ADD P2, P3  ; P2 = P2 + P3 (2-operand ADD)
MOV P3, P2
ADD P3, 2
MOV [P3], R4
MOV P3, P2
ADD P3, 3
MOV [P3], R5
MOV P3, P2
ADD P3, 6
MOV R4, [P3]  ; Read current flags
OR R4, 0x01  ; Set bit 0 (active)
MOV [P3], R4
; Free R3 (last use)
; Free R4 (last use)
; Free R5 (last use)
; SpriteOff - Disable sprite
XOR R3, R3
MOV P2, R3
SHL P2, P2
SHL P2, P2
SHL P2, P2
SHL P2, P2
MOV P3, 0xF000  ; Sprite memory base
ADD P2, P3  ; P2 = P2 + P3 (2-operand ADD)
ADD P2, 6  ; Point to flags byte
MOV R2, [P2]  ; Read current flags
AND R2, R2, 0xFE  ; Clear bit 0 (active)
MOV [P2], R2
; Free R3 (last use)
MOV VX, 0
MOV VY, 0
MOV VC, 15
TEXT STR2
L4:
KEYSTAT R0
CMP R0, 0
JZ L4
HLT
STR0: DEFSTR "Memory test"
STR1: DEFSTR "Sprite test"
STR2: DEFSTR "Done!"