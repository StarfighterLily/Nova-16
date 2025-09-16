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
entry:
; Set active layer to 1
MOV VL, 1
MOV R2, 0
MOV R2, 0
JMP for_header_0
for_header_0:
CMP R2, 50
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
; Generate random number between 1 and 15 (8-bit)
RNDR P0, 1, 15
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
; Halt processor
MOV SP, FP
POP FP
HLT

