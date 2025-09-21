ORG 0x1000

START:
    MOV R0, 0
    MOV R1, 0
    MOV R2, 0
    MOV R3, 255
    MOV R4, 0

LOOP:
    SLINE R0, R1, R2, R3, R4
    CMP R2, 255
    JGE DONE
    ADD R2, 1
    INC R4
    JMP LOOP

DONE:
    HLT