; NovaDOS — SYS Mailbox (Interrupt Vector 4)
; The only sanctioned channel between user programs and kernel services.
; Mailbox fields in the zero page:
;   [0x0012] ZP_SYS_NUM  = opcode (word)
;   [0x0014] ZP_SYS_RET  = result/status (word, 0 = ok, 0xFF = bad opcode)
;   [0x0016/18/1A] SYS_ARG0..2 = arguments (words)
;
; Opcodes: 1=GETKEY 2=PUTCHAR 3=PEEK 4=POKE 5=BANKGET 6=BANKPUT.
; Rules: all work happens between PUSHA/POPA (full register isolation);
; never HLT inside the dispatcher; handlers stay short because the INT
; instruction cleared I — peripheral events only set flag bytes meanwhile.

; ---------------------------------------------------------------------------
; SYS_DISPATCHER — INT 4 entry. PUSHA/POPA protect every kernel register.
; ---------------------------------------------------------------------------
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
    ; Non-blocking: R0 = key scan code, or 0 when the buffer is empty.
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
    MOV R0, [0x0016]    ; SYS_ARG0 = character
    CALL PUTCHAR
    MOV R0, 0
    MOV [0x0014], R0
    JMP SYS_DONE

SYS_DO_PEEK:
    ; Read byte at SYS_ARG0; result in SYS_RET.
    MOV P0, [0x0016]
    MOV R0, [P0]
    MOV [0x0014], R0
    JMP SYS_DONE

SYS_DO_POKE:
    ; Write SYS_ARG2 (low byte) to SYS_ARG0.
    MOV P0, [0x0016]
    MOV R0, [0x001A]
    MOV [P0], R0
    MOV R0, 0
    MOV [0x0014], R0
    JMP SYS_DONE

SYS_DO_BANKGET:
    MOV R0, [0x0010]    ; ZP_CUR_BANK
    MOV [0x0014], R0
    JMP SYS_DONE

SYS_DO_BANKPUT:
    MOV R0, [0x0016]
    MOV [0x0010], R0    ; ZP_CUR_BANK
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
