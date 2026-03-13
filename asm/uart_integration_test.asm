; UART integration test for Nova-16
; Verifies SERCTRL, SEROUT, SERSTAT, and SERIN integration path.
; PASS marker: P0 = 0xBEEF
; FAIL marker: P0 = 0xDEAD

ORG 0x1000

START:
    MOV P0, 0xDEAD      ; Default to failure until all checks pass

    ; Enable serial interrupt control bit (bit 0)
    SERCTRL 0x01

    ; Transmit one byte and verify TX-complete status
    SEROUT 0x41         ; 'A'
    SERSTAT R1
    AND R1, 0x02
    CMP R1, 0x02        ; TX complete expected
    JNZ FAIL

    ; Read data path and verify returned byte
    SERIN R2
    CMP R2, 0x41
    JNZ FAIL

    MOV P0, 0xBEEF      ; PASS
    HLT

FAIL:
    MOV P0, 0xDEAD      ; FAIL
    HLT
