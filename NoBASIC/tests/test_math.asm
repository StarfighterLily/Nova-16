; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
MOV R1, 30
MOV P4, R1
MOV R1, P4
SIN R1
MOV P2, R1
MOV R1, P4
COS R1
MOV P3, R1
; Preserve left operand in register across right-side evaluation
MOV R2, P2
MOV R1, R2
ADD R1, P3
MOV P4, R1
HLT