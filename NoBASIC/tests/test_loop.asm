; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; ClrDraw
MOV VM, 0
MOV VL, 1
SFILL 0x00
XOR R1, R1
MOV P2, R1
MOV R1, 10
MOV R0, R1
L1:
CMP P2, R0
JGT L2
; Preserve left operand in register across right-side evaluation
MOV R2, P2
MOV R3, 1
SHL R3, 1
MOV R1, R2
MUL R1, R3
; Free R3 (last use)
MOV P3, R1
INC P2
JMP L1
L2:
HLT