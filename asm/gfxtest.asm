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
    MOV R0, 0        ; R0 = color counter
    MOV TT, 0        ; Set timer to 0
    MOV TM, 50       ; Trigger at 50 (slower)
    MOV TS, 4        ; Set speed to 4 (slower)
    MOV TC, 3        ; Enable timer and interrupt
    MOV VL, 1        ; Switch to Layer 1

LOOP:
    MOV VX, P0:      ; VX = high byte of P0
    MOV VY, :P0      ; VY = low byte of P0
    SWRITE R0        ; Write R0 to screen at VX,VY
    INC P0           ; Increment P0
    INC R0           ; Increment R0 (color)
    CMP P0, P1       ; Compare P0 with P1 
    JNZ LOOP         ; If not equal, loop back
    MOV VM, 0        ; Set to coordinate mode
    MOV VX, 108      ; Set X to mid point
    MOV VY, 118      ; Set Y to mid point
    MOV R0, 0x5F     ; Set R0 to color 0x5F
    MOV VL, 5        ; Switch to Layer 5
    TEXT TXT, R0     ; Print the text at TXT
    MOV VL, 1        ; Switch back to Layer 1

LOOP2:
    JMP LOOP2        ; Repeat

TXT: DEFSTR "De Nova Stella"

TIMER_HANDLER:       ; Timer interrupt handler
    SROLX 1          ; Roll screen 1 pixel
    IRET             ; Return from interrupt

ORG 0x0100          ; Timer interrupt vector  
    DW TIMER_HANDLER ; Address of timer interrupt handler