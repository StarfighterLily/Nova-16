; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF
MOV P0, 0x0000
PUSH P0
CALL main
HLT

; Function simple_add
simple_add:
PUSH FP
MOV FP, SP
entry:
MOV P6, P9
ADD P6, 4
MOV R3, [P6]
MOV P6, P9
ADD P6, 6
MOV R4, [P6]
ADD R3, R4
MOV :P0, R3
JC add_carry_0
JMP add_done_0
add_carry_0:
MOV R3, 0
ADD R3, 1
MOV P0:, R3
add_done_0:
MOV R0, P0
MOV SP, FP
POP FP
RET

; Function main
main:
PUSH FP
MOV FP, SP
entry:
; Call user function: simple_add
MOV R8, 7
PUSH R8
MOV R8, 15
PUSH R8
CALL simple_add
ADD SP, 4         ; Clean up 2 parameters
MOV P0, R0
MOV P1, P0
; Halt processor
MOV SP, FP
POP FP
HLT

