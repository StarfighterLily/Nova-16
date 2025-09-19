START EQU 0x0000
STAR_COUNT EQU 20     ; Number of stars per layer

ORG 0x1000

SETUP:
    STI
    MOV VM, 1        ; Set to memory mode
    MOV VX, 0x00     ; Set VX to 0
    MOV VY, 0x00     ; Set VY to 0
    MOV P0, START    ; P0 = star counter (0x0000)
    MOV P1, STAR_COUNT ; P1 = number of stars to generate
    MOV R0, 0        ; R0 = color counter
    MOV TT, 0        ; Set timer to 0
    MOV TM, 255      ; Trigger at 10
    MOV TS, 32       ; Set speed
    MOV TC, 3        ; Enable timer and interrupt

LOOP:
    ; Star layer 1
    MOV VL, 1        ; Set layer 1
    RNDR R0, 0x01, 0x06    ; Randomize color 0x01-0x06 (dim stars)
    RND P2           ; Randomize location
    MOV VX, P2:      ; VX = high byte of P2
    MOV VY, :P2      ; VY = low byte of P2
    SWRITE R0        ; Write R0 to screen at VX,VY
    ADD P0, 1        ; Increment star counter
    CMP P0, 256       ; Compare P0 with P1 
    JLT LOOP         ; Loop until counter finishes

MIDPOINT:
    MOV P0, START    ; Reset counter

LOOP2:
    ; Star layer 2
    MOV VL, 2        ; Set layer 2
    RND P2           ; Randomize location
    MOV VX, P2:      ; VX = high byte of P2
    MOV VY, :P2      ; VY = low byte of P2
    RNDR R0, 0x07, 0x0A    ; Randomize color 0x06-0x0A (bright and dim stars)
    SWRITE R0        ; Write R0 to screen at VX,VY
    ADD P0, 1        ; Increment star counter
    CMP P0, 192       ; Compare
    JLT LOOP2        ; Loop until counter finishes

MID2:
    MOV P0, START

LOOP3:
    ; Star layer 3
    MOV VL, 3        ; Set layer 2
    RND P2           ; Randomize location
    MOV VX, P2:      ; VX = high byte of P2
    MOV VY, :P2      ; VY = low byte of P2
    RNDR R0, 0x0B, 0x0F    ; Randomize color 0x0B-0x0F (bright stars)
    SWRITE R0        ; Write R0 to screen at VX,VY
    ADD P0, 1        ; Increment star counter
    CMP P0, 96       ; Compare
    JLT LOOP3        ; Loop until counter finishes

TEXT:
    ; Text layer
    MOV VL, 5        ; Set layer 5
    MOV VM, 0        ; Set coordinate mode
    MOV VX, 101      ; Position shadow text X
    MOV VY, 123      ; Position shadow text Y
    MOV R0, 0x15     ; Set color to dark red
    TEXT TXT, R0     ; Print shadow text
    MOV VX, 100      ; Center main text X
    MOV VY, 124      ; Center main text Y
    MOV R0, 0x1F     ; Set color to bright red
    TEXT TXT, R0     ; Print main text

LOOP4:
    ; Main loop
    JMP LOOP4        ; Repeat forever

TXT: DEFSTR "StarField"

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
    DW BGROLL