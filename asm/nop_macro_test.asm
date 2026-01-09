; Test macro with no parameters
ORG 0x1000

MACRO NOP_MACRO
    NOP
ENDM

NOP_MACRO
NOP_MACRO

HLT