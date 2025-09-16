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
; Call user function: test_function
CALL test_function
; Halt processor
MOV SP, FP
POP FP
HLT

; Function test_function
test_function:
PUSH FP
MOV FP, SP
entry:
MOV SP, FP
POP FP
RET

