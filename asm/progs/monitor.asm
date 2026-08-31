; WozMon-like Monitor Program for Nova-16
; Simple monitor for peeking and poking memory addresses
; Commands: P=Peek, W=Write, R=Read registers, Q=Quit

START:
    ; Initialize stack pointer and graphics
    MOV SP, 0xFFFF
    MOV VM, 0          ; Coordinate mode for graphics
    MOV VL, 0          ; Use layer 0
    MOV VC, 255        ; White color for text
    CALL CLEAR_SCREEN
    
MAIN_LOOP:
    ; Display prompt at position
    MOV VX, 10
    MOV VY, 10
    MOV P0, PROMPT_MSG
    CALL PRINT_STRING
    
    MOV VX, 10
    MOV VY, 20
    MOV P0, PROMPT_MSG2
    CALL PRINT_STRING
    
    MOV VX, 10
    MOV VY, 30
    MOV P0, PROMPT_MSG3
    CALL PRINT_STRING
    
    MOV VX, 10
    MOV VY, 40
    MOV P0, PROMPT_MSG4
    CALL PRINT_STRING
    
    ; Wait for key input
WAIT_KEY:
    KEYSTAT R0         ; Check if key available
    CMP R0, 0
    JZ WAIT_KEY        ; Loop until key pressed
    
    KEYIN R0           ; Read the key
    
    ; Check command
    CMP R0, 'P'        ; Peek command
    JZ CMD_PEEK
    CMP R0, 'p'
    JZ CMD_PEEK
    
    CMP R0, 'W'        ; Write command
    JZ CMD_WRITE
    CMP R0, 'w'
    JZ CMD_WRITE
    
    CMP R0, 'R'        ; Read registers command
    JZ CMD_REGS
    CMP R0, 'r'
    JZ CMD_REGS
    
    CMP R0, 'Q'        ; Quit command
    JZ CMD_QUIT
    CMP R0, 'q'
    JZ CMD_QUIT
    
    ; Invalid command - show error and loop
    CALL CLEAR_SCREEN
    MOV VX, 10
    MOV VY, 30
    MOV P0, ERROR_MSG
    CALL PRINT_STRING
    
    CALL DELAY
    CALL CLEAR_SCREEN
    JMP MAIN_LOOP

CMD_PEEK:
    ; Display peek prompt
    CALL CLEAR_SCREEN
    MOV VX, 10
    MOV VY, 20
    MOV P0, PEEK_MSG
    CALL PRINT_STRING
    
    ; Read 4-digit hex address from keyboard
    CALL READ_HEX_WORD
    MOV P1, P0         ; Save address in P1
    
    ; Read memory at address
    MOV R2, [P1]
    
    ; Display result
    MOV VX, 10
    MOV VY, 40
    MOV P0, VALUE_MSG
    CALL PRINT_STRING
    
    MOV R0, R2
    CALL PRINT_HEX_BYTE
    
    CALL DELAY
    CALL CLEAR_SCREEN
    JMP MAIN_LOOP

CMD_WRITE:
    ; Display write prompt
    CALL CLEAR_SCREEN
    MOV VX, 10
    MOV VY, 20
    MOV P0, WRITE_MSG
    CALL PRINT_STRING
    
    ; Read address
    CALL READ_HEX_WORD
    MOV P1, P0         ; Save address
    
    ; Read value
    MOV VX, 10
    MOV VY, 40
    MOV P0, WRITE_VAL_MSG
    CALL PRINT_STRING
    
    CALL READ_HEX_BYTE
    MOV R2, :P0        ; Get low byte
    
    ; Write to memory
    MOV [P1], R2
    
    ; Confirm
    MOV VX, 10
    MOV VY, 60
    MOV P0, DONE_MSG
    CALL PRINT_STRING
    
    CALL DELAY
    CALL CLEAR_SCREEN
    JMP MAIN_LOOP

CMD_REGS:
    ; Display register values
    CALL CLEAR_SCREEN
    MOV VX, 10
    MOV VY, 20
    MOV P0, REGS_MSG
    CALL PRINT_STRING
    
    ; Show R0-R4
    MOV VX, 10
    MOV VY, 40
    MOV P0, R0_LABEL
    CALL PRINT_STRING
    MOV R0, R0         ; R0 is already in R0 for display
    CALL PRINT_HEX_BYTE
    
    MOV VX, 10
    MOV VY, 50
    MOV P0, R1_LABEL
    CALL PRINT_STRING
    MOV R0, R1
    CALL PRINT_HEX_BYTE
    
    MOV VX, 10
    MOV VY, 60
    MOV P0, R2_LABEL
    CALL PRINT_STRING
    MOV R0, R2
    CALL PRINT_HEX_BYTE
    
    MOV VX, 10
    MOV VY, 70
    MOV P0, R3_LABEL
    CALL PRINT_STRING
    MOV R0, R3
    CALL PRINT_HEX_BYTE
    
    ; Show PC and SP
    MOV VX, 10
    MOV VY, 90
    MOV P0, SP_LABEL
    CALL PRINT_STRING
    CALL PRINT_HEX_WORD_P0
    
    ; Wait for key press
    MOV VX, 10
    MOV VY, 110
    MOV P0, CONTINUE_MSG
    CALL PRINT_STRING
    
WAIT_REG_KEY:
    KEYSTAT R0
    CMP R0, 0
    JZ WAIT_REG_KEY
    KEYIN R0           ; Clear the key
    
    CALL DELAY
    CALL CLEAR_SCREEN
    JMP MAIN_LOOP

CMD_QUIT:
    ; Clear screen and halt
    CALL CLEAR_SCREEN
    MOV VX, 100
    MOV VY, 100
    MOV P0, QUIT_MSG
    CALL PRINT_STRING
    HLT

; ===== Subroutines =====

CLEAR_SCREEN:
    ; Fill screen with black (color 0)
    MOV VC, 0
    SFILL 0
    MOV VC, 255        ; Restore white color for text
    RET

PRINT_STRING:
    ; P0 = address of null-terminated string
    ; VX, VY = position (must be set before call)
PRINT_LOOP:
    MOV R0, [P0]       ; Load character
    CMP R0, 0          ; Check for null terminator
    JZ PRINT_DONE
    
    CHAR R0            ; Draw character at VX, VY (CHAR auto-advances VX by 8)
    INC P0             ; Next character
    JMP PRINT_LOOP
    
PRINT_DONE:
    RET

READ_HEX_WORD:
    ; Read 4 hex digits from keyboard, return in P0
    ; Returns 16-bit value in P0
    MOV P0, 0
    MOV R3, 0          ; Digit counter
    
READ_WORD_LOOP:
    KEYSTAT R0
    CMP R0, 0
    JZ READ_WORD_LOOP
    
    KEYIN R0           ; Get character
    
    ; Convert ASCII hex to value
    CMP R0, '0'
    JLT READ_WORD_LOOP ; Invalid char
    CMP R0, '9'
    JLE DIGIT_0_9
    
    CMP R0, 'A'
    JLT READ_WORD_LOOP
    CMP R0, 'F'
    JLE DIGIT_A_F
    
    CMP R0, 'a'
    JLT READ_WORD_LOOP
    CMP R0, 'f'
    JGT READ_WORD_LOOP
    
    ; Convert a-f
    SUB R0, 'a'
    ADD R0, 10
    JMP ADD_DIGIT
    
DIGIT_A_F:
    ; Convert A-F
    SUB R0, 'A'
    ADD R0, 10
    JMP ADD_DIGIT
    
DIGIT_0_9:
    ; Convert 0-9
    SUB R0, '0'
    
ADD_DIGIT:
    ; Shift P0 left 4 bits and add new digit
    SHL P0, 4
    OR :P0, R0         ; OR into low byte
    
    INC R3
    CMP R3, 4          ; Got 4 digits?
    JLT READ_WORD_LOOP
    
    RET

READ_HEX_BYTE:
    ; Read 2 hex digits from keyboard, return in P0 (low byte)
    MOV P0, 0
    MOV R3, 0
    
READ_BYTE_LOOP:
    KEYSTAT R0
    CMP R0, 0
    JZ READ_BYTE_LOOP
    
    KEYIN R0
    
    ; Convert ASCII hex to value
    CMP R0, '0'
    JLT READ_BYTE_LOOP
    CMP R0, '9'
    JLE BYTE_0_9
    
    CMP R0, 'A'
    JLT READ_BYTE_LOOP
    CMP R0, 'F'
    JLE BYTE_A_F
    
    CMP R0, 'a'
    JLT READ_BYTE_LOOP
    CMP R0, 'f'
    JGT READ_BYTE_LOOP
    
    SUB R0, 'a'
    ADD R0, 10
    JMP ADD_BYTE_DIGIT
    
BYTE_A_F:
    SUB R0, 'A'
    ADD R0, 10
    JMP ADD_BYTE_DIGIT
    
BYTE_0_9:
    SUB R0, '0'
    
ADD_BYTE_DIGIT:
    SHL :P0, 4
    OR :P0, R0
    
    INC R3
    CMP R3, 2
    JLT READ_BYTE_LOOP
    
    RET

PRINT_HEX_BYTE:
    ; Print R0 as 2-digit hex at current VX, VY
    PUSH R1
    MOV R1, R0
    SHR R1, 4          ; Get high nibble
    AND R1, 0x0F
    
    ; Convert to ASCII
    CMP R1, 10
    JLT PRINT_DIGIT1
    ADD R1, 'A'
    SUB R1, 10
    JMP SHOW_DIGIT1
    
PRINT_DIGIT1:
    ADD R1, '0'
    
SHOW_DIGIT1:
    CHAR R1
    ADD VX, 8
    
    ; Low nibble
    MOV R1, R0
    AND R1, 0x0F
    
    CMP R1, 10
    JLT PRINT_DIGIT2
    ADD R1, 'A'
    SUB R1, 10
    JMP SHOW_DIGIT2
    
PRINT_DIGIT2:
    ADD R1, '0'
    
SHOW_DIGIT2:
    CHAR R1
    POP R1
    RET

PRINT_HEX_WORD_P0:
    ; Print P0 as 4-digit hex at current VX, VY
    PUSH R0
    MOV R0, P0:        ; Get high byte of P0
    CALL PRINT_HEX_BYTE
    MOV R0, :P0        ; Get low byte of P0
    CALL PRINT_HEX_BYTE
    POP R0
    RET

DELAY:
    ; Longer delay loop using 16-bit counter (~5-10 seconds)
    MOV P3, 0xFFFF
DELAY_LOOP:
    DEC P3
    CMP P3, 0
    JNZ DELAY_LOOP
    RET

; ===== String Data =====
PROMPT_MSG:     DB "Commands:", 0
PROMPT_MSG2:    DB "P = Peek Address", 0
PROMPT_MSG3:    DB "W = Write to Address", 0
PROMPT_MSG4:    DB "R = Registers  Q = Quit", 0
ERROR_MSG:      DB "Invalid command!", 0
PEEK_MSG:       DB "Enter address (hex):", 0
VALUE_MSG:      DB "Value: ", 0
WRITE_MSG:      DB "Enter address (hex):", 0
WRITE_VAL_MSG:  DB "Enter value (hex):", 0
DONE_MSG:       DB "Written!", 0
REGS_MSG:       DB "Registers:", 0
R0_LABEL:       DB "R0: ", 0
R1_LABEL:       DB "R1: ", 0
R2_LABEL:       DB "R2: ", 0
R3_LABEL:       DB "R3: ", 0
SP_LABEL:       DB "SP: ", 0
CONTINUE_MSG:   DB "Press any key...", 0
QUIT_MSG:       DB "Monitor halted.", 0
