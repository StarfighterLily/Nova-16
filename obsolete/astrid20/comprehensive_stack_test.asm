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
MOV P1, 0
MOV P0, 0
JMP for_header_0
for_header_0:
CMP P0, 10
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
; Call user function: calculate_value
MOV R1, P0
MOV R2, 5
CALL calculate_value
MOV R9, P0
MOV R1, R0
MOV P6, R8
ADD P6, R9
MOV [P6], R1
JMP for_increment_3
for_exit_2:
MOV P0, 0
JMP for_header_4
for_increment_3:
MOV P6, P0
INC P0
JMP for_header_0
for_header_4:
CMP P0, 10
JC cmp_true_1
MOV R9, 0
JMP cmp_done_1
cmp_true_1:
MOV R9, 1
cmp_done_1:
MOV P6, R9
MOV R9, P6
CMP R9, 0
JNZ for_body_5
JMP for_exit_6
for_body_5:
MOV R1, P0
MOV P7, R8
ADD P7, R1
MOV R2, [P7]
MOV R9, R2
; Call user function: add_with_overflow_check
MOV R1, P1
MOV R2, R9
CALL add_with_overflow_check
MOV P1, R0
JMP for_increment_7
for_exit_6:
; Call user function: draw_results
MOV R1, P1
CALL draw_results
; Halt processor
MOV SP, FP
POP FP
HLT
for_increment_7:
MOV P7, P0
INC P0
JMP for_header_4

; Function calculate_value
calculate_value:
PUSH FP
MOV FP, SP
entry:
MOV R4, R2
MOV R5, R3
MUL R4, R5
MOV P0, R4
MOV P1, P0
CMP P1, 50
JC cmp_done_2
JZ cmp_done_2
JMP cmp_true_2
MOV R8, 0
JMP cmp_done_2
cmp_true_2:
MOV R8, 1
cmp_done_2:
MOV P2, R8
MOV R9, P2
CMP R9, 0
JNZ if_then_8
JMP if_merge_10
if_then_8:
MOV R6, P1
MOV R7, 20
SUB R6, R7
MOV P6, R6
MOV P1, P6
JMP if_merge_10
if_merge_10:
MOV R0, P1
MOV SP, FP
POP FP
RET

; Function add_with_overflow_check
add_with_overflow_check:
PUSH FP
MOV FP, SP
entry:
MOV R8, R2
MOV R9, R3
ADD R8, R9
MOV :P0, R8
JC add_carry_3
JMP add_done_3
add_carry_3:
MOV R8, 0
ADD R8, 1
MOV P0:, R8
add_done_3:
MOV P1, P0
CMP P1, 200
JC cmp_done_4
JZ cmp_done_4
JMP cmp_true_4
MOV R1, 0
JMP cmp_done_4
cmp_true_4:
MOV R1, 1
cmp_done_4:
MOV P2, R1
MOV R9, P2
CMP R9, 0
JNZ if_then_11
JMP if_merge_13
if_then_11:
MOV P1, 200
JMP if_merge_13
if_merge_13:
MOV R0, P1
MOV SP, FP
POP FP
RET

; Function draw_results
draw_results:
PUSH FP
MOV FP, SP
entry:
; Set active layer to 2
MOV VL, 2
MOV R3, R2
MOV R1, 10
DIV R3, R1
MOV P0, R3
MOV P1, P0
; Unknown instruction: v41 = % v34, v40
MOV P2, P3
; Set pixel at (P1, P2) to color 255
MOV VM, 0
MOV VX, P1
MOV VY, P2
MOV R8, 255
SWRITE R8
MOV SP, FP
POP FP
RET

