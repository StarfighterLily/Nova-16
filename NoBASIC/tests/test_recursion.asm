; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
PUSH P2
MOV P1, 6
PUSH P1
; Free R0 (last use)
CALL _func_fib_0
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
_func_fib_0:
; Function: fib
; Parameters: n
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV SP, FP
POP FP
RETN P1
L1:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R5, 1
MOV R4, P1
MOV R2, R4
SUB R2, R5
; Free R5 (last use)
MOV P2, R2
PUSH P2
; Free R2 (last use)
CALL _func_fib_0
ADD SP, 2
MOV R1, R0
; Preserve left operand in register across right-side evaluation
MOV P0, FP
MOV R2, R1
ADD P0, 4
MOV P2, [P0]
; Preserve left operand in register across right-side evaluation
MOV R8, 1
MOV R7, P2
SHL R8, 1
MOV R5, R7
SUB R5, R8
; Free R8 (last use)
MOV P3, R5
PUSH P3
; Free R5 (last use)
CALL _func_fib_0
ADD SP, 2
MOV R4, R0
MOV R0, R2
ADD R0, R4
; Free R4 (last use)
MOV SP, FP
POP FP
RETN R0