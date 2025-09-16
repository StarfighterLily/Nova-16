; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF

; Function main
main:
MOV FP, SP
SUB SP, 38  ; Allocate stack space for local variables
entry:
; Generate random number between v0 and v1
RNDR P0, 0, 0
MOV P0, [FP-40]
; Generate random number between v4 and v5
RNDR P0, 65535, 65535
MOV P1, [FP-42]
CMP P0, 0
JNZ cmp_true_0
MOV R8, 0
JMP cmp_done_0
cmp_true_0:
MOV R8, 1
cmp_done_0:
MOV P2, R8
MOV R9, P2
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
CMP P1, 65535
JNZ cmp_true_1
MOV R8, 0
JMP cmp_done_1
cmp_true_1:
MOV R8, 1
cmp_done_1:
MOV P6, R8
MOV R9, P6
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
; Generate random number between v20 and v21
RNDR P0, 100, 50
MOV P7, [FP-44]
; Generate random number between v24 and v25
RNDR P0, 65535, 0
MOV P3, [FP-46]
MOV R8, 0
JMP for_header_6
for_header_6:
CMP R8, 50
JC cmp_true_2
MOV R1, 0
JMP cmp_done_2
cmp_true_2:
MOV R1, 1
cmp_done_2:
MOV R8, R1
MOV R9, R8
CMP R9, 0
JNZ for_body_7
JMP for_exit_8
for_body_7:
; Generate random number between v32 and v33
RNDR P0, 254, 256
MOV P4, [FP-48]
CMP P4, 254
JC cmp_true_3
MOV R9, 0
JMP cmp_done_3
cmp_true_3:
MOV R9, 1
cmp_done_3:
MOV P5, R9
CMP P4, 256
JC cmp_done_4
JZ cmp_done_4
JMP cmp_true_4
MOV R9, 0
JMP cmp_done_4
cmp_true_4:
MOV R9, 1
cmp_done_4:
MOV P6, R9
MOV R9, P5
CMP R9, 0
JNZ or_true
MOV R1, P6
CMP R1, 0
JNZ or_true
MOV R9, 0
JMP or_done
or_true:
MOV R9, 1
or_done:
MOV P7, R9
MOV R9, P7
CMP R9, 0
JNZ if_then_10
JMP if_else_11
for_exit_8:
MOV R9, 0
JMP for_header_13
for_increment_9:
MOV R9, R8
ADD R9, 1
MOV R8, R9
JMP for_header_6
if_then_10:
; Set pixel at (R8, 1) to color 31
MOV VM, 0
MOV VX, R8
MOV VY, 1
MOV R8, 31
SWRITE R8
JMP if_merge_12
if_else_11:
MOV R1, R8
MOV R3, P4
MOV R4, 254
SUB R3, R4
MOV P7, FP
SUB P7, 2
MOV [P7], R3
MOV R5, 10
MOV P7, FP
SUB P7, 2
MOV R6, [P7]
ADD R5, R6
MOV P7, FP
SUB P7, 4
MOV [P7], R5
MOV P7, FP
SUB P7, 4
MOV R9, [P7]
; Set pixel at (R1, R9) to color 15
MOV VM, 0
MOV VX, R1
MOV VY, R9
MOV R8, 15
SWRITE R8
JMP if_merge_12
if_merge_12:
JMP for_increment_9
for_header_13:
CMP R9, 100
JC cmp_true_5
MOV R7, 0
JMP cmp_done_5
cmp_true_5:
MOV R7, 1
cmp_done_5:
MOV R2, R7
MOV R9, R2
CMP R9, 0
JNZ for_body_14
JMP for_exit_15
for_body_14:
; Generate random number between v58 and v59
RNDR P0, 0, 60000
MOV R0, [FP-50]
MOV P7, FP
SUB P7, 6
MOV [P7], R0
MOV R7, [[FP-6]]
MOV P7, 2000
MOV R0, :P7
DIV R7, R0
MOV P7, FP
SUB P7, 8
MOV [P7], R7
MOV P7, FP
SUB P7, 8
MOV R0, [P7]
CMP R0, 30
JC cmp_true_6
MOV R9, 0
JMP cmp_done_6
cmp_true_6:
MOV R9, 1
cmp_done_6:
MOV R7, R9
MOV R9, R7
CMP R9, 0
JNZ if_then_17
JMP if_merge_19
for_exit_15:
; Generate random number between v79 and v80
RNDR P0, 0, 255
MOV R9, [FP-52]
MOV P7, FP
SUB P7, 10
MOV [P7], R9
; Generate random number between v83 and v84
RNDR P0, 0, 511
MOV R9, [FP-54]
MOV P7, FP
SUB P7, 12
MOV [P7], R9
; Generate random number between v87 and v88
RNDR P0, 0, 1023
MOV R9, [FP-56]
MOV P7, FP
SUB P7, 14
MOV [P7], R9
; Generate random number between v91 and v92
RNDR P0, 0, 32767
MOV R9, [FP-58]
MOV P7, FP
SUB P7, 16
MOV [P7], R9
; Set active layer to 2
MOV VL, 2
MOV R9, 0
JMP for_header_20
for_increment_16:
MOV R0, R9
ADD R0, 1
MOV R9, R0
JMP for_header_13
if_then_17:
MOV R9, R0
MOV R8, 8
MUL R9, R8
MOV R3, R9
MOV R4, R3
MOV R8, 10
DIV R9, R8
MOV R5, R9
MOV R9, 50
MOV R8, R5
ADD R9, R8
MOV R6, R9
MOV R7, R6
; Set pixel at (R4, R7) to color 20
MOV VM, 0
MOV VX, R4
MOV VY, R7
MOV R8, 20
SWRITE R8
JMP if_merge_19
if_merge_19:
JMP for_increment_16
for_header_20:
CMP R9, 100
JC cmp_true_7
MOV R9, 0
JMP cmp_done_7
cmp_true_7:
MOV R9, 1
cmp_done_7:
MOV P7, FP
SUB P7, 17
MOV [P7], R9
MOV R9, [[FP-17]]
CMP R9, 0
JNZ for_body_21
JMP for_exit_22
for_body_21:
; Generate random number (0-65535)
RND P0
MOV R9, [FP-60]
MOV P7, FP
SUB P7, 19
MOV [P7], R9
; Generate random number (0-65535)
RND P0
MOV R9, [FP-62]
MOV P7, FP
SUB P7, 21
MOV [P7], R9
; Generate random number (0-65535)
RND P0
MOV R9, [FP-64]
MOV P7, FP
SUB P7, 23
MOV [P7], R9
MOV P7, FP
SUB P7, 19
MOV R9, [P7]
ADD R9, 1
MOV P7, FP
SUB P7, 25
MOV [P7], R9
MOV P7, FP
SUB P7, 21
MOV P7, [P7]
MOV P7, FP
SUB P7, 25
MOV P7, [P7]
CMP P7, P7
JZ cmp_true_8
MOV R9, 0
JMP cmp_done_8
cmp_true_8:
MOV R9, 1
cmp_done_8:
MOV P7, FP
SUB P7, 27
MOV [P7], R9
MOV P7, FP
SUB P7, 21
MOV R9, [P7]
ADD R9, 1
MOV P7, FP
SUB P7, 29
MOV [P7], R9
MOV P7, FP
SUB P7, 23
MOV P7, [P7]
MOV P7, FP
SUB P7, 29
MOV P7, [P7]
CMP P7, P7
JZ cmp_true_9
MOV R9, 0
JMP cmp_done_9
cmp_true_9:
MOV R9, 1
cmp_done_9:
MOV P7, FP
SUB P7, 31
MOV [P7], R9
MOV R9, [[FP-27]]
CMP R9, 0
JZ and_false
MOV R9, [[FP-31]]
CMP R9, 0
JZ and_false
MOV R9, 1
JMP and_done
and_false:
MOV R9, 0
and_done:
MOV P7, FP
SUB P7, 33
MOV [P7], R9
MOV R9, [[FP-33]]
CMP R9, 0
JNZ if_then_24
JMP if_merge_26
for_exit_22:
; Halt processor
HLT
for_increment_23:
MOV R9, R9
ADD R9, 1
MOV P7, FP
SUB P7, 34
MOV [P7], R9
MOV P7, FP
SUB P7, 34
MOV R9, [P7]
JMP for_header_20
if_then_24:
; Set pixel at (R9, 100) to color 31
MOV VM, 0
MOV VX, R9
MOV VY, 100
MOV R8, 31
SWRITE R8
JMP if_merge_26
if_merge_26:
; Unknown instruction: v118 = % v102, v117
MOV R9, [FP-66]
MOV P7, FP
SUB P7, 35
MOV [P7], R9
; Unknown instruction: v122 = % v98, v121
MOV R9, 150
MOV P7, FP
SUB P7, 36
MOV R8, [P7]
ADD R9, R8
MOV P7, FP
SUB P7, 37
MOV [P7], R9
MOV P7, FP
SUB P7, 37
MOV R9, [P7]
MOV P7, FP
SUB P7, 38
MOV [P7], R9
; Set pixel at (v119, v124) to color 5
MOV VM, 0
MOV VX, [FP-35]
MOV VY, [FP-38]
MOV R8, 5
SWRITE R8
JMP for_increment_23

