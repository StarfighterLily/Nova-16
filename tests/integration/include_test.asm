; Test INCLUDE directive
INCLUDE "include_sub.asm"

MAIN_DATA DB 4, 5
START:
    MOV R0, SUB_DATA
    MOV R1, MAIN_DATA
    HLT