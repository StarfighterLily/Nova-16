ORG 0x1000

START:
    STI
    MOV R0, 0x1F
    MOV VX, 0
    MOV VY, 0
    MOV VM, 0
    MOV TT, 0
    MOV TM, 255
    MOV TS, 128
    MOV TC, 3        ; Enable timer (bit 0) AND timer interrupts (bit 1)

MAIN:
    NOP
    JMP MAIN

DO:
    TEXT STR, R0    ; Print string at STR address with color in R0
    INC R0
    IRET

STR: DEFSTR "This is a very long string test to test the string wrapping functionality of the Nova-16 system."

ORG 0x0100
    DW DO