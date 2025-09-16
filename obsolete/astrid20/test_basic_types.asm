; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF

; Function main
main:
PUSH FP
MOV FP, SP
entry:
MOV P0, 10
MOV R3, P0
MOV R4, 5
ADD R3, R4
MOV :P1, R3
JC add_carry_0
JMP add_done_0
add_carry_0:
MOV R3, P0:
ADD R3, 1
MOV P1:, R3
add_done_0:
MOV P0, P1
; Halt processor
MOV SP, FP
POP FP
HLT

