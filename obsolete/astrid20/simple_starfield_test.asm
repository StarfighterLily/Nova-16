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
; Generate random number between v7 and v8
RNDR P0, 0, 255
MOV R8, P2
; Generate random number between v11 and v12
RNDR P0, 0, 255
MOV R2, P3
; Generate random number between v15 and v16
RNDR P0, 1, 31
MOV R3, P4
; Set pixel at (R8, R2) to color R3
MOV VM, 0
MOV VX, R8
MOV VY, R2
MOV R8, R3
SWRITE R8
JMP for_increment_3
for_exit_2:
; Halt processor
HLT
for_increment_3:
MOV P8, P0
INC P0
JMP for_header_0

