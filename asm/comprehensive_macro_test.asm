; Comprehensive macro test
ORG 0x1000

; Macro with parameters
MACRO ADD_TO_REG reg, val
    MOV reg, val
    ADD reg, 1
ENDM

; Macro without parameters
MACRO DOUBLE_NOP
    NOP
    NOP
ENDM

; Nested macros
MACRO OUTER reg
    MOV reg, 10
    INNER reg
ENDM

MACRO INNER reg
    ADD reg, 5
ENDM

; Use macros
ADD_TO_REG R1, 42
DOUBLE_NOP
OUTER R2

; Test parameter replacement in different contexts
MACRO LOAD_ADDR reg, addr
    MOV reg, addr
    MOV [reg], 123
ENDM

LOAD_ADDR P0, 0x2000

HLT