; NovaDOS — Kernel Entry Point
; Phase 1: Kernel Foundation
; Assembles to a single .bin with .org + .sym sidecars.
; Entry point: 0x0120 (just past the IVT).
; NOTE: The legacy assembler does not support EQU constants in memory
; references. We use literal hex addresses with comments.

    ORG 0x0120

START:
    JMP BOOT

; ===========================================================================
; CONSTANTS
; ===========================================================================
ZP_SIG      EQU 0x0000
ZP_VARS_B   EQU 0x0008
ZP_VARS_E   EQU 0x000A
ZP_PROG_B   EQU 0x000C
ZP_CUR_ENT  EQU 0x000E
ZP_CUR_BANK EQU 0x0010
ZP_SYS_NUM  EQU 0x0012
ZP_SYS_RET  EQU 0x0014
ZP_SYS_ARG0 EQU 0x0016
ZP_SYS_ARG1 EQU 0x0018
ZP_SYS_ARG2 EQU 0x001A
ZP_LINE_LEN EQU 0x0022
ZP_VID_CUR  EQU 0x0024
ZP_VID_CUR2 EQU 0x0025
ZP_CONS_CLR EQU 0x0027
ZP_TICK_FL  EQU 0x0030
ZP_UART_FL  EQU 0x0031
ZP_KEY_FL   EQU 0x0032
ZP_MOUSE_FL EQU 0x0033
K_SCRATCH   EQU 0x0030
K_LINEBUF   EQU 0xE800
K_VARS      EQU 0xD000
K_VARS_END  EQU 0xE800
K_PROG      EQU 0x1000
IVT_BASE    EQU 0x0100
K_ENTER     EQU 0x93
K_BACKSP    EQU 0x92
C_BLACK     EQU 0x00
C_WHITE     EQU 0x0F
CONS_COLS   EQU 32
CONS_ROWS   EQU 32
NDF_DIR_OFF EQU 0x0010

; ===========================================================================
; VECTOR TABLE
; One 4-byte slot per vector (handler address word + reserved word) to match
; the 0x0100 + v*4 IVT layout for an exact 32-byte MEMCPY.
; ===========================================================================
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

; ===========================================================================
; BOOT SEQUENCE
; ===========================================================================
BOOT:
    MOV SP, 0xFFFF
    MOV FP, 0xFFFF
    MOV VM, 0
    MOV VL, 0
    MOV VC, C_WHITE
    CALL CLRSCREEN
    MOV R0, 0
    MOV [0x0024], R0    ; cursor X = 0
    MOV [0x0025], R0    ; cursor Y = 0
    MOV VX, 0
    MOV VY, 0
    MOV BANK, 0
    ; Write OS signature
    MOV R0, 0x4E        ; 'N'
    MOV [0x0000], R0
    MOV R0, 0x44        ; 'D'
    MOV [0x0001], R0
    MOV R0, 0x01
    MOV [0x0002], R0
    MOV R0, 0x00
    MOV [0x0003], R0
    CALL WIRE_VECTORS
    CALL INIT_VARS
    CALL PRINT_BANNER
    STI
    JMP REPL_MAIN

WIRE_VECTORS:
    ; The CPU reads the handler address as a word at 0x0100 + v*4, but the
    ; table is laid out with 4-byte slots, so a full 32-byte copy fills all
    ; eight slots cleanly (handler word + zero reserved word each).
    MOV P0, IVT_BASE
    MOV P1, VECTOR_TABLE
    MOV R0, 32          ; 8 slots x 4 bytes
    MEMCPY P0, P1, R0
    RET

; ===========================================================================
; INTERRUPT HANDLERS
; The hardware auto-fires vectors 0-3. Handlers MUST preserve registers —
; they may fire between any two instructions of the interrupted code, and
; IRET restores only PC + flags, not register contents.
; ===========================================================================
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

; ===========================================================================
; PRINT BANNER
; ===========================================================================
PRINT_BANNER:
    MOV VY, 0
    MOV VX, 0
    MOV R0, 0x4E
    CHAR R0
    MOV VX, 8
    MOV R0, 0x4F
    CHAR R0
    MOV VX, 16
    MOV R0, 0x56
    CHAR R0
    MOV VX, 24
    MOV R0, 0x41
    CHAR R0
    MOV VX, 32
    MOV R0, 0x44
    CHAR R0
    MOV VX, 40
    MOV R0, 0x4F
    CHAR R0
    MOV VX, 48
    MOV R0, 0x53
    CHAR R0
    MOV VY, 8
    MOV VX, 0
    MOV R0, 0x52
    CHAR R0
    MOV VX, 8
    MOV R0, 0x45
    CHAR R0
    MOV VX, 16
    MOV R0, 0x41
    CHAR R0
    MOV VX, 24
    MOV R0, 0x44
    CHAR R0
    MOV VX, 32
    MOV R0, 0x59
    CHAR R0
    MOV VX, 40
    MOV R0, 0x2E
    CHAR R0
    MOV R0, 0
    MOV [0x0024], R0    ; cursor X = 0
    MOV R0, 2
    MOV [0x0025], R0    ; cursor Y = 2
    MOV VX, 0
    MOV VY, 16
    RET

; ===========================================================================
; CONSOLE I/O
; ===========================================================================
; CLRSCREEN — clear the active layer to black with a single SFILL. The
; vector-0 timer handler may fire mid-boot, so this must stay register-light.
CLRSCREEN:
    MOV VL, 0
    SFILL 0x00          ; fill entire layer 0 with black (one instruction)
    RET

PUTCHAR:
    CMP R0, 0x0A
    JZ PUTCHAR_NL
    CMP R0, 0x0D
    JZ PUTCHAR_NL
    MOV R1, [0x0024]    ; cursor X
    MOV R2, [0x0025]    ; cursor Y
    MOV R3, R1
    SHL R3, 3
    MOV VX, R3
    MOV R3, R2
    SHL R3, 3
    MOV VY, R3
    CHAR R0
    INC R1
    CMP R1, CONS_COLS
    JNZ PUTCHAR_STORE
    MOV R1, 0
    INC R2
    CMP R2, CONS_ROWS
    JNZ PUTCHAR_STORE
    MOV R2, 0
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

PRINT:
    MOV R0, [P0]
    CMP R0, 0
    JZ PRINT_DONE
    CALL PUTCHAR
    INC P0
    JMP PRINT
PRINT_DONE:
    RET

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

HEXDIGIT:
    CMP R0, 10
    JNC HEXLETTER
    ADD R0, 0x30
    RET
HEXLETTER:
    ADD R0, 0x37
    RET

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

PRINT_DECIMAL:
    MOV R5, R0
    MOV R6, 0
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
    MOV R0, 0x20
    CALL PUTCHAR
    JMP PDEC_DO_TENS
PDEC_PRINT_H:
    MOV R0, R6
    ADD R0, 0x30
    CALL PUTCHAR
PDEC_DO_TENS:
    MOV R7, 0
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

GETLINE:
    MOV P0, K_LINEBUF
    MOV R5, 0
GETLINE_LOOP:
    KEYSTAT R0
    AND R0, 0x01
    CMP R0, 0
    JZ GETLINE_LOOP
    KEYIN R0
    CMP R0, K_ENTER
    JZ GETLINE_DONE
    CMP R0, K_BACKSP
    JZ GETLINE_BS
    MOV [P0], R0
    INC P0
    INC R5
    CALL PUTCHAR
    JMP GETLINE_LOOP
GETLINE_BS:
    CMP R5, 0
    JZ GETLINE_LOOP
    DEC P0
    DEC R5
    JMP GETLINE_LOOP
GETLINE_DONE:
    MOV R0, 0
    MOV [P0], R0
    MOV [0x0022], R5    ; ZP_LINE_LEN
    MOV R0, 0x0A
    CALL PUTCHAR
    RET

; ===========================================================================
; PARSER UTILITIES
; ===========================================================================
SKIP_SPACE:
    MOV R0, [P0]
    CMP R0, 0x20
    JZ SKIP_ADV
    CMP R0, 0x09
    JZ SKIP_ADV
    RET
SKIP_ADV:
    INC P0
    JMP SKIP_SPACE

TOKENIZE:
    CALL SKIP_SPACE
    MOV R0, 0
TOK_LOOP:
    MOV R2, [P0]
    CMP R2, 0
    JZ TOK_DONE
    CMP R2, 0x20
    JZ TOK_DONE
    CMP R2, 0x09
    JZ TOK_DONE
    MOV [P1], R2
    INC P0
    INC P1
    INC R0
    JMP TOK_LOOP
TOK_DONE:
    MOV R2, 0
    MOV [P1], R2
    RET

PARSE_UINT8:
    MOV R2, 0
    MOV R0, 0
PU_LOOP:
    CMP R2, R1
    JZ PU_DONE
    MOV R3, [P0]
    CMP R3, 0
    JZ PU_DONE
    CMP R3, 0x30
    JC PU_DONE
    CMP R3, 0x3A
    JC PU_CONT
    JMP PU_DONE
PU_CONT:
    SUB R3, 0x30
    MOV R4, R0
    SHL R0, 3
    ADD R0, R4
    ADD R0, R4
    ADD R0, R3
    INC P0
    INC R2
    JMP PU_LOOP
PU_DONE:
    RET

PARSE_HEX8:
    MOV R2, 0
    MOV R0, 0
PH_LOOP:
    CMP R2, R1
    JZ PH_DONE
    MOV R3, [P0]
    CMP R3, 0
    JZ PH_DONE
    CALL HEXCHAR_TO_NIBBLE
    CMP R3, 0xFF
    JZ PH_DONE
    SHL R0, 4
    OR R0, R3
    INC P0
    INC R2
    JMP PH_LOOP
PH_DONE:
    RET

HEXCHAR_TO_NIBBLE:
    CMP R3, 0x30
    JC HEX_INVALID
    CMP R3, 0x3A
    JC HEX_DIGIT
    CMP R3, 0x41
    JC HEX_INVALID
    CMP R3, 0x47
    JC HEX_UPPER
    CMP R3, 0x61
    JC HEX_INVALID
    CMP R3, 0x67
    JC HEX_LOWER
    JMP HEX_INVALID
HEX_DIGIT:
    SUB R3, 0x30
    RET
HEX_UPPER:
    SUB R3, 0x37
    RET
HEX_LOWER:
    SUB R3, 0x57
    RET
HEX_INVALID:
    MOV R3, 0xFF
    RET

; ===========================================================================
; VARIABLE SYSTEM
; ===========================================================================
INIT_VARS:
    ; Memory is big-endian: a word at 0x0008 reads (mem[0x0008]<<8)|mem[0x0009].
    MOV R0, 0xD0
    MOV [0x0008], R0    ; ZP_VARS_B high = 0xD0
    MOV R0, 0x00
    MOV [0x0009], R0    ; ZP_VARS_B low  = 0x00  => 0xD000
    MOV R0, 0xE8
    MOV [0x000A], R0    ; ZP_VARS_E high = 0xE8
    MOV R0, 0x00
    MOV [0x000B], R0    ; ZP_VARS_E low  = 0x00  => 0xE800
    MOV R0, 0x10
    MOV [0x000C], R0    ; ZP_PROG_B high = 0x10
    MOV R0, 0x00
    MOV [0x000D], R0    ; ZP_PROG_B low  = 0x00  => 0x1000
    MOV R0, 0
    MOV [0x000E], R0    ; ZP_CUR_ENT high
    MOV [0x000F], R0    ; ZP_CUR_ENT low
    MOV [0x0010], R0    ; ZP_CUR_BANK = 0
    MOV P0, K_VARS
    MOV R0, 0
    MOV R1, 52
INIT_AZ_LOOP:
    CMP R1, 0
    JZ INIT_AZ_DONE
    MOV [P0], R0
    INC P0
    DEC R1
    JMP INIT_AZ_LOOP
INIT_AZ_DONE:
    RET

VAR_GET_AZ:
    MOV R1, R0
    SHL R1, 1
    MOV P0, K_VARS
    ADD P0, R1
    MOV R0, [P0]
    MOV R1, [P0+1]
    MOV P0:, R0
    MOV :P0, R1
    RET

VAR_SET_AZ:
    MOV R1, R0
    MOV P1, P0
    SHL R1, 1
    MOV P0, K_VARS
    ADD P0, R1
    MOV R0, P1:
    MOV [P0], R0
    MOV R0, :P1
    MOV [P0+1], R0
    RET

VAR_GET_STR:
    MOV R1, R0
    MOV P0, K_VARS
    ADD P0, 52          ; skip A-Z area
    CMP R1, 0
    JZ VGSTR_DONE
VGSTR_LOOP:
    ADD P0, 256
    DEC R1
    CMP R1, 0
    JNZ VGSTR_LOOP
VGSTR_DONE:
    RET

VAR_PARSE_NAME:
    MOV R2, 0
    MOV R0, [P0]
    CMP R0, 0
    JZ VPN_INVALID
    CMP R0, 0x53
    JZ VPN_STRING
    CMP R0, 0x73
    JZ VPN_STRING
    CMP R0, 0x41
    JC VPN_INVALID
    CMP R0, 0x5B
    JC VPN_AZ_UPPER
    CMP R0, 0x61
    JC VPN_INVALID
    CMP R0, 0x7B
    JC VPN_AZ_LOWER
    JMP VPN_INVALID
VPN_AZ_UPPER:
    SUB R0, 0x41
    MOV R1, R0
    MOV R0, 0
    RET
VPN_AZ_LOWER:
    SUB R0, 0x61
    MOV R1, R0
    MOV R0, 0
    RET
VPN_STRING:
    INC P0
    MOV R0, [P0]
    CMP R0, 0x74
    JZ VPN_STR_OK
    CMP R0, 0x54
    JZ VPN_STR_OK
    JMP VPN_INVALID
VPN_STR_OK:
    INC P0
    MOV R0, [P0]
    CMP R0, 0x72
    JZ VPN_STR_OK2
    CMP R0, 0x52
    JZ VPN_STR_OK2
    JMP VPN_INVALID
VPN_STR_OK2:
    INC P0
    MOV R0, [P0]
    CMP R0, 0x30
    JC VPN_INVALID
    CMP R0, 0x3A
    JC VPN_STR_VALID
    JMP VPN_INVALID
VPN_STR_VALID:
    SUB R0, 0x30
    MOV R1, R0
    MOV R0, 1
    RET
VPN_INVALID:
    MOV R2, 1
    RET

; ===========================================================================
; SYS MAILBOX (Interrupt Vector 4)
; ===========================================================================
SYS_DISPATCHER:
    PUSHA
    MOV R0, [0x0012]    ; ZP_SYS_NUM
    CMP R0, 1
    JZ SYS_DO_GETKEY
    CMP R0, 2
    JZ SYS_DO_PUTCHAR
    CMP R0, 3
    JZ SYS_DO_PEEK
    CMP R0, 4
    JZ SYS_DO_POKE
    CMP R0, 5
    JZ SYS_DO_BANKGET
    CMP R0, 6
    JZ SYS_DO_BANKPUT
    JMP SYS_UNKNOWN

SYS_DO_GETKEY:
    KEYSTAT R1
    AND R1, 0x01
    CMP R1, 0
    JZ SYS_GETKEY_NONE
    KEYIN R0
    JMP SYS_GETKEY_DONE
SYS_GETKEY_NONE:
    MOV R0, 0
SYS_GETKEY_DONE:
    MOV [0x0014], R0
    JMP SYS_DONE

SYS_DO_PUTCHAR:
    MOV R0, [0x0016]
    CALL PUTCHAR
    MOV R0, 0
    MOV [0x0014], R0
    JMP SYS_DONE

SYS_DO_PEEK:
    MOV P0, [0x0016]
    MOV R0, [P0]
    MOV [0x0014], R0
    JMP SYS_DONE

SYS_DO_POKE:
    MOV P0, [0x0016]
    MOV R0, [0x001A]
    MOV [P0], R0
    MOV R0, 0
    MOV [0x0014], R0
    JMP SYS_DONE

SYS_DO_BANKGET:
    MOV R0, [0x0010]
    MOV [0x0014], R0
    JMP SYS_DONE

SYS_DO_BANKPUT:
    MOV R0, [0x0016]
    MOV [0x0010], R0
    MOV BANK, R0
    MOV R0, 0
    MOV [0x0014], R0
    JMP SYS_DONE

SYS_UNKNOWN:
    MOV R0, 0xFF
    MOV [0x0014], R0

SYS_DONE:
    POPA
    IRET

; ===========================================================================
; NDF LOADER
; Note: these routines carry NDF_* names (not CMD_*) so they never collide
; with the REPL dispatcher labels CMD_LOAD/CMD_RUN/CMD_NEW/CMD_DIR.
; ===========================================================================
NDF_RUN:
    MOV R0, [0x000E]
    MOV R1, [0x000F]
    MOV P0:, R0
    MOV :P0, R1
    CALL P0
    RET

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

NDF_LOAD:
    MOV R5, [0x800E]
    MOV R4, 0
    MOV P1, 0x8010
LOAD_SCAN_LOOP:
    CMP R4, R5
    JZ LOAD_NOT_FOUND
    MOV R6, 0
    MOV P2, P0
LOAD_CMP_LOOP:
    CMP R6, 10
    JZ LOAD_FOUND
    MOV R0, [P1]
    MOV R1, [P2]
    CMP R1, 0
    JZ LOAD_CHECK_PAD
    CMP R0, R1
    JNZ LOAD_NEXT_ENTRY
    INC P1
    INC P2
    INC R6
    JMP LOAD_CMP_LOOP
LOAD_CHECK_PAD:
    CMP R0, 0x20
    JNZ LOAD_NEXT_ENTRY
    INC P1
    INC R6
    JMP LOAD_CMP_LOOP
LOAD_NEXT_ENTRY:
    ADD P1, 16
    INC R4
    JMP LOAD_SCAN_LOOP
LOAD_FOUND:
    ; Start offset is a 16-bit big-endian word at P1+2 (high at P1+2).
    MOV R0, [P1+2]      ; start high
    MOV R1, [P1+3]      ; start low
    MOV P3:, R0
    MOV :P3, R1         ; P3 = word start offset
    MOV P2, 0x8000
    ADD P2, P3          ; source = window base + file offset
    ; Destination = PROG_BASE (big-endian word at 0x000C)
    MOV R0, [0x000C]    ; PROG_BASE high
    MOV R1, [0x000D]    ; PROG_BASE low
    MOV P0:, R0
    MOV :P0, R1
    ; Length is a word at P1+4; Phase 1 loads <= 255 bytes so the low
    ; byte is the copy length (high byte must be 0).
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
    ; Entry point word at P1+6 (high at P1+6, low at P1+7)
    MOV R0, [P1+6]
    MOV R1, [P1+7]
    MOV [0x000E], R0    ; CUR_ENT high
    MOV [0x000F], R1    ; CUR_ENT low
    RET
LOAD_NOT_FOUND:
    RET

; ===========================================================================
; COMMAND IMPLEMENTATIONS
; ===========================================================================
DO_HELP:
    MOV R0, 0x0A
    CALL PUTCHAR
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

DO_PEEK:
    MOV P0, K_LINEBUF
    ADD P0, 4
    CALL SKIP_SPACE
    MOV P1, K_SCRATCH
    CALL TOKENIZE
    MOV P0, K_SCRATCH
    MOV R1, 4
    CALL PARSE_HEX8
    MOV P1, R0
    MOV R0, [P1]
    CALL PRINTHEX
    MOV R0, 0x0A
    CALL PUTCHAR
    RET

DO_BANK:
    MOV P0, K_LINEBUF
    ADD P0, 4
    CALL SKIP_SPACE
    MOV P1, K_SCRATCH
    CALL TOKENIZE
    MOV P0, K_SCRATCH
    MOV R1, 2
    CALL PARSE_UINT8
    MOV [0x0010], R0
    MOV BANK, R0
    RET

DO_LOAD:
    MOV P0, K_LINEBUF
    ADD P0, 4
    CALL SKIP_SPACE
    MOV R0, [P0]
    CMP R0, 0x22
    JZ DL_SKIP_QUOTE
    JMP DL_LOAD
DL_SKIP_QUOTE:
    INC P0
DL_LOAD:
    MOV R0, [0x0010]
    MOV BANK, R0
    CALL NDF_LOAD
    MOV BANK, 0
    RET

DO_PRINT:
    MOV P0, K_LINEBUF
    ADD P0, 5
    CALL SKIP_SPACE
    CALL VAR_PARSE_NAME
    CMP R2, 1
    JZ DP_ERR
    CMP R0, 0
    JZ DP_AZ
    JMP DP_STR
DP_AZ:
    MOV R0, R1
    CALL VAR_GET_AZ
    MOV R0, :P0
    CALL PRINT_DECIMAL
    MOV R0, 0x0A
    CALL PUTCHAR
    RET
DP_STR:
    MOV R0, R1
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

; ===========================================================================
; REPL — Read-Eval-Print Loop
; ===========================================================================
REPL_MAIN:
    MOV R0, 0x3E        ; '>'
    CALL PUTCHAR
    MOV R0, 0x20        ; ' '
    CALL PUTCHAR
    CALL GETLINE
    CALL EXEC_LINE
    JMP REPL_MAIN

EXEC_LINE:
    MOV P0, K_LINEBUF
    CALL SKIP_SPACE
    MOV R0, [P0]
    CMP R0, 0
    JZ EXEC_DONE
    ; Check for assignment (find '=')
    MOV P1, P0
EXEC_FIND_EQ:
    MOV R0, [P1]
    CMP R0, 0
    JZ EXEC_NO_EQ
    CMP R0, 0x3D
    JZ EXEC_ASSIGN
    INC P1
    JMP EXEC_FIND_EQ

EXEC_ASSIGN:
    CALL VAR_PARSE_NAME
    CMP R2, 1
    JZ EXEC_ERR_SYNTAX
    MOV R4, R0          ; type
    MOV R5, R1          ; index
    MOV P0, P1
    INC P0
    CALL SKIP_SPACE
    MOV P1, K_SCRATCH
    CALL TOKENIZE
    MOV P0, K_SCRATCH
    MOV R1, 3
    CALL PARSE_UINT8
    CMP R4, 0
    JZ EXEC_SET_AZ
    JMP EXEC_DONE
EXEC_SET_AZ:
    MOV R1, R5          ; index
    MOV P0, 0
    MOV :P0, R0         ; P0 = value
    MOV R0, R1          ; index
    CALL VAR_SET_AZ
    JMP EXEC_DONE

EXEC_NO_EQ:
    MOV P0, K_LINEBUF
    CALL SKIP_SPACE
    MOV P1, K_SCRATCH
    CALL TOKENIZE
    MOV P0, K_SCRATCH
    MOV R0, [P0]        ; first char of command
    CMP R0, 0x48        ; 'H'
    JZ CMD_HELP
    CMP R0, 0x68        ; 'h'
    JZ CMD_HELP
    CMP R0, 0x50        ; 'P'
    JZ CMD_PCHK
    CMP R0, 0x70        ; 'p'
    JZ CMD_PCHK
    CMP R0, 0x42        ; 'B'
    JZ CMD_BCHK
    CMP R0, 0x62        ; 'b'
    JZ CMD_BCHK
    CMP R0, 0x44        ; 'D'
    JZ CMD_DCHK
    CMP R0, 0x64        ; 'd'
    JZ CMD_DCHK
    CMP R0, 0x4C        ; 'L'
    JZ CMD_LCHK
    CMP R0, 0x6C        ; 'l'
    JZ CMD_LCHK
    CMP R0, 0x52        ; 'R'
    JZ CMD_RCHK
    CMP R0, 0x72        ; 'r'
    JZ CMD_RCHK
    CMP R0, 0x4E        ; 'N'
    JZ CMD_NEW
    CMP R0, 0x6E        ; 'n'
    JZ CMD_NEW
    JMP EXEC_ERR_CMD

CMD_HELP:
    CALL DO_HELP
    JMP EXEC_DONE
CMD_PCHK:
    MOV R0, [P0+1]
    CMP R0, 0x45        ; 'E'
    JZ CMD_PEEK
    CMP R0, 0x65        ; 'e'
    JZ CMD_PEEK
    JMP CMD_PRCHK2
CMD_PEEK:
    CALL DO_PEEK
    JMP EXEC_DONE
CMD_BCHK:
    MOV R0, [P0+1]
    CMP R0, 0x41        ; 'A'
    JZ CMD_BANK
    CMP R0, 0x61        ; 'a'
    JZ CMD_BANK
    JMP CMD_BYCHK2
CMD_BANK:
    CALL DO_BANK
    JMP EXEC_DONE
CMD_DCHK:
    MOV R0, [P0+1]
    CMP R0, 0x49        ; 'I'
    JZ CMD_DIR
    CMP R0, 0x69        ; 'i'
    JZ CMD_DIR
    JMP EXEC_ERR_CMD
CMD_DIR:
    MOV R0, [0x0010]
    MOV BANK, R0
    CALL NDF_DIR
    MOV BANK, 0
    JMP EXEC_DONE
CMD_LCHK:
    MOV R0, [P0+1]
    CMP R0, 0x4F        ; 'O'
    JZ CMD_LOAD
    CMP R0, 0x6F        ; 'o'
    JZ CMD_LOAD
    JMP EXEC_ERR_CMD
CMD_LOAD:
    CALL DO_LOAD
    JMP EXEC_DONE
CMD_RCHK:
    MOV R0, [P0+1]
    CMP R0, 0x55        ; 'U'
    JZ CMD_RUN
    CMP R0, 0x75        ; 'u'
    JZ CMD_RUN
    JMP EXEC_ERR_CMD
CMD_RUN:
    CALL NDF_RUN
    JMP EXEC_DONE
CMD_NEW:
    CALL NDF_NEW
    JMP EXEC_DONE
CMD_BYCHK2:
    MOV R0, [P0+1]
    CMP R0, 0x59        ; 'Y'
    JZ CMD_BYE
    CMP R0, 0x79        ; 'y'
    JZ CMD_BYE
    JMP EXEC_ERR_CMD
CMD_BYE:
    HLT
CMD_PRCHK2:
    MOV R0, [P0+1]
    CMP R0, 0x52        ; 'R'
    JZ CMD_PRINT
    CMP R0, 0x72        ; 'r'
    JZ CMD_PRINT
    JMP EXEC_ERR_CMD
CMD_PRINT:
    CALL DO_PRINT
    JMP EXEC_DONE

EXEC_ERR_SYNTAX:
    MOV R0, 0x0A
    CALL PUTCHAR
    MOV R0, '?'
    CALL PUTCHAR
    MOV R0, 0x0A
    CALL PUTCHAR
    JMP EXEC_DONE
EXEC_ERR_CMD:
    MOV R0, 0x0A
    CALL PUTCHAR
    MOV R0, '?'
    CALL PUTCHAR
    MOV R0, 0x0A
    CALL PUTCHAR
EXEC_DONE:
    RET

; ===========================================================================
; NDF_DIR — list directory entries in current bank (the loader's DIR builtin)
; ===========================================================================
NDF_DIR:
    MOV R0, [0x0010]    ; ZP_CUR_BANK
    MOV BANK, R0
    MOV R5, [0x800E]    ; entry count
    MOV R0, 0x0A
    CALL PUTCHAR
    MOV P0, 0x8010      ; directory start
    MOV R6, 0
DIR_LOOP:
    CMP R6, R5
    JZ DIR_DONE
    MOV R7, 0
DIR_NAME_LOOP:
    CMP R7, 10
    JZ DIR_NAME_DONE
    MOV R0, [P0]
    CMP R0, 0x20
    JZ DIR_NAME_DONE
    CALL PUTCHAR
    INC P0
    INC R7
    JMP DIR_NAME_LOOP
DIR_NAME_DONE:
    ADD P0, R7
    MOV R0, 10
    SUB R0, R7
    ADD P0, R0
    ADD P0, 6           ; skip type/flags/start/len/entry
    MOV R0, 0x0A
    CALL PUTCHAR
    INC R6
    JMP DIR_LOOP
DIR_DONE:
    MOV BANK, 0
    RET
