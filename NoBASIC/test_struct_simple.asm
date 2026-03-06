; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; Struct Point declared with fields: x, y
MOV R1, 10
; Allocate struct point (Point) at 0x0120
; Store to point.x
MOV P0, 288
MOV [P0], R1
MOV R1, 20
; Store to point.y
MOV P0, 290
MOV [P0], R1
XOR VX, VX
XOR VY, VY
MOV VC, 31
TEXT STR0
XOR VX, VX
MOV VY, 1
SHL VY, 4
MOV VC, 31
; Load point.x
MOV P0, 288
MOV P1, [P0]
MOV R0, P1
ITOS P1, R0
TEXT P1
XOR VX, VX
MOV VY, 1
SHL VY, 5
MOV VC, 31
; Load point.y
MOV P0, 290
MOV P1, [P0]
MOV R0, P1
ITOS P1, R0
TEXT P1
L2:
KEYSTAT R0
CMP R0, 0
JZ L2
MOV R1, 50
; Store to point.x
MOV P0, 288
MOV [P0], R1
MOV R1, 100
; Store to point.y
MOV P0, 290
MOV [P0], R1
XOR VX, VX
MOV VY, 48
MOV VC, 31
TEXT STR2
XOR VX, VX
MOV VY, 1
SHL VY, 6
MOV VC, 31
; Load point.x
MOV P0, 288
MOV P1, [P0]
MOV R0, P1
ITOS P1, R0
TEXT P1
XOR VX, VX
MOV VY, 80
MOV VC, 31
; Load point.y
MOV P0, 290
MOV P1, [P0]
MOV R0, P1
ITOS P1, R0
TEXT P1
L4:
KEYSTAT R0
CMP R0, 0
JZ L4
HLT
STR0: DEFSTR "Initial:"
STR2: DEFSTR "Modified:"