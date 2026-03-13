; ================================================================
; uart_tcp_demo.asm - Nova-16 UART TCP Bridge Demo
;
; Run headlessly with:
;   py -3.13 nova_assembler.py asm/uart_tcp_demo.asm
;   py -3.13 nova.py --headless asm/uart_tcp_demo.bin --cycles 50000 ^
;       --uart-bridge tcp --uart-host 127.0.0.1 --uart-port 4080
;
; Behaviour:
;   1. Initialises UART in raw, no-IRQ mode.
;   2. Transmits a greeting banner byte-by-byte.
;   3. Enters an echo loop: any byte arriving from the TCP peer
;      is echoed straight back.
;   4. Exits the echo loop when either:
;        - 256 bytes have been echoed, OR
;        - ~512 consecutive idle iterations pass with no RX data.
;   5. Transmits a farewell banner and halts.
;
; UART status register bits (SERSTAT):
;   bit 0 (0x01) = RX_AVAILABLE  (data waiting to be read)
;   bit 1 (0x02) = TX_COMPLETE   (last TX succeeded)
;
; Registers used:
;   R0  - general scratch / byte I/O
;   P5  - string pointer (16-bit)
;   P6  - echo byte counter
;   P7  - idle iteration counter
; ================================================================

    ORG 0x0400

; ----------------------------------------------------------------
; START - entry point
; ----------------------------------------------------------------
START:
    ; Initialise UART: raw mode, interrupts disabled (control = 0x00)
    MOV  R0, 0x00
    SERCTRL R0

    ; ---- Transmit greeting ----------------------------------------
    MOV  P5, MSG_HELLO
send_hello:
    MOV  R0, [P5]        ; load byte from string
    CMP  R0, 0           ; null terminator?
    JZ   echo_init
    SEROUT R0            ; send byte over UART
    INC  P5              ; advance pointer
    JMP  send_hello

; ----------------------------------------------------------------
; Echo loop - reflect every received byte back to sender
; ----------------------------------------------------------------
echo_init:
    MOV  P6, 0           ; echo byte counter = 0
    MOV  P7, 0           ; idle iteration counter = 0

echo_loop:
    ; Poll UART status
    SERSTAT R0
    AND  R0, 0x01        ; isolate RX_AVAILABLE bit
    CMP  R0, 0
    JZ   no_rx_data      ; no data this iteration

    ; ---- Data available: read and reflect -------------------------
    SERIN  R0            ; read byte from RX FIFO
    SEROUT R0            ; echo it
    MOV  P7, 0           ; reset idle counter after any received byte
    INC  P6              ; count echoed bytes

    ; Exit if we have echoed 256 bytes
    CMP  P6, 0x100
    JGE  send_bye
    JMP  echo_loop

    ; ---- No data this iteration -----------------------------------
no_rx_data:
    INC  P7
    CMP  P7, 0xFFFF      ; 512 consecutive idle iterations -> timeout
    JLT  echo_loop
    ; fall through to farewell

; ----------------------------------------------------------------
; Send farewell and halt
; ----------------------------------------------------------------
send_bye:
    MOV  P5, MSG_BYE
bye_loop:
    MOV  R0, [P5]
    CMP  R0, 0
    JZ   halt
    SEROUT R0
    INC  P5
    JMP  bye_loop

halt:
    HLT

; ================================================================
; String constants
; ================================================================
MSG_HELLO: DEFSTR "Nova-16 UART Echo Server Ready\r\n"
MSG_BYE:   DEFSTR "Nova-16 UART Echo Server Halting\r\n"
