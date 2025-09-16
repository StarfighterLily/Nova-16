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
; Call user function: add_numbers
MOV R1, 10
MOV R2, 20
CALL add_numbers
MOV P0, R0
; Call user function: process_data
MOV R1, P0
MOV R2, 5
CALL process_data
MOV R2, R0
CMP R2, 0
JC cmp_done_0
JZ cmp_done_0
JMP cmp_true_0
MOV R9, 0
JMP cmp_done_0
cmp_true_0:
MOV R9, 1
cmp_done_0:
MOV R3, R9
MOV R9, R3
CMP R9, 0
JNZ if_then_0
JMP if_merge_2
if_then_0:
; Call user function: display_result
MOV R1, P0
CALL display_result
JMP if_merge_2
if_merge_2:
; Halt processor
MOV SP, FP
POP FP
HLT

; Function add_numbers
add_numbers:
PUSH FP
MOV FP, SP
entry:
MOV R4, R2
MOV R5, R3
ADD R4, R5
MOV :P0, R4
JC add_carry_1
JMP add_done_1
add_carry_1:
MOV R4, 0
ADD R4, 1
MOV P0:, R4
add_done_1:
MOV R0, P0
MOV SP, FP
POP FP
RET

; Function process_data
process_data:
PUSH FP
MOV FP, SP
entry:
CMP R2, 100
JC cmp_done_2
JZ cmp_done_2
JMP cmp_true_2
MOV R8, 0
JMP cmp_done_2
cmp_true_2:
MOV R8, 1
cmp_done_2:
MOV P0, R8
MOV R9, P0
CMP R9, 0
JNZ if_then_3
JMP if_else_4
if_then_3:
MOV R6, R3
MOV R7, 2
MUL R6, R7
MOV R8, R6
MOV R0, R8
JMP if_merge_5
if_else_4:
MOV R0, R3
JMP if_merge_5
if_merge_5:
MOV SP, FP
POP FP
RET

; Function display_result
display_result:
PUSH FP
MOV FP, SP
entry:
; Unknown instruction: v24 = % v20, v23
; Set pixel at (100, 100) to color v24
MOV VM, 0
MOV VX, 100
MOV VY, 100
MOV R8, P0
SWRITE R8
MOV SP, FP
POP FP
RET

