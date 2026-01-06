; Nova-16 Word Processor Demo
; Features: text entry, cursor, arrow key movement (no save/load)
; By Pixel, 2025



	ORG 0x0000         ; Zero page (data only)
        JMP 0x0200         ; Ensure execution jumps to code
CUR_X:  DB 0               ; Cursor X (col)
CUR_Y:  DB 0               ; Cursor Y (row)

        ORG 0x0200         ; Program entry point (code)

; --- Constants ---
BUF_START   EQU 0x2000     ; Text buffer base address
COLS        EQU 40         ; Columns per line
ROWS        EQU 16         ; Number of lines
BUF_SIZE    EQU COLS*ROWS  ; Total buffer size
CURSOR_CHAR EQU 0xDB       ; Block char for cursor (ASCII 219)

; --- Registers ---
; R0: temp, R1: key, R2: char, R3: col, R4: row
; P0: buffer ptr, P1: screen ptr
; VX/VY: graphics coords

; --- Zero page vars ---
        ORG 0x0000
CUR_X:  DB 0               ; Cursor X (col)
CUR_Y:  DB 0               ; Cursor Y (row)

        ORG 0x0200         ; Back to code

START:
        ; Clear buffer
        MOV P0, BUF_START
        MOV R0, 0
CLEAR_BUF:
        MOV [P0], R0
        ADD P0, 1
        CMP P0, BUF_START+BUF_SIZE
        JLT CLEAR_BUF

        ; Init cursor
        MOV CUR_X, 0
        MOV CUR_Y, 0

MAIN_LOOP:
        ; Draw screen
        CALL DRAW_SCREEN

        ; Wait for key
WAIT_KEY:
        KEYSTAT R1
        CMP R1, 0
        JZ WAIT_KEY
        KEYIN R1

        ; Handle arrow keys (assume: 0x1B ESC, then code)
        CMP R1, 0x1B
        JNZ CHECK_BACKSPACE
        ; Arrow key sequence
        KEYIN R1
        CMP R1, 'A'         ; Up
        JNZ NOT_UP
        CALL CUR_UP
        JMP MAIN_LOOP
NOT_UP:
        CMP R1, 'B'         ; Down
        JNZ NOT_DOWN
        CALL CUR_DOWN
        JMP MAIN_LOOP
NOT_DOWN:
        CMP R1, 'C'         ; Right
        JNZ NOT_RIGHT
        CALL CUR_RIGHT
        JMP MAIN_LOOP
NOT_RIGHT:
        CMP R1, 'D'         ; Left
        JNZ MAIN_LOOP
        CALL CUR_LEFT
        JMP MAIN_LOOP

; --- Backspace key (ASCII 8) ---
CHECK_BACKSPACE:
        CMP R1, 8
        JNZ CHECK_PRINTABLE
        CALL DO_BACKSPACE
        JMP MAIN_LOOP

CHECK_PRINTABLE:
        ; Printable ASCII 32-126
        CMP R1, 32
        JLT MAIN_LOOP
        CMP R1, 126
        JGT MAIN_LOOP
        ; Insert char
        CALL INSERT_CHAR
        CALL CUR_RIGHT
        JMP MAIN_LOOP

; --- Cursor movement routines ---
CUR_LEFT:
        MOV R0, CUR_X
        CMP R0, 0
        JZ CUR_LEFT_END
        SUB R0, 1
        MOV CUR_X, R0
CUR_LEFT_END:
        RET

CUR_RIGHT:
        MOV R0, CUR_X
        CMP R0, COLS-1
        JGE CUR_RIGHT_END
        ADD R0, 1
        MOV CUR_X, R0
CUR_RIGHT_END:
        RET

CUR_UP:
        MOV R0, CUR_Y
        CMP R0, 0
        JZ CUR_UP_END
        SUB R0, 1
        MOV CUR_Y, R0
CUR_UP_END:
        RET

CUR_DOWN:
        MOV R0, CUR_Y
        CMP R0, ROWS-1
        JGE CUR_DOWN_END
        ADD R0, 1
        MOV CUR_Y, R0
CUR_DOWN_END:
	RET

; --- Backspace routine ---
DO_BACKSPACE:
        ; If at (0,0), nothing to do
        MOV R0, CUR_X
        CMP R0, 0
        JNZ DB_NOT_FIRST_COL
        MOV R0, CUR_Y
        CMP R0, 0
        JZ DB_DONE
        ; Move to end of previous line
        SUB R0, 1
        MOV CUR_Y, R0
        MOV R0, COLS-1
        MOV CUR_X, R0
        JMP DB_ERASE
DB_NOT_FIRST_COL:
        SUB R0, 1
        MOV CUR_X, R0
DB_ERASE:
        ; Compute buffer offset: Y*COLS+X
        MOV R0, CUR_Y
        MUL R0, COLS
        MOV R2, CUR_X
        ADD R0, R2
        MOV P0, BUF_START
        ADD P0, R0
        MOV R1, 0
        MOV [P0], R1
DB_DONE:
        RET

; --- Insert char at cursor ---
INSERT_CHAR:
        ; Compute buffer offset: Y*COLS+X
        MOV R0, CUR_Y
        MUL R0, COLS
        MOV R2, CUR_X
        ADD R0, R2
        MOV P0, BUF_START
        ADD P0, R0
        MOV [P0], R1        ; R1 = char (typed key)
        RET

; --- Draw screen ---
DRAW_SCREEN:
        MOV R3, 0           ; row
DRAW_ROW:
        CMP R3, ROWS
        JGE DRAW_DONE
        MOV R4, 0           ; col
DRAW_COL:
        CMP R4, COLS
        JGE NEXT_ROW
        ; Compute buffer offset
        MOV R0, R3
        MUL R0, COLS
        ADD R0, R4
        MOV P0, BUF_START
        ADD P0, R0
        MOV R2, [P0]
        ; Set coords
        MOV VM, 0
        MOV VX, R4
        MOV VY, R3
        ; Draw char or cursor
        MOV R0, CUR_X
        MOV R1, CUR_Y
        CMP R4, R0
        JNZ NOT_CURSOR
        CMP R3, R1
        JNZ NOT_CURSOR
        MOV R2, CURSOR_CHAR
NOT_CURSOR:
        SWRITE R2
        ADD R4, 1
        JMP DRAW_COL
NEXT_ROW:
        ADD R3, 1
        JMP DRAW_ROW
DRAW_DONE:
        RET

        ; --- End ---
        JMP MAIN_LOOP
