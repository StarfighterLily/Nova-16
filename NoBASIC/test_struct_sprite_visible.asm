ORG 0x0200
MOV SP, 0xF000
MOV FP, SP
; Struct Ball declared with fields: x, y, vx, vy, color
MOV VM, 0
MOV VL, 1
; ClrDraw
MOV VL, 1
SFILL 0x00
MOV P1, 1
SHL P1, 7
; Allocate struct Ball (Ball) at 0x0120
; Store to Ball.x
MOV P0, 288
MOV [P0], P1
MOV P1, 1
SHL P1, 7
; Store to Ball.y
MOV P0, 290
MOV [P0], P1
MOV P1, 1
SHL P1, 3
; Store to Ball.vx
MOV P0, 292
MOV [P0], P1
MOV P1, 6
; Store to Ball.vy
MOV P0, 294
MOV [P0], P1
MOV P1, 31
; Store to Ball.color
MOV P0, 296
MOV [P0], P1
XOR R2, R2
MOV P2, R2
L1:
MOV R0, 100
CMP P2, R0
JC L3
JZ L3
JMP L2
L3:
; Load Ball.x
MOV P0, 288
MOV R3, [P0]
; Load Ball.y
MOV P0, 290
MOV R4, [P0]
MOV VX, R3
MOV VY, R4
; Load Ball.color
MOV P0, 296
MOV R5, [P0]
MOV VC, R5
SWRITE VC
; Load Ball.x
MOV P0, 288
MOV R4, [P0]
MOV R5, 1
MOV R3, R4
ADD R3, R5
; Load Ball.y
MOV P0, 290
MOV R4, [P0]
MOV VX, R3
MOV VY, R4
; Load Ball.color
MOV P0, 296
MOV R5, [P0]
MOV VC, R5
SWRITE VC
; Load Ball.x
MOV P0, 288
MOV R3, [P0]
; Load Ball.y
MOV P0, 290
MOV R5, [P0]
MOV R6, 1
MOV R4, R5
ADD R4, R6
MOV VX, R3
MOV VY, R4
; Load Ball.color
MOV P0, 296
MOV R5, [P0]
MOV VC, R5
SWRITE VC
; Load Ball.x
MOV P0, 288
MOV R4, [P0]
MOV R5, 1
MOV R3, R4
ADD R3, R5
; Load Ball.y
MOV P0, 290
MOV R5, [P0]
MOV R6, 1
MOV R4, R5
ADD R4, R6
MOV VX, R3
MOV VY, R4
; Load Ball.color
MOV P0, 296
MOV R5, [P0]
MOV VC, R5
SWRITE VC
; Load Ball.x
MOV P0, 288
MOV R3, [P0]
; Load Ball.vx
MOV P0, 292
MOV R4, [P0]
MOV P1, R3
ADD P1, R4
; Store to Ball.x
MOV P0, 288
MOV [P0], P1
; Load Ball.y
MOV P0, 290
MOV R3, [P0]
; Load Ball.vy
MOV P0, 294
MOV R4, [P0]
MOV P1, R3
ADD P1, R4
; Store to Ball.y
MOV P0, 290
MOV [P0], P1
; Load Ball.x
MOV P0, 288
MOV R4, [P0]
MOV R5, 245
CMP R4, R5
MOV R3, 0
JGT L6
JMP L7
L6:
MOV R3, 1
L7:
CMP R3, 0
JZ L4
XOR R4, R4
; Load Ball.vx
MOV P0, 292
MOV R5, [P0]
MOV P1, R4
SUB P1, R5
; Store to Ball.vx
MOV P0, 292
MOV [P0], P1
MOV P1, 245
; Store to Ball.x
MOV P0, 288
MOV [P0], P1
L4:
; Load Ball.x
MOV P0, 288
MOV R5, [P0]
MOV R6, 10
CMP R5, R6
MOV R4, 0
JLT L10
JMP L11
L10:
MOV R4, 1
L11:
CMP R4, 0
JZ L8
XOR R5, R5
; Load Ball.vx
MOV P0, 292
MOV R6, [P0]
MOV P1, R5
SUB P1, R6
; Store to Ball.vx
MOV P0, 292
MOV [P0], P1
MOV P1, 10
; Store to Ball.x
MOV P0, 288
MOV [P0], P1
L8:
; Load Ball.y
MOV P0, 290
MOV R6, [P0]
MOV R7, 245
CMP R6, R7
MOV R5, 0
JGT L14
JMP L15
L14:
MOV R5, 1
L15:
CMP R5, 0
JZ L12
XOR R6, R6
; Load Ball.vy
MOV P0, 294
MOV R7, [P0]
MOV P1, R6
SUB P1, R7
; Store to Ball.vy
MOV P0, 294
MOV [P0], P1
MOV P1, 245
; Store to Ball.y
MOV P0, 290
MOV [P0], P1
L12:
; Load Ball.y
MOV P0, 290
MOV R7, [P0]
MOV R8, 10
CMP R7, R8
MOV R6, 0
JLT L18
JMP L19
L18:
MOV R6, 1
L19:
CMP R6, 0
JZ L16
XOR R7, R7
; Load Ball.vy
MOV P0, 294
MOV R8, [P0]
MOV P1, R7
SUB P1, R8
; Store to Ball.vy
MOV P0, 294
MOV [P0], P1
MOV P1, 10
; Store to Ball.y
MOV P0, 290
MOV [P0], P1
L16:
INC P2
JMP L1
L2:
XOR VX, VX
XOR VY, VY
MOV VC, 15
TEXT STR19
HLT
STR19: DEFSTR "Ball bounced!"