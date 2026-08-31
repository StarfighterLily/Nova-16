; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P1, 8192
MOV P7:, 0xFF
MOV R2, 42
MOV P0, 8192
MOV :P7, 0xFF
MOV P2, P0
MOV SP, P7
MOV FP, SP
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P1, 8192
MOV P3, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P0, 8194
MOV P1, 8194
MOV P2, P0
MOV P3, R1
MOV R2, 100
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P1, 8194
MOV P3, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV R2, 123
MOV P3, R1
MOV P1, 12288
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P1, 8192
MOV P2, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV VC, 15
MOV P2, R1
MOV VX, 0
TEXT STR0
ADD VY, 8
HLT
STR0: DEFSTR "All tests complete"