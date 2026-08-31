; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; Struct test declared with fields: x
XOR R1, R1
; Allocate struct test (test) at 0x0120
; Store to test.x
MOV P0, 288
MOV P1, R1
MOV [P0], P1
; Load test.x
MOV P0, 288
MOV P1, [P0]
MOV R0, P1
ADD P1, 1
; Store to test.x
MOV P0, 288
MOV [P0], P1
; Load test.x
MOV P0, 288
MOV P1, [P0]
MOV R0, P1
ITOS P1, R0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
XOR R1, R1
MOV P2, R1
MOV P1, P2
MOV R0, P1
ADD P1, 1
MOV P2, P1
MOV R0, P2
ITOS P1, R0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
HLT