ORG 0x0200
MOV SP, 0xF000
MOV FP, SP
MOV R2, 0
MOV R3, 0
MOV P1, R2
MUL P1, R3
; Free R2 (last use)
; Free R3 (last use)
MOV P2, P1
MOV R3, 0
MOV R4, 0
MOV R0, R3
ADD R0, R4
; Free R3 (last use)
; Free R4 (last use)
MOV P2, R0
MOV R3, 1
MOV R4, 1
SHL R4, 1
MIN R2, R3, R4
; Free R3 (last use)
; Free R4 (last use)
MOV R4, 3
MOV R5, 1
SHL R5, 2
MIN R3, R4, R5
; Free R4 (last use)
; Free R5 (last use)
MAX R1, None, None
MOV P2, None
MOV R4, 100
MOV P2, R4
MOV R5, 200
MOV P3, R5
MOV R9, P2
MOV P0, P3
MOV R6, R9
ADD R6, P0
; Free R9 (last use)
; Free P0 (last use)
MOV P4, R6
MOV P0, P2
MOV P5, 1
SHL P5, 1
MOV R7, P0
MUL R7, P5
; Free P0 (last use)
; Free P5 (last use)
MOV P2, R7
MOV P5, P3
MOV P6, 1
SHL P6, 1
MOV R8, P5
DIV R8, P6
; Free P5 (last use)
; Free P6 (last use)
MOV P2, R8
HLT