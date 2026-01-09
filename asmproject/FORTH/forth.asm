; FORTH Interpreter for Nova-16
; Main entry point and includes

EQU DUP_TOKEN, 0
EQU DROP_TOKEN, 1
EQU SWAP_TOKEN, 2
EQU ADD_TOKEN, 3
EQU SUB_TOKEN, 4
EQU EMIT_TOKEN, 5
EQU KEY_TOKEN, 6
EQU ENTER_TOKEN, 7
EQU MUL_TOKEN, 8
EQU DIV_TOKEN, 9
EQU MOD_TOKEN, 10

EQU DS_BASE, 0xF000
EQU RS_BASE, 0xE000

ORG 0x0000

INPUT_BUFFER: DS 80

; Initialize system
MOV P8, 0xF000  ; DS_SP
MOV P1, 0xE000  ; RS_SP
MOV P3, EQUAL_ENTRY  ; last word
MOV P2, 0  ; is_compiling
MOV P0, 0xD000  ; compile ptr

; Push test data: 5
SUB P8, 2
MOV [P8], 5

JMP INTERPRETER

NEXT:
    MOV P5, [P4]      ; P5 = word address
    ADD P4, 2         ; advance IP
    CMP P5, 0
    JMP HALT
    MOV R0, [P5+2]    ; len
    ADD R0, 3         ; offset to code field
    ADD P5, R0        ; P5 = address of code field
    MOV P5, [P5]      ; P5 = code address
    JMP P5

HALT:
    HLT

INTERPRETER:
    ; Read input line
    MOV P6, INPUT_BUFFER
READ_LOOP:
    KEYIN R0
    CMP R0, 10  ; enter
    JZ PARSE_LINE
    MOV [P6], R0
    INC P6
    JMP READ_LOOP

PARSE_LINE:
    MOV [P6], 0  ; null terminate line
    MOV P6, INPUT_BUFFER

PARSE_WORD_LOOP:
    ; Skip spaces
    MOV R0, [P6]
    CMP R0, 0
    JZ INTERPRETER
    CMP R0, 32
    JNZ FOUND_WORD_START
    INC P6
    JMP PARSE_WORD_LOOP

FOUND_WORD_START:
    MOV P7, P6  ; start
FIND_WORD_END:
    MOV R0, [P7]
    CMP R0, 0
    JZ PROCESS_WORD
    CMP R0, 32
    JZ PROCESS_WORD
    INC P7
    JMP FIND_WORD_END

PROCESS_WORD:
    MOV R0, [P7]  ; save original char
    MOV [P7], 0  ; temp null terminate
    ; Check for :
    MOV R1, P6
    MOV R2, [R1]
    CMP R2, 58
    JNZ CHECK_SEMI
    ; Handle :
    INC P6 ; skip :
    ; Skip spaces
SKIP_SPACES_COLON:
    MOV R2, [P6]
    CMP R2, 0
    JZ INTERPRETER
    CMP R2, 32
    JNZ FOUND_NAME_COLON
    INC P6
    JMP SKIP_SPACES_COLON
FOUND_NAME_COLON:
    MOV P7, P6
FIND_END_COLON:
    MOV R2, [P7]
    CMP R2, 0
    JZ GOT_NAME_COLON
    CMP R2, 32
    JZ GOT_NAME_COLON
    INC P7
    JMP FIND_END_COLON
GOT_NAME_COLON:
    MOV R2, [P7]
    MOV [P7], 0
    ; Create entry
    MOV R1, P0 ; entry addr
    MOV [R1], P3 ; link
    MOV R3, P7
    SUB R3, P6 ; len
    MOV [R1+2], R3
    MOV R4, R1
    ADD R4, 3
    MOV R5, P6
COPY_LOOP:
    CMP R3, 0
    JZ COPY_DONE
    MOV R6, [R5]
    MOV [R4], R6
    INC R4
    INC R5
    DEC R3
    JMP COPY_LOOP
COPY_DONE:
    MOV [R4], ENTER_CODE
    ADD R4, 2
    MOV P0, R4
    MOV P3, R1
    MOV P2, 1
    MOV [P7], R2
    JMP PARSE_WORD_LOOP
CHECK_SEMI:
    CMP R2, 59
    JNZ NORMAL_PROCESS
    ; Handle ;
    CMP P2, 0
    JZ NORMAL_PROCESS ; or error
    MOV [P0], EXIT_CODE
    ADD P0, 2
    MOV P2, 0
    MOV [P7], R2
    JMP PARSE_WORD_LOOP
NORMAL_PROCESS:
    ; Push addr
    PUSH P6
    ; Call FIND
    MOV R1, TEMP_IP
    MOV [R1], FIND_ENTRY
    MOV [R1+2], NUMBER_OR_EXEC
    JMP NEXT

TEMP_IP:
    DW 0, 0

NUMBER_OR_EXEC:
    ; After FIND, top of stack is word addr or 0
    POP R0
    CMP R0, 0
    JNZ EXEC_WORD
    ; Try parse number
    ; P6 is string addr
    ; Simple: assume decimal, convert
    MOV R1, 0  ; number
    MOV R2, P6
PARSE_NUM:
    MOV R3, [R2]
    CMP R3, 0
    JZ PUSH_NUM
    SUB R3, 48
    MUL R1, 10
    ADD R1, R3
    INC R2
    JMP PARSE_NUM
PUSH_NUM:
    CMP P2, 0
    JZ PUSH_NUM_INTERP
    ; compile literal
    MOV [P0], LIT_ENTRY
    ADD P0, 2
    MOV [P0], R1
    ADD P0, 2
    JMP RESTORE_NULL
PUSH_NUM_INTERP:
    PUSH R1
    JMP RESTORE_NULL

EXEC_WORD:
    CMP P2, 0
    JZ EXEC_WORD_INTERP
    ; compile word
    MOV [P0], R0
    ADD P0, 2
    JMP RESTORE_NULL
EXEC_WORD_INTERP:
    ; Set P4 to word addr, JMP NEXT
    MOV P4, R0
    JMP NEXT

RESTORE_NULL:
    MOV [P7], R0  ; restore space or 0
    MOV P6, P7
    INC P6
    JMP PARSE_WORD_LOOP

; Change initial jump
MOV P4, INTERPRETER
JMP NEXT

INCLUDE "macros.inc"
INCLUDE "stacks.inc"
INCLUDE "dict.inc"
INCLUDE "primitives.inc"