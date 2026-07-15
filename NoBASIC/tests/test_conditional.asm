; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV R0, 10
MOV R1, 15
MOV P7:, 0xFF
MOV P2, R1
MOV :P7, 0xFF
MOV P1, P2
MOV SP, P7
CMP P1, R0
MOV FP, SP
; Free P1 (last use)
; Free R0 (last use)
JLE L1
MOV P3, 100
JMP L2
L1:
MOV P3, 200
L2:
MOV R0, 200
; Preserve left operand in register across right-side evaluation
MOV R1, R0
ADD R1, P2
MOV P4, R1
HLT