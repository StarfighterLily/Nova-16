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
SUB SP, 90  ; Allocate stack space for local variables
entry:
; Generate random number (0-65535)
RND P0
MOV P0, P1
; Generate random number (0-65535)
RND P0
MOV P2, P3
; Generate random number (0-65535)
RND P0
MOV P4, P5
CMP P0, P2
JZ cmp_true_0
MOV R8, 0
JMP cmp_done_0
cmp_true_0:
MOV R8, 1
cmp_done_0:
MOV P6, R8
CMP P2, P4
JZ cmp_true_1
MOV R8, 0
JMP cmp_done_1
cmp_true_1:
MOV R8, 1
cmp_done_1:
MOV P7, R8
MOV R8, P6
CMP R8, 0
JZ and_false
MOV R9, P7
CMP R9, 0
JZ and_false
MOV R8, 1
JMP and_done
and_false:
MOV R8, 0
and_done:
MOV P7, R8
MOV R9, P7
CMP R9, 0
JNZ if_then_0
JMP if_merge_2
if_then_0:
; Set pixel at (0, 0) to color 31
MOV VM, 0
MOV VX, 0
MOV VY, 0
MOV R8, 31
SWRITE R8
JMP if_merge_2
if_merge_2:
; Generate random number between 0 and 1 (8-bit)
RNDR P0, 0, 1
MOV P7, P9
SUB P7, 4
MOV R1, [P7]
MOV P7, P9
SUB P7, 2
MOV [P7], R1
; Generate random number between 5 and 7 (8-bit)
RNDR P0, 5, 7
MOV P7, P9
SUB P7, 8
MOV R1, [P7]
MOV P7, P9
SUB P7, 6
MOV [P7], R1
; Generate random number between 42 and 42 (8-bit)
RNDR P0, 42, 42
MOV P7, P9
SUB P7, 12
MOV R1, [P7]
MOV P7, P9
SUB P7, 10
MOV [P7], R1
MOV P7, P9
SUB P7, 10
MOV P7, [P7]
CMP P7, 42
JNZ cmp_true_2
MOV R1, 0
JMP cmp_done_2
cmp_true_2:
MOV R1, 1
cmp_done_2:
MOV P7, P9
SUB P7, 14
MOV [P7], R1
MOV R9, [FP-14]
CMP R9, 0
JNZ if_then_3
JMP if_merge_5
if_then_3:
; Set pixel at (1, 0) to color 31
MOV VM, 0
MOV VX, 1
MOV VY, 0
MOV R8, 31
SWRITE R8
JMP if_merge_5
if_merge_5:
; Generate random number between 0 and 255 (8-bit)
RNDR P0, 0, 255
MOV P7, P9
SUB P7, 18
MOV R1, [P7]
MOV P7, P9
SUB P7, 16
MOV [P7], R1
; Generate random number between 100 and 200 (8-bit)
RNDR P0, 100, 200
MOV P7, P9
SUB P7, 22
MOV R1, [P7]
MOV P7, P9
SUB P7, 20
MOV [P7], R1
; Generate random number between 0 and 65535 (16-bit)
RNDR P0, 0, 65535
MOV P7, P9
SUB P7, 26
MOV R1, [P7]
MOV P7, P9
SUB P7, 24
MOV [P7], R1
; Generate random number between 1000 and 30000 (16-bit)
RNDR P0, 1000, 30000
MOV P7, P9
SUB P7, 30
MOV R1, [P7]
MOV P7, P9
SUB P7, 28
MOV [P7], R1
; Generate random number between 0 and 32767 (16-bit)
RNDR P0, 0, 32767
MOV P7, P9
SUB P7, 34
MOV R1, [P7]
MOV P7, P9
SUB P7, 32
MOV [P7], R1
; Generate random number between 32768 and 65535 (16-bit)
RNDR P0, 32768, 65535
MOV P7, P9
SUB P7, 38
MOV R1, [P7]
MOV P7, P9
SUB P7, 36
MOV [P7], R1
MOV R1, 10
MOV P7, P9
SUB P7, 40
MOV [P7], R1
MOV R1, 20
MOV P7, P9
SUB P7, 42
MOV [P7], R1
MOV P7, P9
SUB P7, 40
MOV P7, [P7]
MOV P7, P9
SUB P7, 42
MOV P7, [P7]
; Generate random number between P7 and P7
RNDR P0, P7, P7
MOV P7, P9
SUB P7, 46
MOV R1, [P7]
MOV P7, P9
SUB P7, 44
MOV [P7], R1
MOV P7, P9
SUB P7, 44
MOV P7, [P7]
CMP P7, 10
JC cmp_true_3
MOV R1, 0
JMP cmp_done_3
cmp_true_3:
MOV R1, 1
cmp_done_3:
MOV P7, P9
SUB P7, 48
MOV [P7], R1
MOV P7, P9
SUB P7, 44
MOV P7, [P7]
CMP P7, 20
JC cmp_done_4
JZ cmp_done_4
JMP cmp_true_4
MOV R1, 0
JMP cmp_done_4
cmp_true_4:
MOV R1, 1
cmp_done_4:
MOV P7, P9
SUB P7, 50
MOV [P7], R1
MOV R1, [FP-48]
CMP R1, 0
JNZ or_true
MOV R0, [FP-50]
CMP R0, 0
JNZ or_true
MOV R1, 0
JMP or_done
or_true:
MOV R1, 1
or_done:
MOV P7, P9
SUB P7, 52
MOV [P7], R1
MOV R9, [FP-52]
CMP R9, 0
JNZ if_then_6
JMP if_merge_8
if_then_6:
; Set pixel at (2, 0) to color 31
MOV VM, 0
MOV VX, 2
MOV VY, 0
MOV R8, 31
SWRITE R8
JMP if_merge_8
if_merge_8:
; Set active layer to 1
MOV VL, 1
MOV R2, 0
MOV P7, P9
SUB P7, 54
MOV [P7], R2
JMP for_header_9
for_header_9:
MOV P7, P9
SUB P7, 54
MOV P7, [P7]
CMP P7, 500
JC cmp_true_5
MOV R2, 0
JMP cmp_done_5
cmp_true_5:
MOV R2, 1
cmp_done_5:
MOV P7, P9
SUB P7, 56
MOV [P7], R2
MOV R9, [FP-56]
CMP R9, 0
JNZ for_body_10
JMP for_exit_11
for_body_10:
; Generate random number between 0 and 255 (8-bit)
RNDR P0, 0, 255
MOV P7, P9
SUB P7, 60
MOV R2, [P7]
MOV P7, P9
SUB P7, 58
MOV [P7], R2
; Generate random number between 0 and 191 (8-bit)
RNDR P0, 0, 191
MOV P7, P9
SUB P7, 64
MOV R2, [P7]
MOV P7, P9
SUB P7, 62
MOV [P7], R2
; Generate random number between 1 and 31 (8-bit)
RNDR P0, 1, 31
MOV P7, P9
SUB P7, 68
MOV R2, [P7]
MOV P7, P9
SUB P7, 66
MOV [P7], R2
MOV P7, P9
SUB P7, 58
MOV R2, [P7]
MOV P7, P9
SUB P7, 62
MOV R2, [P7]
MOV P7, P9
SUB P7, 66
MOV R2, [P7]
; Set pixel at (R2, R2) to color R2
MOV VM, 0
MOV VX, R2
MOV VY, R2
MOV R8, R2
SWRITE R8
JMP for_increment_12
for_increment_12:
MOV P7, P9
SUB P7, 54
MOV R3, [P7]
ADD R3, 1
MOV P7, P9
SUB P7, 70
MOV [P7], R3
MOV P7, P9
SUB P7, 70
MOV R3, [P7]
MOV P7, P9
SUB P7, 54
MOV [P7], R3
JMP for_header_9
for_exit_11:
; Generate random number (0-65535)
RND P0
MOV P7, P9
SUB P7, 74
MOV R3, [P7]
MOV P7, P9
SUB P7, 72
MOV [P7], R3
; Generate random number (0-65535)
RND P0
MOV P7, P9
SUB P7, 78
MOV R3, [P7]
MOV P7, P9
SUB P7, 76
MOV [P7], R3
; Generate random number (0-65535)
RND P0
MOV P7, P9
SUB P7, 82
MOV R3, [P7]
MOV P7, P9
SUB P7, 80
MOV [P7], R3
; Generate random number (0-65535)
RND P0
MOV P7, P9
SUB P7, 86
MOV R3, [P7]
MOV P7, P9
SUB P7, 84
MOV [P7], R3
MOV R3, [FP-72]
MOV P7, 256
MOV R4, :P7
MOD R3, R4
MOV P7, P9
SUB P7, 88
MOV [P7], R3
MOV P7, P9
SUB P7, 88
MOV P7, [P7]
; Set pixel at (P7, 190) to color 10
MOV VM, 0
MOV VX, P7
MOV VY, 190
MOV R8, 10
SWRITE R8
MOV R5, [FP-76]
MOV P7, 256
MOV R6, :P7
MOD R5, R6
MOV P7, P9
SUB P7, 90
MOV [P7], R5
MOV P7, P9
SUB P7, 90
MOV P7, [P7]
; Set pixel at (P7, 191) to color 11
MOV VM, 0
MOV VX, P7
MOV VY, 191
MOV R8, 11
SWRITE R8
; Halt processor
MOV SP, FP
POP FP
HLT

