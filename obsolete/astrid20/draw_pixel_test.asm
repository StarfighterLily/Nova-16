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
; Call user function: draw_single_pixel
MOV R1, 100
MOV R2, 50
MOV R3, 15
CALL draw_single_pixel
; Halt processor
MOV SP, FP
POP FP
HLT

; Function draw_single_pixel
draw_single_pixel:
PUSH FP
MOV FP, SP
entry:
; Set active layer to 1
MOV VL, 1
; Set pixel at (R2, R3) to color R4
MOV VM, 0
MOV VX, R2
MOV VY, R3
MOV R8, R4
SWRITE R8
MOV SP, FP
POP FP
RET

