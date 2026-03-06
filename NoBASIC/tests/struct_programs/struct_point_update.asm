; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; Struct Point declared with fields: x, y
MOV R1, 10
; Allocate struct p (Point) at 0x0120
; Store to p.x
MOV P0, 288
MOV [P0], R1
MOV R1, 20
; Store to p.y
MOV P0, 290
MOV [P0], R1
; Load p.x
MOV P0, 288
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
; Load p.y
MOV P0, 290
MOV P1, [P0]
MOV R1, R2
ADD R1, P1
MOV P2, R1
; Store to p.x
MOV P0, 288
MOV [P0], P2
HLT