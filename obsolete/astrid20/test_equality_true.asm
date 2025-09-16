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
entry:
MOV R2, 0
MOV R2, 50
JMP for_header_0
for_header_0:
CMP R2, 50
JZ cmp_true_0
MOV R9, 0
JMP cmp_done_0
cmp_true_0:
MOV R9, 1
cmp_done_0:
MOV R3, R9
MOV R9, R3
CMP R9, 0
JNZ for_body_1
JMP for_exit_2
for_body_1:
MOV R4, R2
MOV R5, 100
ADD R4, R5
MOV R9, R4
MOV R2, R9
JMP for_increment_3
for_increment_3:
MOV R8, R2
INC R2
JMP for_header_0
for_exit_2:
; Halt processor
MOV SP, FP
POP FP
HLT

