ORG 0x0200
MOV SP, 0xFFFF
MOV FP, SP
MOV VM, 0
MOV VL, 1
XOR VX, VX
XOR VY, VY
MOV VC, 31
TEXT STR0
XOR R2, R2
MOV P2, R2
MOV R2, 240
MOV R0, R2
MOV R2, 1
SHL R2, 3
MOV R1, R2
L2:
CMP P2, R0
JGT L3
XOR VX, VX
MOV VY, P2
MOV VC, 31
TEXT STR3
ADD P2, R1
JMP L2
L3:
XOR VX, VX
MOV VY, 248
MOV VC, 31
TEXT STR0
MOV P1, 1
SHL P1, 3
MOV P2, P1
MOV R0, 1
SHL R0, 3
MOV P3, R0
MOV VM, 0
MOV VL, 5
L5:
MOV R1, 1
CMP R1, 0
JZ L6
MOV P4, P2
MOV P5, P3
KEYIN R0
MOV R4, R0
MOV P6, R4
MOV R9, 97
CMP P6, R9
; Free R9 (last use)
MOV R5, 0
JZ L9
JMP L10
L9:
MOV R5, 1
L10:
CMP R5, 0
JZ L7
MOV P0, P2
MOV P7, 1
SHL P7, 3
MOV R6, P0
SUB R6, P7
; Free P0 (last use)
; Free P7 (last use)
MOV P2, R6
L7:
MOV P7, P6
; Spill P1 to stack (value discarded)
PUSH P1
MOV P1, 100
CMP P7, P1
; Free P7 (last use)
; Free P1 (last use)
MOV R7, 0
JZ L13
JMP L14
L13:
MOV R7, 1
L14:
CMP R7, 0
JZ L11
MOV P7, P2
; Spill R0 to stack (value discarded)
PUSH R0
MOV R0, 1
SHL R0, 3
MOV P1, P7
ADD P1, R0
; Free P7 (last use)
; Free R0 (last use)
MOV P2, P1
; Cleanup 1 spilled register(s) from this statement
POP R0  ; Discard spilled value
L11:
; Cleanup 1 spilled register(s) from this statement
POP P1  ; Discard spilled value
MOV P7, P6
; Spill R1 to stack (value discarded)
PUSH R1
MOV R1, 115
CMP P7, R1
; Free P7 (last use)
; Free R1 (last use)
MOV R0, 0
JZ L17
JMP L18
L17:
MOV R0, 1
L18:
CMP R0, 0
JZ L15
MOV P7, P3
; Spill R2 to stack (value discarded)
PUSH R2
MOV R2, 1
SHL R2, 3
MOV R1, P7
ADD R1, R2
; Free P7 (last use)
; Free R2 (last use)
MOV P3, R1
; Cleanup 1 spilled register(s) from this statement
POP R2  ; Discard spilled value
L15:
; Cleanup 1 spilled register(s) from this statement
POP R1  ; Discard spilled value
MOV P7, P6
; Spill R3 to stack (value discarded)
PUSH R3
MOV R3, 119
CMP P7, R3
; Free P7 (last use)
; Free R3 (last use)
MOV R2, 0
JZ L21
JMP L22
L21:
MOV R2, 1
L22:
CMP R2, 0
JZ L19
MOV P7, P3
; Spill R4 to stack (value discarded)
PUSH R4
MOV R4, 1
SHL R4, 3
MOV R3, P7
SUB R3, R4
; Free P7 (last use)
; Free R4 (last use)
MOV P3, R3
; Cleanup 1 spilled register(s) from this statement
POP R4  ; Discard spilled value
L19:
; Cleanup 1 spilled register(s) from this statement
POP R3  ; Discard spilled value
MOV P7, P2
; Spill R5 to stack (value discarded)
PUSH R5
MOV R5, 1
SHL R5, 3
CMP P7, R5
; Free P7 (last use)
; Free R5 (last use)
MOV R4, 0
JLT L25
JMP L26
L25:
MOV R4, 1
L26:
CMP R4, 0
JZ L23
MOV R5, 1
SHL R5, 3
MOV P2, R5
L23:
; Cleanup 1 spilled register(s) from this statement
POP R5  ; Discard spilled value
; Spill R8 to stack (value discarded)
PUSH R8
; Spill R6 to stack (value discarded)
PUSH R6
MOV R6, 248
CMP P2, R6
; Free R6 (last use)
MOV R9, 0
JGT L29
JMP L30
L29:
MOV R9, 1
L30:
CMP R9, 0
JZ L27
MOV R6, 248
MOV P2, R6
L27:
; Cleanup 2 spilled register(s) from this statement
POP R6  ; Discard spilled value
POP R8  ; Discard spilled value
; Spill R7 to stack (value discarded)
PUSH R7
; Spill P1 to stack (value discarded)
PUSH P1
MOV P1, P3
; Spill R0 to stack (value discarded)
PUSH R0
MOV R0, 1
SHL R0, 3
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
MOV P0, 0
JLT L33
JMP L34
L33:
MOV P0, 1
L34:
CMP P0, 0
JZ L31
MOV P1, 1
SHL P1, 3
MOV P3, P1
L31:
; Cleanup 3 spilled register(s) from this statement
POP R0  ; Discard spilled value
POP P1  ; Discard spilled value
POP R7  ; Discard spilled value
; Spill R1 to stack (value discarded)
PUSH R1
; Spill R2 to stack (value discarded)
PUSH R2
MOV R2, 248
CMP P3, R2
; Free R2 (last use)
MOV R0, 0
JGT L37
JMP L38
L37:
MOV R0, 1
L38:
CMP R0, 0
JZ L35
MOV R2, 248
MOV P3, R2
L35:
; Cleanup 2 spilled register(s) from this statement
POP R2  ; Discard spilled value
POP R1  ; Discard spilled value
; Spill R3 to stack (value discarded)
PUSH R3
; Spill R4 to stack (value discarded)
PUSH R4
; Spill R5 to stack (value discarded)
PUSH R5
CMP P4, P2
MOV R7, 0
JNZ L41
JMP L42
L41:
MOV R7, 1
L42:
CMP R7, 0
JZ L39
MOV VX, P4
MOV VY, P5
XOR VC, VC
TEXT STR42
MOV VX, P4
; Spill R9 to stack (value discarded)
PUSH R9
; Spill R8 to stack (value discarded)
PUSH R8
; Spill R6 to stack (value discarded)
PUSH R6
MOV R6, 1
SHL R6, 3
MOV R3, P5
ADD R3, R6
; Free R6 (last use)
MOV VY, R3
XOR VC, VC
TEXT STR43
; Cleanup 3 spilled register(s) from this statement
POP R6  ; Discard spilled value
POP R8  ; Discard spilled value
POP R9  ; Discard spilled value
L39:
; Cleanup 3 spilled register(s) from this statement
POP R5  ; Discard spilled value
POP R4  ; Discard spilled value
POP R3  ; Discard spilled value
MOV P7, P5
; Spill P0 to stack (value discarded)
PUSH P0
MOV P0, P3
CMP P7, P0
; Free P7 (last use)
; Free P0 (last use)
MOV R3, 0
JNZ L47
JMP L48
L47:
MOV R3, 1
L48:
CMP R3, 0
JZ L45
MOV VX, P4
MOV VY, P5
XOR VC, VC
TEXT STR42
MOV VX, P4
MOV P7, P5
; Spill P1 to stack (value discarded)
PUSH P1
MOV P1, 1
SHL P1, 3
MOV R6, P7
ADD R6, P1
; Free P7 (last use)
; Free P1 (last use)
MOV VY, R6
XOR VC, VC
TEXT STR43
; Cleanup 1 spilled register(s) from this statement
POP P1  ; Discard spilled value
L45:
; Cleanup 1 spilled register(s) from this statement
POP P0  ; Discard spilled value
MOV VX, P2
MOV VY, P3
MOV VC, 15
TEXT STR42
MOV VX, P2
MOV P1, P3
MOV P7, 1
SHL P7, 3
MOV R6, P1
ADD R6, P7
; Free P1 (last use)
; Free P7 (last use)
MOV VY, R6
MOV VC, 15
TEXT STR43
JMP L5
L6:
HLT
STR0: DEFSTR "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
STR3: DEFSTR "X                              X"
STR42: DEFSTR "O"
STR43: DEFSTR "X"