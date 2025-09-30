START EQU 0x0000
FINISH EQU 0xFFFF

ORG 0x1000

SETUP:
    STI
    MOV VM, 1        ; Set to memory mode (linear addressing)
    MOV VX, 0x00     ; Set VX to 0
    MOV VY, 0x00     ; Set VY to 0
    MOV P0, START    ; P0 = start address (0x0000)
    MOV P1, FINISH   ; P1 = end address (0xFFFF)
    MOV VC, 0        ; Set color register to 0
    MOV TT, 0        ; Set timer to 0
    MOV TM, 255      ; Trigger at 255 (max count)
    MOV TS, 32       ; Set speed to 32
    MOV TC, 3        ; Enable timer and interrupt
    MOV VL, 1        ; Switch to Layer 1

LOOP:
    MOV VX, P0:      ; VX = high byte of P0
    MOV VY, :P0      ; VY = low byte of P0
    SWRITE VC        ; Write R0 to screen at VX,VY
    INC VC           ; Increment color
    INC P0           ; Increment P0
    CMP P0, P1       ; Compare P0 with P1 
    JNZ LOOP         ; If not equal, loop back
    INC VY           ; Inc once more
    SWRITE R0        ; Fill in the last pixel
    MOV VM, 0        ; Set to coordinate mode
    MOV VX, 108      ; Set X to mid point
    MOV VY, 118      ; Set Y to mid point
    MOV R0, 0x5F     ; Set R0 to color 0x5F
    MOV VC, R0       ; Set VC to the color
    MOV VL, 5        ; Switch to Layer 5
    TEXT TXT         ; Print the text at TXT (uses VC for color)
    MOV VL, 1        ; Switch back to Layer 1

LOOP2:
    JMP LOOP2        ; Repeat

TXT:
    DEFSTR "De Nova Stella"

TIMER_HANDLER:       ; Timer interrupt handler
    SROL 0, -1        ; Roll screen -1 pixel
    IRET             ; Return from interrupt

ORG 0x0100          ; Timer interrupt vector  
    DW TIMER_HANDLER ; Address of timer interrupt handler