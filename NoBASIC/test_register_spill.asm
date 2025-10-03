ORG 0x0200
MOV SP, 0xFFFF
MOV FP, SP
MOV R5, 0
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
; Spill P1 to stack
PUSH P1
; Spill R0 to stack
PUSH R0
; Spill R2 to stack
PUSH R2
; Spill R1 to stack
PUSH R1
; Spill R3 to stack
PUSH R3
; Spill R4 to stack
PUSH R4
; Spill R5 to stack
PUSH R5
; Spill R6 to stack
PUSH R6
; Spill R7 to stack
PUSH R7
; Spill R8 to stack
PUSH R8
; Spill R9 to stack
PUSH R9
; Spill P0 to stack
PUSH P0
; Spill P5 to stack
PUSH P5
; Spill P6 to stack
PUSH P6
; Spill P7 to stack
PUSH P7
; Spill P1 to stack
PUSH P1
; Spill R0 to stack
PUSH R0
; Spill R2 to stack
PUSH R2
; Spill R1 to stack
PUSH R1
; Spill R3 to stack
PUSH R3
; Spill R4 to stack
PUSH R4
; Spill R5 to stack
PUSH R5
; Spill R6 to stack
PUSH R6
; Spill R7 to stack
PUSH R7
; Spill R8 to stack
PUSH R8
; Spill R9 to stack
PUSH R9
; Constant folded: 1 + 2 = 3
MOV R9, 3
; Spill P0 to stack
PUSH P0
MOV P0, 3
MOV R6, R9
ADD R6, P0
; Free R9 (last use)
; Free P0 (last use)
MOV R7, 1
SHL R7, 2
MOV R3, R6
ADD R3, R7
; Free R6 (last use)
; Free R7 (last use)
MOV R4, 5
MOV R0, R3
ADD R0, R4
; Free R3 (last use)
; Free R4 (last use)
MOV R1, 6
MOV P6, R0
ADD P6, R1
; Free R0 (last use)
; Free R1 (last use)
MOV R0, 7
MOV R9, P6
ADD R9, R0
; Free P6 (last use)
; Free R0 (last use)
MOV R8, 1
SHL R8, 3
MOV R6, R9
ADD R6, R8
; Free R8 (last use)
MOV R5, 9
MOV R3, R6
ADD R3, R5
; Free R5 (last use)
MOV R1, 10
MOV R0, R3
ADD R0, R1
; Free R1 (last use)
MOV P1, 11
MOV P6, R0
ADD P6, P1
; Free P1 (last use)
MOV P5, 12
MOV R9, P6
ADD R9, P5
; Free P5 (last use)
MOV R8, 13
MOV R6, R9
ADD R6, R8
; Free R8 (last use)
MOV R5, 14
MOV R3, R6
ADD R3, R5
; Free R5 (last use)
MOV R2, 15
MOV R0, R3
ADD R0, R2
; Free R2 (last use)
MOV P3, R0
MOV R2, 0
MOV R3, 0
MOV P1, R2
MUL P1, R3
; Free R2 (last use)
; Free R3 (last use)
MOV P4, P1
MOV R6, 0
MOV R7, 0
MOV R3, R6
ADD R3, R7
; Free R6 (last use)
; Free R7 (last use)
MOV R4, 0
MOV R0, R3
ADD R0, R4
; Free R3 (last use)
; Free R4 (last use)
MOV P2, R0
MOV R7, 0
MOV R8, 0
MOV R4, R7
ADD R4, R8
; Free R7 (last use)
; Free R8 (last use)
MOV R5, 0
MOV R1, R4
ADD R1, R5
; Free R4 (last use)
; Free R5 (last use)
MOV P2, R1
HLT