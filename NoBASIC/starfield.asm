; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
MOV VM, 0
MOV VL, 1
XOR R1, R1
MOV P2, R1
MOV R1, 25
MOV R0, R1
L1:
CMP P2, R0
JGT L2
XOR R0, R0
MOV P3, R0
MOV R0, 20
MOV P5, R0
L3:
CMP P3, P5
JGT L4
RND R1
; Preserve left operand in register across right-side evaluation
MOV R2, R1
MOV R0, R2
ADD R0, P2
MOV VX, R0
RND R2
; Preserve left operand in register across right-side evaluation
MOV R4, R2
MOV R0, R4
SUB R0, P3
MOV VY, R0
MOV R4, 1
MOV R6, 5
RNDR R0, R4, R6
; Free R4 (last use)
; Free R6 (last use)
MOV VC, R0
SWRITE VC
INC P3
JMP L3
L4:
INC P2
JMP L1
L2:
MOV VM, 0
MOV VL, 1
SHL VL, 1
XOR R1, R1
MOV P2, R1
MOV R1, 20
MOV R0, R1
L5:
CMP P2, R0
JGT L6
XOR R0, R0
MOV P3, R0
MOV R0, 15
MOV P5, R0
L7:
CMP P3, P5
JGT L8
RND R1
; Preserve left operand in register across right-side evaluation
MOV R2, R1
MOV R0, R2
ADD R0, P2
MOV VX, R0
RND R2
; Preserve left operand in register across right-side evaluation
MOV R4, R2
MOV R0, R4
ADD R0, P2
MOV VY, R0
MOV R4, 6
MOV R6, 10
RNDR R0, R4, R6
; Free R4 (last use)
; Free R6 (last use)
MOV VC, R0
SWRITE VC
INC P3
JMP L7
L8:
INC P2
JMP L5
L6:
MOV VM, 0
MOV VL, 3
XOR R1, R1
MOV P2, R1
MOV R1, 15
MOV R0, R1
L9:
CMP P2, R0
JGT L10
XOR R0, R0
MOV P3, R0
MOV R0, 10
MOV P5, R0
L11:
CMP P3, P5
JGT L12
RND R1
; Preserve left operand in register across right-side evaluation
MOV R2, R1
MOV R0, R2
SUB R0, P2
MOV VX, R0
RND R2
; Preserve left operand in register across right-side evaluation
MOV R4, R2
MOV R0, R4
SUB R0, P3
MOV VY, R0
MOV R4, 11
MOV R6, 15
RNDR R0, R4, R6
; Free R4 (last use)
; Free R6 (last use)
MOV VC, R0
SWRITE VC
INC P3
JMP L11
L12:
INC P2
JMP L9
L10:
MOV VM, 0
MOV VL, 1
SHL VL, 2
MOV VX, 80
MOV VY, 118
MOV VC, 31
TEXT STR12
; --- Inline Assembly Block ---
LOOP:
    MOV VL, 1
    SROL 0, 1
    MOV VL, 2
    SROL 0, 2
    MOV VL, 3
    SROL 0, 3
    CALL SPINWHEELS
    JMP LOOP

SPINWHEELS:
    INC SA
    CMP SA, 0x2FFF
    JNZ SPINWHEELS
    XOR SA, SA
    RET
; --- End Inline Assembly ---
HLT
STR12: DEFSTR "StarField"