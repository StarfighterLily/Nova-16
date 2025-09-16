; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF
MOV P0, 0x0000
PUSH P0
CALL main
HLT

; Function complex_calc
complex_calc:
PUSH FP
MOV FP, SP
entry:
MOV R6, R3
MOV R7, R4
MUL R6, R7
MOV R5, R6
MOV R8, R2
MOV R9, R5
ADD R8, R9
MOV R6, R8
MOV R0, R6
MOV SP, FP
POP FP
RET

; Function main
main:
PUSH FP
MOV FP, SP
SUB SP, 9  ; Allocate stack space for local variables
entry:
MOV R2, 10
MOV R3, 20
MOV R4, 30
MOV R5, 0
JMP for_header_0
for_header_0:
CMP R5, 2
JC cmp_true_0
MOV R0, 0
JMP cmp_done_0
cmp_true_0:
MOV R0, 1
cmp_done_0:
MOV R6, R0
MOV R9, R6
CMP R9, 0
JNZ for_body_1
JMP for_exit_2
for_body_1:
MOV R0, 0
JMP for_header_4
for_increment_3:
MOV R1, R5
INC R5
JMP for_header_0
for_exit_2:
; Halt processor
MOV SP, FP
POP FP
HLT
for_header_4:
CMP R0, 2
JC cmp_true_1
MOV R8, 0
JMP cmp_done_1
cmp_true_1:
MOV R8, 1
cmp_done_1:
MOV R7, R8
MOV R9, R7
CMP R9, 0
JNZ for_body_5
JMP for_exit_6
for_body_5:
MOV R9, R2
MOV R8, R5
ADD R9, R8
MOV R8, R9
MOV R9, R3
MOV R8, R0
ADD R9, R8
MOV P6, P9
SUB P6, 1
MOV [P6], R9
; Call user function: complex_calc
; Preserve caller-save registers
MOV P6, P9
SUB P6, 3
MOV [P6], R0
MOV P6, P9
SUB P6, 5
MOV [P6], R1
MOV P6, P9
SUB P6, 7
MOV [P6], R8
MOV R2, R8
MOV R3, FP-1
CALL complex_calc
; Restore caller-save registers
MOV P6, P9
SUB P6, 3
MOV R0, [P6]
MOV P6, P9
SUB P6, 5
MOV R1, [P6]
MOV P6, P9
SUB P6, 7
MOV R8, [P6]
MOV P6, P9
SUB P6, 8
MOV [P6], R0
MOV P6, P9
SUB P6, 8
MOV R2, [P6]
JMP for_increment_7
for_increment_7:
MOV P6, P9
SUB P6, 9
MOV [P6], R0
INC R0
JMP for_header_4
for_exit_6:
JMP for_increment_3

