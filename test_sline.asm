ORG 0x1000
MOV VM, 0    ; Coordinate mode
MOV VL, 0    ; Layer 0
MOV VX, 10   ; Start X = 10
MOV VY, 10   ; Start Y = 10
MOV VC, 0x1F ; Color = 31
SLINE 20, 20 ; Draw line to (20, 20)
HLT
