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
MOV P3, R1
MOV P1, 8194
MOV P3, P0
MOV R2, 100
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P1, 8194
MOV P4, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P0, 8196
MOV P1, 8196
MOV P3, P0
MOV P4, R1
MOV R2, 255
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P1, 8196
MOV P4, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P4, R1
MOV R2, 77
MOV P0, 12288
MOV R1, 10
MOV P1, 12298
MOV P3, P0
MOV P0, 12298
MOV P4, R1
MOV P5, P0
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P1, 12298
MOV P3, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P3, R1
MOV P1, 8192
MOV P3, 16384
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P1, 16384
MOV P4, R1
; MEMWRITE - Write to memory
MOV [P1], P4
MOV R1, P4
; Free P1 (last use)
MOV P1, 16384
MOV P2, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV R2, 123
MOV P2, R1
MOV P1, 20480
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P0, 24576
MOV P2, R1
MOV P1, 24576
MOV P2, P0
MOV R2, 1
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P1, 24578
MOV R2, 1
SHL R2, 1
MOV P3, R1
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV R2, 3
MOV P3, R1
MOV P1, 24580
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P1, 24582
MOV R2, 1
SHL R2, 2
MOV P3, R1
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P1, 24576
MOV P3, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P1, 24578
MOV P3, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P1, 24580
MOV P3, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P1, 24582
MOV P3, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P1, 61440
MOV P0, 61440
MOV P3, R1
MOV P2, P0
MOV P0, 12288
; MEMWRITE - Write to memory
MOV [P1], P0
MOV R1, P0
; Free P1 (last use)
; Free P0 (last use)
MOV P1, 61440
MOV P3, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P3, R1
MOV P1, 80
MOV R1, 80
MOV R2, 99
MOV P2, R1
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P1, 80
MOV P3, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV VC, 15
MOV P3, R1
MOV VX, 0
TEXT STR0
ADD VY, 8
HLT
STR0: DEFSTR "All tests complete"