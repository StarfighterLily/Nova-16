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
WHILE R1
JZ L7
Player:
MOV P6, P3
MOV P0, 28672
MOV [P0], P4
MOV R0, 1
; Preserve left operand in register across right-side evaluation
MOV R2, R0
MOV R1, R2
ADD R1, P5
MOV P5, R1
KEYIN R0
MOV R1, R0
MOV P2, R1
MOV P1, P2
MOV R0, 101
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JNZ L8
MOV P0, 28674
MOV P1, [P0]
XOR R0, R0
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JNZ L10
; Preserve left operand in register across right-side evaluation
MOV R2, P3
MOV R3, 1
SHL R3, 4
MOV R0, R2
SUB R0, R3
; Free R3 (last use)
MOV VX, R0
MOV R2, 1
SHL R2, 3
; Preserve left operand in register across right-side evaluation
MOV R3, R2
MOV R0, R3
ADD R0, P4
MOV VY, R0
MOV VC, 15
MOV P0, 288
MOV P0, [P0]
TEXT P0
L10:
MOV P0, 28674
MOV P1, [P0]
MOV R0, 1
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JNZ L12
MOV R1, 1
SHL R1, 3
; Preserve left operand in register across right-side evaluation
MOV R2, R1
MOV R0, R2
ADD R0, P3
MOV VX, R0
MOV R2, 1
SHL R2, 3
; Preserve left operand in register across right-side evaluation
MOV R4, R2
MOV R0, R4
ADD R0, P4
MOV VY, R0
MOV VC, 15
MOV P0, 288
MOV P0, [P0]
TEXT P0
L12:
XOR R1, R1
MOV P5, R1
L8:
MOV P1, P2
MOV R0, 97
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JNZ L14
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
L14:
MOV P1, P2
MOV R0, 1
SHL R0, 7
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JNZ L16
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
L16:
MOV P1, P2
MOV R0, 100
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JNZ L18
MOV R0, 1
SHL R0, 3
; Preserve left operand in register across right-side evaluation
MOV R2, R0
MOV R1, R2
ADD R1, P3
MOV P3, R1
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 28674
MOV [P1], P0
L18:
MOV P1, P2
MOV R0, 129
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JNZ L20
MOV R0, 1
SHL R0, 3
; Preserve left operand in register across right-side evaluation
MOV R2, R0
MOV R1, R2
ADD R1, P3
MOV P3, R1
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 28674
MOV [P1], P0
L20:
MOV P1, P2
MOV P0, 515
CMP P1, P0
; Free P1 (last use)
; Free P0 (last use)
JNZ L22
MOV R0, 1
SHL R0, 3
; Preserve left operand in register across right-side evaluation
MOV R2, R0
MOV R1, R2
ADD R1, P4
MOV P4, R1
L22:
MOV P1, P2
MOV R0, 131
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JNZ L24
MOV R0, 1
SHL R0, 3
; Preserve left operand in register across right-side evaluation
MOV R2, R0
MOV R1, R2
ADD R1, P4
MOV P4, R1
L24:
MOV P1, P2
MOV R0, 119
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JNZ L26
; Preserve left operand in register across right-side evaluation
MOV R2, P4
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
MOV P4, R1
L26:
MOV P1, P2
MOV R0, 130
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JNZ L28
; Preserve left operand in register across right-side evaluation
MOV R2, P4
MOV R3, 1
SHL R3, 3
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
MOV P4, R1
L28:
MOV P1, P3
MOV R0, 1
SHL R0, 3
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JGE L30
MOV R1, 1
SHL R1, 3
MOV P3, R1
L30:
MOV P1, P3
MOV R0, 240
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JLE L32
MOV R1, 240
MOV P3, R1
L32:
MOV P1, P4
MOV R0, 1
SHL R0, 3
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JGE L34
MOV R1, 1
SHL R1, 3
MOV P4, R1
L34:
MOV P1, P4
MOV R0, 232
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JLE L36
MOV R1, 232
MOV P4, R1
L36:
MOV P1, P6
CMP P1, P3
; Free P1 (last use)
JZ L38
MOV VX, P6
MOV P0, 28672
MOV P0, [P0]
MOV VY, :P0
XOR VC, VC
TEXT STR39
MOV VX, P6
MOV R1, 1
SHL R1, 3
; Preserve left operand in register across right-side evaluation
MOV R2, R1
MOV P0, 28672
MOV P0, [P0]
MOV R0, R2
ADD R0, P0
; Free P0 (last use)
MOV VY, R0
XOR VC, VC
TEXT STR40
; Preserve left operand in register across right-side evaluation
MOV R2, P6
MOV R3, 1
SHL R3, 4
MOV R0, R2
SUB R0, R3
; Free R3 (last use)
MOV VX, R0
MOV R2, 1
SHL R2, 3
; Preserve left operand in register across right-side evaluation
MOV R3, R2
MOV P0, 28672
MOV P0, [P0]
MOV R0, R3
ADD R0, P0
; Free P0 (last use)
MOV VY, R0
XOR VC, VC
MOV P0, 288
MOV P0, [P0]
TEXT P0
MOV R1, 1
SHL R1, 3
; Preserve left operand in register across right-side evaluation
MOV R2, R1
MOV R0, R2
ADD R0, P6
MOV VX, R0
MOV R2, 1
SHL R2, 3
; Preserve left operand in register across right-side evaluation
MOV R4, R2
MOV P0, 28672
MOV P0, [P0]
MOV R0, R4
ADD R0, P0
; Free P0 (last use)
MOV VY, R0
XOR VC, VC
MOV P0, 288
MOV P0, [P0]
TEXT P0
L38:
MOV P0, 28672
MOV P1, [P0]
CMP P1, P4
; Free P1 (last use)
JZ L42
MOV VX, P6
MOV P0, 28672
MOV P0, [P0]
MOV VY, :P0
XOR VC, VC
TEXT STR39
MOV VX, P6
MOV R1, 1
SHL R1, 3
; Preserve left operand in register across right-side evaluation
MOV R2, R1
MOV P0, 28672
MOV P0, [P0]
MOV R0, R2
ADD R0, P0
; Free P0 (last use)
MOV VY, R0
XOR VC, VC
TEXT STR40
; Preserve left operand in register across right-side evaluation
MOV R2, P6
MOV R3, 1
SHL R3, 4
MOV R0, R2
SUB R0, R3
; Free R3 (last use)
MOV VX, R0
MOV R2, 1
SHL R2, 3
; Preserve left operand in register across right-side evaluation
MOV R3, R2
MOV P0, 28672
MOV P0, [P0]
MOV R0, R3
ADD R0, P0
; Free P0 (last use)
MOV VY, R0
XOR VC, VC
MOV P0, 288
MOV P0, [P0]
TEXT P0
MOV R1, 1
SHL R1, 3
; Preserve left operand in register across right-side evaluation
MOV R2, R1
MOV R0, R2
ADD R0, P6
MOV VX, R0
MOV R2, 1
SHL R2, 3
; Preserve left operand in register across right-side evaluation
MOV R4, R2
MOV P0, 28672
MOV P0, [P0]
MOV R0, R4
ADD R0, P0
; Free P0 (last use)
MOV VY, R0
XOR VC, VC
MOV P0, 288
MOV P0, [P0]
TEXT P0
L42:
MOV VX, P3
MOV VY, P4
MOV VC, 15
TEXT STR39
MOV VX, P3
MOV R1, 1
SHL R1, 3
; Preserve left operand in register across right-side evaluation
MOV R2, R1
MOV R0, R2
ADD R0, P4
MOV VY, R0
MOV VC, 15
TEXT STR40
MOV P1, P5
MOV R0, 255
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JNZ L44
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
MOV R2, 1
SHL R2, 3
; Preserve left operand in register across right-side evaluation
MOV R3, R2
MOV P0, 28672
MOV P0, [P0]
MOV R0, R3
ADD R0, P0
; Free P0 (last use)
MOV VY, R0
XOR VC, VC
MOV P0, 288
MOV P0, [P0]
TEXT P0
MOV R1, 1
SHL R1, 3
; Preserve left operand in register across right-side evaluation
MOV R2, R1
MOV R0, R2
ADD R0, P6
MOV VX, R0
MOV R2, 1
SHL R2, 3
; Preserve left operand in register across right-side evaluation
MOV R4, R2
MOV P0, 28672
MOV P0, [P0]
MOV R0, R4
ADD R0, P0
; Free P0 (last use)
MOV VY, R0
XOR VC, VC
MOV P0, 288
MOV P0, [P0]
TEXT P0
L44:
JMP L6
L7:
HLT
STR0: DEFSTR "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
STR3: DEFSTR "X                              X"
STR4: DEFSTR "--"
STR39: DEFSTR "O"
STR40: DEFSTR "X"