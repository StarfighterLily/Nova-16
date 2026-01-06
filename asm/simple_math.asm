; Simple Math Program for Nova-16
; Demonstrates basic arithmetic operations
; Results stored in registers R0-R4

    ; Addition: 25 + 17 = 42
    MOV R0, 25
    MOV R1, 17
    ADD R0, R1          ; R0 = 42

    ; Subtraction: 100 - 42 = 58
    MOV R2, 100
    SUB R2, R0          ; R2 = 58

    ; Multiplication: 6 * 7 = 42
    MOV R3, 6
    MOV R4, 7
    MUL R3, R4          ; R3 = 42 (low byte)

    ; Division: 100 / 2 = 50
    MOV R5, 100
    MOV R6, 2
    DIV R5, R6          ; R5 = 50 (quotient)

    ; Store final result in P0 (16-bit)
    MOV :P0, R0         ; P0 low byte = 42
    MOV P0:, R2         ; P0 high byte = 58
                        ; P0 = 0x3A2A (58 << 8 | 42 = 14890)

    HLT                 ; Stop execution
