; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF
MOV P0, 0x0000
PUSH P0
CALL main
HLT

; Function main
main:
PUSH FP
MOV FP, SP
SUB SP, 1  ; Allocate stack space for local variables
entry:
MOV R2, 0
MOV R3, 0
MOV R3, 0
JMP for_header_0
for_header_0:
CMP R3, 3
JC cmp_true_0
MOV R9, 0
JMP cmp_done_0
cmp_true_0:
MOV R9, 1
cmp_done_0:
MOV R4, R9
MOV R9, R4
CMP R9, 0
JNZ for_body_1
JMP for_exit_2
for_body_1:
MOV R9, R2
ADD R9, 1
MOV R2, R9
JMP for_increment_3
for_increment_3:
MOV R8, R3
INC R3
JMP for_header_0
for_exit_2:
MOV R2, 0
MOV R3, 5
JMP for_header_4
for_header_4:
CMP R3, 5
JZ cmp_true_1
MOV R0, 0
JMP cmp_done_1
cmp_true_1:
MOV R0, 1
cmp_done_1:
MOV R5, R0
MOV R9, R5
CMP R9, 0
JNZ for_body_5
JMP for_exit_6
for_body_5:
MOV R6, R2
MOV R7, 10
ADD R6, R7
MOV R0, R6
MOV R2, R0
JMP for_increment_7
for_increment_7:
MOV R1, R3
INC R3
JMP for_header_4
for_exit_6:
MOV R2, 0
MOV R3, 7
JMP for_header_8
for_header_8:
CMP R3, 10
JNZ cmp_true_2
MOV R9, 0
JMP cmp_done_2
cmp_true_2:
MOV R9, 1
cmp_done_2:
MOV R6, R9
MOV R9, R6
CMP R9, 0
JNZ for_body_9
JMP for_exit_10
for_body_9:
MOV R7, R2
ADD R7, 1
MOV R2, R7
JMP for_increment_11
for_increment_11:
MOV P6, P9
SUB P6, 1
MOV [P6], R3
INC R3
JMP for_header_8
for_exit_10:
; Halt processor
MOV SP, FP
POP FP
HLT

