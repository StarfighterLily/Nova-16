; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF
MOV P0, 0x0000
PUSH P0
CALL main
HLT

; Function double_value
double_value:
PUSH FP
MOV FP, SP
entry:
MOV R3, R2
MOV R4, R2
ADD R3, R4
MOV :P0, R3
JC add_carry_0
JMP add_done_0
add_carry_0:
MOV R3, 0
ADD R3, 1
MOV P0:, R3
add_done_0:
MOV R0, P0
MOV SP, FP
POP FP
RET

; Function main
main:
PUSH FP
MOV FP, SP
entry:
MOV P0, 0
MOV P1, 1
JMP for_header_0
for_header_0:
CMP P1, 2
JC cmp_true_1
JZ cmp_true_1
MOV R8, 0
JMP cmp_done_1
cmp_true_1:
MOV R8, 1
cmp_done_1:
MOV P2, R8
MOV R9, P2
CMP R9, 0
JNZ for_body_1
JMP for_exit_2
for_body_1:
; Call user function: double_value
MOV R1, P1
CALL double_value
MOV R5, P0
MOV R6, R0
ADD R5, R6
MOV :P6, R5
JC add_carry_2
JMP add_done_2
add_carry_2:
MOV R5, P0:
ADD R5, 1
MOV P6:, R5
add_done_2:
MOV P0, P6
JMP for_increment_3
for_exit_2:
; Halt processor
MOV SP, FP
POP FP
HLT
for_increment_3:
MOV P3, P1
ADD P3, 1
MOV P1, P3
JMP for_header_0

