; NovaDOS — Console I/O
; CLRSCREEN, PUTCHAR, PRINT, PRINTHEX, PRINT_DECIMAL, NEWLINE, GETLINE.
;
; Console geometry: layer 0, 32x32 character grid (8x8 font).
; Cursor state lives in zero page:
;   [0x0024] ZP_VID_CUR  = cursor X (column, 0-31)
;   [0x0025] ZP_VID_CUR2 = cursor Y (row, 0-31)
; Pixel position: VX = col*8, VY = row*8.

; ---------------------------------------------------------------------------
; CLRSCREEN — clear the active layer to black with a single SFILL.
; ---------------------------------------------------------------------------
CLRSCREEN:
    MOV VL, 0
    SFILL 0x00          ; fill entire layer 0 with black (one instruction)
    RET

; ---------------------------------------------------------------------------
; PUTCHAR — display character in R0 at the current cursor, advance cursor.
; Handles newline (0x0A) and carriage return (0x0D). Clobbers R0-R3.
; ---------------------------------------------------------------------------
PUTCHAR:
    CMP R0, 0x0A
    JZ PUTCHAR_NL
    CMP R0, 0x0D
    JZ PUTCHAR_NL
    MOV R1, [0x0024]    ; cursor X
    MOV R2, [0x0025]    ; cursor Y
    MOV R3, R1
    SHL R3, 3           ; VX = col * 8
    MOV VX, R3
    MOV R3, R2
    SHL R3, 3           ; VY = row * 8
    MOV VY, R3
    CHAR R0
    INC R1
    CMP R1, CONS_COLS   ; reached end of row?
    JNZ PUTCHAR_STORE
    MOV R1, 0
    INC R2
    CMP R2, CONS_ROWS   ; reached bottom?
    JNZ PUTCHAR_STORE
    MOV R2, 0           ; wrap to top (no scroll in Phase 1)
PUTCHAR_STORE:
    MOV [0x0024], R1
    MOV [0x0025], R2
    RET

PUTCHAR_NL:
    MOV R1, 0
    MOV R2, [0x0025]
    INC R2
    CMP R2, CONS_ROWS
    JNZ PUTCHAR_STORE
    MOV R2, 0
    JMP PUTCHAR_STORE

; ---------------------------------------------------------------------------
; PRINT — display null-terminated string. Input: P0 = pointer.
; Clobbers R0.
; ---------------------------------------------------------------------------
PRINT:
    MOV R0, [P0]
    CMP R0, 0
    JZ PRINT_DONE
    CALL PUTCHAR
    INC P0
    JMP PRINT
PRINT_DONE:
    RET

; ---------------------------------------------------------------------------
; PRINTHEX — display byte in R0 as two hex digits. Clobbers R0, R3.
; ---------------------------------------------------------------------------
PRINTHEX:
    MOV R3, R0
    SHR R0, 4
    AND R0, 0x0F
    CALL HEXDIGIT
    CALL PUTCHAR
    MOV R0, R3
    AND R0, 0x0F
    CALL HEXDIGIT
    CALL PUTCHAR
    RET

; ---------------------------------------------------------------------------
; HEXDIGIT — convert nibble in R0 (0-15) to ASCII hex. Clobbers R0.
; ---------------------------------------------------------------------------
HEXDIGIT:
    CMP R0, 10
    JNC HEXLETTER
    ADD R0, 0x30        ; '0'-'9'
    RET
HEXLETTER:
    ADD R0, 0x37        ; 'A'-'F'
    RET

; ---------------------------------------------------------------------------
; NEWLINE — move cursor to beginning of next row.
; ---------------------------------------------------------------------------
NEWLINE:
    MOV R0, 0
    MOV [0x0024], R0
    MOV R0, [0x0025]
    INC R0
    CMP R0, CONS_ROWS
    JZ NEWLINE_WRAP
    MOV [0x0025], R0
    RET
NEWLINE_WRAP:
    MOV R0, 0
    MOV [0x0025], R0
    RET

; ---------------------------------------------------------------------------
; PRINT_DECIMAL — display 8-bit value in R0 as decimal (0-255).
; Subtractive digit loop; leading hundreds digit prints as a space when 0.
; Clobbers R0, R5-R7.
; ---------------------------------------------------------------------------
PRINT_DECIMAL:
    MOV R5, R0          ; working value
    MOV R6, 0           ; hundreds digit
PDEC_HUNDREDS:
    CMP R5, 100
    JNC PDEC_HUNDRED_OK
    JMP PDEC_TENS
PDEC_HUNDRED_OK:
    SUB R5, 100
    INC R6
    JMP PDEC_HUNDREDS
PDEC_TENS:
    CMP R6, 0
    JNZ PDEC_PRINT_H
    MOV R0, 0x20        ; space for leading zero
    CALL PUTCHAR
    JMP PDEC_DO_TENS
PDEC_PRINT_H:
    MOV R0, R6
    ADD R0, 0x30
    CALL PUTCHAR
PDEC_DO_TENS:
    MOV R7, 0           ; tens digit
PDEC_TENS_LOOP:
    CMP R5, 10
    JNC PDEC_TEN_OK
    JMP PDEC_ONES
PDEC_TEN_OK:
    SUB R5, 10
    INC R7
    JMP PDEC_TENS_LOOP
PDEC_ONES:
    MOV R0, R7
    ADD R0, 0x30
    CALL PUTCHAR
    MOV R0, R5
    ADD R0, 0x30
    CALL PUTCHAR
    RET

; ---------------------------------------------------------------------------
; GETLINE — read a line from the keyboard into the line buffer (0xE800).
; Busy-polls KEYSTAT; echoes; Enter terminates, Backspace deletes.
;
; Key-code compatibility (verified against nova_keyboard.py + nova_gui.py):
;   Enter     = 0x0A (GUI 'enter') or 0x93 (design-doc scan code)
;   Backspace = 0x08 (GUI 'backspace') or 0x92 (design-doc scan code)
;   CR (0x0D) is accepted as Enter. Any other byte outside printable ASCII
;   (0x20-0x7E) is swallowed — arrows/F-keys/Tab would otherwise echo as
;   random glyphs. Programs needing raw codes use SYS GETKEY instead.
; Output: null-terminated line at K_LINEBUF, length at 0x0022
; (ZP_LINE_LEN). Clobbers R0, R5, P0.
; ---------------------------------------------------------------------------
GETLINE:
    MOV P0, K_LINEBUF
    MOV R5, 0           ; char count
GETLINE_LOOP:
    KEYSTAT R0
    AND R0, 0x01        ; bit 0 = key ready
    CMP R0, 0
    JZ GETLINE_LOOP
    KEYIN R0
    ; --- Enter? (both code sets, plus CR) ---
    CMP R0, K_ENTER     ; 0x0A: what the GUI actually sends
    JZ GETLINE_DONE
    CMP R0, K_ENTER_ALT ; 0x93: design-doc scan code
    JZ GETLINE_DONE
    CMP R0, 0x0D        ; CR
    JZ GETLINE_DONE
    ; --- Backspace? (both code sets) ---
    CMP R0, K_BACKSP    ; 0x08: what the GUI actually sends
    JZ GETLINE_BS
    CMP R0, K_BACKSP_ALT ; 0x92: design-doc scan code
    JZ GETLINE_BS
    ; --- printable ASCII only ---
    CMP R0, 0x20
    JC GETLINE_LOOP     ; < 0x20: ignore control byte
    CMP R0, 0x7F
    JNC GETLINE_LOOP    ; >= 0x7F: ignore scan-code keys
    MOV [P0], R0
    INC P0
    INC R5
    CALL PUTCHAR
    JMP GETLINE_LOOP
GETLINE_BS:
    CMP R5, 0
    JZ GETLINE_LOOP     ; nothing to delete
    DEC P0
    DEC R5
    JMP GETLINE_LOOP
GETLINE_DONE:
    MOV R0, 0
    MOV [P0], R0        ; null-terminate
    MOV [0x0022], R5    ; ZP_LINE_LEN
    MOV R0, 0x0A
    CALL PUTCHAR
    RET
