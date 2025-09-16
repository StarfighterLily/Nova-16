; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF

; Function add
add:
PUSH FP
MOV FP, SP
entry:
MOV R5, R2
MOV R6, R3
ADD R5, R6
MOV R4, R5
MOV R0, R4
MOV SP, FP
POP FP
RET

; Function main
main:
PUSH FP
MOV FP, SP
entry:
; Call user function: add
MOV R1, 15
MOV R2, 25
CALL add
MOV R2, R0
; Halt processor
MOV SP, FP
POP FP
HLT

