; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; GLOBAL variable: counter @ 0x0120
; GLOBAL variable: total @ 0x0122
; GLOBAL variable: max @ 0x0124
XOR R1, R1
MOV P2, R1
XOR R1, R1
MOV P3, R1
MOV R1, 10
MOV P4, R1
MOV R1, 1
MOV R0, P4
MOV P5, R1
L1:
CMP P5, R0
JGT L2
MOV R0, 1
; Preserve left operand in register across right-side evaluation
MOV R1, R0
ADD R1, P2
MOV P2, R1
; Preserve left operand in register across right-side evaluation
MOV R2, P5
MOV R1, R2
ADD R1, P3
INC P5
MOV P3, R1
JMP L1
L2:
MOV VC, 15
MOV VX, 10
MOV VY, 10
TEXT STR2
MOV VC, 15
MOV VX, 10
MOV VY, 20
TEXT STR3
MOV VC, 10
MOV VX, 10
MOV VY, 30
TEXT STR4
L6:
KEYSTAT R0
CMP R0, 0
JZ L6
HLT
STR2: DEFSTR "Counter:"
STR3: DEFSTR "Total:"
STR4: DEFSTR "Done!"