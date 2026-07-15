; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
PUSH P2
PUSH P3
MOV P1, 5
PUSH P1
; Free R0 (last use)
MOV P1, 3
PUSH P1
; Free R0 (last use)
CALL _func_add_0
ADD SP, 4
POP P3
POP P2
MOV R1, R0
MOV P2, R1
PUSH P2
PUSH P3
MOV P1, 6
PUSH P1
; Free R0 (last use)
MOV P1, 7
PUSH P1
; Free R0 (last use)
CALL _func_multiply_1
ADD SP, 4
POP P3
POP P2
MOV VX, 0
MOV R1, R0
MOV VC, 15
MOV P3, R1
TEXT STR0
ADD VY, 8
ITOS P1, R0
MOV VC, 15
MOV R0, P2
MOV VX, 0
TEXT P1
ADD VY, 8
MOV VC, 15
MOV VX, 0
TEXT STR1
ADD VY, 8
ITOS P1, R0
MOV VC, 15
MOV R0, P3
MOV VX, 0
TEXT P1
ADD VY, 8
HLT
_func_add_0:
; Function: add
; Parameters: a, b
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV P0, FP
MOV R2, P1
ADD P0, 4
MOV P2, [P0]
MOV R0, R2
ADD R0, P2
; Free P2 (last use)
MOV SP, FP
POP FP
RETN R0
_func_multiply_1:
; Function: multiply
; Parameters: a, b
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV P0, FP
MOV R2, P1
ADD P0, 4
MOV P2, [P0]
MUL R0, P2
MOV R0, R2
; Free P2 (last use)
MOV SP, FP
POP FP
RETN R0
STR0: DEFSTR "Add result: "
STR1: DEFSTR "Multiply result: "