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
; Call user function: simple_func
CALL simple_func
; Halt processor
MOV SP, FP
POP FP
HLT
for_increment_3:
MOV P6, P0
INC P0
JMP for_header_0

; Function simple_func
simple_func:
PUSH FP
MOV FP, SP
entry:
MOV SP, FP
POP FP
RET

