ORG 0x0200
MOV SP, 0xFFFF
MOV FP, SP
MOV R8, 0
MOV R9, 0
MOV R5, R8
ADD R5, R9
; Free R8 (last use)
; Free R9 (last use)
MOV R6, 0
MOV R2, R5
ADD R2, R6
; Free R5 (last use)
; Free R6 (last use)
MOV R3, 0
MOV P1, R2
ADD P1, R3
; Free R2 (last use)
; Free R3 (last use)
MOV P2, P1
ITOS R0, P2
MOV VX, 0
MOV VC, 15
TEXT R0
ADD VY, 8
HLT