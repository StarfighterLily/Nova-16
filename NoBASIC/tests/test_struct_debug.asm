; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; Struct Player declared with fields: x, y, facing
MOV R1, 1
SHL R1, 3
; Allocate struct player (Player) at 0x0120
; Store to player.x
MOV P1, R1
MOV P0, 288
MOV [P0], P1
MOV R1, 1
SHL R1, 3
; Store to player.y
MOV P1, R1
MOV P0, 290
MOV [P0], P1
XOR R1, R1
; Store to player.facing
MOV P1, R1
MOV P0, 292
MOV [P0], P1
XOR VX, VX
XOR VY, VY
MOV VC, 31
TEXT STR0
XOR VY, VY
MOV VC, 31
MOV VX, 80
; Load player.x
MOV P0, 288
MOV P1, [P0]
ITOS P1, R0
MOV R0, P1
TEXT P1
XOR VX, VX
MOV VY, 1
SHL VY, 4
MOV VC, 31
TEXT STR1
MOV VY, 1
MOV VC, 31
SHL VY, 4
MOV VX, 80
; Load player.y
MOV P0, 290
MOV P1, [P0]
ITOS P1, R0
MOV R0, P1
TEXT P1
XOR VX, VX
MOV VY, 1
SHL VY, 5
MOV VC, 31
TEXT STR2
MOV VY, 1
MOV VC, 31
SHL VY, 5
MOV VX, 80
; Load player.facing
MOV P0, 292
MOV P1, [P0]
ITOS P1, R0
MOV R0, P1
TEXT P1
L4:
KEYSTAT R0
CMP R0, 0
JZ L4
MOV R1, 1
SHL R1, 4
; Store to player.x
MOV P1, R1
MOV P0, 288
MOV [P0], P1
MOV R1, 24
; Store to player.y
MOV P1, R1
MOV P0, 290
MOV [P0], P1
XOR VX, VX
MOV VC, 31
MOV VY, 48
TEXT STR4
XOR VX, VX
MOV VY, 1
SHL VY, 6
MOV VC, 31
TEXT STR5
MOV VX, 1
SHL VX, 5
MOV VY, 1
SHL VY, 6
MOV VC, 31
; Load player.x
MOV P0, 288
MOV P1, [P0]
ITOS P1, R0
MOV R0, P1
TEXT P1
XOR VX, VX
MOV VC, 31
MOV VY, 80
TEXT STR6
MOV VX, 1
SHL VX, 5
MOV VC, 31
MOV VY, 80
; Load player.y
MOV P0, 290
MOV P1, [P0]
ITOS P1, R0
MOV R0, P1
TEXT P1
L8:
KEYSTAT R0
CMP R0, 0
JZ L8
L9:
MOV R1, 1
WHILE R1
JZ L10
KEYIN R0
MOV R1, R0
MOV P3, R1
MOV R0, 100
MOV P1, P3
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JNZ L11
; Load player.x
MOV P0, 288
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, 1
MOV R2, P1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to player.x
MOV P1, R1
MOV P0, 288
MOV [P0], P1
L11:
MOV R0, 97
MOV P1, P3
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JNZ L13
; Load player.x
MOV P0, 288
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, 1
MOV R2, P1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to player.x
MOV P1, R1
MOV P0, 288
MOV [P0], P1
L13:
XOR VX, VX
MOV VC, 31
MOV VY, 100
TEXT STR14
MOV VX, 1
SHL VX, 6
MOV VC, 31
MOV VY, 100
; Load player.x
MOV P0, 288
MOV P1, [P0]
ITOS P1, R0
MOV R0, P1
TEXT P1
XOR VX, VX
MOV VC, 31
MOV VY, 116
TEXT STR15
ITOS P1, R0
MOV VY, 116
MOV VC, 31
MOV R0, P3
MOV VX, 48
TEXT P1
JMP L9
L10:
HLT
STR0: DEFSTR "Player X:"
STR1: DEFSTR "Player Y:"
STR2: DEFSTR "Facing:"
STR4: DEFSTR "After change:"
STR5: DEFSTR "X:"
STR6: DEFSTR "Y:"
STR14: DEFSTR "Loop X:"
STR15: DEFSTR "Key:"