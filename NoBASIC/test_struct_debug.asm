ORG 0x0200
MOV SP, 0xF000
MOV FP, SP
; Struct Sprite declared with fields: x, y, vx, vy, color, active
MOV VM, 0
MOV VL, 1
; ClrDraw
MOV VL, 1
SFILL 0x00
MOV P1, 50
; Allocate struct Sprite (Sprite) at 0x0120
; Store to Sprite.x
MOV P0, 288
MOV [P0], P1
MOV P1, 50
; Store to Sprite.y
MOV P0, 290
MOV [P0], P1
MOV P1, 1
SHL P1, 1
; Store to Sprite.vx
MOV P0, 292
MOV [P0], P1
MOV P1, 1
SHL P1, 1
; Store to Sprite.vy
MOV P0, 294
MOV [P0], P1
MOV P1, 31
; Store to Sprite.color
MOV P0, 296
MOV [P0], P1
MOV P1, 1
; Store to Sprite.active
MOV P0, 298
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
; Load Sprite.x
MOV P0, 288
MOV R3, [P0]
; Load Sprite.vx
MOV P0, 292
MOV R4, [P0]
MOV P1, R3
ADD P1, R4
; Store to Sprite.x
MOV P0, 288
MOV [P0], P1
; Load Sprite.y
MOV P0, 290
MOV R3, [P0]
; Load Sprite.vy
MOV P0, 294
MOV R4, [P0]
MOV P1, R3
ADD P1, R4
; Store to Sprite.y
MOV P0, 290
MOV [P0], P1
; Load Sprite.x
MOV P0, 288
MOV R4, [P0]
MOV R5, 250
CMP R4, R5
MOV R3, 0
JGT L6
JMP L7
L6:
MOV R3, 1
L7:
CMP R3, 0
JZ L4
MOV P1, 1
SHL P1, 1
NEG P1
; Store to Sprite.vx
MOV P0, 292
MOV [P0], P1
L4:
; Load Sprite.x
MOV P0, 288
MOV R5, [P0]
MOV R6, 5
CMP R5, R6
MOV R4, 0
JLT L10
JMP L11
L10:
MOV R4, 1
L11:
CMP R4, 0
JZ L8
MOV P1, 1
SHL P1, 1
; Store to Sprite.vx
MOV P0, 292
MOV [P0], P1
L8:
; Load Sprite.y
MOV P0, 290
MOV R6, [P0]
MOV R7, 250
CMP R6, R7
MOV R5, 0
JGT L14
JMP L15
L14:
MOV R5, 1
L15:
CMP R5, 0
JZ L12
MOV P1, 1
SHL P1, 1
NEG P1
; Store to Sprite.vy
MOV P0, 294
MOV [P0], P1
L12:
; Load Sprite.y
MOV P0, 290
MOV R7, [P0]
MOV R8, 5
CMP R7, R8
MOV R6, 0
JLT L18
JMP L19
L18:
MOV R6, 1
L19:
CMP R6, 0
JZ L16
MOV P1, 1
SHL P1, 1
; Store to Sprite.vy
MOV P0, 294
MOV [P0], P1
L16:
; Load Sprite.x
MOV P0, 288
MOV R7, [P0]
; Load Sprite.y
MOV P0, 290
MOV R8, [P0]
MOV VX, R7
MOV VY, R8
; Load Sprite.color
MOV P0, 296
MOV R9, [P0]
MOV VC, R9
SWRITE VC
XOR R7, R7
MOV P3, R7
L20:
MOV P5, 10000
CMP P3, P5
JC L22
JZ L22
JMP L21
L22:
MOV P1, P3
MOV P2, P1
INC P3
JMP L20
L21:
INC P2
JMP L1
L2:
MOV VX, 0
MOV VY, 0
MOV VC, 15
TEXT STR22
L24:
KEYSTAT R0
CMP R0, 0
JZ L24
HLT
STR22: DEFSTR "Done! Check the trail!"