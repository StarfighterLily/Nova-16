; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
MOV VX, 0
MOV VC, 15
TEXT STR0
ADD VY, 8
MOV VX, 0
MOV VC, 15
TEXT STR1
ADD VY, 8
MOV P2, 8192
MOV P1, 8192
MOV R2, 42
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P3, R1
MOV P3, 8194
MOV P1, 8194
MOV R2, 100
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P4, R1
MOV P4, 8196
MOV P1, 8196
MOV R2, 255
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P5, R1
MOV VX, 0
MOV VC, 15
TEXT STR2
ADD VY, 8
MOV VX, 0
MOV VC, 15
TEXT STR3
ADD VY, 8
MOV P1, P2
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P5, R1
MOV P1, P3
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P2, R1
MOV P1, P4
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P2, R1
MOV VX, 0
MOV VC, 15
TEXT STR4
ADD VY, 8
MOV VX, 0
MOV VC, 15
TEXT STR5
ADD VY, 8
MOV P0, 61440
MOV P2, P0
MOV P1, 61440
MOV P0, 12288
; MEMWRITE - Write to memory
MOV [P1], P0
MOV R1, P0
; Free P1 (last use)
; Free P0 (last use)
MOV P3, R1
MOV P4, 61444
MOV P1, 61444
MOV R2, 1
SHL R2, 4
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P3, R1
MOV P4, 61445
MOV P1, 61445
MOV R2, 1
SHL R2, 4
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P3, R1
MOV P4, 61447
MOV P1, 61447
XOR R2, R2
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P3, R1
; SpriteOn - Enable and position sprite
XOR R1, R1
MOV R2, 50
MOV R3, 50
MOV P2, R1
MOV P3, 0
SHL P2, P3
SHL P2, 1
SHL P2, 1
SHL P2, 1
SHL P2, 1
MOV P3, 0xF000 ; Sprite memory base
ADD P2, P3 ; P2 = P2 + P3 (2-operand ADD)
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
MOV VX, 0
MOV VC, 15
TEXT STR6
ADD VY, 8
MOV R0, 6
; Preserve left operand in register across right-side evaluation
MOV R1, R0
ADD R1, P2
MOV P3, R1
MOV P1, P3
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P2, R1
MOV P2, 50
MOV R0, 100
L8:
CMP P2, R0
JGT L9
; SpriteOn - Enable and position sprite
XOR R1, R1
MOV R3, 50
MOV P2, R1
MOV P3, 0
SHL P2, P3
SHL P2, 1
SHL P2, 1
SHL P2, 1
SHL P2, 1
MOV P3, 0xF000 ; Sprite memory base
ADD P2, P3 ; P2 = P2 + P3 (2-operand ADD)
MOV P3, P2
ADD P3, 2
MOV [P3], P2
MOV P3, P2
ADD P3, 3
MOV [P3], R3
MOV P3, P2
ADD P3, 6
MOV R4, [P3] ; Read current flags
OR R4, 0x01 ; Set bit 0 (active)
MOV [P3], R4
; Free R1 (last use)
; Free R3 (last use)
INC P2
JMP L8
L9:
MOV VX, 0
MOV VC, 15
TEXT STR9
ADD VY, 8
; SpriteOff - Disable sprite
XOR R1, R1
MOV P2, R1
SHL P2, 1
SHL P2, 1
SHL P2, 1
SHL P2, 1
MOV P3, 0xF000 ; Sprite memory base
ADD P2, P3 ; P2 = P2 + P3 (2-operand ADD)
ADD P2, 6 ; Point to flags byte
MOV R2, [P2] ; Read current flags
AND R2, R2, 0xFE ; Clear bit 0 (active)
MOV [P2], R2
; Free R1 (last use)
MOV VX, 0
MOV VC, 15
TEXT STR10
ADD VY, 8
MOV P1, P3
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P2, R1
; SpriteOn - Enable and position sprite
MOV R1, 1
MOV R2, 100
MOV R3, 100
MOV P2, R1
MOV P3, 0
SHL P2, P3
SHL P2, 1
SHL P2, 1
SHL P2, 1
SHL P2, 1
MOV P3, 0xF000 ; Sprite memory base
ADD P2, P3 ; P2 = P2 + P3 (2-operand ADD)
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
; SpriteOn - Enable and position sprite
MOV R1, 1
SHL R1, 1
MOV R2, 150
MOV R3, 150
MOV P2, R1
MOV P3, 0
SHL P2, P3
SHL P2, 1
SHL P2, 1
SHL P2, 1
SHL P2, 1
MOV P3, 0xF000 ; Sprite memory base
ADD P2, P3 ; P2 = P2 + P3 (2-operand ADD)
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
; SpriteOn - Enable and position sprite
MOV R1, 3
MOV R2, 200
MOV R3, 200
MOV P2, R1
MOV P3, 0
SHL P2, P3
SHL P2, 1
SHL P2, 1
SHL P2, 1
SHL P2, 1
MOV P3, 0xF000 ; Sprite memory base
ADD P2, P3 ; P2 = P2 + P3 (2-operand ADD)
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
MOV VX, 0
MOV VC, 15
TEXT STR11
ADD VY, 8
; SpriteOff - Disable sprite
MOV P2, 1
SHL P2, 1
SHL P2, 1
SHL P2, 1
SHL P2, 1
MOV P3, 0xF000 ; Sprite memory base
ADD P2, P3 ; P2 = P2 + P3 (2-operand ADD)
ADD P2, 6 ; Point to flags byte
MOV R2, [P2] ; Read current flags
AND R2, R2, 0xFE ; Clear bit 0 (active)
MOV [P2], R2
; Free R1 (last use)
; SpriteOff - Disable sprite
MOV R1, 1
SHL R1, 1
MOV P2, R1
SHL P2, 1
SHL P2, 1
SHL P2, 1
SHL P2, 1
MOV P3, 0xF000 ; Sprite memory base
ADD P2, P3 ; P2 = P2 + P3 (2-operand ADD)
ADD P2, 6 ; Point to flags byte
MOV R2, [P2] ; Read current flags
AND R2, R2, 0xFE ; Clear bit 0 (active)
MOV [P2], R2
; Free R1 (last use)
; SpriteOff - Disable sprite
MOV P2, 3
SHL P2, 1
SHL P2, 1
SHL P2, 1
SHL P2, 1
MOV P3, 0xF000 ; Sprite memory base
ADD P2, P3 ; P2 = P2 + P3 (2-operand ADD)
ADD P2, 6 ; Point to flags byte
MOV R2, [P2] ; Read current flags
AND R2, R2, 0xFE ; Clear bit 0 (active)
MOV [P2], R2
; Free R1 (last use)
MOV VX, 0
MOV VC, 15
TEXT STR12
ADD VY, 8
L14:
KEYSTAT R0
CMP R0, 0
JZ L14
HLT
STR0: DEFSTR "Priority 1 Test"
STR1: DEFSTR "Testing MEMWRITE..."
STR2: DEFSTR "MEMWRITE done"
STR3: DEFSTR "Testing MEMREAD..."
STR4: DEFSTR "Values read:"
STR5: DEFSTR "Testing Sprites..."
STR6: DEFSTR "Sprite 0 enabled"
STR9: DEFSTR "Sprite moved"
STR10: DEFSTR "Sprite disabled"
STR11: DEFSTR "Multiple sprites"
STR12: DEFSTR "All tests complete!"