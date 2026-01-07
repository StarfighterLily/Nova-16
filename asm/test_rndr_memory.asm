; Test RNDR with memory-loaded values vs immediate
ORG 0x0200

; Store test values in memory
MOV P0, 0x0300
MOV R0, 1
MOV [P0], R0
MOV P0, 0x0302  
MOV R0, 15
MOV [P0], R0

; Test 1: RNDR with immediate-loaded registers (should work)
MOV R6, 1
MOV R8, 15
MOV VX, 50
MOV VY, 50
RNDR R0, R6, R8
MOV VC, R0
SWRITE VC

; Test 2: RNDR with memory-loaded registers
MOV P0, 0x0300
MOV R6, [P0]    ; Load 1 from memory
MOV P0, 0x0302
MOV R8, [P0]    ; Load 15 from memory
MOV VX, 60
MOV VY, 50
RNDR R0, R6, R8
MOV VC, R0
SWRITE VC

HLT
