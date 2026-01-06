; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV SP, 0xFFFF
MOV FP, SP
MOV R0, 3
PUSH R0
; Free R0 (last use)
MOV R0, 5
PUSH R0
; Free R0 (last use)
CALL _func_add_0
ADD SP, 4
MOV R1, R0
MOV P2, R1
ITOS P1, P2
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV R0, 7
PUSH R0
; Free R0 (last use)
MOV R0, 6
PUSH R0
; Free R0 (last use)
CALL _func_multiply_1
ADD SP, 4
MOV R1, R0
MOV P2, R1
ITOS P1, P2
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
HLT

_func_add_0:
; Function: add
; Parameters: a, b
PUSH FP
MOV FP, SP
MOV P0, 288
MOV P0, [P0]
MOV P0, 290
MOV P0, [P0]
MOV R0, P0
ADD R0, P0
MOV SP, FP
POP FP
RET


_func_multiply_1:
; Function: multiply
; Parameters: x, y
PUSH FP
MOV FP, SP
MOV P0, 292
MOV P0, [P0]
MOV P0, 294
MOV P0, [P0]
MOV R0, P0
MUL R0, P0
MOV SP, FP
POP FP
RET
