ORG 0x0200
MOV SP, 0xFFFF
MOV FP, SP
MOV P1, 8192
MOV P2, P1
MOV R2, 42
; MEMWRITE - Write to memory
MOV [P2], R2
MOV R0, R2
; Free R2 (last use)
MOV P3, R0
; MEMREAD - Read from memory
MOV R2, [P2]
MOV P2, R2
MOV P0, 8194
MOV P2, P0
MOV R6, 100
; MEMWRITE - Write to memory
MOV [P2], R6
MOV R4, R6
; Free R6 (last use)
MOV P3, R4
; MEMREAD - Read from memory
MOV R6, [P2]
MOV P2, R6
MOV P4, 12288
MOV R9, 123
; MEMWRITE - Write to memory
MOV [P4], R9
MOV R8, R9
; Free P4 (last use)
; Free R9 (last use)
MOV P2, R8
MOV P4, 8192
; MEMREAD - Read from memory
MOV R9, [P4]
; Free P4 (last use)
MOV P2, R9
MOV VX, 0
MOV VY, 0
MOV VC, 15
TEXT STR0
HLT
STR0: DEFSTR "All tests complete"