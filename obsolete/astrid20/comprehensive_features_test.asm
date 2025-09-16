; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF

; Function main
main:
entry:
CMP P0, P0
JC cmp_done_0
JZ cmp_done_0
JMP cmp_true_0
MOV R8, 0
JMP cmp_done_0
cmp_true_0:
MOV R8, 1
cmp_done_0:
MOV R2, R8
MOV R9, R2
CMP R9, 0
JNZ ternary_then_0
JMP ternary_else_0
ternary_then_0:
MOV R8, P0
JMP ternary_merge_0
ternary_else_0:
MOV R8, P0
JMP ternary_merge_0
ternary_merge_0:
MOV R3, R8
MOV R4, 0
CMP R3, 10
JZ cmp_true_1
MOV R1, 0
JMP cmp_done_1
cmp_true_1:
MOV R1, 1
cmp_done_1:
MOV P6, R1
MOV R9, P6
CMP R9, 0
JNZ switch_case_1_0
JMP switch_test_2_0
switch_case_1_0:
MOV R4, 1
JMP switch_end_1
switch_case_1_1:
MOV R4, 2
JMP switch_end_1
switch_default_1:
MOV R4, 3
JMP switch_end_1
switch_end_1:
switch_test_2_0:
CMP R3, 20
JZ cmp_true_2
MOV R1, 0
JMP cmp_done_2
cmp_true_2:
MOV R1, 1
cmp_done_2:
MOV P1, R1
MOV R9, P1
CMP R9, 0
JNZ switch_case_1_1
JMP switch_test_2_1
switch_test_2_1:
JMP switch_default_1
HLT

