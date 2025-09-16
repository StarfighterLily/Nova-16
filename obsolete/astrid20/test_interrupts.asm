; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF

; Function timer_handler
timer_handler:
PUSH FP
MOV FP, SP
entry:
MOV R2, 100
MOV R3, 100
; Set pixel at (R2, R3) to color 15
MOV VM, 0
MOV VX, R2
MOV VY, R3
MOV R8, 15
SWRITE R8
MOV SP, FP
POP FP
RET

; Function main
main:
PUSH FP
MOV FP, SP
entry:
; Configure timer: match=v6, speed=v7, control=v8
MOV TM, 255    ; Timer match value
MOV TS, 80          ; Timer speed
MOV TC, 3        ; Timer control
; Enable interrupts
STI
JMP while_header_0
while_header_0:
JMP while_body_1
while_body_1:
MOV P0, 0
MOV P0, 0
JMP for_header_3
while_exit_2:
MOV SP, FP
POP FP
HLT
for_header_3:
CMP P0, 1000
JC cmp_true_0
MOV R8, 0
JMP cmp_done_0
cmp_true_0:
MOV R8, 1
cmp_done_0:
MOV P1, R8
MOV R9, P1
CMP R9, 0
JNZ for_body_4
JMP for_exit_5
for_body_4:
JMP for_increment_6
for_exit_5:
JMP while_header_0
for_increment_6:
MOV P6, P0
INC P0
JMP for_header_3

