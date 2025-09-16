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
MOV R2, 2
MOV R3, 0
MOV R3, 2
MOV R3, 4
MOV R3, 8
MOV R3, 7
; Set pixel at (100, 100) to color R3
MOV VM, 0
MOV VX, 100
MOV VY, 100
MOV R8, R3
SWRITE R8
; Halt processor
MOV SP, FP
POP FP
HLT

