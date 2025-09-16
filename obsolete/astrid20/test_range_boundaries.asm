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
SUB SP, 4  ; Allocate stack space for local variables
entry:
; Generate random number between 0 and 255 (8-bit)
RNDR P0, 0, 255
MOV P0, P1
; Generate random number between 0 and 191 (8-bit)
RNDR P0, 0, 191
MOV P2, P3
; Generate random number between 1 and 31 (8-bit)
RNDR P0, 1, 31
MOV P4, P5
CMP P0, 255
JC cmp_done_0
JZ cmp_done_0
JMP cmp_true_0
MOV R8, 0
JMP cmp_done_0
cmp_true_0:
MOV R8, 1
cmp_done_0:
MOV P6, R8
MOV R9, P6
CMP R9, 0
JNZ if_then_0
JMP if_else_1
if_then_0:
; Set pixel at (0, 0) to color 31
MOV VM, 0
MOV VX, 0
MOV VY, 0
MOV R8, 31
SWRITE R8
JMP if_merge_2
if_else_1:
CMP P2, 191
JC cmp_done_1
JZ cmp_done_1
JMP cmp_true_1
MOV R8, 0
JMP cmp_done_1
cmp_true_1:
MOV R8, 1
cmp_done_1:
MOV P7, R8
MOV R9, P7
CMP R9, 0
JNZ if_then_3
JMP if_else_4
if_merge_2:
; Halt processor
MOV SP, FP
POP FP
HLT
if_then_3:
; Set pixel at (1, 0) to color 31
MOV VM, 0
MOV VX, 1
MOV VY, 0
MOV R8, 31
SWRITE R8
JMP if_merge_5
if_else_4:
CMP P4, 31
JC cmp_done_2
JZ cmp_done_2
JMP cmp_true_2
MOV R8, 0
JMP cmp_done_2
cmp_true_2:
MOV R8, 1
cmp_done_2:
MOV P7, R8
CMP P4, 1
JC cmp_true_3
MOV R8, 0
JMP cmp_done_3
cmp_true_3:
MOV R8, 1
cmp_done_3:
MOV P7, P9
SUB P7, 2
MOV [P7], R8
MOV R8, P7
CMP R8, 0
JNZ or_true
MOV R9, [FP-2]
CMP R9, 0
JNZ or_true
MOV R8, 0
JMP or_done
or_true:
MOV R8, 1
or_done:
MOV P7, P9
SUB P7, 4
MOV [P7], R8
MOV R9, [FP-4]
CMP R9, 0
JNZ if_then_6
JMP if_else_7
if_merge_5:
JMP if_merge_2
if_then_6:
; Set pixel at (2, 0) to color 31
MOV VM, 0
MOV VX, 2
MOV VY, 0
MOV R8, 31
SWRITE R8
JMP if_merge_8
if_else_7:
; Set pixel at (0, 0) to color 1
MOV VM, 0
MOV VX, 0
MOV VY, 0
MOV R8, 1
SWRITE R8
JMP if_merge_8
if_merge_8:
JMP if_merge_5

