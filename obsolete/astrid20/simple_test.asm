; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF

; Function simple_func
simple_func:
PUSH FP
MOV FP, SP
entry:
MOV R0, 42
MOV SP, FP
POP FP
RET

; Function main
main:
PUSH FP
MOV FP, SP
entry:
; Call user function: simple_func
CALL simple_func
MOV R2, R0
; Halt processor
MOV SP, FP
POP FP
HLT

