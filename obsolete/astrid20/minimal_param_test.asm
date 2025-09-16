; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF

; Function main
main:
entry:
; Call user function: test_func
MOV R1, 10
MOV R2, 20
MOV R3, 30
CALL test_func
; Halt processor
HLT

; Function test_func
test_func:
PUSH FP
MOV FP, SP
entry:
; Set pixel at (R2, R3) to color R4
MOV VM, 0
MOV VX, R2
MOV VY, R3
MOV R8, R4
SWRITE R8
MOV SP, FP
POP FP
RET

