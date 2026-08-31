; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV R0, 30
MOV P7:, 0xFF
MOV R1, 30
MOV :P7, 0xFF
MOV P4, R1
MOV SP, P7
MOV R1, R0
MOV FP, SP
; Free R0 (last use)
SIN R1
MOV R0, 30
MOV P2, R1
MOV R1, R0
; Free R0 (last use)
COS R1
MOV P3, R1
; Preserve left operand in register across right-side evaluation
MOV R2, P2
MOV R1, R2
ADD R1, P3
MOV P4, R1
HLT