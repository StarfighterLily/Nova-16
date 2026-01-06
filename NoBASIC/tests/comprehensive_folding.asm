; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; Constant folded: 100 + 50 = 150
MOV R1, 150
MOV P2, R1
; Constant folded: 200 - 75 = 125
MOV R1, 125
MOV P2, R1
; Constant folded: 12 * 8 = 96
MOV R1, 96
MOV P2, R1
; Constant folded: 144 / 12 = 12
MOV R1, 12
MOV P2, R1
; Constant folded: 255 & 127 = 127
MOV R1, 127
MOV P2, R1
; Constant folded: 16 | 8 = 24
MOV R1, 24
MOV P2, R1
; Constant folded: 255 ^ 128 = 127
MOV R1, 127
MOV P2, R1
; Constant folded: 1 << 8 = 256
MOV R1, 256
MOV P2, R1
; Constant folded: 1024 >> 4 = 64
MOV R1, 64
MOV P2, R1
; Constant folded: 10 > 5 = 1
MOV R1, 1
MOV P2, R1
; Constant folded: 3 < 2 = 0
MOV R1, 0
MOV P2, R1
; Constant folded: 7 = 7 = 1
MOV R1, 1
MOV P2, R1
; Constant folded: 5 <> 5 = 0
MOV R1, 0
MOV P2, R1
; Constant folded: -(128) = -128
MOV R1, -128
MOV P2, R1
; Constant folded: 8 + 7 = 15
MOV R1, 15
MOV P2, R1
; Constant folded: 12 + 0 = 12
MOV R1, 12
MOV P3, R1
; Constant folded: 4 + 4 = 8
MOV R1, 8
MOV P3, R1
; Constant folded: 1 - 1 = 0
MOV R1, 0
MOV P3, R1
; ClrDraw
MOV VM, 0
MOV VL, 1
SFILL 0x00
XOR R1, R1
MOV P3, R1
MOV R1, 50
MOV R0, R1
L1:
CMP P3, R0
JGT L2
XOR R0, R0
MOV P4, R0
MOV R0, 50
MOV P5, R0
L3:
CMP P4, P5
JGT L4
MOV VX, P4
MOV VY, P3
MOV VC, P2
SWRITE VC
INC P4
JMP L3
L4:
INC P3
JMP L1
L2:
MOV VX, 0
MOV VC, 15
TEXT STR4
ADD VY, 8
MOV VX, 0
MOV VC, 15
TEXT STR5
ADD VY, 8
HLT
STR4: DEFSTR "Constant folding demo complete!"
STR5: DEFSTR "All expressions evaluated at compile time"