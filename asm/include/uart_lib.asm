; ================================================================
; uart_lib.asm - Reusable UART helper routines for Nova-16
;
; Include from another program:
;   INCLUDE "uart_lib.asm"
;
; Calling convention:
;   - Caller initializes stack pointer before CALL/RET usage.
;   - R0/R1 and P0 may be clobbered by routines.
;
; Constants:
;   UART_STATUS_RX_AVAILABLE = 0x01
;   UART_STATUS_TX_COMPLETE  = 0x02
;   UART_CTRL_IRQ_ENABLE     = 0x01
;   UART_CTRL_FRAMED_MODE    = 0x04
;
; API:
;   UART_INIT         ; R0=control -> SERCTRL
;   UART_INIT_RAW     ; control=0x00 (raw, IRQ off)
;   UART_STATUS       ; R0=status bits
;   UART_RX_READY     ; R0=1 if RX available else 0
;   UART_READ_NONBLOCK; R1=1 and R0=byte if available, else R1=0
;   UART_READ_BLOCKING; wait for RX, return byte in R0
;   UART_WAIT_TX      ; wait for TX complete bit
;   UART_WRITE_BYTE   ; R0=byte to send
;   UART_WRITE_CSTR   ; P0 -> null-terminated string, write bytes
;   UART_WRITE_CRLF   ; send 0x0D 0x0A
; ================================================================

UART_STATUS_RX_AVAILABLE EQU 0x01
UART_STATUS_TX_COMPLETE  EQU 0x02
UART_CTRL_IRQ_ENABLE     EQU 0x01
UART_CTRL_FRAMED_MODE    EQU 0x04

UART_INIT:
    SERCTRL R0
    RET

UART_INIT_RAW:
    MOV R0, 0x00
    SERCTRL R0
    RET

UART_STATUS:
    SERSTAT R0
    RET

UART_RX_READY:
    SERSTAT R0
    AND R0, UART_STATUS_RX_AVAILABLE
    CMP R0, 0
    JZ UART_RX_READY_NO
    MOV R0, 1
    RET

UART_RX_READY_NO:
    MOV R0, 0
    RET

UART_READ_NONBLOCK:
    SERSTAT R1
    AND R1, UART_STATUS_RX_AVAILABLE
    CMP R1, 0
    JZ UART_READ_NONBLOCK_EMPTY
    SERIN R0
    MOV R1, 1
    RET

UART_READ_NONBLOCK_EMPTY:
    MOV R0, 0
    MOV R1, 0
    RET

UART_READ_BLOCKING:
UART_READ_BLOCKING_WAIT:
    SERSTAT R1
    AND R1, UART_STATUS_RX_AVAILABLE
    CMP R1, 0
    JZ UART_READ_BLOCKING_WAIT
    SERIN R0
    RET

UART_WAIT_TX:
UART_WAIT_TX_LOOP:
    SERSTAT R1
    AND R1, UART_STATUS_TX_COMPLETE
    CMP R1, 0
    JZ UART_WAIT_TX_LOOP
    RET

UART_WRITE_BYTE:
    SEROUT R0
    RET

UART_WRITE_CSTR:
UART_WRITE_CSTR_LOOP:
    MOV R0, [P0]
    CMP R0, 0
    JZ UART_WRITE_CSTR_DONE
    SEROUT R0
    INC P0
    JMP UART_WRITE_CSTR_LOOP

UART_WRITE_CSTR_DONE:
    RET

UART_WRITE_CRLF:
    MOV R0, 0x0D
    SEROUT R0
    MOV R0, 0x0A
    SEROUT R0
    RET
