; Test macro defined after use
ORG 0x1000

LOAD_ADD R1, 42

MACRO LOAD_ADD reg, val
    MOV reg, val
    ADD reg, 1
ENDM

HLT