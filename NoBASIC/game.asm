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
TEXT STR0
XOR R2, R2
MOV P2, R2
MOV R2, 240
MOV R0, R2
MOV R2, 1
SHL R2, 3
MOV R1, R2
L2:
CMP P2, R0
JGT L3
XOR VX, VX
MOV VY, P2
MOV VC, 31
TEXT STR3
ADD P2, R1
JMP L2
L3:
XOR VX, VX
MOV VY, 248
MOV VC, 31
TEXT STR0
MOV P1, STR4
MOV P0, 288
MOV [P0], P1
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
MOV VM, 0
MOV VL, 5
L6:
MOV R1, 1
CMP R1, 0
JZ L7
Player:
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
MOV P2, R1
MOV P1, P2
MOV R2, 101
CMP P1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV R1, 0
JZ L10
JMP L11
L10:
MOV R1, 1
L11:
CMP R1, 0
JZ L8
; Load player.facing
MOV P0, 298
MOV P1, [P0]
XOR R2, R2
CMP P1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV R1, 0
JZ L14
JMP L15
L14:
MOV R1, 1
L15:
CMP R1, 0
JZ L12
; Load player.x
MOV P0, 290
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
MOV P0, 292
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
MOV P0, 288
MOV P0, [P0]
TEXT P0
L12:
; Load player.facing
MOV P0, 298
MOV P1, [P0]
MOV R2, 1
CMP P1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV R1, 0
JZ L18
JMP L19
L18:
MOV R1, 1
L19:
CMP R1, 0
JZ L16
; Load player.x
MOV P0, 290
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
MOV P0, 292
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
MOV P0, 288
MOV P0, [P0]
TEXT P0
L16:
XOR R1, R1
; Store to player.counter
MOV P0, 300
MOV P1, R1
MOV [P0], P1
L8:
MOV P1, P2
MOV R2, 97
CMP P1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV R1, 0
JZ L22
JMP L23
L22:
MOV R1, 1
L23:
CMP R1, 0
JZ L20
; Load player.x
MOV P0, 290
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to player.x
MOV P0, 290
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to player.facing
MOV P0, 298
MOV P1, R1
MOV [P0], P1
L20:
MOV P1, P2
MOV R2, 1
SHL R2, 7
CMP P1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV R1, 0
JZ L26
JMP L27
L26:
MOV R1, 1
L27:
CMP R1, 0
JZ L24
; Load player.x
MOV P0, 290
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to player.x
MOV P0, 290
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to player.facing
MOV P0, 298
MOV P1, R1
MOV [P0], P1
L24:
MOV P1, P2
MOV R2, 100
CMP P1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV R1, 0
JZ L30
JMP L31
L30:
MOV R1, 1
L31:
CMP R1, 0
JZ L28
; Load player.x
MOV P0, 290
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to player.x
MOV P0, 290
MOV P1, R1
MOV [P0], P1
MOV R1, 1
; Store to player.facing
MOV P0, 298
MOV P1, R1
MOV [P0], P1
L28:
MOV P1, P2
MOV R2, 129
CMP P1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV R1, 0
JZ L34
JMP L35
L34:
MOV R1, 1
L35:
CMP R1, 0
JZ L32
; Load player.x
MOV P0, 290
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to player.x
MOV P0, 290
MOV P1, R1
MOV [P0], P1
MOV R1, 1
; Store to player.facing
MOV P0, 298
MOV P1, R1
MOV [P0], P1
L32:
MOV P1, P2
MOV R2, 115
CMP P1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV R1, 0
JZ L38
JMP L39
L38:
MOV R1, 1
L39:
CMP R1, 0
JZ L36
; Load player.y
MOV P0, 292
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to player.y
MOV P0, 292
MOV P1, R1
MOV [P0], P1
L36:
MOV P1, P2
MOV R2, 131
CMP P1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV R1, 0
JZ L42
JMP L43
L42:
MOV R1, 1
L43:
CMP R1, 0
JZ L40
; Load player.y
MOV P0, 292
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to player.y
MOV P0, 292
MOV P1, R1
MOV [P0], P1
L40:
MOV P1, P2
MOV R2, 119
CMP P1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV R1, 0
JZ L46
JMP L47
L46:
MOV R1, 1
L47:
CMP R1, 0
JZ L44
; Load player.y
MOV P0, 292
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to player.y
MOV P0, 292
MOV P1, R1
MOV [P0], P1
L44:
MOV P1, P2
MOV R2, 130
CMP P1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV R1, 0
JZ L50
JMP L51
L50:
MOV R1, 1
L51:
CMP R1, 0
JZ L48
; Load player.y
MOV P0, 292
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to player.y
MOV P0, 292
MOV P1, R1
MOV [P0], P1
L48:
; Load player.x
MOV P0, 290
MOV P1, [P0]
MOV R2, 1
SHL R2, 3
CMP P1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV R1, 0
JLT L54
JMP L55
L54:
MOV R1, 1
L55:
CMP R1, 0
JZ L52
MOV R1, 1
SHL R1, 3
; Store to player.x
MOV P0, 290
MOV P1, R1
MOV [P0], P1
L52:
; Load player.x
MOV P0, 290
MOV P1, [P0]
MOV R2, 240
CMP P1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV R1, 0
JGT L58
JMP L59
L58:
MOV R1, 1
L59:
CMP R1, 0
JZ L56
MOV R1, 240
; Store to player.x
MOV P0, 290
MOV P1, R1
MOV [P0], P1
L56:
; Load player.y
MOV P0, 292
MOV P1, [P0]
MOV R2, 1
SHL R2, 3
CMP P1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV R1, 0
JLT L62
JMP L63
L62:
MOV R1, 1
L63:
CMP R1, 0
JZ L60
MOV R1, 1
SHL R1, 3
; Store to player.y
MOV P0, 292
MOV P1, R1
MOV [P0], P1
L60:
; Load player.y
MOV P0, 292
MOV P1, [P0]
MOV R2, 232
CMP P1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV R1, 0
JGT L66
JMP L67
L66:
MOV R1, 1
L67:
CMP R1, 0
JZ L64
MOV R1, 232
; Store to player.y
MOV P0, 292
MOV P1, R1
MOV [P0], P1
L64:
; Load player.oldx
MOV P0, 294
MOV P1, [P0]
; Load player.x
MOV P0, 290
MOV P4, [P0]
CMP P1, P4
; Free P1 (last use)
MOV R1, 0
JNZ L70
JMP L71
L70:
MOV R1, 1
L71:
CMP R1, 0
JZ L68
; Load player.oldx
MOV P0, 294
MOV P1, [P0]
MOV VX, P1
; Load player.oldy
MOV P0, 296
MOV P1, [P0]
MOV VY, P1
XOR VC, VC
TEXT STR71
; Load player.oldx
MOV P0, 294
MOV P1, [P0]
MOV VX, P1
; Load player.oldy
MOV P0, 296
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
TEXT STR72
; Load player.oldx
MOV P0, 294
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
MOV P0, 296
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
MOV P0, 288
MOV P0, [P0]
TEXT P0
; Load player.oldx
MOV P0, 294
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
MOV P0, 296
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
MOV P0, 288
MOV P0, [P0]
TEXT P0
L68:
; Load player.oldy
MOV P0, 296
MOV P1, [P0]
; Load player.y
MOV P0, 292
MOV P4, [P0]
CMP P1, P4
; Free P1 (last use)
MOV R1, 0
JNZ L76
JMP L77
L76:
MOV R1, 1
L77:
CMP R1, 0
JZ L74
; Load player.oldx
MOV P0, 294
MOV P1, [P0]
MOV VX, P1
; Load player.oldy
MOV P0, 296
MOV P1, [P0]
MOV VY, P1
XOR VC, VC
TEXT STR71
; Load player.oldx
MOV P0, 294
MOV P1, [P0]
MOV VX, P1
; Load player.oldy
MOV P0, 296
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
TEXT STR72
; Load player.oldx
MOV P0, 294
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
MOV P0, 296
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
MOV P0, 288
MOV P0, [P0]
TEXT P0
; Load player.oldx
MOV P0, 294
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
MOV P0, 296
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
MOV P0, 288
MOV P0, [P0]
TEXT P0
L74:
; Load player.x
MOV P0, 290
MOV P1, [P0]
MOV VX, P1
; Load player.y
MOV P0, 292
MOV P1, [P0]
MOV VY, P1
MOV VC, 15
TEXT STR71
; Load player.x
MOV P0, 290
MOV P1, [P0]
MOV VX, P1
; Load player.y
MOV P0, 292
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
TEXT STR72
; Load player.counter
MOV P0, 300
MOV P1, [P0]
MOV R2, 255
CMP P1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV R1, 0
JZ L80
JMP L81
L80:
MOV R1, 1
L81:
CMP R1, 0
JZ L78
XOR R1, R1
; Store to player.counter
MOV P0, 300
MOV P1, R1
MOV [P0], P1
; Load player.oldx
MOV P0, 294
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
MOV P0, 296
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
MOV P0, 288
MOV P0, [P0]
TEXT P0
; Load player.oldx
MOV P0, 294
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
MOV P0, 296
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
MOV P0, 288
MOV P0, [P0]
TEXT P0
L78:
JMP L6
L7:
HLT
STR0: DEFSTR "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
STR3: DEFSTR "X                              X"
STR4: DEFSTR "--"
STR71: DEFSTR "O"
STR72: DEFSTR "X"