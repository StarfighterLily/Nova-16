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
; Call user function: draw_pixel_at
MOV R8, 15
PUSH R8
MOV R8, 50
PUSH R8
MOV R8, 100
PUSH R8
CALL draw_pixel_at
ADD SP, 6         ; Clean up 3 parameters
MOV P0, R0
; Halt processor
MOV SP, FP
POP FP
HLT

; Function draw_pixel_at
draw_pixel_at:
PUSH FP
MOV FP, SP
entry:
; Set active layer to 1
MOV VL, 1
MOV P7, P9
ADD P7, 4
MOV P6, [P7]
MOV P1, P9
ADD P1, 6
MOV P7, [P1]
MOV P0, P9
ADD P0, 8
MOV P1, [P0]
; Set pixel at (P6, P7) to color P1
MOV VM, 0
MOV VX, P6
MOV VY, P7
MOV R8, P1
SWRITE R8
MOV SP, FP
POP FP
RET

