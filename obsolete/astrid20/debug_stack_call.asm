; Astrid 2.0 Generated Assembly
ORG 0x1000
STI

; Initialize stack pointer
MOV P8, 0xFFFF
MOV P0, 0x0000
PUSH P0
CALL main
HLT

; Function simple_func
simple_func:
PUSH FP
MOV FP, SP
entry:
MOV SP, FP
POP FP
RET

; Function main
main:
PUSH FP
MOV FP, SP
entry:
; Call user function: simple_func
CALL simple_func
; Halt processor
MOV SP, FP
POP FP
HLT

