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
CMP P1, 100
JC cmp_done_0
JZ cmp_done_0
JMP cmp_true_0
MOV R8, 0
JMP cmp_done_0
cmp_true_0:
MOV R8, 1
cmp_done_0:
MOV P2, R8
MOV R9, P2
CMP R9, 0
JNZ if_then_0
JMP if_merge_2
if_then_0:
MOV R6, P1
MOV R7, 50
SUB R6, R7
MOV P6, R6
MOV P1, P6
JMP if_merge_2
if_merge_2:
MOV R0, P1
MOV SP, FP
POP FP
RET

