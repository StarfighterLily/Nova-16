; Test nested macros
ORG 0x1000

MACRO OUTER reg, val
    MOV reg, val
    INNER reg
ENDM

MACRO INNER reg
    ADD reg, 1
ENDM

OUTER R1, 42

HLT