; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF

; Function main
main:
entry:
; Set active layer to 1
MOV VL, 1
; Set pixel at (100, 100) to color 15
MOV VM, 0
MOV VX, 100
MOV VY, 100
MOV R8, 15
SWRITE R8
; Halt processor
HLT

