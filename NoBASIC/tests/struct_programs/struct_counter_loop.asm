; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; Struct Counter declared with fields: count, total
XOR R1, R1
; Allocate struct c (Counter) at 0x0120
; Store to c.count
MOV P0, 288
MOV [P0], R1
XOR R1, R1
; Store to c.total
MOV P0, 290
MOV [P0], R1
MOV R1, 1
MOV P2, R1
MOV R1, 5
MOV R0, R1
L1:
CMP P2, R0
JGT L2
; Load c.count
MOV P0, 288
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to c.count
MOV P0, 288
MOV [P0], R1
; Load c.total
MOV P0, 290
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R1, R2
ADD R1, P2
; Store to c.total
MOV P0, 290
MOV [P0], R1
INC P2
JMP L1
L2:
; Load c.total
MOV P0, 290
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
; Load c.count
MOV P0, 288
MOV P1, [P0]
MOV R1, R2
SUB R1, P1
MOV P2, R1
MOV P1, 10272
; Load c.count
MOV P0, 288
MOV P1, [P0]
; MEMWRITE - Write to memory
MOV [P1], P1
MOV R0, P1
; Free P1 (last use)
MOV P1, 10274
; Load c.total
MOV P0, 290
MOV P1, [P0]
; MEMWRITE - Write to memory
MOV [P1], P1
MOV R0, P1
; Free P1 (last use)
MOV P1, 10276
; MEMWRITE - Write to memory
MOV [P1], P2
MOV R0, P2
; Free P1 (last use)
HLT