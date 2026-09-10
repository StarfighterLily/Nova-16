; NovaDOS — NDF Loader
; NovaDisk filesystem: each bank (1-15) holds one 16 KB NDF volume inside
; the 0x8000-0xBFFF window.
;
; Volume layout:
;   +0x0000  magic b"NDB1"
;   +0x000E  1 byte entry count
;   +0x0010  16-byte directory entries:
;              name[10] (space-padded) type(1) flags(1)
;              start(2) len(2) entry(2)   -- all words big-endian
;   +0x0400  file bytes
;
; Routines are NDF_* (not CMD_*) so they never collide with the REPL
; dispatcher labels of the same command names. All words are big-endian.

; ---------------------------------------------------------------------------
; NDF_RUN — CALL the entry point of the loaded program (CUR_ENTRY word at
; 0x000E, big-endian). The program returns to the REPL via RET.
; Indirect CALL P0 is verified emulator behavior (get_operand_value returns
; the register contents as the branch target).
; ---------------------------------------------------------------------------
NDF_RUN:
    MOV R0, [0x000E]    ; CUR_ENTRY high
    MOV R1, [0x000F]    ; CUR_ENTRY low
    MOV P0:, R0
    MOV :P0, R1
    CALL P0
    RET

; ---------------------------------------------------------------------------
; NDF_NEW — clear the A-Z variable heap (26 words = 52 bytes).
; ---------------------------------------------------------------------------
NDF_NEW:
    MOV R0, 0
    MOV R1, 52
    MOV P0, K_VARS
NEW_LOOP:
    CMP R1, 0
    JZ NEW_DONE
    MOV [P0], R0
    INC P0
    DEC R1
    JMP NEW_LOOP
NEW_DONE:
    RET

; ---------------------------------------------------------------------------
; NDF_LOAD — copy the named file from the banked volume to PROG_BASE.
; In: P0 = filename pointer (bank must already be selected by caller).
; Scans up to entry-count entries, matching name chars until the user
; string ends; remaining directory name bytes must be space padding.
; On match: MEMCPY window[start..start+len] -> PROG_BASE, store entry
; point in CUR_ENTRY. Clobbers R0-R6, P0-P3.
; ---------------------------------------------------------------------------
NDF_LOAD:
    MOV R5, [0x800E]    ; entry count
    MOV R4, 0           ; entry index
    MOV P1, 0x8010      ; directory start (window + NDF_DIR_OFF)
LOAD_SCAN_LOOP:
    CMP R4, R5
    JZ LOAD_NOT_FOUND
    MOV R6, 0           ; char index within the 10-byte name
    MOV P2, P0          ; user filename pointer
LOAD_CMP_LOOP:
    CMP R6, 10
    JZ LOAD_FOUND
    MOV R0, [P1]        ; directory name char
    MOV R1, [P2]        ; user char
    CMP R1, 0           ; end of user string?
    JZ LOAD_CHECK_PAD
    CMP R0, R1
    JNZ LOAD_NEXT_ENTRY
    INC P1
    INC P2
    INC R6
    JMP LOAD_CMP_LOOP
LOAD_CHECK_PAD:
    ; User string ended: remaining directory chars must be space padding.
    CMP R0, 0x20
    JNZ LOAD_NEXT_ENTRY
    INC P1
    INC R6
    JMP LOAD_CMP_LOOP
LOAD_NEXT_ENTRY:
    ADD P1, 16          ; next 16-byte directory entry
    INC R4
    JMP LOAD_SCAN_LOOP
LOAD_FOUND:
    ; Source = window base + file offset (start word at P1+2, big-endian)
    MOV R0, [P1+2]      ; start high
    MOV R1, [P1+3]      ; start low
    MOV P3:, R0
    MOV :P3, R1         ; P3 = word start offset
    MOV P2, 0x8000
    ADD P2, P3
    ; Destination = PROG_BASE (big-endian word at 0x000C)
    MOV R0, [0x000C]    ; PROG_BASE high
    MOV R1, [0x000D]    ; PROG_BASE low
    MOV P0:, R0
    MOV :P0, R1
    ; Length: Phase 1 caps files at 255 bytes, so the low byte of the
    ; length word is the copy count; a nonzero high byte clamps to 255.
    MOV R0, [P1+4]      ; len high
    CMP R0, 0
    JNZ LOAD_FOUND_MAX
    MOV R1, [P1+5]      ; len low
    MEMCPY P0, P2, R1
    JMP LOAD_FOUND_ENT
LOAD_FOUND_MAX:
    MOV R1, 255
    MEMCPY P0, P2, R1
LOAD_FOUND_ENT:
    ; Store entry point (word at P1+6, big-endian)
    MOV R0, [P1+6]      ; entry high
    MOV R1, [P1+7]      ; entry low
    MOV [0x000E], R0    ; ZP_CUR_ENT high
    MOV [0x000F], R1    ; ZP_CUR_ENT low
    RET
LOAD_NOT_FOUND:
    RET

; ---------------------------------------------------------------------------
; NDF_DIR — print the entry names of the volume in the current bank.
; Selects CUR_BANK, prints each name (up to its space padding), restores
; bank 0. Clobbers R0, R5-R7, P0.
; ---------------------------------------------------------------------------
NDF_DIR:
    MOV R0, [0x0010]    ; ZP_CUR_BANK
    MOV BANK, R0
    MOV R5, [0x800E]    ; entry count
    MOV R0, 0x0A        ; leading newline
    CALL PUTCHAR
    MOV P0, 0x8010      ; directory start
    MOV R6, 0           ; entry index
DIR_LOOP:
    CMP R6, R5
    JZ DIR_DONE
    MOV R7, 0           ; char index
DIR_NAME_LOOP:
    CMP R7, 10
    JZ DIR_NAME_DONE
    MOV R0, [P0]
    CMP R0, 0x20        ; stop at space padding
    JZ DIR_NAME_DONE
    CALL PUTCHAR
    INC P0
    INC R7
    JMP DIR_NAME_LOOP
DIR_NAME_DONE:
    ; Skip the remaining name bytes, then type/flags/start/len/entry (6)
    ADD P0, R7
    MOV R0, 10
    SUB R0, R7
    ADD P0, R0
    ADD P0, 6
    MOV R0, 0x0A
    CALL PUTCHAR
    INC R6
    JMP DIR_LOOP
DIR_DONE:
    MOV BANK, 0
    RET
