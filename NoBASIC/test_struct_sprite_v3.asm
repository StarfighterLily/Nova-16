ORG 0x0200
MOV SP, 0xF000
MOV FP, SP
; Struct Sprite declared with fields: x, y, vx, vy, color, active
MOV VM, 0
MOV VL, 1
; ClrDraw
MOV VL, 1
SFILL 0x00
MOV P1, 1
SHL P1, 7
; Allocate struct Sprite (Sprite) at 0x0120
; Store to Sprite.x
MOV P0, 288
MOV [P0], P1
MOV P1, 1
SHL P1, 7
; Store to Sprite.y
MOV P0, 290
MOV [P0], P1
MOV P1, 1
; Store to Sprite.vx
MOV P0, 292
MOV [P0], P1
MOV P1, 1
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
MOV R0, 20
CMP P2, R0
JC L3
JZ L3
JMP L2
L3:
; Load Sprite.x
MOV P0, 288
MOV P1, [P0]
MOV R3, :P1
; Load Sprite.y
MOV P0, 290
MOV P1, [P0]
MOV R4, :P1
MOV VX, R3
MOV VY, R4
MOV VC, 0
SWRITE VC
; Load Sprite.x
MOV P0, 288
MOV P1, [P0]
MOV R5, :P1
; Load Sprite.vx
MOV P0, 292
MOV P1, [P0]
MOV R6, :P1
MOV P1, R5
ADD P1, R6
; Store to Sprite.x
MOV P0, 288
MOV [P0], P1
; Load Sprite.y
MOV P0, 290
MOV P1, [P0]
MOV R5, :P1
; Load Sprite.vy
MOV P0, 294
MOV P1, [P0]
MOV R6, :P1
MOV P1, R5
ADD P1, R6
; Store to Sprite.y
MOV P0, 290
MOV [P0], P1
; Load Sprite.x
MOV P0, 288
MOV P1, [P0]
MOV R6, :P1
MOV R7, 250
CMP R6, R7
MOV R5, 0
JGT L6
JMP L7
L6:
MOV R5, 1
L7:
CMP R5, 0
JZ L4
MOV P1, 1
NEG P1
; Store to Sprite.vx
MOV P0, 292
MOV [P0], P1
MOV P1, 250
; Store to Sprite.x
MOV P0, 288
MOV [P0], P1
L4:
; Load Sprite.x
MOV P0, 288
MOV P1, [P0]
MOV R7, :P1
MOV R8, 5
CMP R7, R8
MOV R6, 0
JLT L10
JMP L11
L10:
MOV R6, 1
L11:
CMP R6, 0
JZ L8
MOV P1, 1
; Store to Sprite.vx
MOV P0, 292
MOV [P0], P1
MOV P1, 5
; Store to Sprite.x
MOV P0, 288
MOV [P0], P1
L8:
; Load Sprite.y
MOV P0, 290
MOV P1, [P0]
MOV R8, :P1
MOV R9, 250
CMP R8, R9
MOV R7, 0
JGT L14
JMP L15
L14:
MOV R7, 1
L15:
CMP R7, 0
JZ L12
MOV P1, 1
NEG P1
; Store to Sprite.vy
MOV P0, 294
MOV [P0], P1
MOV P1, 250
; Store to Sprite.y
MOV P0, 290
MOV [P0], P1
L12:
; Load Sprite.y
MOV P0, 290
MOV P1, [P0]
MOV R9, :P1
MOV P0, 5
CMP R9, P0
MOV R8, 0
JLT L18
JMP L19
L18:
MOV R8, 1
L19:
CMP R8, 0
JZ L16
MOV P1, 1
; Store to Sprite.vy
MOV P0, 294
MOV [P0], P1
MOV P1, 5
; Store to Sprite.y
MOV P0, 290
MOV [P0], P1
L16:
; Load Sprite.x
MOV P0, 288
MOV P1, [P0]
MOV R9, :P1
; Load Sprite.y
MOV P0, 290
MOV P0, [P0]
MOV VX, R9
MOV VY, P0
; Load Sprite.color
MOV P0, 296
MOV P4, [P0]
MOV VC, P4
SWRITE VC
XOR R9, R9
MOV P3, R9
L20:
MOV P5, 20000
CMP P3, P5
JC L22
JZ L22
JMP L21
L22:
MOV P1, P3
MOV P3, P1
INC P3
JMP L20
L21:
L23:
KEYSTAT R0
CMP R0, 0
JZ L23
INC P2
JMP L1
L2:
MOV VX, 0
MOV VY, 0
MOV VC, 15
TEXT STR23
L25:
KEYSTAT R0
CMP R0, 0
JZ L25
HLT
STR23: DEFSTR "Done! Struct animation complete!"