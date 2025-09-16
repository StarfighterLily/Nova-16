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
; Call user function: set_layer_num
MOV R1, 1
CALL set_layer_num
; Halt processor
MOV SP, FP
POP FP
HLT

; Function set_layer_num
set_layer_num:
PUSH FP
MOV FP, SP
entry:
; Set active layer to R2
MOV VL, R2
MOV SP, FP
POP FP
RET

