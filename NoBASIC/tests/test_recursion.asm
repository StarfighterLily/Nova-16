; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
MOV R0, 6
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
; Locals:  (0 bytes)
ENTER 0
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
MOV R0, P1
; Free P1 (last use)
LEAVE
RET
L1:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R4, P1
MOV R5, 1
MOV R2, R4
SUB R2, R5
; Free R5 (last use)
MOV R4, R2
PUSH R4
; Free R2 (last use)
CALL _func_fib_0
ADD SP, 2
MOV R1, R0
; Preserve left operand in register across right-side evaluation
MOV R2, R1
MOV P0, FP
ADD P0, 4
MOV R7, [P0]
; Preserve left operand in register across right-side evaluation
MOV R8, R7
MOV R9, 1
SHL R9, 1
MOV R5, R8
SUB R5, R9
; Free R9 (last use)
MOV R8, R5
PUSH R8
; Free R5 (last use)
CALL _func_fib_0
ADD SP, 2
MOV R4, R0
MOV R0, R2
ADD R0, R4
; Free R4 (last use)
LEAVE
RET
