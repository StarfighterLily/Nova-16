; Simple test: RNDR with loaded registers vs. direct
ORG 0x0200

MOV SP, 0xFFFF
MOV FP, SP
MOV P7:, 0xFF
MOV :P7, 0xFF

; Test 1: Direct RNDR with literals
MOV VX, 50
MOV VY, 50
RNDR R0, 1, 15
MOV VC, R0
SWRITE VC

; Test 2: Load into registers then RNDR
MOV R6, 1
MOV R8, 15
MOV VX, 60
MOV VY, 50
RNDR R0, R6, R8
MOV VC, R0
SWRITE VC

; Test 3: Load from memory then RNDR
MOV P0, 0xFFF8
MOV R6, [P0]     ; Should have 1
ADD P0, 2
MOV R8, [P0]     ; Should have 15
MOV VX, 70
MOV VY, 50
RNDR R0, R6, R8
MOV VC, R0
SWRITE VC

HLT

; Store test data at end
ORG 0xFFF8
DEFWORD 1
DEFWORD 15
