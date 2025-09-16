; Nova-16 Monitor Program v2.0 (WozMon-inspired)
; Commands:
;   AAAA      - Examine memory at address AAAA (hex)
;   AAAA.BBBB - Examine memory range AAAA to BBBB  
;   AAAA:DD   - Store byte DD at address AAAA
;   R AAAA    - Run program at address AAAA
;   ESC       - Exit monitor

ORG 0x2000

MONITOR_START:
    STI                 ; Enable interrupts
    MOV VM, 0           ; Coordinate mode
    MOV VX, 0           ; X = 0
    MOV VY, 0           ; Y = 0  
    MOV R0, 0x0F        ; White color
    
    ; Initialize memory pointer for dumps
    MOV P3, 0x1000      ; Starting memory address for dumps
    
    ; Show banner
    TEXT BANNER, R0
    MOV VY, 16          ; Next line
    MOV VX, 0
    
    ; Show help
    TEXT HELP1, R0
    MOV VY, 24
    MOV VX, 0
    TEXT HELP2, R0
    MOV VY, 32
    MOV VX, 0
    TEXT HELP3, R0
    MOV VY, 48
    MOV VX, 0
    
    ; Show prompt
PROMPT:
    MOV VX, 0
    TEXT PROMPT_STR, R0
    MOV VX, 32          ; Position after ">"
    
    ; Clear input buffer
    MOV P0, 0           ; Input buffer pointer
    MOV P1, INPUT_BUF   ; Input buffer address

INPUT_LOOP:
    KEYSTAT R1
    CMP R1, 0
    JZ INPUT_LOOP
    
    KEYIN R2
    
    ; Check for special keys
    MOV R3, 0x1B        ; ESC
    CMP R2, R3
    JZ EXIT_MONITOR
    
    MOV R3, 0x0A        ; Enter/Return
    CMP R2, R3
    JZ PROCESS_COMMAND
    
    MOV R3, 0x08        ; Backspace
    CMP R2, R3
    JZ HANDLE_BACKSPACE
    
    ; Regular character - add to buffer and display
    CMP R2, 0x20        ; Space
    JLT INPUT_LOOP      ; Ignore control chars
    
    CMP R2, 0x7E        ; Tilde
    JGT INPUT_LOOP      ; Ignore extended chars
    
    ; Display character (we'll skip storing for now)
    CHAR R2, R0
    ADD VX, 8
    
    ; Increment buffer pointer
    INC P0
    CMP P0, 20          ; Max input length
    JLT INPUT_LOOP      ; Continue if not full
    
    ; Buffer full - ignore further input
    JMP INPUT_LOOP

HANDLE_BACKSPACE:
    CMP P0, 0           ; At start of line?
    JZ INPUT_LOOP      ; Yes, ignore backspace
    
    DEC P0              ; Back up buffer pointer
    SUB VX, 8           ; Back up cursor
    MOV R2, 0x20        ; Space character
    CHAR R2, R0         ; Erase character
    SUB VX, 8           ; Back up cursor again
    JMP INPUT_LOOP

PROCESS_COMMAND:
    ; Move to next line
    ADD VY, 8
    MOV VX, 0
    
    ; Parse command - check if empty command (just continue dump)
    CMP P0, 0
    JZ CONTINUE_DUMP
    
    ; If user typed anything (P0 > 0), cycle through addresses
    ; Simplified: any input will cycle the address
    JMP PARSE_HEX_ADDR  ; Always parse if there's input
    
CONTINUE_DUMP:
    ; Simple hex dump command: show memory starting at current address
    TEXT ADDR_STR, R0
    MOV VX, 48          ; Set X position for address display
    
    ; Use current memory pointer
    MOV P4, P3          ; P3 holds current address
    CALL HEX_OUT_16     ; Output address in hex
    JMP DUMP_MEM
    
PARSE_HEX_ADDR:
    ; Simple address cycling for now - will implement full hex parsing later
    ; If user typed anything, cycle to next common address
    MOV P6, P3          ; Get current address (using P6 to avoid P2/P1 conflicts)
    CMP P6, 0x1000      ; Currently at 0x1000?
    JZ GOTO_2000       ; Yes, go to 0x2000
    CMP P6, 0x2000      ; Currently at 0x2000?  
    JZ GOTO_3000       ; Yes, go to 0x3000
    ; Otherwise go to 0x1000
    MOV P3, 0x1000
    JMP CONTINUE_DUMP
    
GOTO_2000:
    MOV P3, 0x2000
    JMP CONTINUE_DUMP
    
GOTO_3000:
    MOV P3, 0x3000
    JMP CONTINUE_DUMP
    
DUMP_MEM:
    
    MOV R2, 0x3A        ; ':'
    CHAR R2, R0
    ADD VX, 8
    
    ; Move to next line before showing bytes
    ADD VY, 8           ; Move down one line
    MOV VX, 16          ; Set consistent indentation for all bytes
    
    ; Show 8 bytes of memory
    MOV R1, 8           ; Counter
    MOV R4, P3          ; R4 = current memory address to read

DUMP_LOOP:
    ; Display each byte on its own line to prevent wrapping
    ; All bytes should have the same indentation
    MOV R2, 0x20        ; Space
    CHAR R2, R0
    ADD VX, 8
    MOV R2, 0x20        ; Another space  
    CHAR R2, R0
    ADD VX, 8
    
    ; For now, just show dummy data based on address
    MOV R3, P3          ; Get current address
    ADD R3, 8           ; Add 8
    SUB R3, R1          ; Subtract counter (R1 counts down from 8 to 1)
    AND R3, 0xFF        ; Keep as byte value
    CALL HEX_OUT_8      ; Output byte in hex (expects value in R3)
    
    ; Move to next line for each byte
    ADD VY, 8           ; Move down one line
    MOV VX, 16          ; Reset to SAME position (consistent indentation)
    
    ADD R4, 1           ; Next memory address
    DEC R1              ; Decrement counter
    CMP R1, 0
    JNZ DUMP_LOOP
    
    ; Update address for next dump and wrap to new line
    ADD P3, 8           ; Advance address by 8 bytes for next time
    ADD VY, 12          ; Move to next line (bigger gap for clarity)
    MOV VX, 0           ; Reset to left margin
    
    ; Check if we're getting close to bottom of screen
    CMP VY, 180         ; If Y > 180, scroll or reset
    JLT PROMPT          ; If still room, continue
    MOV VY, 50          ; Reset to near top, leaving room for header
    JMP PROMPT

; Output 16-bit hex value in P2
HEX_OUT_16:
    ; Display high byte first (upper 2 hex digits)
    MOV R3, P4          ; Copy value from P4 to R3 (gets low byte only)
    MOV P5, P4          ; Copy full 16-bit value to P5
    DIV P5, 256         ; Divide P5 by 256 to get high byte
    MOV R3, P5          ; Move result to R3
    CALL HEX_OUT_8      ; Output high byte as hex
    
    ; Display low byte (lower 2 hex digits)  
    MOV R3, P4          ; Copy original low byte from P4
    CALL HEX_OUT_8      ; Output low byte as hex
    RET

; Output 8-bit hex value in R3
HEX_OUT_8:
    ; Show the high nibble (upper 4 bits)
    MOV R2, R3
    AND R2, 0xF0        ; Get high nibble
    SHR R2              ; Shift right 4 times
    SHR R2
    SHR R2
    SHR R2
    CMP R2, 10
    JLT SHOW_DIGIT2
    ADD R2, 0x37        ; A-F (0x37 + 10 = 0x41 = 'A')
    JMP SHOW_HEX_CHAR2
SHOW_DIGIT2:
    ADD R2, 0x30        ; 0-9
SHOW_HEX_CHAR2:
    CHAR R2, R0
    ADD VX, 8
    
    ; Show the low nibble (lower 4 bits)
    MOV R2, R3
    AND R2, 0x0F        ; Get low nibble
    CMP R2, 10
    JLT SHOW_DIGIT3
    ADD R2, 0x37        ; A-F
    JMP SHOW_HEX_CHAR3
SHOW_DIGIT3:
    ADD R2, 0x30        ; 0-9
SHOW_HEX_CHAR3:
    CHAR R2, R0
    ADD VX, 8
    RET

EXIT_MONITOR:
    ; Clear screen and show exit message
    MOV VY, 200
    MOV VX, 0
    TEXT EXIT_STR, R0
    HLT

; Data section
BANNER:     DEFSTR "Nova-16 Monitor v2.0"
HELP1:      DEFSTR "AAAA - examine memory"
HELP2:      DEFSTR "AAAA:DD - store byte"  
HELP3:      DEFSTR "ESC - exit"
PROMPT_STR: DEFSTR "> "
ADDR_STR:   DEFSTR "Addr: "
EXIT_STR:   DEFSTR "Monitor Exit"

; Input buffer space
INPUT_BUF: DEFSTR "                    "
