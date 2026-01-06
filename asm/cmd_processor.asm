ORG 0x0200

; Initialize graphics
MOV VM, 0          ; Coordinate mode (VX,VY = x,y)
MOV VL, 0          ; Layer 0
MOV VC, 0x1F       ; Red color

; Initialize variables
MOV P0, 0          ; Cursor X
MOV P1, 0          ; Cursor Y
MOV P2, 0x0300     ; Buffer pointer
MOV P3, 0          ; Buffer length

; Main loop
main_loop:
    CALL show_cursor

    ; Wait for key
wait_key:
    KEYSTAT R0
    CMP R0, 0
    JZ wait_key

    KEYIN R0

    CALL hide_cursor

    ; Process key
    CMP R0, 13       ; Enter
    JZ process_command
    CMP R0, 8        ; Backspace
    JZ backspace
    CMP R0, 32       ; Space or higher (printable)
    JC wait_key      ; Ignore non-printable

    ; Add to buffer
    MOV R1, P3
    MOV P4, 0x0300
    ADD P4, R1
    MOV [P4], R0
    INC P3

    JMP main_loop

backspace:
    CMP P3, 0
    JZ main_loop
    DEC P3
    JMP main_loop

process_command:
    ; Remove cursor
    MOV R1, P3
    MOV P4, 0x0300
    ADD P4, R1
    MOV [P4], 0

    ; Display result (echo)
    MOV VX, 0
    MOV VY, 0
    TEXT 0x0300

    ; Delay
    MOV TT, 0
    MOV TM, 1000
    MOV TS, 1
    MOV TC, 1
delay_loop:
    CMP TT, TM
    JNZ delay_loop

    ; Clear screen
    CALL clear_screen

    ; Reset buffer
    MOV P3, 0
    MOV P4, 0x0300
    MOV [P4], '_'
    INC P4
    MOV [P4], 0

    JMP main_loop

    ; Delay
    MOV TT, 0
    MOV TM, 1000
    MOV TS, 1
    MOV TC, 1
delay_loop:
    CMP TT, TM
    JNZ delay_loop

    ; Clear screen
    CALL clear_screen

    ; Reset buffer
    MOV P3, 0
    MOV P0, 0x0300
    MOV [P0], '_'
    INC P0
    MOV [P0], 0

    JMP main_loop

show_cursor:
    MOV VX, 0
    MOV VY, 0
    MOV R0, P3
    MOV P4, 0x0300
    ADD P4, R0
    MOV [P4], '_'
    INC P4
    MOV [P4], 0
    TEXT 0x0300
    RET

hide_cursor:
    MOV VX, 0
    MOV VY, 0
    MOV R0, P3
    MOV P4, 0x0300
    ADD P4, R0
    MOV [P4], 0
    TEXT 0x0300
    RET

clear_screen:
    MOV VC, 0        ; Black
    MOV VX, 0
    MOV VY, 0
clear_loop:
    SWRITE
    INC VX
    CMP VX, 320
    JNZ clear_loop
    MOV VX, 0
    INC VY
    CMP VY, 200
    JNZ clear_loop
    RET

; Interrupt vectors removed