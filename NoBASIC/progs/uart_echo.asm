; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
XOR R1, R1
MOV P2, R1
XOR R1, R1
MOV P5, R1
XOR R1, R1
MOV P3, R1
MOV VX, 0
MOV VC, 15
TEXT STR0
ADD VY, 8
MOV VX, 0
MOV VC, 15
TEXT STR1
ADD VY, 8
XOR R0, R0
SERCTRL R0
; Free R0 (last use)
PUSH P2
PUSH P3
PUSH P5
CALL _func_sendbanner_1
POP P5
POP P3
POP P2
L3:
MOV R1, 1
WHILE R1
JZ L4
SERSTAT R0
MOV P2, R0
MOV R0, 1
; Preserve left operand in register across right-side evaluation
MOV R1, R0
MOV P1, R1
AND P1, P2
XOR R1, R1
CMP P1, R1
; Free P1 (last use)
; Free R1 (last use)
JZ L5
SERIN R0
MOV P5, R0
MOV R0, P5
ITOS P1, R0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
L5:
MOV R0, 1
; Preserve left operand in register across right-side evaluation
MOV R1, R0
MOV P1, R1
AND P1, P2
XOR R1, R1
CMP P1, R1
; Free P1 (last use)
; Free R1 (last use)
JNZ L7
KEYIN R0
MOV R1, R0
MOV P3, R1
MOV P1, P3
XOR R0, R0
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JZ L9
MOV P1, P3
MOV R0, 151
CMP P1, R0
; Free P1 (last use)
; Free R0 (last use)
JZ L11
SEROUT P3
L11:
L9:
L7:
JMP L3
L4:
HLT

_func_sendbyte_0:
; Function: sendbyte
; Parameters: value
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
SEROUT P1
; Free P1 (last use)
MOV SP, FP
POP FP
RETN 0

_func_sendbanner_1:
; Function: sendbanner
; Parameters: 
; Locals:  (0 bytes)
ENTER 0
MOV R1, 85
MOV P1, R1
PUSH P1
; Free R1 (last use)
CALL _func_sendbyte_0
ADD SP, 2
MOV R1, 65
MOV P1, R1
PUSH P1
; Free R1 (last use)
CALL _func_sendbyte_0
ADD SP, 2
MOV R1, 82
MOV P1, R1
PUSH P1
; Free R1 (last use)
CALL _func_sendbyte_0
ADD SP, 2
MOV R1, 84
MOV P1, R1
PUSH P1
; Free R1 (last use)
CALL _func_sendbyte_0
ADD SP, 2
MOV R1, 1
SHL R1, 5
MOV P1, R1
PUSH P1
; Free R1 (last use)
CALL _func_sendbyte_0
ADD SP, 2
MOV R1, 82
MOV P1, R1
PUSH P1
; Free R1 (last use)
CALL _func_sendbyte_0
ADD SP, 2
MOV R1, 69
MOV P1, R1
PUSH P1
; Free R1 (last use)
CALL _func_sendbyte_0
ADD SP, 2
MOV R1, 65
MOV P1, R1
PUSH P1
; Free R1 (last use)
CALL _func_sendbyte_0
ADD SP, 2
MOV R1, 68
MOV P1, R1
PUSH P1
; Free R1 (last use)
CALL _func_sendbyte_0
ADD SP, 2
MOV R1, 89
MOV P1, R1
PUSH P1
; Free R1 (last use)
CALL _func_sendbyte_0
ADD SP, 2
MOV R1, 13
MOV P1, R1
PUSH P1
; Free R1 (last use)
CALL _func_sendbyte_0
ADD SP, 2
MOV R1, 10
MOV P1, R1
PUSH P1
; Free R1 (last use)
CALL _func_sendbyte_0
ADD SP, 2
MOV SP, FP
POP FP
RETN 0
STR0: DEFSTR "UART ready"
STR1: DEFSTR "Waiting for RX"