; Test macro without ENDM
ORG 0x1000

MACRO BAD_MACRO
    NOP

MOV R0, 1