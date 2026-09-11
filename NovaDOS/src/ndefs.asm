; NovaDOS — Canonical Constant Definitions
; EQU block from memory-map.md §4. Every fixed address NovaDOS uses is
; defined here — never use raw literals in new code.
;
; LIMITATION (verified against nova_assembler1.py): the legacy 2-pass
; assembler does NOT substitute EQU symbols inside memory-reference
; operands like [ZP_VID_CUR] or [ZP_CUR_BANK]. Memory references in the
; kernel therefore use literal hex addresses with the symbolic name in a
; trailing comment; these EQU constants remain valid for immediate
; operands (MOV R0, K_ENTER), documentation, and future assembler work.

; ---- Regions ----
K_KERNEL    EQU 0x0120     ; kernel entry point (first ORG)
K_EXTENT    EQU 0x1000     ; overflow zone start
K_PROG      EQU 0x1000     ; default program base
K_VARS      EQU 0xD000     ; variable heap base
K_VARS_END  EQU 0xE800     ; variable heap end
K_LINEBUF   EQU 0xE800     ; command line buffer address
K_SCRATCH   EQU 0x0030     ; zero-page scratch region
K_DEV_TBL   EQU 0x0F00     ; device table (16 x 8 B, Phase 2)

; ---- Zero page OS globals ----
ZP_SIG      EQU 0x0000     ; OS signature "ND\x01\x00"
ZP_VARS_B   EQU 0x0008     ; VARS_BASE (word, big-endian)
ZP_VARS_E   EQU 0x000A     ; VARS_END (word)
ZP_PROG_B   EQU 0x000C     ; PROG_BASE (word)
ZP_CUR_ENT  EQU 0x000E     ; current entry point (word)
ZP_CUR_BANK EQU 0x0010     ; current bank (byte)
ZP_SYS_NUM  EQU 0x0012     ; SYS opcode (word)
ZP_SYS_RET  EQU 0x0014     ; SYS return code (word)
ZP_SYS_ARG0 EQU 0x0016     ; SYS argument 0 (word)
ZP_SYS_ARG1 EQU 0x0018     ; SYS argument 1 (word)
ZP_SYS_ARG2 EQU 0x001A     ; SYS argument 2 (word)
ZP_LINE_LEN EQU 0x0022     ; line length (byte)
ZP_VID_CUR  EQU 0x0024     ; text cursor X (byte)
ZP_VID_CUR2 EQU 0x0025     ; text cursor Y (byte)
ZP_CONS_CLR EQU 0x0027     ; console color (byte)
ZP_TICK_FL  EQU 0x0030     ; timer tick flag (byte)
ZP_UART_FL  EQU 0x0031     ; UART flag (byte)
ZP_KEY_FL   EQU 0x0032     ; keyboard flag (byte)
ZP_MOUSE_FL EQU 0x0033     ; mouse flag (byte)

; ---- IVT ----
IVT_BASE    EQU 0x0100

; ---- Keyboard codes ----
; Ground truth verified in nova_keyboard.py::_create_key_mapping and
; nova_gui.py::map_event_to_nova_key: the GUI path ('enter'/'backspace'
; key names) produces plain ASCII control codes. The design docs' 0x93/0x92
; scan codes are NOT produced by the emulator's keyboard path; GETLINE
; accepts both so raw-injected and GUI-driven input behave identically.
K_ENTER     EQU 0x0A      ; GUI 'enter' (pygame K_RETURN -> key_mapping)
K_BACKSP    EQU 0x08      ; GUI 'backspace'
K_ENTER_ALT EQU 0x93      ; design-doc scan code (headless injections)
K_BACKSP_ALT EQU 0x92     ; design-doc scan code

; ---- Colors ----
C_BLACK     EQU 0x00
C_WHITE     EQU 0x0F

; ---- Console geometry ----
CONS_COLS   EQU 32        ; 256 / 8 font width
CONS_ROWS   EQU 32        ; 256 / 8 font height

; ---- Console layers (layer discipline: volatile vs static) ----
; Layer 1 = console text (volatile: scrolled, erased, rewritten).
; Layer 2 = GUI/banner chrome (static: banner survives scroll + CLS).
CONS_LAYER  EQU 1         ; scrolling console text layer
BANNER_LAYER EQU 2        ; static title / status layer above console
CONS_TOP_ROW EQU 3        ; first writable console row (banner owns 0-2)

; ---- NDF format ----
NDF_DIR_OFF EQU 0x0010    ; directory offset within bank window
