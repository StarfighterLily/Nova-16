ORG 0x0200
MOV SP, 0xFFFF
MOV FP, SP
MOV VM, 0
MOV VL, 1
XOR P1, P1
MOV P2, P1
XOR R0, R0
MOV P3, R0
L1:
MOV R1, 1
CMP R1, 0
JZ L2
KEYIN R0
MOV R2, R0
MOV P4, R2
MOV R7, 97
CMP P4, R7
; Free R7 (last use)
MOV R3, 0
JZ L5
JMP L6
L5:
MOV R3, 1
L6:
CMP R3, 0
JZ L3
MOV R9, 1
MOV R4, P2
SUB R4, R9
; Free R9 (last use)
MOV P2, R4
L3:
MOV P0, P4
MOV P5, 100
CMP P0, P5
; Free P0 (last use)
; Free P5 (last use)
MOV R5, 0
JZ L9
JMP L10
L9:
MOV R5, 1
L10:
CMP R5, 0
JZ L7
MOV P5, P2
MOV P6, 1
MOV R7, P5
ADD R7, P6
; Free P5 (last use)
; Free P6 (last use)
MOV P2, R7
L7:
MOV P6, P4
MOV P7, 115
CMP P6, P7
; Free P6 (last use)
; Free P7 (last use)
MOV R9, 0
JZ L13
JMP L14
L13:
MOV R9, 1
L14:
CMP R9, 0
JZ L11
MOV P7, P3
; Spill P1 to stack (value discarded)
PUSH P1
MOV P1, 1
MOV P0, P7
ADD P0, P1
; Free P7 (last use)
; Free P1 (last use)
MOV P3, P0
; Cleanup 1 spilled register(s) from this statement
POP P1  ; Discard spilled value
L11:
MOV P7, P4
; Spill R0 to stack (value discarded)
PUSH R0
MOV R0, 119
CMP P7, R0
; Free P7 (last use)
; Free R0 (last use)
MOV P1, 0
JZ L17
JMP L18
L17:
MOV P1, 1
L18:
CMP P1, 0
JZ L15
MOV P7, P3
; Spill R1 to stack (value discarded)
PUSH R1
MOV R1, 1
MOV R0, P7
SUB R0, R1
; Free P7 (last use)
; Free R1 (last use)
MOV P3, R0
; Cleanup 1 spilled register(s) from this statement
POP R1  ; Discard spilled value
L15:
; Cleanup 1 spilled register(s) from this statement
POP R0  ; Discard spilled value
; ClrDraw
SFILL 0x00
MOV VX, P2
MOV VY, P3
MOV VC, 15
TEXT STR18
JMP L1
L2:
HLT
STR18: DEFSTR "X"