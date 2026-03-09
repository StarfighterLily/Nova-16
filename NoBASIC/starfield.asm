; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
MOV VM, 0
MOV VL, 1
XOR R1, R1
MOV P2, R1
MOV R1, 25
MOV R0, R1
L1:
CMP P2, R0
JGT L2
XOR R0, R0
MOV P3, R0
MOV R0, 20
MOV P5, R0
L3:
CMP P3, P5
JGT L4
RND R1
; Preserve left operand in register across right-side evaluation
MOV R2, R1
MOV R0, R2
ADD R0, P2
MOV VX, R0
RND R2
; Preserve left operand in register across right-side evaluation
MOV R4, R2
MOV R0, R4
SUB R0, P3
MOV VY, R0
MOV R4, 1
MOV R6, 5
RNDR R0, R4, R6
; Free R4 (last use)
; Free R6 (last use)
MOV VC, R0
SWRITE VC
INC P3
JMP L3
L4:
INC P2
JMP L1
L2:
MOV R0, 1
XOR R1, R1
SROT R0, R1
; Free R0 (last use)
; Free R1 (last use)
MOV VM, 0
MOV VL, 1
SHL VL, 1
XOR R1, R1
MOV P2, R1
MOV R1, 20
MOV R0, R1
L5:
CMP P2, R0
JGT L6
XOR R0, R0
MOV P3, R0
MOV R0, 15
MOV P5, R0
L7:
CMP P3, P5
JGT L8
RND R1
; Preserve left operand in register across right-side evaluation
MOV R2, R1
MOV R0, R2
ADD R0, P2
MOV VX, R0
RND R2
; Preserve left operand in register across right-side evaluation
MOV R4, R2
MOV R0, R4
ADD R0, P2
MOV VY, R0
MOV R4, 6
MOV R6, 10
RNDR R0, R4, R6
; Free R4 (last use)
; Free R6 (last use)
MOV VC, R0
SWRITE VC
INC P3
JMP L7
L8:
INC P2
JMP L5
L6:
MOV R0, 1
MOV R1, 1
SROT R0, R1
; Free R0 (last use)
; Free R1 (last use)
MOV VM, 0
MOV VL, 3
XOR R1, R1
MOV P2, R1
MOV R1, 15
MOV R0, R1
L9:
CMP P2, R0
JGT L10
XOR R0, R0
MOV P3, R0
MOV R0, 10
MOV P5, R0
L11:
CMP P3, P5
JGT L12
RND R1
; Preserve left operand in register across right-side evaluation
MOV R2, R1
MOV R0, R2
SUB R0, P2
MOV VX, R0
RND R2
; Preserve left operand in register across right-side evaluation
MOV R4, R2
MOV R0, R4
SUB R0, P3
MOV VY, R0
MOV R4, 11
MOV R6, 15
RNDR R0, R4, R6
; Free R4 (last use)
; Free R6 (last use)
MOV VC, R0
SWRITE VC
INC P3
JMP L11
L12:
INC P2
JMP L9
L10:
MOV R0, 1
MOV R1, 1
SHL R1, 1
SROT R0, R1
; Free R0 (last use)
; Free R1 (last use)
MOV VM, 0
MOV VL, 1
SHL VL, 2
MOV VX, 80
MOV VY, 118
MOV VC, 31
TEXT STR12
L14:
MOV R1, 1
WHILE R1
JZ L15
MOV VM, 0
MOV VL, 1
XOR R0, R0
MOV R1, 1
SROL R0, R1
; Free R0 (last use)
; Free R1 (last use)
MOV VM, 0
MOV VL, 1
SHL VL, 1
XOR R0, R0
MOV R1, 1
SHL R1, 1
SROL R0, R1
; Free R0 (last use)
; Free R1 (last use)
MOV VM, 0
MOV VL, 3
XOR R0, R0
MOV R1, 3
SROL R0, R1
; Free R0 (last use)
; Free R1 (last use)
XOR R1, R1
MOV P2, R1
MOV R1, 255
MOV R0, R1
L16:
CMP P2, R0
JGT L17
XOR R0, R0
MOV P3, R0
MOV R0, 40
MOV P5, R0
L18:
CMP P3, P5
JGT L19
INC P3
JMP L18
L19:
INC P2
JMP L16
L17:
JMP L14
L15:
HLT
STR12: DEFSTR "StarField"