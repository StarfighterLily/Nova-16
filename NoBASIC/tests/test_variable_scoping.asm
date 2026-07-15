; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV VX, 0
MOV R1, 10
MOV P7:, 0xFF
MOV VC, 15
MOV P2, R1
MOV R1, 20
MOV :P7, 0xFF
MOV P2, R1
MOV SP, P7
MOV FP, SP
TEXT STR0
ADD VY, 8
; GLOBAL variable: globalVar @ 0x0120
MOV VX, 0
MOV R1, 100
MOV VC, 15
MOV P2, R1
TEXT STR1
ADD VY, 8
; GLOBAL variable: a @ 0x0122
; GLOBAL variable: b @ 0x0124
; GLOBAL variable: c @ 0x0126
MOV R1, 1
MOV P2, R1
MOV R1, 1
SHL R1, 1
MOV P3, R1
MOV VX, 0
MOV R1, 3
MOV VC, 15
MOV P4, R1
TEXT STR2
ADD VY, 8
; Preserve left operand in register across right-side evaluation
MOV R3, P2
MOV R0, R3
ADD R0, P3
; Preserve left operand in register across right-side evaluation
MOV R1, R0
ADD R1, P4
MOV VX, 10
MOV VY, 10
MOV VC, 15
MOV P5, R1
TEXT STR3
MOV VC, 15
MOV VX, 10
MOV VY, 20
TEXT STR4
MOV VC, 15
MOV VX, 10
MOV VY, 30
TEXT STR5
MOV VC, 15
MOV VX, 10
MOV VY, 40
TEXT STR6
L8:
KEYSTAT R0
CMP R0, 0
JZ L8
HLT
STR0: DEFSTR "Global x and y declared implicitly"
STR1: DEFSTR "Explicit global variable"
STR2: DEFSTR "Multiple global variables"
STR3: DEFSTR "Result:"
STR4: DEFSTR "x="
STR5: DEFSTR "globalVar="
STR6: DEFSTR "result="