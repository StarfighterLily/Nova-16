; Macros for FORTH interpreter

; ENTER: Enter a colon definition
MACRO ENTER
    PUSH_RS P4
    MOV R0, P5
    ADD R0, 2
    MOV P4, R0
    JMP NEXT
ENDM

; EXIT: Exit a colon definition
MACRO EXIT
    POP_RS P4
ENDM