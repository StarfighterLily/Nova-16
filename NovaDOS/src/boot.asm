; NovaDOS — Boot Sequence
; Reset entry flow, interrupt vector wiring, default handlers, banner.

; ---------------------------------------------------------------------------
; VECTOR TABLE
; One 4-byte slot per vector (handler address word + reserved word) to match
; the 0x0100 + v*4 IVT layout for an exact 32-byte MEMCPY.
; ---------------------------------------------------------------------------
VECTOR_TABLE:
    DW V0_HANDLER
    DW 0
    DW V1_HANDLER
    DW 0
    DW V2_HANDLER
    DW 0
    DW V3_HANDLER
    DW 0
    DW SYS_DISPATCHER
    DW 0
    DW V5_HANDLER
    DW 0
    DW V6_HANDLER
    DW 0
    DW V7_HANDLER
    DW 0

; ---------------------------------------------------------------------------
; BOOT — reset entry point. Initializes hardware, wires vectors, prints
; banner, then jumps to the REPL.
; ---------------------------------------------------------------------------
BOOT:
    MOV SP, 0xFFFF      ; reset hardware stack
    MOV FP, 0xFFFF      ; reset frame pointer
    MOV VM, 0           ; coordinate mode
    MOV VL, 1           ; console text on the volatile layer (CONS_LAYER)
    MOV VC, C_WHITE     ; white pen
    CALL CLRSCREEN      ; clear layers 0/1/2
    MOV R0, 0
    MOV [0x0024], R0    ; ZP_VID_CUR: cursor X = 0
    MOV R0, 3           ; CONS_TOP_ROW: below the banner (rows 0-2)
    MOV [0x0025], R0    ; ZP_VID_CUR2: cursor Y = 3
    MOV VX, 0
    MOV VY, 24          ; row 3 * 8px: first console row
    MOV VL, 1
    MOV BANK, 0
    ; Write OS signature "ND\x01\x00"
    MOV R0, 0x4E        ; 'N'
    MOV [0x0000], R0    ; ZP_SIG
    MOV R0, 0x44        ; 'D'
    MOV [0x0001], R0
    MOV R0, 0x01        ; version 1
    MOV [0x0002], R0
    MOV R0, 0x00
    MOV [0x0003], R0
    CALL WIRE_VECTORS
    CALL INIT_VARS
    CALL PRINT_BANNER
    STI
    JMP REPL_MAIN

; ---------------------------------------------------------------------------
; WIRE_VECTORS — copy the 32-byte VECTOR_TABLE into the IVT at 0x0100.
; The CPU reads the handler address as a word at 0x0100 + v*4, but the
; table is laid out with 4-byte slots, so a full 32-byte copy fills all
; eight slots cleanly (handler word + zero reserved word each).
; ---------------------------------------------------------------------------
WIRE_VECTORS:
    MOV P0, IVT_BASE
    MOV P1, VECTOR_TABLE
    MOV R0, 32          ; 8 slots x 4 bytes
    MEMCPY P0, P1, R0
    RET

; ---------------------------------------------------------------------------
; INTERRUPT HANDLERS
; The hardware auto-fires vectors 0-3. Handlers MUST preserve registers —
; they may fire between any two instructions of the interrupted code, and
; IRET restores only PC + flags, not register contents.
; ---------------------------------------------------------------------------
V0_HANDLER:
    PUSH R0
    MOV R0, 1
    MOV [0x0030], R0    ; ZP_TICK_FL
    POP R0
    IRET

V1_HANDLER:
    PUSH R0
    MOV R0, 1
    MOV [0x0031], R0    ; ZP_UART_FL
    POP R0
    IRET

V2_HANDLER:
    PUSH R0
    MOV R0, 1
    MOV [0x0032], R0    ; ZP_KEY_FL
    POP R0
    IRET

V3_HANDLER:
    PUSH R0
    MOV R0, 1
    MOV [0x0033], R0    ; ZP_MOUSE_FL
    POP R0
    IRET

V5_HANDLER:
    IRET

V6_HANDLER:
    IRET

V7_HANDLER:
    IRET

; ---------------------------------------------------------------------------
; PRINT_BANNER — display the NovaDOS boot banner on the STATIC layer 2.
; Row 0 "NOVADOS", row 1 "READY."; console cursor starts at row 3 col 0.
; Layer discipline: banner saves VL in P2, draws on BANNER_LAYER, leaves
; VL on CONS_LAYER so the REPL never has to reselect it. Preserves the
; caller's VC (re-whitens after drawing). Clobbers R0, P2.
; ---------------------------------------------------------------------------
PRINT_BANNER:
    PUSH P2
    MOV P2, VL
    MOV VL, 2           ; BANNER_LAYER: static chrome above scrolling text
    MOV VY, 0
    MOV VX, 0
    MOV R0, 0x4E        ; 'N'
    CHAR R0
    MOV VX, 8
    MOV R0, 0x4F        ; 'O'
    CHAR R0
    MOV VX, 16
    MOV R0, 0x56        ; 'V'
    CHAR R0
    MOV VX, 24
    MOV R0, 0x41        ; 'A'
    CHAR R0
    MOV VX, 32
    MOV R0, 0x44        ; 'D'
    CHAR R0
    MOV VX, 40
    MOV R0, 0x4F        ; 'O'
    CHAR R0
    MOV VX, 48
    MOV R0, 0x53        ; 'S'
    CHAR R0
    MOV VY, 8
    MOV VX, 0
    MOV R0, 0x52        ; 'R'
    CHAR R0
    MOV VX, 8
    MOV R0, 0x45        ; 'E'
    CHAR R0
    MOV VX, 16
    MOV R0, 0x41        ; 'A'
    CHAR R0
    MOV VX, 24
    MOV R0, 0x44        ; 'D'
    CHAR R0
    MOV VX, 32
    MOV R0, 0x59        ; 'Y'
    CHAR R0
    MOV VX, 40
    MOV R0, 0x2E        ; '.'
    CHAR R0
    MOV VC, C_WHITE     ; restore pen (CHAR leaves VC untouched, be explicit)
    MOV VL, 1           ; hand the REPL the volatile console layer
    POP P2
    MOV R0, 0
    MOV [0x0024], R0    ; ZP_VID_CUR: cursor X = 0
    MOV R0, 3           ; CONS_TOP_ROW
    MOV [0x0025], R0    ; ZP_VID_CUR2: cursor Y = 3
    MOV VX, 0
    MOV VY, 24          ; row 3 * 8px
    RET
