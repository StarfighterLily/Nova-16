; Primitive words

; DUP: duplicate top of stack
DUP_CODE:
    POP R0
    PUSH R0
    PUSH R0
    JMP NEXT

; DROP: remove top
DROP_CODE:
    POP R0
    JMP NEXT

; SWAP: exchange top two
SWAP_CODE:
    POP R0
    POP R1
    PUSH R0
    PUSH R1
    JMP NEXT

; + : add top two
ADD_CODE:
    POP R0
    POP R1
    ADD R0, R1
    PUSH R0
    JMP NEXT

; - : subtract
SUB_CODE:
    POP R0
    POP R1
    SUB R1, R0
    PUSH R1
    JMP NEXT

; EMIT: output char
EMIT_CODE:
    POP R0
    CHAR R0
    JMP NEXT

; KEY: input char
KEY_CODE:
    KEYIN R0
    PUSH R0
    JMP NEXT

; ENTER: for colon definitions
ENTER_CODE:
    PUSH_RS P4
    MOV P4, P5
    ADD P4, 2
    JMP NEXT

; * : multiply
MUL_CODE:
    POP R0
    POP R1
    MUL R0, R1
    PUSH R0
    JMP NEXT

; / : divide
DIV_CODE:
    POP R0
    POP R1
    DIV R1, R0
    PUSH R1
    JMP NEXT

; MOD : modulo
MOD_CODE:
    POP R0
    POP R1
    MOD R1, R0
    PUSH R1
    JMP NEXT

; OVER: duplicate second item
OVER_CODE:
    POP R0
    POP R1
    PUSH R1
    PUSH R0
    PUSH R1
    JMP NEXT

; ROT: rotate top three
ROT_CODE:
    POP R0
    POP R1
    POP R2
    PUSH R1
    PUSH R0
    PUSH R2
    JMP NEXT

; Dictionary entries
DUP_ENTRY:
    DW 0
    DB 3, "DUP"
    DW DUP_CODE

DROP_ENTRY:
    DW DUP_ENTRY
    DB 4, "DROP"
    DW DROP_CODE

SWAP_ENTRY:
    DW DROP_ENTRY
    DB 4, "SWAP"
    DW SWAP_CODE

ADD_ENTRY:
    DW SWAP_ENTRY
    DB 1, "+"
    DW ADD_CODE

SUB_ENTRY:
    DW ADD_ENTRY
    DB 1, "-"
    DW SUB_CODE

EMIT_ENTRY:
    DW SUB_ENTRY
    DB 4, "EMIT"
    DW EMIT_CODE

KEY_ENTRY:
    DW EMIT_ENTRY
    DB 3, "KEY"
    DW KEY_CODE

MUL_ENTRY:
    DW KEY_ENTRY
    DB 1, "*"
    DW MUL_CODE

DIV_ENTRY:
    DW MUL_ENTRY
    DB 1, "/"
    DW DIV_CODE

MOD_ENTRY:
    DW DIV_ENTRY
    DB 3, "MOD"
    DW MOD_CODE

OVER_ENTRY:
    DW MOD_ENTRY
    DB 4, "OVER"
    DW OVER_CODE

ROT_ENTRY:
    DW OVER_ENTRY
    DB 3, "ROT"
    DW ROT_CODE

; . : print top of stack as digit (add 48)
DOT_CODE:
    POP R0
    ADD R0, 48
    CHAR R0
    JMP NEXT

DOT_ENTRY:
    DW MOD_ENTRY
    DB 1, "."
    DW DOT_CODE

; CR: carriage return
CR_CODE:
    MOV R0, 10
    CHAR R0
    JMP NEXT

CR_ENTRY:
    DW DOT_ENTRY
    DB 2, "CR"
    DW CR_CODE

; EXIT: exit colon definition
EXIT_CODE:
    POP_RS P4
    JMP NEXT

EXIT_ENTRY:
    DW DOT_ENTRY
    DB 4, "EXIT"
    DW EXIT_CODE

; SQUARE: colon definition DUP *
SQUARE_ENTRY:
    DW EXIT_ENTRY
    DB 6, "SQUARE"
    DW ENTER_CODE
    DW DUP_ENTRY
    DW MUL_ENTRY
    DW EXIT_CODE

; FIND: find word by name, takes string addr, returns word addr or 0
FIND_CODE:
    POP R0        ; string addr
    MOV R1, P3    ; latest
FIND_LOOP:
    CMP R1, 0
    JZ FIND_NOT_FOUND
    ; compare names
    MOV R2, [R1+2] ; len
    MOV R3, [R0]   ; str len
    CMP R2, R3
    JNZ FIND_NEXT
    ; compare strings
    MOV R4, R1
    ADD R4, 3     ; name start
    MOV R5, R0
    INC R5        ; str start
    MOV R6, R2    ; len
FIND_CMP:
    CMP R6, 0
    JZ FIND_FOUND
    MOV R7, [R4]
    MOV R8, [R5]
    CMP R7, R8
    JNZ FIND_NEXT
    INC R4
    INC R5
    DEC R6
    JMP FIND_CMP
FIND_FOUND:
    PUSH R1
    JMP NEXT
FIND_NEXT:
    MOV R1, [R1]  ; link
    JMP FIND_LOOP
FIND_NOT_FOUND:
    PUSH 0
    JMP NEXT

FIND_ENTRY:
    DW SQUARE_ENTRY
    DB 4, "FIND"
    DW FIND_CODE

; LIT: push literal
LIT_CODE:
    MOV R0, [P4]
    ADD P4, 2
    PUSH R0
    JMP NEXT

LIT_ENTRY:
    DW FIND_ENTRY
    DB 3, "LIT"
    DW LIT_CODE

; = : equal
EQUAL_CODE:
    POP R0
    POP R1
    CMP R0, R1
    MOV R0, 0
    JNZ EQUAL_END
    MOV R0, 1
EQUAL_END:
    PUSH R0
    JMP NEXT

EQUAL_ENTRY:
    DW LIT_ENTRY
    DB 1, "="
    DW EQUAL_CODE