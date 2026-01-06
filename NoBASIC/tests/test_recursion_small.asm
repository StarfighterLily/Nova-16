; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
MOV R0, 1
SHL R0, 2
MOV P1, R0
PUSH P1
; Free R0 (last use)
CALL _func_fib_0
ADD SP, 2
MOV R1, R0
MOV P2, R1
ITOS P1, P2
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
HLT

_func_fib_0:
; Function: fib
; Parameters: n
PUSH FP
MOV FP, SP
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV R3, 1
SHL R3, 1
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
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV SP, FP
POP FP
RET
L1:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand across right-side evaluation
PUSH P1
MOV R4, 1
POP P1
MOV R2, P1
SUB R2, R4
; Free P1 (last use)
; Free R4 (last use)
MOV P1, R2
PUSH P1
; Free R2 (last use)
CALL _func_fib_0
ADD SP, 2
MOV R1, R0
; Preserve left operand across right-side evaluation
MOV P1, R1
PUSH P1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand across right-side evaluation
PUSH P1
MOV R6, 1
SHL R6, 1
POP P1
MOV R4, P1
SUB R4, R6
; Free P1 (last use)
; Free R6 (last use)
MOV P1, R4
PUSH P1
; Free R4 (last use)
CALL _func_fib_0
ADD SP, 2
MOV R2, R0
POP P1
MOV R1, P1
MOV R0, R1
ADD R0, R2
; Free R1 (last use)
; Free R2 (last use)
MOV SP, FP
POP FP
RET
