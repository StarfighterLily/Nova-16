; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; Constant folded: -(5) = -5
MOV R0, -5
MOV P1, R0
PUSH P1
; Free R0 (last use)
CALL _func_earlysign_1
ADD SP, 2
MOV R1, R0
MOV P2, R1
MOV R0, 7
MOV P1, R0
PUSH P1
; Free R0 (last use)
CALL _func_earlysign_1
ADD SP, 2
MOV R1, R0
MOV P3, R1
MOV R0, 10
MOV P1, R0
PUSH P1
; Free R0 (last use)
CALL _func_noreturn_2
ADD SP, 2
MOV R1, R0
MOV P4, R1
MOV R0, 1
SHL R0, 2
MOV P1, R0
PUSH P1
; Free R0 (last use)
MOV R0, 3
MOV P1, R0
PUSH P1
; Free R0 (last use)
MOV R0, 1
SHL R0, 1
MOV P1, R0
PUSH P1
; Free R0 (last use)
CALL _func_nestedsum_3
ADD SP, 6
MOV R1, R0
MOV P5, R1
ITOS P1, P2
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
ITOS P1, P3
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
ITOS P1, P4
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
ITOS P1, P5
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV R1, 31
MOV P1, R1
PUSH P1
; Free R1 (last use)
MOV R1, 30
MOV P1, R1
PUSH P1
; Free R1 (last use)
MOV R1, 40
MOV P1, R1
PUSH P1
; Free R1 (last use)
CALL _func_drawtick_4
ADD SP, 6
MOV R1, 15
MOV P1, R1
PUSH P1
; Free R1 (last use)
MOV R1, 50
MOV P1, R1
PUSH P1
; Free R1 (last use)
MOV R1, 60
MOV P1, R1
PUSH P1
; Free R1 (last use)
CALL _func_drawtick_4
ADD SP, 6
HLT

_func_add_0:
; Function: add
; Parameters: a, b
PUSH FP
MOV FP, SP
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand across right-side evaluation
PUSH P1
MOV P0, FP
ADD P0, 6
MOV R3, [P0]
POP P1
MOV R0, P1
ADD R0, R3
; Free P1 (last use)
; Free R3 (last use)
MOV SP, FP
POP FP
RET


_func_earlysign_1:
; Function: earlysign
; Parameters: n
PUSH FP
MOV FP, SP
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
XOR R3, R3
CMP P1, R3
; Free P1 (last use)
; Free R3 (last use)
MOV R1, 0
JLT L3
JMP L4
L3:
MOV R1, 1
L4:
CMP R1, 0
JZ L1
; Constant folded: -(1) = -1
MOV R0, -1
MOV SP, FP
POP FP
RET
L1:
MOV R0, 1
MOV SP, FP
POP FP
RET


_func_noreturn_2:
; Function: noreturn
; Parameters: a
PUSH FP
MOV FP, SP
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand across right-side evaluation
PUSH P1
MOV R2, 1
SHL R2, 1
POP P1
MOV R1, P1
MUL R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P0, 289
MOV [P0], R1
MOV R0, 0
MOV SP, FP
POP FP
RET


_func_nestedsum_3:
; Function: nestedsum
; Parameters: a, b, c
PUSH FP
MOV FP, SP
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
PUSH P1
; Free P1 (last use)
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
PUSH P1
; Free P1 (last use)
CALL _func_add_0
ADD SP, 4
MOV R1, R0
; Preserve left operand across right-side evaluation
MOV P1, R1
PUSH P1
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
POP P1
MOV R1, P1
MOV R0, R1
ADD R0, P1
; Free R1 (last use)
; Free P1 (last use)
MOV SP, FP
POP FP
RET


_func_drawtick_4:
; Function: drawtick
; Parameters: x, y, color
PUSH FP
MOV FP, SP
MOV P0, FP
ADD P0, 4
MOV VX, [P0]
MOV P0, FP
ADD P0, 6
MOV VY, [P0]
MOV P0, FP
ADD P0, 8
MOV VC, [P0]
SWRITE VC
XOR R0, R0
MOV SP, FP
POP FP
RET
