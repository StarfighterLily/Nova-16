; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
PUSH P2
MOV P1, 5
PUSH P1
; Free R0 (last use)
CALL _func_testlocals_0
ADD SP, 2
POP P2
ITOS P1, R0
MOV R1, R0
MOV VX, 0
MOV P2, R1
MOV VC, 15
MOV R0, P2
TEXT P1
ADD VY, 8
HLT
_func_testlocals_0:
; Function: testlocals
; Parameters: a
; Locals: x, y (4 bytes)
ENTER 4
; LOCAL variable: x @ FP-2
; LOCAL variable: y @ FP-4
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, 1
MOV R2, P1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, FP
ADD P0, -2
MOV [P0], R1
MOV P0, FP
ADD P0, -2
MOV P1, [P0]
MOV R1, P1
SHL R1, 1
; Free P1 (last use)
MOV P0, FP
ADD P0, -4
MOV [P0], R1
MOV P0, FP
ADD P0, -4
MOV P1, [P0]
MOV SP, FP
POP FP
RETN P1