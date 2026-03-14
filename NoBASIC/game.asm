; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; Struct Player declared with fields: x, y, oldx, oldy, facing, counter
; Struct Enemy declared with fields: ex, ey, eoldx, eoldy, ecounter
MOV R1, 1
SHL R1, 3
; Store to player.x
MOV P0, 288
MOV P1, R1
MOV [P0], P1
MOV R1, 1
SHL R1, 3
; Store to player.y
MOV P0, 290
MOV P1, R1
MOV [P0], P1
MOV R1, 1
SHL R1, 3
; Store to player.oldx
MOV P0, 292
MOV P1, R1
MOV [P0], P1
MOV R1, 1
SHL R1, 3
; Store to player.oldy
MOV P0, 294
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to player.facing
MOV P0, 296
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to player.counter
MOV P0, 298
MOV P1, R1
MOV [P0], P1
MOV R1, 1
SHL R1, 7
; Store to Enemy.ex
MOV P0, 300
MOV P1, R1
MOV [P0], P1
MOV R1, 1
SHL R1, 7
; Store to Enemy.ey
MOV P0, 302
MOV P1, R1
MOV [P0], P1
MOV R1, 1
SHL R1, 7
; Store to Enemy.eoldx
MOV P0, 304
MOV P1, R1
MOV [P0], P1
MOV R1, 1
SHL R1, 7
; Store to Enemy.eoldy
MOV P0, 306
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to Enemy.eoldy
MOV P0, 306
MOV P1, R1
MOV [P0], P1
MOV P1, STR59
MOV P0, 310
MOV [P0], P1
MOV VM, 0
MOV VL, 1
XOR R1, R1
MOV P2, R1
MOV R1, 248
MOV R0, R1
MOV R1, 1
SHL R1, 2
MOV P3, R1
L61:
CMP P2, R0
JGT L62
XOR VX, VX
MOV VY, P2
MOV VC, 31
TEXT STR62
ADD P2, P3
JMP L61
L62:
XOR R0, R0
MOV R1, 1
SROT R0, R1
; Free R0 (last use)
; Free R1 (last use)
XOR R1, R1
MOV P2, R1
MOV R1, 248
MOV R0, R1
MOV R1, 1
SHL R1, 2
MOV P3, R1
L64:
CMP P2, R0
JGT L65
XOR VX, VX
MOV VY, P2
MOV VC, 31
TEXT STR62
ADD P2, P3
JMP L64
L65:
MOV VM, 0
MOV VL, 5
L66:
MOV R1, 1
WHILE R1
JZ L67
PUSH P2
CALL _func_callenemy_7
POP P2
PUSH P2
CALL _func_callplayer_6
POP P2
JMP L66
L67:
HLT

_func_renderplayer_0:
; Function: renderplayer
; Parameters: x, y, color
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV VX, :P1
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV VY, :P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV VC, :P1
TEXT STR0
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV VX, :P1
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, P1
MOV R4, 1
SHL R4, 3
MOV R1, R3
ADD R1, R4
; Free R4 (last use)
MOV VY, R1
MOV P0, FP
ADD P0, 4
MOV P2, [P0]
MOV VC, :P2
TEXT STR1
MOV SP, FP
POP FP
RETN 0

_func_renderenemy_1:
; Function: renderenemy
; Parameters: x, y, color
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV VX, :P1
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV VY, :P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV VC, :P1
TEXT STR2
MOV SP, FP
POP FP
RETN 0

_func_drawplayer_2:
; Function: drawplayer
; Parameters: 
; Locals:  (0 bytes)
ENTER 0
; Allocate struct player (Player) at 0x0120
; Load player.oldx
MOV P0, 292
MOV P1, [P0]
; Load player.x
MOV P0, 288
MOV P2, [P0]
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JZ L4
; Load player.oldx
MOV P0, 292
MOV P1, [P0]
PUSH P1
; Load player.oldy
MOV P0, 294
MOV P1, [P0]
PUSH P1
XOR R3, R3
MOV P1, R3
PUSH P1
; Free R3 (last use)
CALL _func_renderplayer_0
ADD SP, 6
L4:
; Load player.oldy
MOV P0, 294
MOV P1, [P0]
; Load player.y
MOV P0, 290
MOV P2, [P0]
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JZ L6
; Load player.oldx
MOV P0, 292
MOV P1, [P0]
PUSH P1
; Load player.oldy
MOV P0, 294
MOV P1, [P0]
PUSH P1
XOR R3, R3
MOV P1, R3
PUSH P1
; Free R3 (last use)
CALL _func_renderplayer_0
ADD SP, 6
L6:
; Load player.x
MOV P0, 288
MOV P1, [P0]
PUSH P1
; Load player.y
MOV P0, 290
MOV P1, [P0]
PUSH P1
MOV R3, 15
MOV P1, R3
PUSH P1
; Free R3 (last use)
CALL _func_renderplayer_0
ADD SP, 6
MOV SP, FP
POP FP
RETN 0

_func_drawenemy_3:
; Function: drawenemy
; Parameters: 
; Locals:  (0 bytes)
ENTER 0
; Allocate struct Enemy (Enemy) at 0x012C
; Load Enemy.eoldx
MOV P0, 304
MOV P1, [P0]
; Load Enemy.ex
MOV P0, 300
MOV P2, [P0]
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JZ L8
; Load Enemy.eoldx
MOV P0, 304
MOV P1, [P0]
PUSH P1
; Load Enemy.eoldy
MOV P0, 306
MOV P1, [P0]
PUSH P1
XOR R3, R3
MOV P1, R3
PUSH P1
; Free R3 (last use)
CALL _func_renderenemy_1
ADD SP, 6
L8:
; Load Enemy.eoldy
MOV P0, 306
MOV P1, [P0]
; Load Enemy.ey
MOV P0, 302
MOV P2, [P0]
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JZ L10
; Load Enemy.eoldx
MOV P0, 304
MOV P1, [P0]
PUSH P1
; Load Enemy.eoldy
MOV P0, 306
MOV P1, [P0]
PUSH P1
XOR R3, R3
MOV P1, R3
PUSH P1
; Free R3 (last use)
CALL _func_renderenemy_1
ADD SP, 6
L10:
; Load Enemy.ex
MOV P0, 300
MOV P1, [P0]
PUSH P1
; Load Enemy.ey
MOV P0, 302
MOV P1, [P0]
PUSH P1
MOV R3, 12
MOV P1, R3
PUSH P1
; Free R3 (last use)
CALL _func_renderenemy_1
ADD SP, 6
MOV SP, FP
POP FP
RETN 0

_func_attack_4:
; Function: attack
; Parameters: 
; Locals:  (0 bytes)
ENTER 0
; Load player.facing
MOV P0, 296
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L12
; Load player.x
MOV P0, 288
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 4
MOV R0, R2
SUB R0, R3
; Free R3 (last use)
MOV VX, R0
; Load player.y
MOV P0, 290
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
MOV P0, 310
MOV P0, [P0]
TEXT P0
L12:
; Load player.facing
MOV P0, 296
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L14
; Load player.x
MOV P0, 288
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R0, R2
ADD R0, R3
; Free R3 (last use)
MOV VX, R0
; Load player.y
MOV P0, 290
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
MOV P0, 310
MOV P0, [P0]
TEXT P0
L14:
XOR R1, R1
; Store to player.counter
MOV P0, 298
MOV P1, R1
MOV [P0], P1
MOV SP, FP
POP FP
RETN 0

_func_keycheck_5:
; Function: keycheck
; Parameters: 
; Locals:  (0 bytes)
ENTER 0
KEYIN R0
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P1, 312
MOV [P1], P0
MOV P0, 312
MOV P1, [P0]
MOV P2, 101
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L16
CALL _func_attack_4
L16:
MOV P0, 312
MOV P1, [P0]
MOV P2, 97
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L18
; Load player.x
MOV P0, 288
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to player.x
MOV P0, 288
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to player.facing
MOV P0, 296
MOV P1, R1
MOV [P0], P1
L18:
MOV P0, 312
MOV P1, [P0]
MOV P2, 1
SHL P2, 7
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L20
; Load player.x
MOV P0, 288
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to player.x
MOV P0, 288
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to player.facing
MOV P0, 296
MOV P1, R1
MOV [P0], P1
L20:
MOV P0, 312
MOV P1, [P0]
MOV P2, 100
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L22
; Load player.x
MOV P0, 288
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to player.x
MOV P0, 288
MOV P1, R1
MOV [P0], P1
MOV R1, 1
; Store to player.facing
MOV P0, 296
MOV P1, R1
MOV [P0], P1
L22:
MOV P0, 312
MOV P1, [P0]
MOV P2, 129
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L24
; Load player.x
MOV P0, 288
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to player.x
MOV P0, 288
MOV P1, R1
MOV [P0], P1
MOV R1, 1
; Store to player.facing
MOV P0, 296
MOV P1, R1
MOV [P0], P1
L24:
MOV P0, 312
MOV P1, [P0]
MOV P2, 115
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L26
; Load player.y
MOV P0, 290
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to player.y
MOV P0, 290
MOV P1, R1
MOV [P0], P1
L26:
MOV P0, 312
MOV P1, [P0]
MOV P2, 131
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L28
; Load player.y
MOV P0, 290
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to player.y
MOV P0, 290
MOV P1, R1
MOV [P0], P1
L28:
MOV P0, 312
MOV P1, [P0]
MOV P2, 119
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L30
; Load player.y
MOV P0, 290
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to player.y
MOV P0, 290
MOV P1, R1
MOV [P0], P1
L30:
MOV P0, 312
MOV P1, [P0]
MOV P2, 130
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L32
; Load player.y
MOV P0, 290
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to player.y
MOV P0, 290
MOV P1, R1
MOV [P0], P1
L32:
MOV SP, FP
POP FP
RETN 0

_func_callplayer_6:
; Function: callplayer
; Parameters: 
; Locals:  (0 bytes)
ENTER 0
; Load player.x
MOV P0, 288
MOV P1, [P0]
; Store to player.oldx
MOV P0, 292
MOV [P0], P1
; Load player.y
MOV P0, 290
MOV P1, [P0]
; Store to player.oldy
MOV P0, 294
MOV [P0], P1
; Load player.counter
MOV P0, 298
MOV P1, [P0]
MOV R0, P1
ADD P1, 1
; Store to player.counter
MOV P0, 298
MOV [P0], P1
CALL _func_keycheck_5
; Load player.x
MOV P0, 288
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L34
MOV R1, 1
SHL R1, 3
; Store to player.x
MOV P0, 288
MOV P1, R1
MOV [P0], P1
L34:
; Load player.x
MOV P0, 288
MOV P1, [P0]
MOV P2, 240
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L36
MOV R1, 240
; Store to player.x
MOV P0, 288
MOV P1, R1
MOV [P0], P1
L36:
; Load player.y
MOV P0, 290
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L38
MOV R1, 1
SHL R1, 3
; Store to player.y
MOV P0, 290
MOV P1, R1
MOV [P0], P1
L38:
; Load player.y
MOV P0, 290
MOV P1, [P0]
MOV P2, 232
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L40
MOV R1, 232
; Store to player.y
MOV P0, 290
MOV P1, R1
MOV [P0], P1
L40:
CALL _func_drawplayer_2
; Load player.counter
MOV P0, 298
MOV P1, [P0]
MOV P2, 255
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L42
XOR R1, R1
; Store to player.counter
MOV P0, 298
MOV P1, R1
MOV [P0], P1
; Load player.oldx
MOV P0, 292
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 4
MOV R0, R2
SUB R0, R3
; Free R3 (last use)
MOV VX, R0
; Load player.oldy
MOV P0, 294
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, P1
MOV R4, 1
SHL R4, 3
MOV R0, R3
ADD R0, R4
; Free R4 (last use)
MOV VY, R0
XOR VC, VC
MOV P0, 310
MOV P0, [P0]
TEXT P0
; Load player.oldx
MOV P0, 292
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R0, R2
ADD R0, R3
; Free R3 (last use)
MOV VX, R0
; Load player.oldy
MOV P0, 294
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, P1
MOV R4, 1
SHL R4, 3
MOV R0, R3
ADD R0, R4
; Free R4 (last use)
MOV VY, R0
XOR VC, VC
MOV P0, 310
MOV P0, [P0]
TEXT P0
L42:
MOV SP, FP
POP FP
RETN 0

_func_callenemy_7:
; Function: callenemy
; Parameters: 
; Locals:  (0 bytes)
ENTER 0
; Load Enemy.eoldy
MOV P0, 306
MOV P1, [P0]
MOV R0, P1
ADD P1, 1
; Store to Enemy.eoldy
MOV P0, 306
MOV [P0], P1
XOR R1, R1
; Store to Enemy.eoldy
MOV P0, 306
MOV P1, R1
MOV [P0], P1
; Load Enemy.ex
MOV P0, 300
MOV P1, [P0]
; Store to Enemy.eoldx
MOV P0, 304
MOV [P0], P1
; Load Enemy.ey
MOV P0, 302
MOV P1, [P0]
; Store to Enemy.eoldy
MOV P0, 306
MOV [P0], P1
XOR R0, R0
MOV R2, 3
RNDR R1, R0, R2
; Free R0 (last use)
; Free R2 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 314
MOV [P1], P0
MOV P0, 314
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L44
; Load Enemy.ex
MOV P0, 300
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to Enemy.ex
MOV P0, 300
MOV P1, R1
MOV [P0], P1
L44:
MOV P0, 314
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L46
; Load Enemy.ex
MOV P0, 300
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to Enemy.ex
MOV P0, 300
MOV P1, R1
MOV [P0], P1
L46:
MOV P0, 314
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L48
; Load Enemy.ey
MOV P0, 302
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to Enemy.ey
MOV P0, 302
MOV P1, R1
MOV [P0], P1
L48:
MOV P0, 314
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L50
; Load Enemy.ey
MOV P0, 302
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to Enemy.ey
MOV P0, 302
MOV P1, R1
MOV [P0], P1
L50:
; Load Enemy.ex
MOV P0, 300
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L52
MOV R1, 1
SHL R1, 3
; Store to Enemy.ex
MOV P0, 300
MOV P1, R1
MOV [P0], P1
L52:
; Load Enemy.ex
MOV P0, 300
MOV P1, [P0]
MOV P2, 240
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L54
MOV R1, 240
; Store to Enemy.ex
MOV P0, 300
MOV P1, R1
MOV [P0], P1
L54:
; Load Enemy.ey
MOV P0, 302
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L56
MOV R1, 1
SHL R1, 3
; Store to Enemy.ey
MOV P0, 302
MOV P1, R1
MOV [P0], P1
L56:
; Load Enemy.ey
MOV P0, 302
MOV P1, [P0]
MOV P2, 232
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L58
MOV R1, 232
; Store to Enemy.ey
MOV P0, 302
MOV P1, R1
MOV [P0], P1
L58:
CALL _func_drawenemy_3
MOV SP, FP
POP FP
RETN 0
STR0: DEFSTR "O"
STR1: DEFSTR "X"
STR2: DEFSTR "m"
STR59: DEFSTR "--"
STR62: DEFSTR "X                              X"