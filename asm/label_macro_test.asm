; Test macro with labels
ORG 0x1000

MACRO LOOP_MACRO reg, count
loop_label:
    DEC reg
    JNZ loop_label
ENDM

MOV R1, 5
LOOP_MACRO R1, 5

MOV R2, 3
LOOP_MACRO R2, 3

HLT