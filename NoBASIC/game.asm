; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; Struct Player declared with fields: x, y, oldx, oldy, facing, counter
MOV VM, 0
MOV VL, 1
XOR VX, VX
XOR VY, VY
MOV VC, 31
TEXT STR47
XOR R2, R2
MOV P2, R2
MOV R2, 240
MOV R0, R2
MOV R2, 1
SHL R2, 3
MOV R1, R2
L49:
CMP P2, R0
JGT L50
XOR VX, VX
MOV VY, P2
MOV VC, 31
TEXT STR50
ADD P2, R1
JMP L49
L50:
XOR VX, VX
MOV VY, 248
MOV VC, 31
TEXT STR47
MOV R1, 1
SHL R1, 3
; Allocate struct player (Player) at 0x0122
; Store to player.x
MOV P0, 290
MOV P1, R1
MOV [P0], P1
MOV R1, 1
SHL R1, 3
; Store to player.y
MOV P0, 292
MOV P1, R1
MOV [P0], P1
MOV R1, 1
SHL R1, 3
; Store to player.oldx
MOV P0, 294
MOV P1, R1
MOV [P0], P1
MOV R1, 1
SHL R1, 3
; Store to player.oldy
MOV P0, 296
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to player.facing
MOV P0, 298
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to player.counter
MOV P0, 300
MOV P1, R1
MOV [P0], P1
MOV R1, 1
SHL R1, 3
MOV P3, R1
MOV VM, 0
MOV VL, 5
L52:
MOV R1, 1
WHILE R1
JZ L53
; Load player.x
MOV P0, 290
MOV P1, [P0]
; Store to player.oldx
MOV P0, 294
MOV [P0], P1
; Load player.y
MOV P0, 292
MOV P1, [P0]
; Store to player.oldy
MOV P0, 296
MOV [P0], P1
; Load player.counter
MOV P0, 300
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to player.counter
MOV P0, 300
MOV P1, R1
MOV [P0], P1
KEYIN R0
MOV R1, R0
MOV P4, R1
; Load player.x
MOV P0, 290
MOV P1, [P0]
MOV P3, P1
PUSH P2
PUSH P3
PUSH P4
PUSH P4
; Load player.facing
MOV P0, 298
MOV P1, [P0]
PUSH P1
; Load player.y
MOV P0, 292
MOV P1, [P0]
PUSH P1
CALL _func_attackifpressed_2
ADD SP, 6
POP P4
POP P3
POP P2
MOV R1, R0
MOV P3, R1
WHILE P3
JZ L54
XOR R1, R1
; Store to player.counter
MOV P0, 300
MOV P1, R1
MOV [P0], P1
L54:
PUSH P2
PUSH P3
PUSH P4
PUSH P4
; Load player.x
MOV P0, 290
MOV P1, [P0]
PUSH P1
CALL _func_movexbykey_3
ADD SP, 4
POP P4
POP P3
POP P2
MOV R1, R0
; Store to player.x
MOV P0, 290
MOV P1, R1
MOV [P0], P1
PUSH P2
PUSH P3
PUSH P4
PUSH P4
; Load player.y
MOV P0, 292
MOV P1, [P0]
PUSH P1
CALL _func_moveybykey_4
ADD SP, 4
POP P4
POP P3
POP P2
MOV R1, R0
; Store to player.y
MOV P0, 292
MOV P1, R1
MOV [P0], P1
PUSH P2
PUSH P3
PUSH P4
PUSH P4
; Load player.facing
MOV P0, 298
MOV P1, [P0]
PUSH P1
CALL _func_facingbykey_5
ADD SP, 4
POP P4
POP P3
POP P2
MOV R1, R0
; Store to player.facing
MOV P0, 298
MOV P1, R1
MOV [P0], P1
PUSH P2
PUSH P3
PUSH P4
; Load player.x
MOV P0, 290
MOV P1, [P0]
PUSH P1
CALL _func_clampx_6
ADD SP, 2
POP P4
POP P3
POP P2
MOV R1, R0
; Store to player.x
MOV P0, 290
MOV P1, R1
MOV [P0], P1
PUSH P2
PUSH P3
PUSH P4
; Load player.y
MOV P0, 292
MOV P1, [P0]
PUSH P1
CALL _func_clampy_7
ADD SP, 2
POP P4
POP P3
POP P2
MOV R1, R0
; Store to player.y
MOV P0, 292
MOV P1, R1
MOV [P0], P1
; Load player.oldx
MOV P0, 294
MOV P1, [P0]
; Load player.x
MOV P0, 290
MOV P5, [P0]
CMP P1, P5
; Free P1 (last use)
JZ L56
PUSH P2
PUSH P3
PUSH P4
; Load player.oldx
MOV P0, 294
MOV P1, [P0]
PUSH P1
; Load player.oldy
MOV P0, 296
MOV P1, [P0]
PUSH P1
CALL _func_clearplayerat_0
ADD SP, 4
POP P4
POP P3
POP P2
L56:
; Load player.oldy
MOV P0, 296
MOV P1, [P0]
; Load player.y
MOV P0, 292
MOV P5, [P0]
CMP P1, P5
; Free P1 (last use)
JZ L58
PUSH P2
PUSH P3
PUSH P4
; Load player.oldx
MOV P0, 294
MOV P1, [P0]
PUSH P1
; Load player.oldy
MOV P0, 296
MOV P1, [P0]
PUSH P1
CALL _func_clearplayerat_0
ADD SP, 4
POP P4
POP P3
POP P2
L58:
PUSH P2
PUSH P3
PUSH P4
; Load player.x
MOV P0, 290
MOV P1, [P0]
PUSH P1
; Load player.y
MOV P0, 292
MOV P1, [P0]
PUSH P1
CALL _func_drawplayerat_1
ADD SP, 4
POP P4
POP P3
POP P2
PUSH P2
PUSH P3
PUSH P4
; Load player.counter
MOV P0, 300
MOV P1, [P0]
PUSH P1
; Load player.oldx
MOV P0, 294
MOV P1, [P0]
PUSH P1
; Load player.oldy
MOV P0, 296
MOV P1, [P0]
PUSH P1
CALL _func_clearattackontimeout_8
ADD SP, 6
POP P4
POP P3
POP P2
MOV R1, R0
; Store to player.counter
MOV P0, 300
MOV P1, R1
MOV [P0], P1
JMP L52
L53:
HLT

_func_clearplayerat_0:
; Function: clearplayerat
; Parameters: x, y
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV VX, :P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV VY, :P1
XOR VC, VC
TEXT STR0
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV VX, :P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, P1
MOV R4, 1
SHL R4, 3
MOV R1, R3
ADD R1, R4
; Free R4 (last use)
MOV VY, R1
XOR VC, VC
TEXT STR1
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 4
MOV R0, R2
SUB R0, R3
; Free R3 (last use)
MOV VX, R0
MOV P0, FP
ADD P0, 4
MOV R3, [P0]
; Preserve left operand in register across right-side evaluation
MOV R4, R3
MOV R5, 1
SHL R5, 3
MOV R0, R4
ADD R0, R5
; Free R5 (last use)
MOV VY, R0
XOR VC, VC
TEXT STR2
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R0, R2
ADD R0, R3
; Free R3 (last use)
MOV VX, R0
MOV P0, FP
ADD P0, 4
MOV R3, [P0]
; Preserve left operand in register across right-side evaluation
MOV R4, R3
MOV R5, 1
SHL R5, 3
MOV R0, R4
ADD R0, R5
; Free R5 (last use)
MOV VY, R0
XOR VC, VC
TEXT STR2
MOV SP, FP
POP FP
RETN 0

_func_drawplayerat_1:
; Function: drawplayerat
; Parameters: x, y
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV VX, :P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV VY, :P1
MOV VC, 15
TEXT STR0
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV VX, :P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, P1
MOV R4, 1
SHL R4, 3
MOV R1, R3
ADD R1, R4
; Free R4 (last use)
MOV VY, R1
MOV VC, 15
TEXT STR1
MOV SP, FP
POP FP
RETN 0

_func_attackifpressed_2:
; Function: attackifpressed
; Parameters: key, facing, y
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV P2, 101
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L4
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L6
MOV P0, 288
MOV P1, [P0]
MOV P2, 1
SHL P2, 4
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLT L8
MOV P0, 288
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
SHL R3, 4
MOV R0, R2
SUB R0, R3
; Free R3 (last use)
MOV VX, R0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, P1
MOV R4, 1
SHL R4, 3
MOV R0, R3
ADD R0, R4
; Free R4 (last use)
MOV VY, R0
MOV VC, 15
TEXT STR2
L8:
L6:
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L10
MOV P0, 288
MOV P1, [P0]
MOV P2, 232
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGT L12
MOV P0, 288
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
SHL R3, 3
MOV R0, R2
ADD R0, R3
; Free R3 (last use)
MOV VX, R0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, P1
MOV R4, 1
SHL R4, 3
MOV R0, R3
ADD R0, R4
; Free R4 (last use)
MOV VY, R0
MOV VC, 15
TEXT STR2
L12:
L10:
MOV R0, 1
MOV SP, FP
POP FP
RETN R0
L4:
XOR R0, R0
MOV SP, FP
POP FP
RETN R0

_func_movexbykey_3:
; Function: movexbykey
; Parameters: key, x
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 97
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L14
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R0, R2
SUB R0, R3
; Free R3 (last use)
MOV SP, FP
POP FP
RETN R0
L14:
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 1
SHL P2, 7
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L16
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R0, R2
SUB R0, R3
; Free R3 (last use)
MOV SP, FP
POP FP
RETN R0
L16:
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 100
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L18
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R0, R2
ADD R0, R3
; Free R3 (last use)
MOV SP, FP
POP FP
RETN R0
L18:
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 129
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L20
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R0, R2
ADD R0, R3
; Free R3 (last use)
MOV SP, FP
POP FP
RETN R0
L20:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV SP, FP
POP FP
RETN P1

_func_moveybykey_4:
; Function: moveybykey
; Parameters: key, y
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 115
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L22
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R0, R2
ADD R0, R3
; Free R3 (last use)
MOV SP, FP
POP FP
RETN R0
L22:
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 131
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L24
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R0, R2
ADD R0, R3
; Free R3 (last use)
MOV SP, FP
POP FP
RETN R0
L24:
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 119
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L26
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R0, R2
SUB R0, R3
; Free R3 (last use)
MOV SP, FP
POP FP
RETN R0
L26:
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 130
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L28
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R0, R2
SUB R0, R3
; Free R3 (last use)
MOV SP, FP
POP FP
RETN R0
L28:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV SP, FP
POP FP
RETN P1

_func_facingbykey_5:
; Function: facingbykey
; Parameters: key, facing
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 97
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L30
XOR R0, R0
MOV SP, FP
POP FP
RETN R0
L30:
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 1
SHL P2, 7
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L32
XOR R0, R0
MOV SP, FP
POP FP
RETN R0
L32:
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 100
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L34
MOV R0, 1
MOV SP, FP
POP FP
RETN R0
L34:
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 129
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L36
MOV R0, 1
MOV SP, FP
POP FP
RETN R0
L36:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV SP, FP
POP FP
RETN P1

_func_clampx_6:
; Function: clampx
; Parameters: x
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L38
MOV R0, 1
SHL R0, 3
MOV SP, FP
POP FP
RETN R0
L38:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 240
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L40
MOV R0, 240
MOV SP, FP
POP FP
RETN R0
L40:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV SP, FP
POP FP
RETN P1

_func_clampy_7:
; Function: clampy
; Parameters: y
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L42
MOV R0, 1
SHL R0, 3
MOV SP, FP
POP FP
RETN R0
L42:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 232
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L44
MOV R0, 232
MOV SP, FP
POP FP
RETN R0
L44:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV SP, FP
POP FP
RETN P1

_func_clearattackontimeout_8:
; Function: clearattackontimeout
; Parameters: counter, oldx, oldy
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV P2, 255
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L46
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 4
MOV R0, R2
SUB R0, R3
; Free R3 (last use)
MOV VX, R0
MOV P0, FP
ADD P0, 4
MOV R3, [P0]
; Preserve left operand in register across right-side evaluation
MOV R4, R3
MOV R5, 1
SHL R5, 3
MOV R0, R4
ADD R0, R5
; Free R5 (last use)
MOV VY, R0
XOR VC, VC
TEXT STR2
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R0, R2
ADD R0, R3
; Free R3 (last use)
MOV VX, R0
MOV P0, FP
ADD P0, 4
MOV R3, [P0]
; Preserve left operand in register across right-side evaluation
MOV R4, R3
MOV R5, 1
SHL R5, 3
MOV R0, R4
ADD R0, R5
; Free R5 (last use)
MOV VY, R0
XOR VC, VC
TEXT STR2
XOR R0, R0
MOV SP, FP
POP FP
RETN R0
L46:
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV SP, FP
POP FP
RETN P1
STR0: DEFSTR "O"
STR1: DEFSTR "X"
STR2: DEFSTR "--"
STR47: DEFSTR "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
STR50: DEFSTR "X                              X"