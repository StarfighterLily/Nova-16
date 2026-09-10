; NovaDOS — Command Implementations
; DO_HELP, DO_PEEK, DO_BANK, DO_LOAD, DO_PRINT — the actions behind the
; REPL dispatcher. Each parses its arguments from the line buffer at
; 0xE800 (K_LINEBUF), offset past the command word.

; ---------------------------------------------------------------------------
; DO_HELP — print the command list (one command per screen row).
; Uses direct VX placement + PUTCHAR; PUTCHAR manages the cursor wrap.
; ---------------------------------------------------------------------------
DO_HELP:
    MOV R0, 0x0A
    CALL PUTCHAR
    ; HELP
    MOV VX, 0
    MOV R0, 'H'
    CALL PUTCHAR
    MOV VX, 8
    MOV R0, 'E'
    CALL PUTCHAR
    MOV VX, 16
    MOV R0, 'L'
    CALL PUTCHAR
    MOV VX, 24
    MOV R0, 'P'
    CALL PUTCHAR
    MOV R0, 0x0A
    CALL PUTCHAR
    ; PEEK
    MOV VX, 0
    MOV R0, 'P'
    CALL PUTCHAR
    MOV VX, 8
    MOV R0, 'E'
    CALL PUTCHAR
    MOV VX, 16
    MOV R0, 'E'
    CALL PUTCHAR
    MOV VX, 24
    MOV R0, 'K'
    CALL PUTCHAR
    MOV R0, 0x0A
    CALL PUTCHAR
    ; BANK
    MOV VX, 0
    MOV R0, 'B'
    CALL PUTCHAR
    MOV VX, 8
    MOV R0, 'A'
    CALL PUTCHAR
    MOV VX, 16
    MOV R0, 'N'
    CALL PUTCHAR
    MOV VX, 24
    MOV R0, 'K'
    CALL PUTCHAR
    MOV R0, 0x0A
    CALL PUTCHAR
    ; DIR
    MOV VX, 0
    MOV R0, 'D'
    CALL PUTCHAR
    MOV VX, 8
    MOV R0, 'I'
    CALL PUTCHAR
    MOV VX, 16
    MOV R0, 'R'
    CALL PUTCHAR
    MOV R0, 0x0A
    CALL PUTCHAR
    ; LOAD
    MOV VX, 0
    MOV R0, 'L'
    CALL PUTCHAR
    MOV VX, 8
    MOV R0, 'O'
    CALL PUTCHAR
    MOV VX, 16
    MOV R0, 'A'
    CALL PUTCHAR
    MOV VX, 24
    MOV R0, 'D'
    CALL PUTCHAR
    MOV R0, 0x0A
    CALL PUTCHAR
    ; RUN
    MOV VX, 0
    MOV R0, 'R'
    CALL PUTCHAR
    MOV VX, 8
    MOV R0, 'U'
    CALL PUTCHAR
    MOV VX, 16
    MOV R0, 'N'
    CALL PUTCHAR
    MOV R0, 0x0A
    CALL PUTCHAR
    ; NEW
    MOV VX, 0
    MOV R0, 'N'
    CALL PUTCHAR
    MOV VX, 8
    MOV R0, 'E'
    CALL PUTCHAR
    MOV VX, 16
    MOV R0, 'W'
    CALL PUTCHAR
    MOV R0, 0x0A
    CALL PUTCHAR
    ; PRINT
    MOV VX, 0
    MOV R0, 'P'
    CALL PUTCHAR
    MOV VX, 8
    MOV R0, 'R'
    CALL PUTCHAR
    MOV VX, 16
    MOV R0, 'I'
    CALL PUTCHAR
    MOV VX, 24
    MOV R0, 'N'
    CALL PUTCHAR
    MOV VX, 32
    MOV R0, 'T'
    CALL PUTCHAR
    MOV R0, 0x0A
    CALL PUTCHAR
    ; BYE
    MOV VX, 0
    MOV R0, 'B'
    CALL PUTCHAR
    MOV VX, 8
    MOV R0, 'Y'
    CALL PUTCHAR
    MOV VX, 16
    MOV R0, 'E'
    CALL PUTCHAR
    MOV R0, 0x0A
    CALL PUTCHAR
    RET

; ---------------------------------------------------------------------------
; DO_PEEK — PEEK <addr>: tokenize the hex address, then print the byte at
; that address and the one following as hex digits ("4E 44" for the OS
; signature at 0x0000, per the Phase 1 acceptance matrix). Phase 1
; addresses are single bytes (0-255).
; ---------------------------------------------------------------------------
DO_PEEK:
    MOV P0, K_LINEBUF
    ADD P0, 4           ; skip "PEEK"
    CALL SKIP_SPACE
    MOV P1, K_SCRATCH
    CALL TOKENIZE
    MOV P0, K_SCRATCH
    MOV R1, 4
    CALL PARSE_HEX8     ; R0 = address
    MOV P1, R0
    MOV R0, [P1]        ; byte at address
    CALL PRINTHEX
    MOV R0, 0x20        ; space between bytes
    CALL PUTCHAR
    MOV R0, [P1+1]      ; byte at address+1
    CALL PRINTHEX
    MOV R0, 0x0A
    CALL PUTCHAR
    RET

; ---------------------------------------------------------------------------
; DO_BANK — BANK <n>: parse decimal bank number, update CUR_BANK and the
; hardware BANK register.
; ---------------------------------------------------------------------------
DO_BANK:
    MOV P0, K_LINEBUF
    ADD P0, 4           ; skip "BANK"
    CALL SKIP_SPACE
    MOV P1, K_SCRATCH
    CALL TOKENIZE
    MOV P0, K_SCRATCH
    MOV R1, 2
    CALL PARSE_UINT8
    MOV [0x0010], R0    ; ZP_CUR_BANK
    MOV BANK, R0
    RET

; ---------------------------------------------------------------------------
; DO_LOAD — LOAD "name" (quotes optional): select CUR_BANK and run the
; NDF directory scan/copy. Restores bank 0 afterwards.
; ---------------------------------------------------------------------------
DO_LOAD:
    MOV P0, K_LINEBUF
    ADD P0, 4           ; skip "LOAD"
    CALL SKIP_SPACE
    MOV R0, [P0]
    CMP R0, 0x22        ; '"'
    JZ DL_SKIP_QUOTE
    JMP DL_LOAD
DL_SKIP_QUOTE:
    INC P0
DL_LOAD:
    MOV R0, [0x0010]    ; ZP_CUR_BANK
    MOV BANK, R0
    CALL NDF_LOAD
    MOV BANK, 0
    RET

; ---------------------------------------------------------------------------
; DO_PRINT — PRINT <var>: parse the variable name and print its value
; (reals as decimal, strings verbatim).
; ---------------------------------------------------------------------------
DO_PRINT:
    MOV P0, K_LINEBUF
    ADD P0, 5           ; skip "PRINT"
    CALL SKIP_SPACE
    CALL VAR_PARSE_NAME
    CMP R2, 1           ; invalid name?
    JZ DP_ERR
    CMP R0, 0           ; real?
    JZ DP_AZ
    JMP DP_STR
DP_AZ:
    MOV R0, R1          ; index
    CALL VAR_GET_AZ     ; P0 = value
    MOV R0, :P0         ; low byte drives the Phase 1 decimal printer
    CALL PRINT_DECIMAL
    MOV R0, 0x0A
    CALL PUTCHAR
    RET
DP_STR:
    MOV R0, R1          ; index
    CALL VAR_GET_STR
    CALL PRINT
    MOV R0, 0x0A
    CALL PUTCHAR
    RET
DP_ERR:
    MOV R0, '?'
    CALL PUTCHAR
    MOV R0, 0x0A
    CALL PUTCHAR
    RET
