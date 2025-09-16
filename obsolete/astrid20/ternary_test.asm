; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF

; Function main
main:
entry:
MOV R2, 5
MOV R3, 10
CMP R2, R3
JC cmp_done_0
JZ cmp_done_0
JMP cmp_true_0
MOV R9, 0
JMP cmp_done_0
cmp_true_0:
MOV R9, 1
cmp_done_0:
MOV R4, R9
MOV R9, R4
CMP R9, 0
JNZ ternary_then_0
JMP ternary_else_0
ternary_then_0:
MOV R9, R2
JMP ternary_merge_0
ternary_else_0:
MOV R9, R3
JMP ternary_merge_0
ternary_merge_0:
MOV R8, R9
HLT

