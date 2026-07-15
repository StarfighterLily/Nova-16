; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P0, 602
MOV P7:, 0xFF
MOV R1, 21
MOV R2, 1
MOV R3, 1
MIN R0, R2, R3
SHL R3, 1
MOV P2, R1
MOV :P7, 0xFF
MOV P2, P0
MOV SP, P7
MOV FP, SP
; Free R2 (last use)
; Free R3 (last use)
MIN R2, R3, R4
MOV R4, 1
SHL R4, 2
MOV R3, 3
; Free R3 (last use)
; Free R4 (last use)
MAX R1, R0, R2
; Free R0 (last use)
; Free R2 (last use)
MOV P0, 300
MOV P2, R1
MOV R1, 100
MOV P4, P0
MOV P2, R1
MOV P3, 200
MOV P4, 200
MOV P2, 100
HLT