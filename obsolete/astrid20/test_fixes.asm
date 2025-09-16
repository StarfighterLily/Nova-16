; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF
MOV P0, 0x0000
PUSH P0
CALL main
HLT

; Function add_two
add_two:
PUSH FP
MOV FP, SP
entry:
MOV R5, R2
MOV R6, R3
ADD R5, R6
MOV R4, R5
MOV R0, R4
MOV SP, FP
POP FP
RET

; Function main
main:
PUSH FP
MOV FP, SP
SUB SP, 2  ; Allocate stack space for local variables
entry:
MOV R2, 42
; Call user function: add_two
MOV R2, 10
MOV R3, 20
CALL add_two
MOV R3, R0
MOV R4, 0
JMP for_header_0
for_header_0:
CMP R4, 3
JC cmp_true_0
MOV R9, 0
JMP cmp_done_0
cmp_true_0:
MOV R9, 1
cmp_done_0:
MOV R5, R9
MOV R9, R5
CMP R9, 0
JNZ for_body_1
JMP for_exit_2
for_body_1:
; Call user function: add_two
; Preserve caller-save registers
MOV P6, P9
SUB P6, 2
MOV [P6], R0
MOV R2, R4
MOV R3, R2
CALL add_two
; Restore caller-save registers
MOV P6, P9
SUB P6, 2
MOV R0, [P6]
MOV R3, R0
JMP for_increment_3
for_increment_3:
MOV R9, R4
INC R4
JMP for_header_0
for_exit_2:
; Halt processor
MOV SP, FP
POP FP
HLT

