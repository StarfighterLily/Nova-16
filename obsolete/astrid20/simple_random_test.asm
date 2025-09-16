; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF

; Function main
main:
entry:
; Generate random number (0-65535)
RND P0
MOV P0, [FP-2]
; Generate random number between v2 and v3
RNDR P0, 0, 10
MOV P1, [FP-4]
; Generate random number between v6 and v7
RNDR P0, 100, 200
MOV P2, [FP-6]
; Generate random number between v10 and v11
RNDR P0, 42, 42
MOV P3, [FP-8]
; Set active layer to 1
MOV VL, 1
MOV R2, 0
JMP for_header_0
for_header_0:
CMP R2, 20
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
; Generate random number between v20 and v21
RNDR P0, 0, 255
MOV P4, [FP-10]
; Generate random number between v24 and v25
RNDR P0, 0, 191
MOV P5, [FP-12]
; Generate random number between v28 and v29
RNDR P0, 1, 31
MOV P6, [FP-14]
MOV R9, P4
MOV R8, P5
MOV R4, P6
; Set pixel at (R9, R8) to color R4
MOV VM, 0
MOV VX, R9
MOV VY, R8
MOV R8, R4
SWRITE R8
JMP for_increment_3
for_exit_2:
CMP P3, 42
JNZ cmp_true_1
MOV R1, 0
JMP cmp_done_1
cmp_true_1:
MOV R1, 1
cmp_done_1:
MOV P7, R1
MOV R9, P7
CMP R9, 0
JNZ if_then_4
JMP if_merge_6
for_increment_3:
MOV R1, R2
ADD R1, 1
MOV R2, R1
JMP for_header_0
if_then_4:
; Set pixel at (0, 0) to color 31
MOV VM, 0
MOV VX, 0
MOV VY, 0
MOV R8, 31
SWRITE R8
JMP if_merge_6
if_merge_6:
HLT
; Halt processor
HLT

