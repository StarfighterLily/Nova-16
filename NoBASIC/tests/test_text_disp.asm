; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
MOV VX, 0
MOV VC, 15
TEXT STR0
ADD VY, 8
MOV R1, 42
MOV P2, R1
MOV R0, P2
ITOS P1, R0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
; Constant folded: 5 + 3 = 8
MOV R1, 8
ITOS P1, R1
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV R0, 10
MOV P1, R0
PUSH P1
; Free R0 (last use)
MOV R0, 20
MOV P1, R0
PUSH P1
; Free R0 (last use)
CALL _func_add_0
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
STR0: DEFSTR "Hello World"