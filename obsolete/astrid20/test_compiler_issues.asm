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
CMP P0, 50
JC cmp_done_0
JZ cmp_done_0
JMP cmp_true_0
MOV R8, 0
JMP cmp_done_0
cmp_true_0:
MOV R8, 1
cmp_done_0:
MOV P1, R8
MOV R9, P1
CMP R9, 0
JNZ ternary_then_0
JMP ternary_else_0
ternary_then_0:
MOV R8, 1
JMP ternary_merge_0
ternary_else_0:
MOV R8, 0
JMP ternary_merge_0
ternary_merge_0:
MOV R2, R8
; Set pixel at (P0, P0) to color P0
MOV VM, 0
MOV VX, P0
MOV VY, P0
MOV R8, P0
SWRITE R8
CMP P0, 1
JZ cmp_true_1
MOV R9, 0
JMP cmp_done_1
cmp_true_1:
MOV R9, 1
cmp_done_1:
MOV P6, R9
MOV R9, P6
CMP R9, 0
JNZ switch_case_1_0
JMP switch_test_2_0
switch_case_1_0:
JMP switch_end_1
switch_case_1_1:
JMP switch_end_1
switch_default_1:
JMP switch_end_1
switch_end_1:
; Set pixel at (P0, P0) to color P0
MOV VM, 0
MOV VX, P0
MOV VY, P0
MOV R8, P0
SWRITE R8
; Halt processor
MOV SP, FP
POP FP
HLT
switch_test_2_0:
CMP P0, 2
JZ cmp_true_2
MOV R9, 0
JMP cmp_done_2
cmp_true_2:
MOV R9, 1
cmp_done_2:
MOV P7, R9
MOV R9, P7
CMP R9, 0
JNZ switch_case_1_1
JMP switch_test_2_1
switch_test_2_1:
JMP switch_default_1

