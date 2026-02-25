ORG 0x1000

START:
    MOV VC, 0x1F    ; Use VC to hold the 8-bit color, 0x1F (bright red)
    MOV VX, 0       ; X coordinate set to 0
    MOV VY, 0       ; Y coordinate set to 0
    MOV VM, 0       ; Video mode set to 0 (coordinate system instead of linear addressing)

MAIN:
    MOV P0, CHR
    CHAR [P0]
    MOV VX, 9
    CHAR 'B'
    MOV VX, 17
    CHAR 0x43    ; Hex value for 'C'
    HLT

CHR:
    DW 0x41    ; Hex value for 'A'