; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; Struct Point declared with fields: x, y
; Allocate struct p (Point) at 0x0120
; Load p.x
MOV P0, 288
MOV P1, [P0]
MOV P2, P1
MOV R1, 9
; Store to p.x
MOV P0, 288
MOV [P0], R1
; Load p.x
MOV P0, 288
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 2
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to p.y
MOV P0, 290
MOV [P0], R1
; Load p.x
MOV P0, 288
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, P1
; Load p.y
MOV P0, 290
MOV P1, [P0]
MOV R0, R3
ADD R0, P1
; Preserve left operand in register across right-side evaluation
MOV R3, R0
MOV R1, R3
ADD R1, P2
MOV P4, R1
MOV P1, 10240
; MEMWRITE - Write to memory
MOV [P1], P2
MOV R0, P2
; Free P1 (last use)
MOV P1, 10242
; Load p.x
MOV P0, 288
MOV P1, [P0]
; MEMWRITE - Write to memory
MOV [P1], P1
MOV R0, P1
; Free P1 (last use)
MOV P1, 10244
; Load p.y
MOV P0, 290
MOV P1, [P0]
; MEMWRITE - Write to memory
MOV [P1], P1
MOV R0, P1
; Free P1 (last use)
MOV P1, 10246
; MEMWRITE - Write to memory
MOV [P1], P4
MOV R0, P4
; Free P1 (last use)
HLT