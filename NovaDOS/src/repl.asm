; NovaDOS — REPL (Read-Eval-Print Loop)
; Prompt -> GETLINE -> EXEC_LINE -> repeat.
;
; EXEC_LINE first looks for '=' (variable assignment: "A = 5"), otherwise
; tokenizes and dispatches on the first command character, with a second
; character check to disambiguate shared prefixes (P: PEEK/PRINT,
; B: BANK/BYE). BYE halts the emulator — the only legal HLT in the system.

; ---------------------------------------------------------------------------
; REPL_MAIN — the outer loop. Print "> ", read a line, execute it.
; ---------------------------------------------------------------------------
REPL_MAIN:
    MOV R0, 0x3E        ; '>'
    CALL PUTCHAR
    MOV R0, 0x20        ; ' '
    CALL PUTCHAR
    CALL GETLINE
    CALL EXEC_LINE
    JMP REPL_MAIN

; ---------------------------------------------------------------------------
; EXEC_LINE — parse and execute one command line.
; ---------------------------------------------------------------------------
EXEC_LINE:
    MOV P0, K_LINEBUF
    CALL SKIP_SPACE
    MOV R0, [P0]
    CMP R0, 0
    JZ EXEC_DONE        ; empty line
    ; Scan for '=' to detect an assignment
    MOV P1, P0
EXEC_FIND_EQ:
    MOV R0, [P1]
    CMP R0, 0
    JZ EXEC_NO_EQ
    CMP R0, 0x3D        ; '='
    JZ EXEC_ASSIGN
    INC P1
    JMP EXEC_FIND_EQ

; ----- assignment: <var> = <value> -----------------------------------------
EXEC_ASSIGN:
    CALL VAR_PARSE_NAME
    CMP R2, 1           ; invalid name?
    JZ EXEC_ERR_SYNTAX
    MOV R4, R0          ; type
    MOV R5, R1          ; index
    MOV P0, P1
    INC P0              ; skip '='
    CALL SKIP_SPACE
    MOV P1, K_SCRATCH
    CALL TOKENIZE
    MOV P0, K_SCRATCH
    MOV R1, 3
    CALL PARSE_UINT8    ; R0 = value (0-255 in Phase 1)
    CMP R4, 0           ; real?
    JZ EXEC_SET_AZ
    JMP EXEC_DONE       ; string assignment: Phase 1b
EXEC_SET_AZ:
    MOV R1, R5          ; index
    MOV P0, 0
    MOV :P0, R0         ; value into P0 low byte
    MOV R0, R1
    CALL VAR_SET_AZ
    JMP EXEC_DONE

; ----- command dispatch -----------------------------------------------------
EXEC_NO_EQ:
    MOV P0, K_LINEBUF
    CALL SKIP_SPACE
    MOV P1, K_SCRATCH
    CALL TOKENIZE
    MOV P0, K_SCRATCH
    MOV R0, [P0]        ; first char of the command
    CMP R0, 0x48        ; 'H'
    JZ CMD_HELP
    CMP R0, 0x68        ; 'h'
    JZ CMD_HELP
    CMP R0, 0x50        ; 'P' -> PEEK or PRINT
    JZ CMD_PCHK
    CMP R0, 0x70        ; 'p'
    JZ CMD_PCHK
    CMP R0, 0x42        ; 'B' -> BANK or BYE
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
    CMP R0, 0x43        ; 'C' -> CLS
    JZ CMD_CLS
    CMP R0, 0x63        ; 'c'
    JZ CMD_CLS
    JMP EXEC_ERR_CMD

CMD_HELP:
    CALL DO_HELP
    JMP EXEC_DONE
CMD_CLS:
    CALL DO_CLS
    JMP EXEC_DONE
; P-prefixed: PEEK / PRINT
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
; B-prefixed: BANK / BYE
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
; D-prefixed: DIR
CMD_DCHK:
    MOV R0, [P0+1]
    CMP R0, 0x49        ; 'I'
    JZ CMD_DIR
    CMP R0, 0x69        ; 'i'
    JZ CMD_DIR
    JMP EXEC_ERR_CMD
CMD_DIR:
    MOV R0, [0x0010]    ; ZP_CUR_BANK
    MOV BANK, R0
    CALL NDF_DIR
    MOV BANK, 0
    JMP EXEC_DONE
; L-prefixed: LOAD
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
; R-prefixed: RUN
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
; NEW
CMD_NEW:
    CALL NDF_NEW
    JMP EXEC_DONE
; B-prefixed fallback: BYE
CMD_BYCHK2:
    MOV R0, [P0+1]
    CMP R0, 0x59        ; 'Y'
    JZ CMD_BYE
    CMP R0, 0x79        ; 'y'
    JZ CMD_BYE
    JMP EXEC_ERR_CMD
CMD_BYE:
    HLT                 ; the only legal HLT: graceful shutdown
; P-prefixed fallback: PRINT
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

; ----- errors ---------------------------------------------------------------
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
