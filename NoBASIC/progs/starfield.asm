; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV VL, 1
XOR R1, R1
MOV P7:, 0xFF
MOV P2, R1
MOV :P7, 0xFF
MOV R1, 25
MOV SP, P7
MOV R0, R1
MOV FP, SP
MOV VM, 0
L1:
CMP P2, R0
JGT L2
XOR R0, R0
MOV P3, R0
MOV P5, 20
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
MOV R0, R2
SUB R0, P3
MOV R6, 5
MOV VY, R0
MOV R4, 1
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
XOR R1, R1
MOV R0, 1
SROT R0, R1
; Free R0 (last use)
; Free R1 (last use)
MOV VL, 1
MOV VM, 0
SHL VL, 1
XOR R1, R1
MOV P2, R1
MOV R0, 20
L5:
CMP P2, R0
JGT L6
XOR R0, R0
MOV P3, R0
MOV P5, 15
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
MOV R0, R2
ADD R0, P2
MOV R6, 10
MOV VY, R0
MOV R4, 6
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
MOV R1, 1
MOV R0, 1
SROT R0, R1
; Free R0 (last use)
; Free R1 (last use)
XOR R1, R1
MOV P2, R1
MOV VM, 0
MOV R1, 15
MOV VL, 3
MOV R0, R1
L9:
CMP P2, R0
JGT L10
XOR R0, R0
MOV P3, R0
MOV P5, 10
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
MOV R0, R2
SUB R0, P3
MOV R6, 15
MOV VY, R0
MOV R4, 11
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
MOV R1, 1
MOV R0, 1
SHL R1, 1
SROT R0, R1
; Free R0 (last use)
; Free R1 (last use)
MOV VL, 1
MOV VY, 118
SHL VL, 2
MOV VX, 80
MOV VM, 0
MOV VC, 31
TEXT STR12
L14:
MOV R1, 1
WHILE R1
JZ L15
XOR R0, R0
MOV R1, 1
MOV VM, 0
MOV VL, 1
SROL R0, R1
; Free R0 (last use)
; Free R1 (last use)
MOV VL, 1
MOV R1, 1
SHL VL, 1
XOR R0, R0
SHL R1, 1
MOV VM, 0
SROL R0, R1
; Free R0 (last use)
; Free R1 (last use)
XOR R0, R0
MOV R1, 3
MOV VM, 0
MOV VL, 3
SROL R0, R1
; Free R0 (last use)
; Free R1 (last use)
XOR R1, R1
MOV P2, R1
MOV R0, 255
L16:
CMP P2, R0
JGT L17
XOR R0, R0
MOV P3, R0
MOV P5, 40
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