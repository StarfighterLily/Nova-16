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
MOV P0, 42
MOV P1, P0
ADD P1, 1
MOV P0, P1
; Halt processor
MOV SP, FP
POP FP
HLT

