; Test to verify RNDR mode byte encoding with registers
ORG 0x0200

MOV R0, 5      ; Clear R0
MOV R6, 1      ; colormin = 1
MOV R8, 15     ; colormax = 15

; Test RNDR with all three operands as registers
RNDR R0, R6, R8

; Set pixel
MOV VX, 100
MOV VY, 100
MOV VC, R0
SWRITE VC

HLT
