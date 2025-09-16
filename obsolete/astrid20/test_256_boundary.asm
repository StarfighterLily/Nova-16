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
; Generate random number between 254 and 256 (16-bit)
RNDR P0, 254, 256
MOV P0, P1
; Set pixel at (0, 0) to color 1
MOV VM, 0
MOV VX, 0
MOV VY, 0
MOV R8, 1
SWRITE R8
; Halt processor
MOV SP, FP
POP FP
HLT

