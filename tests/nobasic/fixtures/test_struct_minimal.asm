; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; Struct Test declared with fields: val
MOV R1, 42
; Allocate struct test (Test) at 0x0120
; Store to test.val
MOV P1, R1
MOV P0, 288
MOV [P0], P1
; Load test.val
MOV P0, 288
MOV P1, [P0]
XOR VX, VX
XOR VY, VY
MOV VC, 31
MOV P2, P1
TEXT STR0
MOV VX, 1
SHL VX, 6
XOR VY, VY
ITOS P1, R0
MOV R0, P2
MOV VC, 31
TEXT P1
L2:
KEYSTAT R0
CMP R0, 0
JZ L2
HLT
STR0: DEFSTR "Value:"