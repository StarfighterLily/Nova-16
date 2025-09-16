; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF

; Function main
main:
PUSH FP
MOV FP, SP
SUB SP, 64  ; Allocate stack space for local variables
entry:
MOV P0, 100
MOV P1, 200
MOV R3, P0
MOV R4, P1
ADD R3, R4
MOV :P2, R3
JC add_carry_0
JMP add_done_0
add_carry_0:
MOV R3, P0:
ADD R3, 1
MOV P2:, R3
add_done_0:
MOV P3, P2
MOV P4, 0
MOV P5, 1
MOV P6, 2
MOV P7, 3
MOV R8, 4
MOV P7, P9
SUB P7, 2
MOV [P7], R8
MOV R8, 5
MOV P7, P9
SUB P7, 4
MOV [P7], R8
MOV R8, 6
MOV P7, P9
SUB P7, 6
MOV [P7], R8
MOV R8, 7
MOV P7, P9
SUB P7, 8
MOV [P7], R8
MOV R8, 8
MOV P7, P9
SUB P7, 10
MOV [P7], R8
MOV R8, 9
MOV P7, P9
SUB P7, 12
MOV [P7], R8
MOV R8, 10
MOV P7, P9
SUB P7, 14
MOV [P7], R8
MOV R8, 11
MOV P7, P9
SUB P7, 16
MOV [P7], R8
MOV R8, 0
MOV P7, P9
SUB P7, 18
MOV [P7], R8
JMP for_header_0
for_header_0:
MOV P7, P9
SUB P7, 18
MOV P7, [P7]
CMP P7, 5
JC cmp_true_1
MOV R8, 0
JMP cmp_done_1
cmp_true_1:
MOV R8, 1
cmp_done_1:
MOV P7, P9
SUB P7, 20
MOV [P7], R8
MOV R9, [P5]
CMP R9, 0
JNZ for_body_1
JMP for_exit_2
for_body_1:
MOV R5, P4
MOV R6, P5
ADD R5, R6
MOV P7, P9
SUB P7, 22
MOV [P7], R5
MOV P7, P9
SUB P7, 22
MOV R8, [P7]
MOV P7, P9
SUB P7, 24
MOV [P7], R8
MOV R7, P6
MOV R8, P7
MUL R7, R8
MOV P7, P9
SUB P7, 26
MOV [P7], R7
MOV P7, P9
SUB P7, 26
MOV R9, [P7]
MOV P7, P9
SUB P7, 28
MOV [P7], R9
MOV R9, [[FP-24]]
MOV P7, P9
SUB P7, 28
MOV R1, [P7]
ADD R9, R1
MOV P7, P9
SUB P7, 30
MOV [P7], R9
MOV P7, P9
SUB P7, 30
MOV R0, [P7]
MOV P7, P9
SUB P7, 32
MOV [P7], R0
; Unknown instruction: v41 = % v39, v40
; Set pixel at (v31, v31) to color v41
MOV VM, 0
MOV VX, P6
MOV VY, P6
MOV R8, 0x2000
SWRITE R8
JMP for_increment_3
for_exit_2:
; Call user function: calculate_value
MOV R1, P7
MOV R2, [FP-2]
MOV R3, [FP-4]
CALL calculate_value
MOV P7, P9
SUB P7, 34
MOV [P7], R0
MOV R9, [[FP-8]]
MOV P7, P9
SUB P7, 10
MOV R8, [P7]
ADD R9, R8
MOV P7, P9
SUB P7, 36
MOV [P7], R9
MOV R9, [[FP-12]]
MOV P7, P9
SUB P7, 14
MOV R8, [P7]
SUB R9, R8
MOV P7, P9
SUB P7, 38
MOV [P7], R9
MOV R9, [[FP-36]]
MOV P7, P9
SUB P7, 38
MOV R8, [P7]
MUL R9, R8
MOV P7, P9
SUB P7, 40
MOV [P7], R9
MOV P7, P9
SUB P7, 16
MOV R2, [P7]
ADD R2, 1
MOV P7, P9
SUB P7, 42
MOV [P7], R2
MOV R9, [[FP-40]]
MOV P7, P9
SUB P7, 42
MOV R8, [P7]
DIV R9, R8
MOV P7, P9
SUB P7, 44
MOV [P7], R9
MOV P7, P9
SUB P7, 44
MOV R2, [P7]
MOV P7, P9
SUB P7, 46
MOV [P7], R2
; Set active layer to 1
MOV VL, 1
MOV R2, 0
MOV P7, P9
SUB P7, 48
MOV [P7], R2
JMP for_header_4
for_increment_3:
MOV P7, P9
SUB P7, 18
MOV R2, [P7]
MOV P7, P9
SUB P7, 50
MOV [P7], R2
INC R2
MOV P7, P9
SUB P7, 18
MOV [P7], R2
JMP for_header_0
for_header_4:
MOV P7, P9
SUB P7, 48
MOV P7, [P7]
CMP P7, 10
JC cmp_true_2
MOV R2, 0
JMP cmp_done_2
cmp_true_2:
MOV R2, 1
cmp_done_2:
MOV P7, P9
SUB P7, 52
MOV [P7], R2
MOV R9, [[FP-6]]
CMP R9, 0
JNZ for_body_5
JMP for_exit_6
for_body_5:
MOV R2, 0
MOV P7, P9
SUB P7, 54
MOV [P7], R2
JMP for_header_8
for_exit_6:
for_increment_7:
MOV P7, P9
SUB P7, 48
MOV R2, [P7]
MOV P7, P9
SUB P7, 56
MOV [P7], R2
INC R2
MOV P7, P9
SUB P7, 48
MOV [P7], R2
JMP for_header_4
for_header_8:
MOV P7, P9
SUB P7, 54
MOV P7, [P7]
CMP P7, 10
JC cmp_true_3
MOV R2, 0
JMP cmp_done_3
cmp_true_3:
MOV R2, 1
cmp_done_3:
MOV P7, P9
SUB P7, 58
MOV [P7], R2
MOV R9, [[FP-8]]
CMP R9, 0
JNZ for_body_9
JMP for_exit_10
for_body_9:
MOV R9, [[FP-54]]
MOV P7, P9
SUB P7, 48
MOV R8, [P7]
ADD R9, R8
MOV P7, P9
SUB P7, 60
MOV [P7], R9
MOV R9, [[FP-60]]
MOV P7, P9
SUB P7, 46
MOV R8, [P7]
ADD R9, R8
MOV P7, P9
SUB P7, 62
MOV [P7], R9
; Unknown instruction: v66 = % v64, v65
; Set pixel at (v60, v56) to color v66
MOV VM, 0
MOV VX, 0x2002
MOV VY, 0x2004
MOV R8, [FP-10]
SWRITE R8
JMP for_increment_11
for_exit_10:
JMP for_increment_7
for_increment_11:
MOV P7, P9
SUB P7, 54
MOV R2, [P7]
MOV P7, P9
SUB P7, 64
MOV [P7], R2
INC R2
MOV P7, P9
SUB P7, 54
MOV [P7], R2
JMP for_header_8
MOV SP, FP
POP FP
HLT

; Function calculate_value
calculate_value:
PUSH FP
MOV FP, SP
entry:
MOV R0, R2
MOV R8, 2
MUL R0, R8
MOV P0, R0
MOV P1, P0
MOV R9, R3
MOV R8, R4
ADD R9, R8
MOV :P2, R9
JC add_carry_4
JMP add_done_4
add_carry_4:
MOV R9, 0
ADD R9, 1
MOV P2:, R9
add_done_4:
MOV P3, P2
MOV R9, P1
MOV R8, P3
ADD R9, R8
MOV :P4, R9
JC add_carry_5
JMP add_done_5
add_carry_5:
MOV R9, P1:
ADD R9, 1
MOV P4:, R9
add_done_5:
MOV R0, P4
MOV SP, FP
POP FP
RET

