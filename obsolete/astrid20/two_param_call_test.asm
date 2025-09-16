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
; Call user function: test_two_params
MOV R1, 10
MOV R2, 20
CALL test_two_params
; Halt processor
MOV SP, FP
POP FP
HLT

; Function test_two_params
test_two_params:
PUSH FP
MOV FP, SP
entry:
; Set active layer to R2
MOV VL, R2
MOV SP, FP
POP FP
RET

