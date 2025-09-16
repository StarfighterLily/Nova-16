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
; Call user function: test_three_params
MOV R1, 100
MOV R2, 50
MOV R3, 15
CALL test_three_params
; Halt processor
MOV SP, FP
POP FP
HLT

; Function test_three_params
test_three_params:
PUSH FP
MOV FP, SP
entry:
; Set active layer to 1
MOV VL, 1
MOV SP, FP
POP FP
RET

