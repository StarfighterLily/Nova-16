; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF

; Function main
main:
entry:
MOV P0, 0
; Set active layer to 1
MOV VL, 1
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
MOV P1, R8
MOV R9, P1
CMP R9, 0
JNZ for_body_1
JMP for_exit_2
for_body_1:
; Call user function: draw_random_star
CALL draw_random_star
JMP for_increment_3
for_exit_2:
; Halt processor
HLT
for_increment_3:
MOV P8, P0
INC P0
JMP for_header_0

; Function draw_random_star
draw_random_star:
PUSH FP
MOV FP, SP
entry:
; Set pixel at (128, 64) to color 15
MOV VM, 0
MOV VX, 128
MOV VY, 64
MOV R8, 15
SWRITE R8
MOV SP, FP
POP FP
RET

