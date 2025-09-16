; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF

; Function main
main:
MOV FP, SP
SUB SP, 6  ; Allocate stack space for local variables
entry:
; Generate random number (0-65535)
RND P0
MOV P0, [FP-8]
; Generate random number (0-65535)
RND P0
MOV P1, [FP-10]
; Generate random number (0-65535)
RND P0
MOV P2, [FP-12]
; Generate random number between v6 and v7
RNDR P0, 1, 6
MOV P3, [FP-14]
; Generate random number between v10 and v11
RNDR P0, 0, 255
MOV P4, [FP-16]
; Generate random number between v14 and v15
RNDR P0, 0, 255
MOV P5, [FP-18]
; Generate random number between v18 and v19
RNDR P0, 0, 31
MOV P6, [FP-20]
MOV R2, P4
MOV R3, P5
MOV R4, P6
MOV P7, 10
MOV R8, 50
MOV P8, FP
SUB P8, 2
MOV [P8], R8
; Generate random number with mixed reg/immediate
MOV P9, [FP-2]
RNDR P0, P7, P9
MOV P8, [FP-22]
; Set active layer to 1
MOV VL, 1
MOV R8, 0
JMP for_header_0
for_header_0:
CMP R8, 10
JC cmp_true_0
MOV R1, 0
JMP cmp_done_0
cmp_true_0:
MOV R1, 1
cmp_done_0:
MOV R5, R1
MOV R9, R5
CMP R9, 0
JNZ for_body_1
JMP for_exit_2
for_body_1:
; Generate random number between v37 and v38
RNDR P0, 0, 255
MOV R9, [FP-24]
MOV P9, FP
SUB P9, 4
MOV [P9], R9
; Generate random number between v41 and v42
RNDR P0, 0, 255
MOV P9, [FP-26]
; Generate random number between v45 and v46
RNDR P0, 1, 31
MOV R9, [FP-28]
MOV P9, FP
SUB P9, 6
MOV [P9], R9
MOV P9, FP
SUB P9, 4
MOV R9, [P9]
MOV R9, P9
MOV P9, FP
SUB P9, 6
MOV R1, [P9]
; Set pixel at (R9, R9) to color R1
MOV VM, 0
MOV VX, R9
MOV VY, R9
MOV R8, R1
SWRITE R8
JMP for_increment_3
for_exit_2:
; Halt processor
HLT
for_increment_3:
MOV R9, R8
ADD R9, 1
MOV R8, R9
JMP for_header_0

