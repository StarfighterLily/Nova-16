; Test RNDR with memory-loaded R registers
ORG 0x0200

; Set up "stack" with parameters
MOV SP, 0xFFFF
MOV FP, SP
SUB SP, 8
MOV P0, FP
SUB P0, 2
MOV [P0], 1       ; colormin at FP-2
MOV P0, FP  
SUB P0, 4
MOV [P0], 15      ; colormax at FP-4

; Now load and use like NoBASIC does
MOV P0, FP
SUB P0, 2
MOV R2, [P0]      ; Load colormin
MOV P0, FP
SUB P0, 4
MOV R4, [P0]      ; Load colormax

RNDR R0, R2, R4
MOV VX, 100
MOV VY, 100
MOV VC, R0
SWRITE VC

HLT
