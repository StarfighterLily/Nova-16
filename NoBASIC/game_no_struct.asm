; WARNING: 2 variable(s) using dedicated spill slots
;          Spilled variables: oldy, facing
;          Spill region: 0x7000-0x7004
;          Register pressure: 2 (max), 5 available
;          This will impact performance. Consider:
;          - Reducing total variable count (currently 8)
;          - Reducing variable lifetimes by localizing scope
;          - Breaking complex expressions into simpler parts
; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
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
MOV P3, R1
MOV R1, 1
SHL R1, 3
MOV P4, R1
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 28674
MOV [P1], P0
XOR R1, R1
MOV P5, R1
MOV VM, 0
MOV VL, 5
L6:
MOV R1, 1
CMP R1, 0
JZ L7
Player:
MOV P6, P3
MOV P0, 28672
MOV [P0], P4
; Preserve left operand in register across right-side evaluation
MOV R2, P5
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P5, R1
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
MOV P0, 28674
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
; Preserve left operand in register across right-side evaluation
MOV R2, P3
MOV R3, 1
SHL R3, 4
MOV R0, R2
SUB R0, R3
; Free R3 (last use)
MOV VX, R0
; Preserve left operand in register across right-side evaluation
MOV R3, P4
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
MOV P0, 28674
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
; Preserve left operand in register across right-side evaluation
MOV R2, P3
MOV R3, 1
SHL R3, 3
MOV R0, R2
ADD R0, R3
; Free R3 (last use)
MOV VX, R0
; Preserve left operand in register across right-side evaluation
MOV R3, P4
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
MOV P5, R1
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
; Preserve left operand in register across right-side evaluation
MOV R2, P3
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
MOV P3, R1
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 28674
MOV [P1], P0
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
; Preserve left operand in register across right-side evaluation
MOV R2, P3
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
MOV P3, R1
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 28674
MOV [P1], P0
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
; Preserve left operand in register across right-side evaluation
MOV R2, P3
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P3, R1
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 28674
MOV [P1], P0
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
; Preserve left operand in register across right-side evaluation
MOV R2, P3
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P3, R1
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 28674
MOV [P1], P0
L32:
MOV P1, P2
MOV P0, 515
CMP P1, P0
; Free P1 (last use)
; Free P0 (last use)
MOV R1, 0
JZ L38
JMP L39
L38:
MOV R1, 1
L39:
CMP R1, 0
JZ L36
; Preserve left operand in register across right-side evaluation
MOV R2, P4
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P4, R1
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
; Preserve left operand in register across right-side evaluation
MOV R2, P4
MOV R3, 1
SHL R3, 3
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P4, R1
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
; Preserve left operand in register across right-side evaluation
MOV R2, P4
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
MOV P4, R1
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
; Preserve left operand in register across right-side evaluation
MOV R2, P4
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
MOV P4, R1
L48:
MOV P1, P3
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
MOV P3, R1
L52:
MOV P1, P3
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
MOV P3, R1
L56:
MOV P1, P4
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
MOV P4, R1
L60:
MOV P1, P4
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
MOV P4, R1
L64:
MOV P1, P6
CMP P1, P3
; Free P1 (last use)
MOV R1, 0
JNZ L70
JMP L71
L70:
MOV R1, 1
L71:
CMP R1, 0
JZ L68
MOV VX, P6
MOV P0, 28672
MOV P0, [P0]
MOV VY, :P0
XOR VC, VC
TEXT STR71
MOV VX, P6
MOV P0, 28672
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
SHL R3, 3
MOV R0, R2
ADD R0, R3
; Free R3 (last use)
MOV VY, R0
XOR VC, VC
TEXT STR72
; Preserve left operand in register across right-side evaluation
MOV R2, P6
MOV R3, 1
SHL R3, 4
MOV R0, R2
SUB R0, R3
; Free R3 (last use)
MOV VX, R0
MOV P0, 28672
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, P0
MOV R4, 1
SHL R4, 3
MOV R0, R3
ADD R0, R4
; Free R4 (last use)
MOV VY, R0
XOR VC, VC
MOV P0, 288
MOV P1, [P0]
TEXT P1
; Preserve left operand in register across right-side evaluation
MOV R2, P6
MOV R3, 1
SHL R3, 3
MOV R0, R2
ADD R0, R3
; Free R3 (last use)
MOV VX, R0
MOV P0, 28672
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, P0
MOV R4, 1
SHL R4, 3
MOV R0, R3
ADD R0, R4
; Free R4 (last use)
MOV VY, R0
XOR VC, VC
MOV P0, 288
MOV P1, [P0]
TEXT P1
L68:
MOV P0, 28672
MOV P1, [P0]
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
MOV VX, P6
MOV P0, 28672
MOV P0, [P0]
MOV VY, :P0
XOR VC, VC
TEXT STR71
MOV VX, P6
MOV P0, 28672
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
SHL R3, 3
MOV R0, R2
ADD R0, R3
; Free R3 (last use)
MOV VY, R0
XOR VC, VC
TEXT STR72
; Preserve left operand in register across right-side evaluation
MOV R2, P6
MOV R3, 1
SHL R3, 4
MOV R0, R2
SUB R0, R3
; Free R3 (last use)
MOV VX, R0
MOV P0, 28672
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, P0
MOV R4, 1
SHL R4, 3
MOV R0, R3
ADD R0, R4
; Free R4 (last use)
MOV VY, R0
XOR VC, VC
MOV P0, 288
MOV P1, [P0]
TEXT P1
; Preserve left operand in register across right-side evaluation
MOV R2, P6
MOV R3, 1
SHL R3, 3
MOV R0, R2
ADD R0, R3
; Free R3 (last use)
MOV VX, R0
MOV P0, 28672
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, P0
MOV R4, 1
SHL R4, 3
MOV R0, R3
ADD R0, R4
; Free R4 (last use)
MOV VY, R0
XOR VC, VC
MOV P0, 288
MOV P1, [P0]
TEXT P1
L74:
MOV VX, P3
MOV VY, P4
MOV VC, 15
TEXT STR71
MOV VX, P3
; Preserve left operand in register across right-side evaluation
MOV R2, P4
MOV R3, 1
SHL R3, 3
MOV R0, R2
ADD R0, R3
; Free R3 (last use)
MOV VY, R0
MOV VC, 15
TEXT STR72
MOV P1, P5
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
MOV P5, R1
; Preserve left operand in register across right-side evaluation
MOV R2, P6
MOV R3, 1
SHL R3, 4
MOV R0, R2
SUB R0, R3
; Free R3 (last use)
MOV VX, R0
MOV P0, 28672
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, P0
MOV R4, 1
SHL R4, 3
MOV R0, R3
ADD R0, R4
; Free R4 (last use)
MOV VY, R0
XOR VC, VC
MOV P0, 288
MOV P1, [P0]
TEXT P1
; Preserve left operand in register across right-side evaluation
MOV R2, P6
MOV R3, 1
SHL R3, 3
MOV R0, R2
ADD R0, R3
; Free R3 (last use)
MOV VX, R0
MOV P0, 28672
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, P0
MOV R4, 1
SHL R4, 3
MOV R0, R3
ADD R0, R4
; Free R4 (last use)
MOV VY, R0
XOR VC, VC
MOV P0, 288
MOV P1, [P0]
TEXT P1
L78:
JMP L6
L7:
HLT
STR0: DEFSTR "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
STR3: DEFSTR "X                              X"
STR4: DEFSTR "--"
STR71: DEFSTR "O"
STR72: DEFSTR "X"