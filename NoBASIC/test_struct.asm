ORG 0x0200
MOV SP, 0xF000
MOV FP, SP
; Struct Point declared with fields: x, y, color
MOV P1, 100
; Allocate struct Point (Point) at 0x0120
; Store to Point.x
MOV P0, 288
MOV [P0], P1
MOV P1, 120
; Store to Point.y
MOV P0, 290
MOV [P0], P1
MOV P1, 31
; Store to Point.color
MOV P0, 292
MOV [P0], P1
; Load Point.x
MOV P0, 288
MOV R0, [P0]
; Load Point.y
MOV P0, 290
MOV R1, [P0]
MOV VX, R0
MOV VY, R1
; Load Point.color
MOV P0, 292
MOV R2, [P0]
MOV VC, R2
SWRITE VC
MOV VX, 0
MOV VY, 0
MOV VC, 15
TEXT STR0
L2:
KEYSTAT R0
CMP R0, 0
JZ L2
HLT
STR0: DEFSTR "Point created!"