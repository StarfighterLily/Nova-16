; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
MOV R0, 5
MOV P1, R0
PUSH P1
; Free R0 (last use)
MOV R0, 3
MOV P1, R0
PUSH P1
; Free R0 (last use)
CALL _func_add_0
ADD SP, 4
MOV R1, R0
MOV P7, R1
MOV R0, P7
ITOS P1, R0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV R0, 6
MOV P1, R0
PUSH P1
; Free R0 (last use)
MOV R0, 7
MOV P1, R0
PUSH P1
; Free R0 (last use)
CALL _func_multiply_1
ADD SP, 4
MOV R1, R0
MOV P2, R1
MOV R0, P2
ITOS P1, R0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
HLT

_func_add_0:
; Function: add
; Parameters: a, b
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV P0, FP
ADD P0, 6
MOV R4, [P0]
MOV R0, R2
ADD R0, R4
; Free R4 (last use)
LEAVE
RET

_func_multiply_1:
; Function: multiply
; Parameters: x, y
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV P0, FP
ADD P0, 6
MOV R4, [P0]
MOV R0, R2
MUL R0, R4
; Free R4 (last use)
LEAVE
RET