; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
XOR R1, R1
MOV P2, R1
MOV P7:, 0xFF
MOV R1, 3
MOV :P7, 0xFF
MOV P3, R1
MOV SP, P7
MOV FP, SP
; GLOBAL variable: level @ 0x0120
; GLOBAL variable: bonus @ 0x0122
MOV P3, 1
MOV P3, 100
MOV P4, 1
MOV R0, 5
L1:
CMP P4, R0
JGT L2
; Preserve left operand in register across right-side evaluation
MOV R2, P4
MOV R1, R2
ADD R1, P2
INC P4
MOV P2, R1
JMP L1
L2:
; Preserve left operand in register across right-side evaluation
MOV R2, P3
MOV R1, R2
ADD R1, P2
MOV P2, R1
; ClrDraw
MOV VL, 1
MOV VM, 0
SFILL 0x00
MOV VC, 15
MOV VX, 10
MOV VY, 10
TEXT STR2
MOV VC, 15
MOV VX, 10
MOV VY, 20
TEXT STR3
MOV VC, 15
MOV VX, 10
MOV VY, 30
TEXT STR4
MOV VC, 15
MOV VX, 10
MOV VY, 40
TEXT STR5
L7:
KEYSTAT R0
CMP R0, 0
JZ L7
HLT
STR2: DEFSTR "Score:"
STR3: DEFSTR "Lives:"
STR4: DEFSTR "Level:"
STR5: DEFSTR "Bonus:"