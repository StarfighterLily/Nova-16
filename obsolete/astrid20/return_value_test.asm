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
; Call user function: calculate_sum
MOV R1, 10
MOV R2, 20
CALL calculate_sum
MOV P0, R0
; Halt processor
MOV SP, FP
POP FP
HLT

; Function calculate_sum
calculate_sum:
PUSH FP
MOV FP, SP
entry:
MOV R4, R2
MOV R5, R3
ADD R4, R5
MOV :P0, R4
JC add_carry
JMP add_done
add_carry:
MOV R4, 0
ADD R4, 1
MOV P0:, R4
add_done:
MOV P1, P0
MOV R0, P1
MOV SP, FP
POP FP
RET

