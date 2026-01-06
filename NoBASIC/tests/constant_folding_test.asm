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
; Constant folded: 10 - 2 = 8
MOV R1, 8
MOV P3, R1
; Constant folded: 4 * 5 = 20
MOV R1, 20
MOV P3, R1
; Constant folded: 100 / 4 = 25
MOV R1, 25
MOV P3, R1
MOV R0, 1
SHL R0, 1
; Preserve left operand across right-side evaluation
MOV P1, R0
PUSH P1
; Constant folded: 3 * 4 = 12
MOV R2, 12
POP P1
MOV R0, P1
MOV R1, R0
ADD R1, R2
; Free R0 (last use)
; Free R2 (last use)
MOV P3, R1
; Constant folded: 255 & 15 = 15
MOV R1, 15
MOV P4, R1
; Constant folded: 16 | 8 = 24
MOV R1, 24
MOV P4, R1
; Constant folded: 255 ^ 128 = 127
MOV R1, 127
MOV P4, R1
; Constant folded: 1 << 4 = 16
MOV R1, 16
MOV P4, R1
; Constant folded: 256 >> 2 = 64
MOV R1, 64
MOV P5, R1
; Constant folded: 5 > 3 = 1
MOV R1, 1
MOV P5, R1
; Constant folded: 2 < 1 = 0
MOV R1, 0
MOV P6, R1
; Constant folded: 10 = 10 = 1
MOV R1, 1
MOV P6, R1
; Constant folded: -(42) = -42
MOV R1, -42
MOV P6, R1
MOV VX, 0
MOV VC, 15
TEXT STR0
ADD VY, 8
ITOS P1, P2
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV VX, 0
MOV VC, 15
TEXT STR1
ADD VY, 8
ITOS P1, P3
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV VX, 0
MOV VC, 15
TEXT STR2
ADD VY, 8
ITOS P1, P4
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV VX, 0
MOV VC, 15
TEXT STR3
ADD VY, 8
ITOS P1, P5
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV VX, 0
MOV VC, 15
TEXT STR4
ADD VY, 8
ITOS P1, P6
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
HLT
STR0: DEFSTR "x (5+3):"
STR1: DEFSTR "a (2+3*4):"
STR2: DEFSTR "g (1<<4):"
STR3: DEFSTR "i (5>3):"
STR4: DEFSTR "n (-42):"