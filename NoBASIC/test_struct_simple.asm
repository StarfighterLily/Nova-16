ORG 0x0200
MOV SP, 0xF000
MOV FP, SP
; Struct Point declared with fields: x, y
MOV VM, 0
MOV VL, 1
; ClrDraw
MOV VL, 1
SFILL 0x00
MOV P1, 1
SHL P1, 7
; Allocate struct Point (Point) at 0x0120
; Store to Point.y
MOV P0, 290
MOV [P0], P1
XOR R1, R1
MOV P2, R1
L1:
MOV R0, 100
CMP P2, R0
JC L3
JZ L3
JMP L2
L3:
MOV P1, P2
; Store to Point.x
MOV P0, 288
MOV [P0], P1
; Load Point.x
MOV P0, 288
MOV P1, [P0]
MOV R2, :P1
; Load Point.y
MOV P0, 290
MOV P1, [P0]
MOV R3, :P1
MOV VX, R2
MOV VY, R3
MOV R4, 31
MOV VC, R4
SWRITE VC
INC P2
JMP L1
L2:
MOV VX, 0
MOV VY, 0
MOV VC, 15
TEXT STR3
L5:
KEYSTAT R0
CMP R0, 0
JZ L5
HLT
STR3: DEFSTR "Line drawn!"