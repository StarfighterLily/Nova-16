; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; Struct Player declared with fields: x, y, oldx, oldy, facing, counter
MOV R1, 1
SHL R1, 3
; Store to Player.x
MOV P0, 288
MOV P1, R1
MOV [P0], P1
MOV R1, 1
SHL R1, 3
; Store to Player.y
MOV P0, 290
MOV P1, R1
MOV [P0], P1
MOV R1, 1
SHL R1, 3
; Store to Player.oldx
MOV P0, 292
MOV P1, R1
MOV [P0], P1
MOV R1, 1
SHL R1, 3
; Store to Player.oldy
MOV P0, 294
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to Player.facing
MOV P0, 296
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to Player.counter
MOV P0, 298
MOV P1, R1
MOV [P0], P1
MOV P1, STR38
MOV P0, 300
MOV [P0], P1
MOV VM, 0
MOV VL, 1
XOR VX, VX
XOR VY, VY
MOV VC, 31
TEXT STR39
MOV R1, 1
SHL R1, 3
MOV P2, R1
MOV R1, 240
MOV R0, R1
MOV R1, 1
SHL R1, 3
MOV P3, R1
L41:
CMP P2, R0
JGT L42
XOR VX, VX
MOV VY, P2
MOV VC, 31
TEXT STR42
ADD P2, P3
JMP L41
L42:
XOR VX, VX
MOV VY, 248
MOV VC, 31
TEXT STR39
MOV VM, 0
MOV VL, 5
L44:
MOV R1, 1
WHILE R1
JZ L45
PUSH P2
CALL _func_callplayer_4
POP P2
JMP L44
L45:
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

_func_drawplayer_1:
; Function: drawplayer
; Parameters: 
; Locals:  (0 bytes)
ENTER 0
; Allocate struct Player (Player) at 0x0120
; Load Player.oldx
MOV P0, 292
MOV P1, [P0]
; Load Player.x
MOV P0, 288
MOV P2, [P0]
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JZ L3
; Load Player.oldx
MOV P0, 292
MOV P1, [P0]
PUSH P1
; Load Player.oldy
MOV P0, 294
MOV P1, [P0]
PUSH P1
XOR R3, R3
MOV P1, R3
PUSH P1
; Free R3 (last use)
CALL _func_renderplayer_0
ADD SP, 6
L3:
; Load Player.oldy
MOV P0, 294
MOV P1, [P0]
; Load Player.y
MOV P0, 290
MOV P2, [P0]
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JZ L5
; Load Player.oldx
MOV P0, 292
MOV P1, [P0]
PUSH P1
; Load Player.oldy
MOV P0, 294
MOV P1, [P0]
PUSH P1
XOR R3, R3
MOV P1, R3
PUSH P1
; Free R3 (last use)
CALL _func_renderplayer_0
ADD SP, 6
L5:
; Load Player.x
MOV P0, 288
MOV P1, [P0]
PUSH P1
; Load Player.y
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

_func_attack_2:
; Function: attack
; Parameters: 
; Locals:  (0 bytes)
ENTER 0
; Load Player.facing
MOV P0, 296
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L7
; Load Player.x
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
; Load Player.y
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
MOV P0, 300
MOV P0, [P0]
TEXT P0
L7:
; Load Player.facing
MOV P0, 296
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L9
; Load Player.x
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
; Load Player.y
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
MOV P0, 300
MOV P0, [P0]
TEXT P0
L9:
XOR R1, R1
; Store to Player.counter
MOV P0, 298
MOV P1, R1
MOV [P0], P1
MOV SP, FP
POP FP
RETN 0

_func_keycheck_3:
; Function: keycheck
; Parameters: 
; Locals:  (0 bytes)
ENTER 0
KEYIN R0
MOV R1, R0
MOV P0, 0
MOV :P0, R1
MOV P1, 302
MOV [P1], P0
MOV P0, 302
MOV P1, [P0]
MOV P2, 101
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L11
CALL _func_attack_2
L11:
MOV P0, 302
MOV P1, [P0]
MOV P2, 97
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L13
; Load Player.x
MOV P0, 288
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to Player.x
MOV P0, 288
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to Player.facing
MOV P0, 296
MOV P1, R1
MOV [P0], P1
L13:
MOV P0, 302
MOV P1, [P0]
MOV P2, 1
SHL P2, 7
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L15
; Load Player.x
MOV P0, 288
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to Player.x
MOV P0, 288
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to Player.facing
MOV P0, 296
MOV P1, R1
MOV [P0], P1
L15:
MOV P0, 302
MOV P1, [P0]
MOV P2, 100
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L17
; Load Player.x
MOV P0, 288
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to Player.x
MOV P0, 288
MOV P1, R1
MOV [P0], P1
MOV R1, 1
; Store to Player.facing
MOV P0, 296
MOV P1, R1
MOV [P0], P1
L17:
MOV P0, 302
MOV P1, [P0]
MOV P2, 129
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L19
; Load Player.x
MOV P0, 288
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to Player.x
MOV P0, 288
MOV P1, R1
MOV [P0], P1
MOV R1, 1
; Store to Player.facing
MOV P0, 296
MOV P1, R1
MOV [P0], P1
L19:
MOV P0, 302
MOV P1, [P0]
MOV P2, 115
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L21
; Load Player.y
MOV P0, 290
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to Player.y
MOV P0, 290
MOV P1, R1
MOV [P0], P1
L21:
MOV P0, 302
MOV P1, [P0]
MOV P2, 131
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L23
; Load Player.y
MOV P0, 290
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to Player.y
MOV P0, 290
MOV P1, R1
MOV [P0], P1
L23:
MOV P0, 302
MOV P1, [P0]
MOV P2, 119
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L25
; Load Player.y
MOV P0, 290
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to Player.y
MOV P0, 290
MOV P1, R1
MOV [P0], P1
L25:
MOV P0, 302
MOV P1, [P0]
MOV P2, 130
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L27
; Load Player.y
MOV P0, 290
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to Player.y
MOV P0, 290
MOV P1, R1
MOV [P0], P1
L27:
MOV SP, FP
POP FP
RETN 0

_func_callplayer_4:
; Function: callplayer
; Parameters: 
; Locals:  (0 bytes)
ENTER 0
; Load Player.x
MOV P0, 288
MOV P1, [P0]
; Store to Player.oldx
MOV P0, 292
MOV [P0], P1
; Load Player.y
MOV P0, 290
MOV P1, [P0]
; Store to Player.oldy
MOV P0, 294
MOV [P0], P1
; Load Player.counter
MOV P0, 298
MOV P1, [P0]
MOV R0, P1
ADD P1, 1
; Store to Player.counter
MOV P0, 298
MOV [P0], P1
CALL _func_keycheck_3
; Load Player.x
MOV P0, 288
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L29
MOV R1, 1
SHL R1, 3
; Store to Player.x
MOV P0, 288
MOV P1, R1
MOV [P0], P1
L29:
; Load Player.x
MOV P0, 288
MOV P1, [P0]
MOV P2, 240
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L31
MOV R1, 240
; Store to Player.x
MOV P0, 288
MOV P1, R1
MOV [P0], P1
L31:
; Load Player.y
MOV P0, 290
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L33
MOV R1, 1
SHL R1, 3
; Store to Player.y
MOV P0, 290
MOV P1, R1
MOV [P0], P1
L33:
; Load Player.y
MOV P0, 290
MOV P1, [P0]
MOV P2, 232
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L35
MOV R1, 232
; Store to Player.y
MOV P0, 290
MOV P1, R1
MOV [P0], P1
L35:
CALL _func_drawplayer_1
; Load Player.counter
MOV P0, 298
MOV P1, [P0]
MOV P2, 255
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L37
XOR R1, R1
; Store to Player.counter
MOV P0, 298
MOV P1, R1
MOV [P0], P1
; Load Player.oldx
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
; Load Player.oldy
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
MOV P0, 300
MOV P0, [P0]
TEXT P0
; Load Player.oldx
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
; Load Player.oldy
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
MOV P0, 300
MOV P0, [P0]
TEXT P0
L37:
MOV SP, FP
POP FP
RETN 0
STR0: DEFSTR "O"
STR1: DEFSTR "X"
STR38: DEFSTR "--"
STR39: DEFSTR "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
STR42: DEFSTR "X                              X"