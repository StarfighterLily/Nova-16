; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; ClrDraw
MOV VL, 1
MOV VM, 0
SFILL 0x00
XOR R1, R1
MOV P2, R1
MOV R0, 5
L1:
CMP P2, R0
JGT L2
PUSH P2
PUSH P3
PUSH P4
PUSH P2
CALL _func_addten_0
ADD SP, 2
POP P4
POP P3
POP P2
MOV R1, R0
MOV P3, R1
PUSH P2
PUSH P3
PUSH P4
PUSH P3
CALL _func_doubleit_1
ADD SP, 2
POP P4
POP P3
POP P2
MOV R1, R0
MOV VX, P3
MOV P4, R1
MOV VC, 10
MOV VY, P4
SWRITE VC
INC P2
JMP L1
L2:
PUSH P2
PUSH P3
PUSH P4
MOV P1, 5
PUSH P1
; Free R0 (last use)
CALL _func_addten_0
ADD SP, 2
POP P4
POP P3
POP P2
XOR VX, VX
XOR VY, VY
MOV R1, R0
MOV P2, R1
MOV VC, P2
TEXT STR2
HLT
_func_addten_0:
; Function: addten
; Parameters: val
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, 10
MOV R2, P1
MOV R0, R2
ADD R0, R3
; Free R3 (last use)
MOV SP, FP
POP FP
RETN R0
_func_doubleit_1:
; Function: doubleit
; Parameters: val
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV R0, P1
SHL R0, 1
; Free P1 (last use)
MOV SP, FP
POP FP
RETN R0
STR2: DEFSTR "Inline test OK"