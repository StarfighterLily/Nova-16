; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF
MOV P0, 0x0000
PUSH P0
CALL main
HLT

; Function multiply
multiply:
PUSH FP
MOV FP, SP
entry:
MOV R5, R2
MOV R6, R3
MUL R5, R6
MOV R4, R5
MOV R0, R4
MOV SP, FP
POP FP
RET

; Function add_three
add_three:
PUSH FP
MOV FP, SP
entry:
MOV R7, R2
MOV R8, R3
ADD R7, R8
MOV R5, R7
MOV R9, R5
MOV R1, R4
ADD R9, R1
MOV R6, R9
MOV R0, R6
MOV SP, FP
POP FP
RET

; Function main
main:
PUSH FP
MOV FP, SP
SUB SP, 13  ; Allocate stack space for local variables
entry:
MOV R2, 99
MOV R3, 0
MOV R4, 1
JMP for_header_0
for_header_0:
CMP R4, 3
JC cmp_true_0
JZ cmp_true_0
MOV R8, 0
JMP cmp_done_0
cmp_true_0:
MOV R8, 1
cmp_done_0:
MOV R5, R8
MOV R9, R5
CMP R9, 0
JNZ for_body_1
JMP for_exit_2
for_body_1:
MOV R8, 1
JMP for_header_4
for_increment_3:
MOV R0, R4
INC R4
JMP for_header_0
for_exit_2:
; Halt processor
MOV SP, FP
POP FP
HLT
for_header_4:
CMP R8, 2
JC cmp_true_1
JZ cmp_true_1
MOV R9, 0
JMP cmp_done_1
cmp_true_1:
MOV R9, 1
cmp_done_1:
MOV R6, R9
MOV R9, R6
CMP R9, 0
JNZ for_body_5
JMP for_exit_6
for_body_5:
; Call user function: multiply
; Preserve caller-save registers
MOV P6, P9
SUB P6, 2
MOV [P6], R8
MOV P6, P9
SUB P6, 4
MOV [P6], R0
MOV R2, R4
MOV R3, R8
CALL multiply
; Restore caller-save registers
MOV P6, P9
SUB P6, 2
MOV R8, [P6]
MOV P6, P9
SUB P6, 4
MOV R0, [P6]
MOV R9, R0
; Call user function: add_three
; Preserve caller-save registers
MOV P6, P9
SUB P6, 6
MOV [P6], R8
MOV P6, P9
SUB P6, 8
MOV [P6], R0
MOV P6, P9
SUB P6, 10
MOV [P6], R0
MOV P6, P9
SUB P6, 12
MOV [P6], R9
MOV R2, R9
MOV R3, R2
MOV R4, R3
CALL add_three
; Restore caller-save registers
MOV P6, P9
SUB P6, 6
MOV R8, [P6]
MOV P6, P9
SUB P6, 8
MOV R0, [P6]
MOV P6, P9
SUB P6, 10
MOV R0, [P6]
MOV P6, P9
SUB P6, 12
MOV R9, [P6]
MOV R7, R0
MOV R3, R7
JMP for_increment_7
for_increment_7:
MOV P6, P9
SUB P6, 13
MOV [P6], R8
INC R8
JMP for_header_4
for_exit_6:
JMP for_increment_3

