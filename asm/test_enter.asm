; Test ENTER instruction - stack frame creation
; Expected: FP pushed, SP adjusted for local variables

ORG 0x0000

    ; Setup initial state
    MOV P0, 24              ; Frame size = 24
    MOV P8, 0xFFF0          ; Set SP
    MOV P9, 0x2000          ; Set FP
    
    ; Call ENTER with register operand
    ENTER P0                ; Push FP, allocate 24 bytes
    
    ; Verify:
    ; SP should be 0xFFF0 - 2 - 24 = 0xFFD4
    ; FP should be 0xFFF0 - 2 = 0xFFEE
    MOV P1, P8              ; P1 = final SP
    MOV P2, P9              ; P2 = final FP
    
    HLT
