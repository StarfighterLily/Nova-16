; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF

; Function main
main:
entry:
MOV R2, 2
MOV R3, 0
CMP R2, 1
JZ cmp_true_0
MOV R9, 0
JMP cmp_done_0
cmp_true_0:
MOV R9, 1
cmp_done_0:
MOV P0, R9
MOV R9, P0
CMP R9, 0
JNZ switch_case_0_0
JMP switch_test_1_0
switch_case_0_0:
MOV R3, 10
JMP switch_end_0
switch_case_0_1:
MOV R3, 20
JMP switch_end_0
switch_default_0:
MOV R3, 30
JMP switch_end_0
switch_end_0:
switch_test_1_0:
CMP R2, 2
JZ cmp_true_1
MOV R9, 0
JMP cmp_done_1
cmp_true_1:
MOV R9, 1
cmp_done_1:
MOV P1, R9
MOV R9, P1
CMP R9, 0
JNZ switch_case_0_1
JMP switch_test_1_1
switch_test_1_1:
JMP switch_default_0
HLT

