; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
MOV P0, 8192
MOV P2, P0
MOV P1, P2
MOV R2, 42
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P3, R1
MOV P1, P2
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P3, R1
MOV P0, 8194
MOV P3, P0
MOV P1, P3
MOV R2, 100
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P4, R1
MOV P1, P3
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P4, R1
MOV P0, 8196
MOV P3, P0
MOV P1, P3
MOV R2, 255
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P4, R1
MOV P1, P3
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P4, R1
MOV P0, 12288
MOV P3, P0
MOV R1, 10
MOV P4, R1
; Preserve left operand in register across right-side evaluation
MOV R2, P3
MOV R1, R2
ADD R1, P4
MOV P5, R1
MOV P1, P5
MOV R2, 77
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P3, R1
MOV P1, P5
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P3, R1
MOV P0, 16384
MOV P3, P0
MOV P1, P2
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P4, R1
MOV P1, P3
; MEMWRITE - Write to memory
MOV [P1], P4
MOV R1, P4
; Free P1 (last use)
MOV P2, R1
MOV P1, P3
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P2, R1
MOV P1, 20480
MOV R2, 123
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P2, R1
MOV P0, 24576
MOV P2, P0
MOV P1, P2
MOV R2, 1
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P3, R1
; Preserve left operand in register across right-side evaluation
MOV R2, P2
MOV R3, 1
SHL R3, 1
MOV P1, R2
ADD P1, R3
; Free R3 (last use)
MOV R2, 1
SHL R2, 1
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P3, R1
; Preserve left operand in register across right-side evaluation
MOV R2, P2
MOV R3, 1
SHL R3, 2
MOV P1, R2
ADD P1, R3
; Free R3 (last use)
MOV R2, 3
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P3, R1
; Preserve left operand in register across right-side evaluation
MOV R2, P2
MOV R3, 6
MOV P1, R2
ADD P1, R3
; Free R3 (last use)
MOV R2, 1
SHL R2, 2
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P3, R1
MOV P1, P2
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P3, R1
; Preserve left operand in register across right-side evaluation
MOV R2, P2
MOV R3, 1
SHL R3, 1
MOV P1, R2
ADD P1, R3
; Free R3 (last use)
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P3, R1
; Preserve left operand in register across right-side evaluation
MOV R2, P2
MOV R3, 1
SHL R3, 2
MOV P1, R2
ADD P1, R3
; Free R3 (last use)
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P3, R1
; Preserve left operand in register across right-side evaluation
MOV R2, P2
MOV R3, 6
MOV P1, R2
ADD P1, R3
; Free R3 (last use)
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P3, R1
MOV P0, 61440
MOV P2, P0
MOV P1, P2
MOV P0, 12288
; MEMWRITE - Write to memory
MOV [P1], P0
MOV R1, P0
; Free P1 (last use)
; Free P0 (last use)
MOV P3, R1
MOV P1, P2
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P3, R1
MOV R1, 80
MOV P2, R1
MOV P1, P2
MOV R2, 99
; MEMWRITE - Write to memory
MOV [P1], R2
MOV R1, R2
; Free P1 (last use)
; Free R2 (last use)
MOV P3, R1
MOV P1, P2
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P3, R1
MOV VX, 0
MOV VC, 15
TEXT STR0
ADD VY, 8
HLT
STR0: DEFSTR "All tests complete"