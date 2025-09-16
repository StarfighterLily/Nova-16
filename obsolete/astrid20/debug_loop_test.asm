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
MOV P0, 0
MOV P1, 0
MOV P1, 0
JMP for_header_0
for_header_0:
CMP P1, 3
JC cmp_true_0
MOV R8, 0
JMP cmp_done_0
cmp_true_0:
MOV R8, 1
cmp_done_0:
MOV P2, R8
MOV R9, P2
CMP R9, 0
JNZ for_body_1
JMP for_exit_2
for_body_1:
MOV P6, P0
ADD P6, 1
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

