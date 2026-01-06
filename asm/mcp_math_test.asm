; MCP Math Test Program for Nova-16
; Performs basic arithmetic and stores results in memory for validation
;
; Memory layout for results (starting at 0x0120):
;   0x0120: R0 = 25 + 17 = 42
;   0x0121: R2 = 100 - R0 = 58
;   0x0122: R3 = 6 * 7 = 42 (low byte)
;   0x0123: R5 = 100 / 2 = 50 (quotient)
;   0x0124-0x0125: P1 = 0xABCD (word test)

    ; Addition: 25 + 17 = 42
    MOV R0, 25
    MOV R1, 17
    ADD R0, R1
    MOV [0x0120], R0

    ; Subtraction: 100 - 42 = 58
    MOV R2, 100
    SUB R2, R0
    MOV [0x0121], R2

    ; Multiplication: 6 * 7 = 42 (low byte)
    MOV R3, 6
    MOV R4, 7
    MUL R3, R4
    MOV [0x0122], R3

    ; Division: 100 / 2 = 50 (quotient)
    MOV R5, 100
    MOV R6, 2
    DIV R5, R6
    MOV [0x0123], R5

    ; Word write test
    MOV P1, 0xABCD
    MOV [0x0124], P1

    HLT
