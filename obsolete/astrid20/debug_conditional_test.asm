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
MOV P0, 0
MOV P0, 0
JMP for_header_0
for_header_0:
CMP P0, 3
JC cmp_true_0
MOV R8, 0
JMP cmp_done_0
cmp_true_0:
MOV R8, 1
cmp_done_0:
MOV P1, R8
MOV R9, P1
CMP R9, 0
JNZ for_body_1
JMP for_exit_2
for_body_1:
JMP for_increment_3
for_exit_2:
; Call user function: conditional_func
MOV R1, 10
MOV R2, 20
CALL conditional_func
MOV P6, R0
; Halt processor
MOV SP, FP
POP FP
HLT
for_increment_3:
MOV P2, P0
INC P0
JMP for_header_0

; Function conditional_func
conditional_func:
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
CMP P1, 25
JC cmp_done_1
JZ cmp_done_1
JMP cmp_true_1
MOV R8, 0
JMP cmp_done_1
cmp_true_1:
MOV R8, 1
cmp_done_1:
MOV P2, R8
MOV R9, P2
CMP R9, 0
JNZ if_then_4
JMP if_merge_6
if_then_4:
MOV R6, P1
MOV R7, 5
SUB R6, R7
MOV P6, R6
MOV P1, P6
JMP if_merge_6
if_merge_6:
MOV R0, P1
MOV SP, FP
POP FP
RET

