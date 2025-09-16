; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF

; Function main
main:
entry:
; Generate random number (0-65535)
RND P0
MOV P0, P2
; Set active layer to 1
MOV VL, 1
; Set pixel at (100, 100) to color 15
MOV VM, 0
MOV VX, 100
MOV VY, 100
MOV R8, 15
SWRITE R8
; Generate random number between v8 and v9
RNDR P0, 1, 6
MOV P1, P3
; Set pixel at (50, 50) to color 10
MOV VM, 0
MOV VX, 50
MOV VY, 50
MOV R8, 10
SWRITE R8
; Halt processor
HLT

