; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
PUSH P2
PUSH P3
PUSH P4
PUSH P6
MOV P0, -5
PUSH P0
; Free P0 (last use)
CALL _func_earlysign_1
ADD SP, 2
POP P6
POP P4
POP P3
POP P2
MOV R1, R0
MOV P2, R1
PUSH P2
PUSH P3
PUSH P4
PUSH P6
MOV P1, 7
PUSH P1
; Free R0 (last use)
CALL _func_earlysign_1
ADD SP, 2
POP P6
POP P4
POP P3
POP P2
MOV R1, R0
MOV P6, R1
PUSH P2
PUSH P3
PUSH P4
PUSH P6
MOV P1, 10
PUSH P1
; Free R0 (last use)
CALL _func_noreturn_2
ADD SP, 2
POP P6
POP P4
POP P3
POP P2
MOV R1, R0
MOV P3, R1
PUSH P2
PUSH P3
PUSH P4
PUSH P6
MOV R0, 1
SHL R0, 1
MOV P1, R0
PUSH P1
; Free R0 (last use)
MOV R0, 3
MOV P1, R0
PUSH P1
; Free R0 (last use)
MOV R0, 1
SHL R0, 2
MOV P1, R0
PUSH P1
; Free R0 (last use)
CALL _func_nestedsum_3
ADD SP, 6
POP P6
POP P4
POP P3
POP P2
ITOS P1, R0
MOV R1, R0
MOV VX, 0
MOV P4, R1
MOV R0, P2
MOV VC, 15
TEXT P1
ADD VY, 8
ITOS P1, R0
MOV VC, 15
MOV R0, P6
MOV VX, 0
TEXT P1
ADD VY, 8
ITOS P1, R0
MOV VC, 15
MOV R0, P3
MOV VX, 0
TEXT P1
ADD VY, 8
ITOS P1, R0
MOV VC, 15
MOV R0, P4
MOV VX, 0
TEXT P1
ADD VY, 8
PUSH P2
PUSH P3
PUSH P4
PUSH P6
MOV P1, 40
PUSH P1
; Free R1 (last use)
MOV P1, 30
PUSH P1
; Free R1 (last use)
MOV P1, 31
PUSH P1
; Free R1 (last use)
CALL _func_drawtick_4
ADD SP, 6
POP P6
POP P4
POP P3
POP P2
PUSH P2
PUSH P3
PUSH P4
PUSH P6
MOV P1, 60
PUSH P1
; Free R1 (last use)
MOV P1, 50
PUSH P1
; Free R1 (last use)
MOV P1, 15
PUSH P1
; Free R1 (last use)
CALL _func_drawtick_4
ADD SP, 6
POP P6
POP P4
POP P3
POP P2
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
_func_earlysign_1:
; Function: earlysign
; Parameters: n
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L1
; Constant folded: -(1) = -1
MOV SP, FP
MOV R0, -1
POP FP
RETN R0
L1:
MOV SP, FP
MOV R0, 1
POP FP
RETN R0
_func_noreturn_2:
; Function: noreturn
; Parameters: a
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV R1, P1
SHL R1, 1
; Free P1 (last use)
MOV P0, 0
MOV P1, 288
MOV :P0, R1
MOV [P1], P0
MOV SP, FP
POP FP
RETN 0
_func_nestedsum_3:
; Function: nestedsum
; Parameters: a, b, c
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
PUSH P1
; Free P1 (last use)
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
PUSH P1
; Free P1 (last use)
CALL _func_add_0
ADD SP, 4
MOV R1, R0
; Preserve left operand in register across right-side evaluation
MOV P0, FP
MOV R4, R1
ADD P0, 4
MOV P1, [P0]
MOV R0, R4
ADD R0, P1
; Free P1 (last use)
MOV SP, FP
POP FP
RETN R0
_func_drawtick_4:
; Function: drawtick
; Parameters: x, y, color
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 8
MOV P1, [P0]
MOV P0, FP
MOV VX, :P1
ADD P0, 6
MOV P1, [P0]
MOV P0, FP
MOV VY, :P1
ADD P0, 4
MOV P1, [P0]
MOV VC, :P1
SWRITE VC
XOR R0, R0
MOV SP, FP
POP FP
RETN R0