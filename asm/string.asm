ORG 0x1000

START:
    MOV VC, 0x1F    ; Use VC to hold the 8-bit color, 0x1F (bright red)
    MOV VX, 0       ; X coordinate set to 0
    MOV VY, 0       ; Y coordinate set to 0
    MOV VM, 0       ; Video mode set to 0 (coordinate system instead of linear addressing)

MAIN:
    TEXT STR    ; Print string at STR label with color in R0, at position set in VX, VY
    HLT

STR: 
    DEFSTR "A simple string."