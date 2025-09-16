; Simple stack test without interrupts
ORG 0x1000
STI

; Test basic PUSH/POP
MOV P0, 0x1234
PUSH P0
POP P1

; Test PUSHF/POPF
MOV R0, 0x0F
CMP R0, R1  ; Set some flags
PUSHF
POPF

; Test PUSHA/POPA
PUSHA
POPA

; Test function call
CALL simple_func

done:
HLT

simple_func:
    PUSH FP
    MOV FP, SP
    ; Simple function body
    MOV SP, FP
    POP FP
    RET
