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
TEXT STR91
XOR R2, R2
MOV P2, R2
MOV R2, 240
MOV R0, R2
MOV R2, 1
SHL R2, 3
MOV R1, R2
L93:
CMP P2, R0
JGT L94
XOR VX, VX
MOV VY, P2
MOV VC, 31
TEXT STR94
ADD P2, R1
JMP L93
L94:
XOR VX, VX
MOV VY, 248
MOV VC, 31
TEXT STR91
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
L96:
MOV R1, 1
CMP R1, 0
JZ L97
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
MOV R1, R0
MOV P3, R1
CMP P3, 0
JZ L98
XOR R1, R1
; Store to player.counter
MOV P0, 300
MOV P1, R1
MOV [P0], P1
L98:
PUSH P4
; Load player.x
MOV P0, 290
MOV P1, [P0]
PUSH P1
CALL _func_movexbykey_3
ADD SP, 4
MOV R1, R0
; Store to player.x
MOV P0, 290
MOV P1, R1
MOV [P0], P1
PUSH P4
; Load player.y
MOV P0, 292
MOV P1, [P0]
PUSH P1
CALL _func_moveybykey_4
ADD SP, 4
MOV R1, R0
; Store to player.y
MOV P0, 292
MOV P1, R1
MOV [P0], P1
PUSH P4
; Load player.facing
MOV P0, 298
MOV P1, [P0]
PUSH P1
CALL _func_facingbykey_5
ADD SP, 4
MOV R1, R0
; Store to player.facing
MOV P0, 298
MOV P1, R1
MOV [P0], P1
; Load player.x
MOV P0, 290
MOV P1, [P0]
PUSH P1
CALL _func_clampx_6
ADD SP, 2
MOV R1, R0
; Store to player.x
MOV P0, 290
MOV P1, R1
MOV [P0], P1
; Load player.y
MOV P0, 292
MOV P1, [P0]
PUSH P1
CALL _func_clampy_7
ADD SP, 2
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
MOV R1, 0
JNZ L102
JMP L103
L102:
MOV R1, 1
L103:
CMP R1, 0
JZ L100
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
L100:
; Load player.oldy
MOV P0, 296
MOV P1, [P0]
; Load player.y
MOV P0, 292
MOV P5, [P0]
CMP P1, P5
; Free P1 (last use)
MOV R1, 0
JNZ L106
JMP L107
L106:
MOV R1, 1
L107:
CMP R1, 0
JZ L104
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
L104:
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
MOV R1, R0
; Store to player.counter
MOV P0, 300
MOV P1, R1
MOV [P0], P1
JMP L96
L97:
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
MOV R0, 0
MOV SP, FP
POP FP
RET

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
MOV R0, 0
MOV SP, FP
POP FP
RET

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
MOV R1, 0
JZ L6
JMP L7
L6:
MOV R1, 1
L7:
CMP R1, 0
JZ L4
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
MOV R1, 0
JZ L10
JMP L11
L10:
MOV R1, 1
L11:
CMP R1, 0
JZ L8
MOV P0, 288
MOV P1, [P0]
MOV P2, 1
SHL P2, 4
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
MOV R1, 0
JGE L14
JMP L15
L14:
MOV R1, 1
L15:
CMP R1, 0
JZ L12
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
L12:
L8:
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
MOV R1, 0
JZ L18
JMP L19
L18:
MOV R1, 1
L19:
CMP R1, 0
JZ L16
MOV P0, 288
MOV P1, [P0]
MOV P2, 232
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
MOV R1, 0
JLE L22
JMP L23
L22:
MOV R1, 1
L23:
CMP R1, 0
JZ L20
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
L20:
L16:
MOV R0, 1
MOV SP, FP
POP FP
RET
L4:
XOR R0, R0
MOV SP, FP
POP FP
RET

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
MOV R1, 0
JZ L26
JMP L27
L26:
MOV R1, 1
L27:
CMP R1, 0
JZ L24
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
RET
L24:
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 1
SHL P2, 7
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
MOV R1, 0
JZ L30
JMP L31
L30:
MOV R1, 1
L31:
CMP R1, 0
JZ L28
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
RET
L28:
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 100
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
MOV R1, 0
JZ L34
JMP L35
L34:
MOV R1, 1
L35:
CMP R1, 0
JZ L32
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
RET
L32:
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 129
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
MOV R1, 0
JZ L38
JMP L39
L38:
MOV R1, 1
L39:
CMP R1, 0
JZ L36
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
RET
L36:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV R0, P1
; Free P1 (last use)
MOV SP, FP
POP FP
RET

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
MOV R1, 0
JZ L42
JMP L43
L42:
MOV R1, 1
L43:
CMP R1, 0
JZ L40
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
RET
L40:
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 131
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
MOV R1, 0
JZ L46
JMP L47
L46:
MOV R1, 1
L47:
CMP R1, 0
JZ L44
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
RET
L44:
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 119
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
MOV R1, 0
JZ L50
JMP L51
L50:
MOV R1, 1
L51:
CMP R1, 0
JZ L48
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
RET
L48:
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 130
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
MOV R1, 0
JZ L54
JMP L55
L54:
MOV R1, 1
L55:
CMP R1, 0
JZ L52
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
RET
L52:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV R0, P1
; Free P1 (last use)
MOV SP, FP
POP FP
RET

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
MOV R1, 0
JZ L58
JMP L59
L58:
MOV R1, 1
L59:
CMP R1, 0
JZ L56
XOR R0, R0
MOV SP, FP
POP FP
RET
L56:
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 1
SHL P2, 7
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
MOV R1, 0
JZ L62
JMP L63
L62:
MOV R1, 1
L63:
CMP R1, 0
JZ L60
XOR R0, R0
MOV SP, FP
POP FP
RET
L60:
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 100
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
MOV R1, 0
JZ L66
JMP L67
L66:
MOV R1, 1
L67:
CMP R1, 0
JZ L64
MOV R0, 1
MOV SP, FP
POP FP
RET
L64:
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
MOV P2, 129
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
MOV R1, 0
JZ L70
JMP L71
L70:
MOV R1, 1
L71:
CMP R1, 0
JZ L68
MOV R0, 1
MOV SP, FP
POP FP
RET
L68:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV R0, P1
; Free P1 (last use)
MOV SP, FP
POP FP
RET

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
MOV R1, 0
JLT L74
JMP L75
L74:
MOV R1, 1
L75:
CMP R1, 0
JZ L72
MOV R0, 1
SHL R0, 3
MOV SP, FP
POP FP
RET
L72:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 240
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
MOV R1, 0
JGT L78
JMP L79
L78:
MOV R1, 1
L79:
CMP R1, 0
JZ L76
MOV R0, 240
MOV SP, FP
POP FP
RET
L76:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV R0, P1
; Free P1 (last use)
MOV SP, FP
POP FP
RET

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
MOV R1, 0
JLT L82
JMP L83
L82:
MOV R1, 1
L83:
CMP R1, 0
JZ L80
MOV R0, 1
SHL R0, 3
MOV SP, FP
POP FP
RET
L80:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 232
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
MOV R1, 0
JGT L86
JMP L87
L86:
MOV R1, 1
L87:
CMP R1, 0
JZ L84
MOV R0, 232
MOV SP, FP
POP FP
RET
L84:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV R0, P1
; Free P1 (last use)
MOV SP, FP
POP FP
RET

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
MOV R1, 0
JZ L90
JMP L91
L90:
MOV R1, 1
L91:
CMP R1, 0
JZ L88
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
RET
L88:
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV R0, P1
; Free P1 (last use)
MOV SP, FP
POP FP
RET
STR0: DEFSTR "O"
STR1: DEFSTR "X"
STR2: DEFSTR "--"
STR91: DEFSTR "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
STR94: DEFSTR "X                              X"