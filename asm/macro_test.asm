; Macro test for Nova-16 assembler
; Defines a macro and uses it with parameters

ORG 0x1000

MACRO LOAD_ADD reg, val
    MOV reg, val
    ADD reg, 1
ENDM

LOAD_ADD R1, 42
LOAD_ADD R2, 99

HLT
