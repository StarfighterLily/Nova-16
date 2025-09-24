ORG 0x1000
MOV VM, 0    ; Coordinate mode
MOV VL, 0    ; Layer 0
MOV VX, 50   ; Center X = 50
MOV VY, 50   ; Center Y = 50
MOV VC, 0x1F ; Color = 31
SCIRC 10, 1  ; Draw filled circle with radius 10
HLT
