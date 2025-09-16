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
MOV P0, 0
MOV P1, 0
MOV R2, 0
MOV P2, 0x3000
; Set active layer to 1
MOV VL, 1
MOV P1, 0
JMP for_header_0
for_header_0:
CMP P1, 255
JC cmp_true_0
JZ cmp_true_0
MOV R8, 0
JMP cmp_done_0
cmp_true_0:
MOV R8, 1
cmp_done_0:
MOV P3, R8
MOV R9, P3
CMP R9, 0
JNZ for_body_1
JMP for_exit_2
for_body_1:
MOV P0, 0
JMP for_header_4
for_increment_3:
MOV P6, P1
INC P1
JMP for_header_0
for_exit_2:
; Set active layer to 5
MOV VL, 5
; print_string(string, x, y, color) - print string using Nova-16 TEXT instruction
; Input: String pointer in register, coordinates, color
MOV P0, P2      ; Load string pointer into P0
MOV VM, 0                 ; Set coordinate mode for VX,VY positioning
MOV VX, 90               ; Set X coordinate
MOV VY, 124               ; Set Y coordinate  
TEXT P0, 31          ; Draw string at VX,VY coordinates with specified color
; Call user function: screen_roll
; Preserve caller-save registers
MOV P7, P9
SUB P7, 2
MOV [P7], P0
MOV P7, P9
SUB P7, 4
MOV [P7], P1
CALL screen_roll
; Restore caller-save registers
MOV P7, P9
SUB P7, 2
MOV P0, [P7]
MOV P7, P9
SUB P7, 4
MOV P1, [P7]
for_header_4:
CMP P0, 255
JC cmp_true_1
JZ cmp_true_1
MOV R8, 0
JMP cmp_done_1
cmp_true_1:
MOV R8, 1
cmp_done_1:
MOV P7, R8
MOV R9, P7
CMP R9, 0
JNZ for_body_5
JMP for_exit_6
for_body_5:
; Set pixel at (P0, P1) to color R2
MOV VM, 0
MOV VX, P0
MOV VY, P1
MOV R8, R2
SWRITE R8
MOV R8, R2
INC R2
JMP for_increment_7
for_increment_7:
MOV P4, P0
INC P0
JMP for_header_4
for_exit_6:
JMP for_increment_3
MOV SP, FP
POP FP
HLT

; Function screen_roll
screen_roll:
PUSH FP
MOV FP, SP
entry:
MOV P0, 0
; Set active layer to 1
MOV VL, 1
MOV P0, 0
JMP for_header_8
for_header_8:
CMP P0, 512
JC cmp_true_2
MOV R8, 0
JMP cmp_done_2
cmp_true_2:
MOV R8, 1
cmp_done_2:
MOV P1, R8
MOV R9, P1
CMP R9, 0
JNZ for_body_9
JMP for_exit_10
for_body_9:
CMP P0, 511
JZ cmp_true_3
MOV R8, 0
JMP cmp_done_3
cmp_true_3:
MOV R8, 1
cmp_done_3:
MOV P6, R8
MOV R9, P6
CMP R9, 0
JNZ if_then_12
JMP if_merge_14
for_increment_11:
MOV P7, P0
INC P0
JMP for_header_8
for_exit_10:
if_then_12:
; Roll screen horizontally by 1
MOV R0, 1
SROLX R0
MOV P0, 0
JMP if_merge_14
if_merge_14:
JMP for_increment_11
MOV SP, FP
POP FP
RET


; String literal data
ORG 0x3000
string_literal_3000:
DEFSTR "De Nova Stella"
