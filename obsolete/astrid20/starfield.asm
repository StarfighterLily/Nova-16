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
SUB SP, 16  ; Allocate stack space for local variables
entry:
; Set active layer to 1
MOV VL, 1
MOV R2, 0
MOV R2, 0
JMP for_header_0
for_header_0:
CMP R2, 65
JC cmp_true_0
MOV R9, 0
JMP cmp_done_0
cmp_true_0:
MOV R9, 1
cmp_done_0:
MOV R3, R9
MOV R9, R3
CMP R9, 0
JNZ for_body_1
JMP for_exit_2
for_body_1:
; Generate random number between 0 and 255 (8-bit)
RNDR P0, 0, 255
MOV P1, P0
; Generate random number between 0 and 255 (8-bit)
RNDR P0, 0, 255
MOV P2, P0
MOV P3, P2
; Generate random number between 1 and 5 (8-bit)
RNDR P0, 1, 5
MOV P4, P0
MOV R9, P4
; Set pixel at (P1, P3) to color R9
MOV VM, 0
MOV VX, P1
MOV VY, P3
MOV R8, R9
SWRITE R8
JMP for_increment_3
for_increment_3:
MOV R8, R2
INC R2
JMP for_header_0
for_exit_2:
; Set active layer to 2
MOV VL, 2
MOV R4, 0
MOV R4, 0
JMP for_header_4
for_header_4:
CMP R4, 65
JC cmp_true_1
MOV R0, 0
JMP cmp_done_1
cmp_true_1:
MOV R0, 1
cmp_done_1:
MOV R5, R0
MOV R9, R5
CMP R9, 0
JNZ for_body_5
JMP for_exit_6
for_body_5:
; Generate random number between 0 and 255 (8-bit)
RNDR P0, 0, 255
MOV P5, P0
MOV P6, P5
; Generate random number between 0 and 255 (8-bit)
RNDR P0, 0, 255
MOV P7, P0
MOV P7, P9
SUB P7, 2
MOV [P7], P7
; Generate random number between 6 and 11 (8-bit)
RNDR P0, 6, 11
MOV P7, P9
SUB P7, 4
MOV [P7], P0
MOV P7, P9
SUB P7, 4
MOV R0, [P7]
MOV P7, P9
SUB P7, 2
MOV P7, [P7]
; Set pixel at (P6, P7) to color R0
MOV VM, 0
MOV VX, P6
MOV VY, P7
MOV R8, R0
SWRITE R8
JMP for_increment_7
for_increment_7:
MOV R1, R4
INC R4
JMP for_header_4
for_exit_6:
; Set active layer to 3
MOV VL, 3
MOV R6, 0
MOV R6, 0
JMP for_header_8
for_header_8:
CMP R6, 65
JC cmp_true_2
MOV R9, 0
JMP cmp_done_2
cmp_true_2:
MOV R9, 1
cmp_done_2:
MOV R7, R9
MOV R9, R7
CMP R9, 0
JNZ for_body_9
JMP for_exit_10
for_body_9:
; Generate random number between 0 and 255 (8-bit)
RNDR P0, 0, 255
MOV P7, P9
SUB P7, 6
MOV [P7], P0
MOV P7, P9
SUB P7, 6
MOV R9, [P7]
MOV P7, P9
SUB P7, 8
MOV [P7], R9
; Generate random number between 0 and 255 (8-bit)
RNDR P0, 0, 255
MOV P7, P9
SUB P7, 10
MOV [P7], P0
MOV P7, P9
SUB P7, 10
MOV R9, [P7]
MOV P7, P9
SUB P7, 12
MOV [P7], R9
; Generate random number between 12 and 15 (8-bit)
RNDR P0, 12, 15
MOV P7, P9
SUB P7, 14
MOV [P7], P0
MOV P7, P9
SUB P7, 14
MOV R9, [P7]
MOV P7, P9
SUB P7, 15
MOV [P7], R9
MOV P7, P9
SUB P7, 8
MOV P7, [P7]
MOV P7, P9
SUB P7, 12
MOV P7, [P7]
MOV P7, P9
SUB P7, 15
MOV P7, [P7]
; Set pixel at (P7, P7) to color P7
MOV VM, 0
MOV VX, P7
MOV VY, P7
MOV R8, P7
SWRITE R8
JMP for_increment_11
for_increment_11:
MOV P7, P9
SUB P7, 16
MOV [P7], R6
INC R6
JMP for_header_8
for_exit_10:
; Halt processor
MOV SP, FP
POP FP
HLT

