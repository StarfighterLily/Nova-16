; Test recursive macro (should fail)
ORG 0x1000

MACRO RECURSE reg
    DEC reg
    JNZ skip
    RECURSE reg
skip:
ENDM

MOV R1, 1
RECURSE R1

HLT