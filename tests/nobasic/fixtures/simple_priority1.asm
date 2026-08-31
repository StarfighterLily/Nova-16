; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV VC, 15
MOV P7:, 0xFF
MOV VX, 0
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
TEXT STR0
ADD VY, 8
MOV R2, 42
MOV P1, 8192
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P1, 8192
MOV P2, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV VC, 15
MOV P2, R1
MOV VX, 0
TEXT STR1
ADD VY, 8
; SpriteOn - Enable and position sprite
XOR R1, R1
MOV P2, R1
MOV P3, 0
MOV R2, 100
SHL P2, P3
SHL P2, 1
SHL P2, 1
SHL P2, 1
MOV R3, 100
SHL P2, 1
ADD P2, P3 ; P2 = P2 + P3 (2-operand ADD)
MOV P3, 0xF000 ; Sprite memory base
MOV P3, P2
ADD P3, 2
MOV [P3], R2
MOV P3, P2
ADD P3, 3
MOV [P3], R3
MOV P3, P2
ADD P3, 6
MOV R4, [P3] ; Read current flags
OR R4, 0x01 ; Set bit 0 (active)
MOV [P3], R4
; Free R1 (last use)
; Free R2 (last use)
; Free R3 (last use)
; SpriteOff - Disable sprite
XOR R1, R1
MOV P2, R1
SHL P2, 1
SHL P2, 1
SHL P2, 1
SHL P2, 1
ADD P2, P3 ; P2 = P2 + P3 (2-operand ADD)
ADD P2, 6 ; Point to flags byte
MOV P3, 0xF000 ; Sprite memory base
MOV R2, [P2] ; Read current flags
AND R2, R2, 0xFE ; Clear bit 0 (active)
MOV [P2], R2
; Free R1 (last use)
MOV VC, 15
MOV VX, 0
TEXT STR2
ADD VY, 8
L4:
KEYSTAT R0
CMP R0, 0
JZ L4
HLT
STR0: DEFSTR "Memory test"
STR1: DEFSTR "Sprite test"
STR2: DEFSTR "Done!"