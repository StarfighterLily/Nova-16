; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF

; Function draw_pixel
draw_pixel:
PUSH FP
MOV FP, SP
entry:
; Set pixel at (R2, R3) to color R4
MOV VM, 0
MOV VX, R2
MOV VY, R3
MOV R8, R4
SWRITE R8
MOV SP, FP
POP FP
RET

; Function calculate_area
calculate_area:
PUSH FP
MOV FP, SP
entry:
MOV R4, P0
MOV R5, P0
SUB R4, R5
MOV R3, R4
MOV R4, R3
MOV R6, P0
MOV R7, P0
SUB R6, R7
MOV R5, R6
MOV R6, R5
MOV R8, R4
MOV R9, R6
MUL R8, R9
MOV R7, R8
MOV R0, R7
MOV SP, FP
POP FP
RET

; Function draw_rectangle
draw_rectangle:
PUSH FP
MOV FP, SP
entry:
MOV R3, None
JMP while_header_0
while_header_0:
CMP R3, P0
JC cmp_true_0
JZ cmp_true_0
MOV R1, 0
JMP cmp_done_0
cmp_true_0:
MOV R1, 1
cmp_done_0:
MOV R4, R1
MOV R9, R4
CMP R9, 0
JNZ while_body_1
JMP while_exit_2
while_body_1:
MOV R1, P0
JMP while_header_3
while_exit_2:
while_header_3:
CMP R1, P0
JC cmp_true_1
JZ cmp_true_1
MOV R0, 0
JMP cmp_done_1
cmp_true_1:
MOV R0, 1
cmp_done_1:
MOV R5, R0
MOV R9, R5
CMP R9, 0
JNZ while_body_4
JMP while_exit_5
while_body_4:
; Call user function: draw_pixel
MOV R1, R3
MOV R2, R1
MOV R3, P0
CALL draw_pixel
MOV R0, R1
ADD R0, 1
MOV R1, R0
JMP while_header_3
while_exit_5:
MOV R6, R3
ADD R6, 1
MOV R3, R6
JMP while_header_0
MOV SP, FP
POP FP
RET

; Function main
main:
PUSH FP
MOV FP, SP
SUB SP, 14  ; Allocate stack space for local variables
entry:
; Call user function: calculate_area
MOV R1, P5
CALL calculate_area
MOV P0, R0
CMP P0, 1000
JC cmp_done_2
JZ cmp_done_2
JMP cmp_true_2
MOV R1, 0
JMP cmp_done_2
cmp_true_2:
MOV R1, 1
cmp_done_2:
MOV P1, R1
MOV R9, P1
CMP R9, 0
JNZ ternary_then_6
JMP ternary_else_6
ternary_then_6:
MOV R1, 3
JMP ternary_merge_6
ternary_else_6:
CMP P0, 500
JC cmp_done_3
JZ cmp_done_3
JMP cmp_true_3
MOV R2, 0
JMP cmp_done_3
cmp_true_3:
MOV R2, 1
cmp_done_3:
MOV P6, R2
MOV R9, P6
CMP R9, 0
JNZ ternary_then_7
JMP ternary_else_7
MOV R1, R8
JMP ternary_merge_6
ternary_merge_6:
MOV R2, R1
CMP R2, 1
JZ cmp_true_4
MOV R8, 0
JMP cmp_done_4
cmp_true_4:
MOV R8, 1
cmp_done_4:
MOV P7, R8
MOV R9, P7
CMP R9, 0
JNZ switch_case_8_0
JMP switch_test_9_0
ternary_then_7:
MOV R8, 2
JMP ternary_merge_7
ternary_else_7:
MOV R8, 1
JMP ternary_merge_7
ternary_merge_7:
switch_case_8_0:
JMP switch_end_8
switch_case_8_1:
JMP switch_end_8
switch_case_8_2:
JMP switch_end_8
switch_default_8:
JMP switch_end_8
switch_end_8:
MOV R3, 0
JMP while_header_9
switch_test_9_0:
CMP R2, 2
JZ cmp_true_5
MOV R9, 0
JMP cmp_done_5
cmp_true_5:
MOV R9, 1
cmp_done_5:
MOV P2, R9
MOV R9, P2
CMP R9, 0
JNZ switch_case_8_1
JMP switch_test_9_1
switch_test_9_1:
CMP R2, 3
JZ cmp_true_6
MOV R9, 0
JMP cmp_done_6
cmp_true_6:
MOV R9, 1
cmp_done_6:
MOV P3, R9
MOV R9, P3
CMP R9, 0
JNZ switch_case_8_2
JMP switch_test_9_2
switch_test_9_2:
JMP switch_default_8
while_header_9:
CMP R3, 3
JC cmp_true_7
MOV R9, 0
JMP cmp_done_7
cmp_true_7:
MOV R9, 1
cmp_done_7:
MOV R9, R9
CMP R9, 0
JNZ while_body_10
JMP while_exit_11
while_body_10:
MOV R9, R3
MOV R8, 5
MUL R9, R8
MOV R9, P4
MOV R8, R9
ADD R9, R8
MOV R2, R9
MOV R9, R3
MOV R8, 5
MUL R9, R8
MOV R3, R9
MOV R9, P4
MOV R8, R3
ADD R9, R8
MOV R4, R9
MOV R9, P4
MOV R8, 10
ADD R9, R8
MOV R5, R9
MOV R9, P4
MOV R8, 10
ADD R9, R8
MOV R6, R9
MOV R9, P4
MOV R8, R3
ADD R9, R8
MOV R7, R9
; Call user function: draw_rectangle
MOV R1, P5
CALL draw_rectangle
MOV R9, R3
ADD R9, 1
MOV P5, FP
SUB P5, 1
MOV [P5], R9
MOV P5, FP
SUB P5, 1
MOV R3, [P5]
JMP while_header_9
while_exit_11:
MOV R9, 0
MOV P5, FP
SUB P5, 2
MOV [P5], R9
JMP for_header_12
for_header_12:
MOV P5, FP
SUB P5, 2
MOV R9, [P5]
CMP R9, 5
JC cmp_true_8
MOV R9, 0
JMP cmp_done_8
cmp_true_8:
MOV R9, 1
cmp_done_8:
MOV P5, FP
SUB P5, 3
MOV [P5], R9
MOV R9, [[FP-3]]
CMP R9, 0
JNZ for_body_13
JMP for_exit_14
for_body_13:
; Unknown instruction: v72 = % v68, v71
MOV P5, FP
SUB P5, 4
MOV R9, [P5]
CMP R9, 0
JZ cmp_true_9
MOV R9, 0
JMP cmp_done_9
cmp_true_9:
MOV R9, 1
cmp_done_9:
MOV P5, FP
SUB P5, 5
MOV [P5], R9
MOV R9, [[FP-5]]
CMP R9, 0
JNZ if_then_16
JMP if_else_17
for_exit_14:
; Halt processor
MOV SP, FP
POP FP
HLT
for_increment_15:
MOV P5, FP
SUB P5, 2
MOV R9, [P5]
ADD R9, 1
MOV P5, FP
SUB P5, 6
MOV [P5], R9
MOV P5, FP
SUB P5, 6
MOV R9, [P5]
MOV P5, FP
SUB P5, 2
MOV [P5], R9
JMP for_header_12
if_then_16:
MOV R9, [[FP-2]]
MOV R8, 10
MUL R9, R8
MOV P5, FP
SUB P5, 7
MOV [P5], R9
MOV R9, [[FP-2]]
MOV R8, 10
MUL R9, R8
MOV P5, FP
SUB P5, 8
MOV [P5], R9
MOV P5, FP
SUB P5, 2
MOV R9, [P5]
ADD R9, 1
MOV P5, FP
SUB P5, 9
MOV [P5], R9
; Call user function: draw_pixel
MOV R1, [FP-7]
MOV R2, [FP-8]
MOV R3, [FP-9]
CALL draw_pixel
JMP if_merge_18
if_else_17:
MOV R9, [[FP-2]]
MOV R8, 10
MUL R9, R8
MOV P5, FP
SUB P5, 10
MOV [P5], R9
MOV R9, [[FP-10]]
MOV R8, 5
ADD R9, R8
MOV P5, FP
SUB P5, 11
MOV [P5], R9
MOV R9, [[FP-2]]
MOV R8, 10
MUL R9, R8
MOV P5, FP
SUB P5, 12
MOV [P5], R9
MOV R9, [[FP-12]]
MOV R8, 5
ADD R9, R8
MOV P5, FP
SUB P5, 13
MOV [P5], R9
MOV P5, FP
SUB P5, 2
MOV R9, [P5]
ADD R9, 1
MOV P5, FP
SUB P5, 14
MOV [P5], R9
; Call user function: draw_pixel
MOV R1, [FP-11]
MOV R2, [FP-13]
MOV R3, [FP-14]
CALL draw_pixel
JMP if_merge_18
if_merge_18:
JMP for_increment_15

