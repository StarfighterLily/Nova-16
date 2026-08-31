; WARNING: 5 variable(s) using dedicated spill slots
;          Spilled variables: F, A, G, H, I
;          Spill region: 0x7000-0x700A
;          Register pressure: 5 (max), 5 available
;          This will impact performance. Consider:
;          - Reducing total variable count (currently 10)
;          - Reducing variable lifetimes by localizing scope
;          - Breaking complex expressions into simpler parts
; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P0, 0
MOV P1, 128
MOV P7:, 0xFF
MOV R1, 100
MOV :P7, 0xFF
MOV :P0, R1
MOV SP, P7
MOV FP, SP
MOV [P1], P0
MOV R1, 200
MOV P0, 300
MOV P1, 28674
MOV P2, P0
MOV P6, R1
MOV P0, 400
MOV P3, P0
MOV P0, 500
MOV P4, P0
MOV P0, 600
MOV [P1], P0
MOV P1, 28676
MOV P0, 700
MOV [P1], P0
MOV P1, 28678
MOV P0, 800
MOV [P1], P0
MOV P1, 28680
MOV P0, 900
MOV [P1], P0
MOV P0, 1000
MOV P5, P0
MOV P0, 128
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R1, R2
ADD R1, P6
ITOS P1, R1
MOV VC, 15
MOV VX, 0
TEXT P1
ADD VY, 8
; Preserve left operand in register across right-side evaluation
MOV R2, P2
MOV R1, R2
ADD R1, P3
ITOS P1, R1
MOV VC, 15
MOV VX, 0
TEXT P1
ADD VY, 8
; Preserve left operand in register across right-side evaluation
MOV P0, 28674
MOV R2, P4
MOV P0, [P0]
MOV R1, R2
ADD R1, P0
; Free P0 (last use)
ITOS P1, R1
MOV VC, 15
MOV VX, 0
TEXT P1
ADD VY, 8
MOV P0, 28676
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV P0, 28678
MOV P0, [P0]
MOV R1, R2
ADD R1, P0
; Free P0 (last use)
ITOS P1, R1
MOV VC, 15
MOV VX, 0
TEXT P1
ADD VY, 8
MOV P0, 28680
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R1, R2
ADD R1, P5
ITOS P1, R1
MOV VC, 15
MOV VX, 0
TEXT P1
ADD VY, 8
MOV P0, 128
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R5, P0
MOV R3, R5
ADD R3, P6
; Preserve left operand in register across right-side evaluation
MOV R2, R3
ADD R2, P2
; Preserve left operand in register across right-side evaluation
MOV R0, R2
ADD R0, P3
; Preserve left operand in register across right-side evaluation
MOV R1, R0
ADD R1, P4
ITOS P1, R1
MOV VC, 15
MOV VX, 0
TEXT P1
ADD VY, 8
MOV P0, 128
MOV P0, [P0]
MOV R0, P0
SHL R0, 1
; Free P0 (last use)
; Preserve left operand in register across right-side evaluation
MOV R4, P6
MOV R3, R0
SHL R4, 1
MOV R1, R3
ADD R1, R4
; Free R4 (last use)
ITOS P1, R1
MOV VC, 15
MOV VX, 0
TEXT P1
ADD VY, 8
; Preserve left operand in register across right-side evaluation
MOV R3, P2
MOV R0, R3
ADD R0, P3
; Preserve left operand in register across right-side evaluation
MOV R3, R0
; Preserve left operand in register across right-side evaluation
MOV P0, 28674
MOV R7, P4
MOV P0, [P0]
MOV R5, R7
ADD R5, P0
; Free P0 (last use)
MUL R1, R5
MOV R1, R3
; Free R5 (last use)
ITOS P1, R1
MOV VC, 15
MOV VX, 0
TEXT P1
ADD VY, 8
HLT