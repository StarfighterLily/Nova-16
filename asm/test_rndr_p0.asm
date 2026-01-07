; Test P0 memory addressing with RNDR
ORG 0x0200

; Put some test values in memory near the top of the stack
MOV SP, 0xFFFF
MOV FP, SP
MOV P7:, 0xFF
MOV :P7, 0xFF

; Store colormin (1) and colormax (15) in stack memory
MOV SP, 0xFFF8
MOV P0, SP
MOV R0, 1
MOV [P0], R0  ; colormax at 0xFFF8
ADD P0, 2
MOV R0, 15
MOV [P0], R0  ; colormin at 0xFFFA

; Now try to load and use with RNDR
MOV P0, 0xFFF8
MOV R6, [P0]  ; Load colormax
ADD P0, 2
MOV R8, [P0]  ; Load colormin (15)
MOV R6, 1     ; colormin
MOV R8, 15    ; colormax

; Draw pixels with RNDR
MOV VX, 100
MOV VY, 100
RNDR R0, R6, R8
MOV VC, R0
SWRITE VC

MOV VX, 110
MOV VY, 100
RNDR R0, 1, 15
MOV VC, R0
SWRITE VC

HLT
