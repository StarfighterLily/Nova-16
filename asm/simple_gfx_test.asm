; Simple graphics test without interrupts
ORG 0x1000

MAIN:
    MOV VM, 1        ; Set to memory mode (linear addressing)
    MOV VL, 1        ; Switch to Layer 1
    MOV P0, 0x0000   ; Start address
    MOV P1, 0x0100   ; End address (draw 256 pixels)
    MOV R0, 1        ; Color

LOOP:
    MOV VX, P0:      ; VX = high byte of P0
    MOV VY, :P0      ; VY = low byte of P0
    SWRITE R0        ; Write R0 to screen at VX,VY
    INC P0           ; Increment P0
    INC R0           ; Increment R0 (color)
    CMP P0, P1       ; Compare P0 with P1 
    JNZ LOOP         ; If not equal, loop back

    HLT              ; Halt when done
