; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV R1, 42
MOV P7:, 0xFF
MOV P1, 8192
MOV P0, 8192
MOV R2, 42
MOV P3, R1
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
MOV P4, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV R2, 255
MOV P3, R1
MOV P0, 8208
MOV P1, 8208
MOV R1, 255
MOV P2, P0
MOV P3, R1
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P1, 8208
MOV P4, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P0, 8224
MOV P3, R1
XOR R1, R1
XOR R2, R2
MOV P3, R1
MOV P2, P0
MOV P1, 8224
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P1, 8224
MOV P4, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P1, 20480
MOV P3, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P0, 8240
MOV P2, R1
MOV P1, 8240
MOV P2, P0
MOV R2, 100
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P1, 8240
MOV P3, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV R2, 200
MOV P3, R1
MOV P1, 8240
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P1, 8240
MOV P3, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P0, 12288
MOV P1, 12288
MOV P2, P0
MOV P3, R1
MOV R2, 10
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV R2, 20
MOV P3, R1
MOV P1, 12290
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV R2, 30
MOV P3, R1
MOV P1, 12292
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P1, 12288
MOV P3, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P1, 12290
MOV P3, R1
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P1, 12292
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
STR0: DEFSTR "Tests complete"