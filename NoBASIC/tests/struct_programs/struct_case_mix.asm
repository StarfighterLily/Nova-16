; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; Struct Pixel declared with fields: X, Y, COLOR
MOV R1, 12
; Allocate struct px (Pixel) at 0x0120
; Store to px.x
MOV P0, 288
MOV [P0], R1
MOV R1, 34
; Store to PX.Y
MOV P0, 290
MOV [P0], R1
MOV R1, 56
; Store to pX.color
MOV P0, 292
MOV [P0], R1
; Load px.X
MOV P0, 288
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, P1
; Load PX.y
MOV P0, 290
MOV P1, [P0]
MOV R0, R3
ADD R0, P1
; Preserve left operand in register across right-side evaluation
MOV R3, R0
; Load pX.COLOR
MOV P0, 292
MOV P1, [P0]
MOV R1, R3
ADD R1, P1
MOV P2, R1
; Allocate struct p2 (Pixel) at 0x0126
; Load p2.y
MOV P0, 296
MOV P1, [P0]
MOV P2, P1
MOV R1, 7
; Store to p2.CoLoR
MOV P0, 298
MOV [P0], R1
; Load P2.Y
MOV P0, 296
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
; Load p2.color
MOV P0, 298
MOV P1, [P0]
MOV R1, R2
ADD R1, P1
MOV P2, R1
MOV P1, 10304
; MEMWRITE - Write to memory
MOV [P1], P2
MOV R0, P2
; Free P1 (last use)
MOV P1, 10306
; MEMWRITE - Write to memory
MOV [P1], P2
MOV R0, P2
; Free P1 (last use)
MOV P1, 10308
; MEMWRITE - Write to memory
MOV [P1], P2
MOV R0, P2
; Free P1 (last use)
HLT