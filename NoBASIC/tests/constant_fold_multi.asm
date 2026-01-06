; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; Constant folded: 5 + 3 = 8
MOV R1, 8
MOV P2, R1
; Constant folded: 10 * 2 = 20
MOV R1, 20
MOV P3, R1
; Constant folded: 1 << 4 = 16
MOV R1, 16
MOV P4, R1
; Constant folded: -(42) = -42
MOV R1, -42
MOV P5, R1
MOV VX, 0
MOV VC, 15
TEXT STR0
ADD VY, 8
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
HLT
STR0: DEFSTR "Results:"