; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
MOV R1, 42
MOV P2, R1
MOV P1, 8192
; MEMREAD - Read from memory
MOV R1, [P1]
; Free P1 (last use)
MOV P2, R1
HLT