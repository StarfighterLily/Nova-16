; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF

; Function main
main:
PUSH FP
MOV FP, SP
entry:
; Call user function: simple_function
CALL simple_function
; Halt processor
MOV SP, FP
POP FP
HLT

; Function simple_function
simple_function:
PUSH FP
MOV FP, SP
entry:
; Set active layer to 1
MOV VL, 1
MOV SP, FP
POP FP
RET

