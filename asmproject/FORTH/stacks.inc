; Stack management macros

; Initialize stacks
MACRO INIT_STACKS
    MOV P8, DS_BASE  ; Data stack pointer
    MOV P1, RS_BASE  ; Return stack pointer
ENDM

; Data Stack operations
MACRO PUSH_DS reg
    SUB P8, 2
    MOV [P8], reg
ENDM

MACRO POP_DS reg
    MOV reg, [P8]
    ADD P8, 2
ENDM

; Return Stack operations
MACRO PUSH_RS reg
    SUB P1, 2
    MOV [P1], reg
ENDM

MACRO POP_RS reg
    MOV reg, [P1]
    ADD P1, 2
ENDM