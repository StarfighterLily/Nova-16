; Test timer interrupts specifically
ORG 0x1000

MAIN:
    STI              ; Enable interrupts
    MOV TT, 0        ; Set timer to 0
    MOV TM, 10       ; Trigger at 10 (small value for quick testing)
    MOV TS, 1        ; Set speed to 1 (slow)
    MOV TC, 3        ; Enable timer and interrupt
    MOV R0, 0        ; Counter
    
LOOP:
    INC R0           ; Increment counter
    CMP R0, 100      ; Compare with 100
    JNZ LOOP         ; If not equal, loop back
    HLT              ; Should halt after 100 increments

    
ORG 0x0100           ; Timer vector
    NOP              ; Simple no-op for timer interrupt
    IRET             ; Return from interrupt
