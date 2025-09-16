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
CMP P0, 5
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
MOV R3, P0
MOV R4, 10
ADD R3, R4
MOV :P6, R3
JC add_carry_1
JMP add_done_1
add_carry_1:
MOV R3, P0:
ADD R3, 1
MOV P6:, R3
add_done_1:
JMP for_increment_3
for_exit_2:
; Call user function: draw_single_pixel
MOV R1, 100
MOV R2, 50
MOV R3, 15
CALL draw_single_pixel
; Call user function: calculate_sum
MOV R1, 10
MOV R2, 20
CALL calculate_sum
MOV P2, R0
; Halt processor
MOV SP, FP
POP FP
HLT
for_increment_3:
MOV P3, P0
INC P0
JMP for_header_0

; Function draw_single_pixel
draw_single_pixel:
PUSH FP
MOV FP, SP
entry:
; Set active layer to 1
MOV VL, 1
; Set pixel at (R2, R3) to color R4
MOV VM, 0
MOV VX, R2
MOV VY, R3
MOV R8, R4
SWRITE R8
MOV SP, FP
POP FP
RET

; Function calculate_sum
calculate_sum:
PUSH FP
MOV FP, SP
entry:
MOV R5, R2
MOV R6, R3
ADD R5, R6
MOV :P0, R5
JC add_carry_2
JMP add_done_2
add_carry_2:
MOV R5, 0
ADD R5, 1
MOV P0:, R5
add_done_2:
MOV P1, P0
MOV R0, P1
MOV SP, FP
POP FP
RET

