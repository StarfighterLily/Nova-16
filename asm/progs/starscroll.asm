START EQU 0x0000
FINISH EQU 0xFFFF

ORG 0x1000

SETUP:
    STI
    MOV VM, 1        ; Set to memory mode
    MOV VX, 0x00     ; Set VX to 0
    MOV VY, 0x00     ; Set VY to 0
    MOV P0, START    ; P0 = start address (0x0000)
    MOV P1, FINISH   ; P1 = end address (0xFFFF)
    MOV R0, 0        ; R0 = color counter
    MOV TT, 0        ; Set timer to 0
    MOV TM, 128      ; Trigger at 128
    MOV TS, 80       ; Set speed
    MOV TC, 3        ; Enable timer and interrupt

LOOP:
    ; Star layer 1
    MOV VL, 1        ; Set layer 1
    RND P2           ; Randomize location
    MOV VX, P2:      ; VX = high byte of P2
    MOV VY, :P2      ; VY = low byte of P2
    SWRITE R0        ; Write R0 to screen at VX,VY
    ADD P0, 32       ; Add 32 to the counter (many stars)
    RNDR R0, 0x00, 0x06    ; Randomize color 0x00-0x06 (dim stars)
    CMP P0, P1       ; Compare P0 with P1 
    JGE LOOP         ; Loop until counter finishes

MIDPOINT:
    MOV P0, START    ; Reset counter

LOOP2:
    ; Star layer 2
    MOV VL, 2        ; Set layer 2
    RND P2           ; Randomize location
    MOV VX, P2:      ; VX = high byte of P2
    MOV VY, :P2      ; VY = low byte of P2
    RNDR R0, 0x07, 0x0A    ; Randomize color 0x00-0x0A (bright and dim stars)
    SWRITE R0        ; Write R0 to screen at VX,VY
    ADD P0, 128       ; Add 128 to the counter (fewer stars)
    CMP P0, P1       ; Compare
    JGE LOOP2        ; Loop until counter finishes

MID2:
    MOV P0, START

LOOP3:
    ; Star layer 3
    MOV VL, 3        ; Set layer 3
    RND P2           ; Randomize location
    MOV VX, P2:      ; VX = high byte of P2
    MOV VY, :P2      ; VY = low byte of P2
    RNDR R0, 0x0B, 0x0F    ; Randomize color 0x00-0x0A (bright stars)
    SWRITE R0        ; Write R0 to screen at VX,VY
    ADD P0, 256       ; Add 256 to the counter (fewer stars)
    CMP P0, P1       ; Compare
    JGE LOOP3        ; Loop until counter finishes

LOOP4:
    ; Main loop
    JMP LOOP4        ; Repeat forever

BGROLL:
    ; Layer roll subroutine
    MOV VL, 1
    SROL 0, 1
    MOV VL, 2
    SROL 0, 2
    MOV VL, 3
    SROL 0, 3
    IRET

ORG 0x0100
    ; Timer vector
    DW BGROLL