; NovaDOS — Console I/O
; CLRSCREEN, PUTCHAR, PRINT, PRINTHEX, PRINT_DECIMAL, NEWLINE, GETLINE.
;
; Console geometry: scrolling text on layer 1 (CONS_LAYER), 32x32 grid.
; Static chrome (banner) lives on layer 2 (BANNER_LAYER) ABOVE the
; console, so scrolling / CLS never erase it. Layer 0 is left blank.
; Cursor state lives in zero page:
;   [0x0024] ZP_VID_CUR  = cursor X (column, 0-31)
;   [0x0025] ZP_VID_CUR2 = cursor Y (row, 0-31, never above CONS_TOP_ROW)
; Pixel position: VX = col*8, VY = row*8.
;
; Layer discipline: every routine that draws saves VL in P2 (PUSH P2 +
; MOV P2, VL), selects its target layer, draws, then restores VL. The
; scroll helper uses P3 so it nests safely inside PUTCHAR (which owns P2).

; ---------------------------------------------------------------------------
; CLRSCREEN — clear layers 0/1/2 to black. Used once at boot.
; Preserves VL (saved in P2). Clobbers P2.
; ---------------------------------------------------------------------------
CLRSCREEN:
    PUSH P2
    MOV P2, VL
    MOV VL, 0
    SFILL 0x00          ; blank base layer (unused, kept clean)
    MOV VL, 1
    SFILL 0x00          ; volatile console layer
    MOV VL, 2
    SFILL 0x00          ; static banner layer
    MOV VL, P2
    POP P2
    RET

; ---------------------------------------------------------------------------
; CONS_CLEAR — clear ONLY the volatile console layer (layer 1), keep the
; banner on layer 2 intact, reset cursor to (0, CONS_TOP_ROW).
; This is what CLS uses. Preserves VL. Clobbers R0, P2.
; ---------------------------------------------------------------------------
CONS_CLEAR:
    PUSH P2
    MOV P2, VL
    MOV VL, 1
    SFILL 0x00          ; wipe volatile text only; banner survives
    MOV VL, P2
    POP P2
    MOV R0, 0
    MOV [0x0024], R0    ; cursor X = 0
    MOV R0, 3           ; CONS_TOP_ROW: banner owns rows 0-2
    MOV [0x0025], R0    ; cursor Y = top of scroll region
    RET

; ---------------------------------------------------------------------------
; CONS_SCROLL — scroll the volatile console layer up by one text row.
; SSHFT fills the vacated bottom row with black, so no extra clear is
; needed. Banner layer untouched. Preserves VL via P3 (nests in PUTCHAR).
; Clobbers P3.
; ---------------------------------------------------------------------------
CONS_SCROLL:
    PUSH P3
    MOV P3, VL
    MOV VL, 1           ; CONS_LAYER: volatile console text
    SSHFT 1, -8         ; shift active layer up 8px (one glyph row)
    MOV VL, P3
    POP P3
    RET

; ---------------------------------------------------------------------------
; PUTCHAR — display character in R0 on the console layer, advance cursor.
; Handles newline (0x0A) and carriage return (0x0D). Scrolls instead of
; wrapping to the top: cursor clamps to rows CONS_TOP_ROW..31.
; Preserves VL (saved in P2). Clobbers R0-R3, P2.
; ---------------------------------------------------------------------------
PUTCHAR:
    CMP R0, 0x0A
    JZ PUTCHAR_NL
    CMP R0, 0x0D
    JZ PUTCHAR_NL
    PUSH P2
    MOV P2, VL
    MOV VL, 1           ; CONS_LAYER: volatile console text
    MOV R1, [0x0024]    ; cursor X
    MOV R2, [0x0025]    ; cursor Y
    CMP R2, 3           ; below CONS_TOP_ROW (stale boot value)?
    JNC PUTCHAR_DRAW
    MOV R2, 3           ; clamp into the scroll region
    MOV R1, 0
PUTCHAR_DRAW:
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
    CALL CONS_SCROLL    ; scroll up, stay on the last row
    MOV R2, 31          ; CONS_ROWS - 1
PUTCHAR_STORE:
    MOV [0x0024], R1
    MOV [0x0025], R2
    MOV VL, P2
    POP P2
    RET

PUTCHAR_NL:
    PUSH P2
    MOV P2, VL
    MOV VL, 1           ; keep VL discipline even for cursor-only move
    MOV R1, 0
    MOV R2, [0x0025]
    CMP R2, 3           ; CONS_TOP_ROW: clamp stale values
    JNC PUTCHAR_NL_INC
    MOV R2, 3
    JMP PUTCHAR_NL_STORE
PUTCHAR_NL_INC:
    INC R2
    CMP R2, CONS_ROWS
    JNZ PUTCHAR_NL_STORE
    CALL CONS_SCROLL    ; newline past bottom scrolls, no wrap
    MOV R2, 31          ; CONS_ROWS - 1
PUTCHAR_NL_STORE:
    MOV [0x0024], R1
    MOV [0x0025], R2
    MOV VL, P2
    POP P2
    RET

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
; Note: PUTCHAR clobbers R3, so we must save/restore it across the call.
; ---------------------------------------------------------------------------
PRINTHEX:
    MOV R3, R0
    SHR R0, 4
    AND R0, 0x0F
    CALL HEXDIGIT
    PUSH R3              ; save original value across PUTCHAR call
    CALL PUTCHAR
    POP R3               ; restore original value
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
; NEWLINE — move cursor to beginning of next row (scrolls at bottom).
; ---------------------------------------------------------------------------
NEWLINE:
    MOV R0, 0
    MOV [0x0024], R0
    MOV R0, [0x0025]
    CMP R0, 3           ; CONS_TOP_ROW: clamp stale boot values
    JNC NEWLINE_INC
    MOV R0, 3
    MOV [0x0025], R0
    RET
NEWLINE_INC:
    INC R0
    CMP R0, CONS_ROWS
    JNZ NEWLINE_STORE
    CALL CONS_SCROLL    ; past bottom: scroll, stay on last row
    MOV R0, 31          ; CONS_ROWS - 1
NEWLINE_STORE:
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
; Busy-polls KEYSTAT; echoes; Enter terminates, Backspace visually erases.
;
; Key-code compatibility (verified against nova_keyboard.py + nova_gui.py):
;   Enter     = 0x0A (GUI 'enter') or 0x93 (design-doc scan code)
;   Backspace = 0x08 (GUI 'backspace') or 0x92 (design-doc scan code)
;   CR (0x0D) is accepted as Enter. Any other byte outside printable ASCII
;   (0x20-0x7E) is swallowed — arrows/F-keys/Tab would otherwise echo as
;   random glyphs. Programs needing raw codes use SYS GETKEY instead.
; Output: null-terminated line at K_LINEBUF, length at 0x0022
; (ZP_LINE_LEN). Clobbers R0-R4, R5, P0-P2.
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
    CMP R5, 255         ; line buffer cap (0xE800-0xEFFF is 2KB, shared)
    JZ GETLINE_LOOP     ; full: swallow the key, keep echo honest
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
    ; Erase the echoed glyph: the cursor sits one cell PAST the glyph
    ; (PUTCHAR advanced it, with wrap to the next row at the edge).
    ; Step one cell back - with row borrow at column 0 - then paint the
    ; 8x8 cell black on the console layer.
    MOV R1, [0x0024]    ; cursor X (one past the glyph)
    MOV R2, [0x0025]    ; cursor Y
    CMP R1, 0
    JZ GETLINE_BS_PREV
    DEC R1
    JMP GETLINE_BS_WIPE
GETLINE_BS_PREV:
    ; Cursor wrapped to column 0 of the next row: the glyph is the last
    ; cell of the previous row.
    CMP R2, 3           ; CONS_TOP_ROW: never erase above the console
    JZ GETLINE_BS_TOP   ; wrapped past row 3? (scroll desync guard)
    DEC R2
    MOV R1, 31          ; CONS_COLS - 1
    JMP GETLINE_BS_WIPE
GETLINE_BS_TOP:
    ; Cursor is (0,3) after an auto-wrap off the top scroll edge: the
    ; glyph wrapped from (31,3)... but row 3 is the TOP row, so scroll
    ; already moved it. Safest: wipe cell (31,3) is wrong; wipe (0,3)-8?
    ; Actually PUTCHAR at (31,3) does NOT scroll (row 3 < 31): it stores
    ; (0,4). So (0,3) here means the glyph is at (31,3) only if R2 was 4.
    ; Fall through and wipe the last cell of row 2 above... no: rows
    ; above CONS_TOP_ROW belong to the banner. Wipe (31,3) instead.
    MOV R1, 31
    MOV R2, 3
GETLINE_BS_WIPE:
    MOV [0x0024], R1
    MOV [0x0025], R2
    PUSH P2
    MOV P2, VL
    MOV VL, 1           ; CONS_LAYER: volatile console text
    MOV R3, R1
    SHL R3, 3           ; VX = col * 8
    MOV VX, R3
    MOV R3, R2
    SHL R3, 3           ; VY = row * 8
    MOV VY, R3
    MOV R4, VC
    MOV VC, 0           ; black paint erases without touching VC state
    MOV R3, VX          ; x1 (8-bit, exact)
    ADD R3, 7           ; x2 = x1 + 7 (248+7=255 max: no overflow)
    MOV R0, VY          ; y1 (8-bit, exact)
    ADD R0, 7           ; y2 = y1 + 7
    SRECT R3, R0, 1     ; filled 8x8 rect; R operands avoid P high-byte garbage
    MOV VC, R4
    MOV VL, P2
    POP P2
    JMP GETLINE_LOOP
GETLINE_DONE:
    MOV R0, 0
    MOV [P0], R0        ; null-terminate
    MOV [0x0022], R5    ; ZP_LINE_LEN
    MOV R0, 0x0A
    CALL PUTCHAR
    RET
