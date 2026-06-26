; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; Struct Player declared with fields: x, y, oldx, oldy, facing, counter
; Struct Enemy declared with fields: ex, ey, eoldx, eoldy, ecounter, ehit
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
; Store to enemy.ex
MOV P0, 300
MOV P1, R1
MOV [P0], P1
MOV R1, 1
SHL R1, 7
; Store to enemy.ey
MOV P0, 302
MOV P1, R1
MOV [P0], P1
MOV R1, 1
SHL R1, 7
; Store to enemy.eoldx
MOV P0, 304
MOV P1, R1
MOV [P0], P1
MOV R1, 1
SHL R1, 7
; Store to enemy.eoldy
MOV P0, 306
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to enemy.ecounter
MOV P0, 308
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to enemy.ehit
MOV P0, 310
MOV P1, R1
MOV [P0], P1
MOV P1, STR80
MOV P0, 312
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
L82:
CMP P2, R0
JGT L83
XOR VX, VX
MOV VY, P2
MOV VC, 31
TEXT STR83
ADD P2, P3
JMP L82
L83:
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
L85:
CMP P2, R0
JGT L86
XOR VX, VX
MOV VY, P2
MOV VC, 31
TEXT STR83
ADD P2, P3
JMP L85
L86:
MOV VM, 0
MOV VL, 5
L87:
; Load enemy.ehit
MOV P0, 310
MOV P1, [P0]
MOV R0, 1
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JZ L88
PUSH P2
PUSH P4
CALL _func_callenemy_8
POP P4
POP P2
PUSH P2
PUSH P4
CALL _func_callplayer_7
POP P4
POP P2
JMP L87
L88:
MOV VM, 0
MOV VL, 1
; ClrDraw
MOV VM, 0
MOV VL, 1
SFILL 0x00
MOV VM, 0
MOV VL, 5
; ClrDraw
MOV VM, 0
MOV VL, 1
SFILL 0x00
MOV VM, 0
MOV VL, 6
; ClrDraw
MOV VM, 0
MOV VL, 1
SFILL 0x00
XOR VX, VX
XOR VY, VY
MOV VC, 31
TEXT STR88
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
MOV P1, 15
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
; Allocate struct enemy (Enemy) at 0x012C
; Load enemy.eoldx
MOV P0, 304
MOV P1, [P0]
; Load enemy.ex
MOV P0, 300
MOV P2, [P0]
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JZ L8
; Load enemy.eoldx
MOV P0, 304
MOV P1, [P0]
PUSH P1
; Load enemy.eoldy
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
; Load enemy.eoldy
MOV P0, 306
MOV P1, [P0]
; Load enemy.ey
MOV P0, 302
MOV P2, [P0]
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JZ L10
; Load enemy.eoldx
MOV P0, 304
MOV P1, [P0]
PUSH P1
; Load enemy.eoldy
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
; Load enemy.ehit
MOV P0, 310
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JZ L12
; Load enemy.ex
MOV P0, 300
MOV P1, [P0]
PUSH P1
; Load enemy.ey
MOV P0, 302
MOV P1, [P0]
PUSH P1
MOV P1, 12
PUSH P1
; Free R3 (last use)
CALL _func_renderenemy_1
ADD SP, 6
L12:
MOV SP, FP
POP FP
RETN 0
_func_clearsword_4:
; Function: clearsword
; Parameters:
; Locals:  (0 bytes)
ENTER 0
MOV VM, 0
MOV VL, 5
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
MOV P0, 312
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
MOV P0, 312
MOV P0, [P0]
TEXT P0
MOV SP, FP
POP FP
RETN 0
_func_attack_5:
; Function: attack
; Parameters:
; Locals:  (0 bytes)
ENTER 0
MOV VM, 0
MOV VL, 5
; Load player.facing
MOV P0, 296
MOV P1, [P0]
XOR P2, P2
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
MOV P0, 312
MOV P0, [P0]
TEXT P0
L14:
; Load player.facing
MOV P0, 296
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L16
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
MOV P0, 312
MOV P0, [P0]
TEXT P0
L16:
XOR R1, R1
; Store to player.counter
MOV P0, 298
MOV P1, R1
MOV [P0], P1
; Load player.facing
MOV P0, 296
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L18
; Load enemy.ex
MOV P0, 300
MOV P1, [P0]
; Load player.x
MOV P0, 288
MOV P3, [P0]
; Preserve left operand in register across right-side evaluation
MOV R1, P3
MOV R2, 1
SHL R2, 3
MOV P2, R1
ADD P2, R2
; Free R2 (last use)
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L18
; Load enemy.ey
MOV P0, 302
MOV P1, [P0]
; Load player.y
MOV P0, 290
MOV P3, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P3
MOV R3, 1
SHL R3, 3
MOV P2, R2
ADD P2, R3
; Free R3 (last use)
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L18
MOV R1, 1
; Store to enemy.ehit
MOV P0, 310
MOV P1, R1
MOV [P0], P1
L18:
; Load player.facing
MOV P0, 296
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L22
; Load enemy.ex
MOV P0, 300
MOV P1, [P0]
; Load player.x
MOV P0, 288
MOV P3, [P0]
; Preserve left operand in register across right-side evaluation
MOV R1, P3
MOV R2, 1
SHL R2, 4
MOV P2, R1
ADD P2, R2
; Free R2 (last use)
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L22
; Load enemy.ey
MOV P0, 302
MOV P1, [P0]
; Load player.y
MOV P0, 290
MOV P3, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P3
MOV R3, 1
SHL R3, 3
MOV P2, R2
ADD P2, R3
; Free R3 (last use)
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L22
MOV R1, 1
; Store to enemy.ehit
MOV P0, 310
MOV P1, R1
MOV [P0], P1
L22:
; Load player.facing
MOV P0, 296
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L26
; Load enemy.ex
MOV P0, 300
MOV P1, [P0]
; Load player.x
MOV P0, 288
MOV P3, [P0]
; Preserve left operand in register across right-side evaluation
MOV R1, P3
MOV R2, 24
MOV P2, R1
SUB P2, R2
; Free R2 (last use)
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L26
; Load enemy.ey
MOV P0, 302
MOV P1, [P0]
; Load player.y
MOV P0, 290
MOV P3, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P3
MOV R3, 1
SHL R3, 3
MOV P2, R2
ADD P2, R3
; Free R3 (last use)
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L26
MOV R1, 1
; Store to enemy.ehit
MOV P0, 310
MOV P1, R1
MOV [P0], P1
L26:
MOV SP, FP
POP FP
RETN 0
_func_keycheck_6:
; Function: keycheck
; Parameters:
; Locals:  (0 bytes)
ENTER 0
KEYIN R0
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P1, 314
MOV [P1], P0
MOV P0, 314
MOV P1, [P0]
MOV P2, 101
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L30
CALL _func_attack_5
L30:
MOV P0, 314
MOV P1, [P0]
MOV P2, 97
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L32
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
L32:
MOV P0, 314
MOV P1, [P0]
MOV P2, 1
SHL P2, 7
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L34
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
L34:
MOV P0, 314
MOV P1, [P0]
MOV P2, 100
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L36
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
L36:
MOV P0, 314
MOV P1, [P0]
MOV P2, 129
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L38
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
L38:
MOV P0, 314
MOV P1, [P0]
MOV P2, 115
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L40
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
L40:
MOV P0, 314
MOV P1, [P0]
MOV P2, 131
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L42
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
L42:
MOV P0, 314
MOV P1, [P0]
MOV P2, 119
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L44
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
L44:
MOV P0, 314
MOV P1, [P0]
MOV P2, 130
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L46
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
L46:
MOV SP, FP
POP FP
RETN 0
_func_callplayer_7:
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
CALL _func_keycheck_6
; Load player.x
MOV P0, 288
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L48
MOV R1, 1
SHL R1, 3
; Store to player.x
MOV P0, 288
MOV P1, R1
MOV [P0], P1
L48:
; Load player.x
MOV P0, 288
MOV P1, [P0]
MOV P2, 240
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L50
MOV R1, 240
; Store to player.x
MOV P0, 288
MOV P1, R1
MOV [P0], P1
L50:
; Load player.y
MOV P0, 290
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L52
MOV R1, 1
SHL R1, 3
; Store to player.y
MOV P0, 290
MOV P1, R1
MOV [P0], P1
L52:
; Load player.y
MOV P0, 290
MOV P1, [P0]
MOV P2, 232
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L54
MOV R1, 232
; Store to player.y
MOV P0, 290
MOV P1, R1
MOV [P0], P1
L54:
MOV VM, 0
MOV VL, 5
CALL _func_drawplayer_2
; Load player.counter
MOV P0, 298
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L59
; Load player.x
MOV P0, 288
MOV P1, [P0]
; Load player.oldx
MOV P0, 292
MOV P2, [P0]
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JZ L58
L59:
; Load player.y
MOV P0, 290
MOV P1, [P0]
; Load player.oldy
MOV P0, 294
MOV P2, [P0]
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JZ L56
L58:
CALL _func_clearsword_4
L56:
MOV SP, FP
POP FP
RETN 0
_func_callenemy_8:
; Function: callenemy
; Parameters:
; Locals:  (0 bytes)
ENTER 0
; Load enemy.ecounter
MOV P0, 308
MOV P1, [P0]
MOV R0, P1
ADD P1, 1
; Store to enemy.ecounter
MOV P0, 308
MOV [P0], P1
; Load enemy.ex
MOV P0, 300
MOV P1, [P0]
; Store to enemy.eoldx
MOV P0, 304
MOV [P0], P1
; Load enemy.ey
MOV P0, 302
MOV P1, [P0]
; Store to enemy.eoldy
MOV P0, 306
MOV [P0], P1
XOR R0, R0
MOV R2, 3
RNDR R1, R0, R2
; Free R0 (last use)
; Free R2 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 316
MOV [P1], P0
; Load enemy.ecounter
MOV P0, 308
MOV P1, [P0]
MOV P2, 1
SHL P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L60
MOV P0, 316
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L62
; Load enemy.ex
MOV P0, 300
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to enemy.ex
MOV P0, 300
MOV P1, R1
MOV [P0], P1
L62:
MOV P0, 316
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L64
; Load enemy.ex
MOV P0, 300
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to enemy.ex
MOV P0, 300
MOV P1, R1
MOV [P0], P1
L64:
MOV P0, 316
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L66
; Load enemy.ey
MOV P0, 302
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to enemy.ey
MOV P0, 302
MOV P1, R1
MOV [P0], P1
L66:
MOV P0, 316
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L68
; Load enemy.ey
MOV P0, 302
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to enemy.ey
MOV P0, 302
MOV P1, R1
MOV [P0], P1
L68:
MOV P0, 316
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L72
MOV P0, 316
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L70
L72:
; Load enemy.ex
MOV P0, 300
MOV P1, [P0]
; Store to enemy.ex
MOV P0, 300
MOV [P0], P1
L70:
; Load enemy.ex
MOV P0, 300
MOV P1, [P0]
MOV P2, 1
SHL P2, 4
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L73
MOV R1, 1
SHL R1, 4
; Store to enemy.ex
MOV P0, 300
MOV P1, R1
MOV [P0], P1
L73:
; Load enemy.ex
MOV P0, 300
MOV P1, [P0]
MOV P2, 240
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L75
MOV R1, 240
; Store to enemy.ex
MOV P0, 300
MOV P1, R1
MOV [P0], P1
L75:
; Load enemy.ey
MOV P0, 302
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L77
MOV R1, 1
SHL R1, 3
; Store to enemy.ey
MOV P0, 302
MOV P1, R1
MOV [P0], P1
L77:
; Load enemy.ey
MOV P0, 302
MOV P1, [P0]
MOV P2, 232
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L79
MOV R1, 232
; Store to enemy.ey
MOV P0, 302
MOV P1, R1
MOV [P0], P1
L79:
XOR R1, R1
; Store to enemy.ecounter
MOV P0, 308
MOV P1, R1
MOV [P0], P1
L60:
MOV VM, 0
MOV VL, 6
CALL _func_drawenemy_3
MOV SP, FP
POP FP
RETN 0
STR0: DEFSTR "O"
STR1: DEFSTR "X"
STR2: DEFSTR "m"
STR80: DEFSTR "--"
STR83: DEFSTR "X                              X"
STR88: DEFSTR "WIN"