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
; Generate random number (0-65535)
RND P0
MOV P0, P1
; Generate random number between 0 and 10 (8-bit)
RNDR P0, 0, 10
MOV P2, P3
; Generate random number between 42 and 42 (8-bit)
RNDR P0, 42, 42
MOV P4, P5
CMP P4, 42
JZ cmp_true_0
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
; Set pixel at (0, 0) to color 1
MOV VM, 0
MOV VX, 0
MOV VY, 0
MOV R8, 1
SWRITE R8
JMP if_merge_2
if_else_1:
; Set pixel at (0, 0) to color 31
MOV VM, 0
MOV VX, 0
MOV VY, 0
MOV R8, 31
SWRITE R8
JMP if_merge_2
if_merge_2:
; Halt processor
MOV SP, FP
POP FP
HLT

