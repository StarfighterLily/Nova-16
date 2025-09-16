; Stack Operations Test Program
; Tests basic stack functionality with SP and FP registers

ORG 0x1000
STI

; Initialize registers
MOV P0, 0x1111
MOV P1, 0x2222
MOV P2, 0x3333
MOV R0, 0xAA
MOV R1, 0xBB

; Test basic PUSH/POP
PUSH P0        ; Push 0x1111 onto stack
PUSH P1        ; Push 0x2222 onto stack
POP P3         ; Pop 0x2222 into P3
POP P4         ; Pop 0x1111 into P4

; Verify results (P3 should be 0x2222, P4 should be 0x1111)
; In a real test, we'd check these values

; Test PUSHF/POPF
MOV R0, 0x0F   ; Set some flags by doing operations
CMP R0, R1     ; This sets flags
PUSHF          ; Push flags onto stack
POPF           ; Pop flags from stack

; Test PUSHA/POPA
PUSHA          ; Push all registers
POPA           ; Pop all registers

; Test function call
CALL test_function

; Test interrupt simulation
INT 0          ; Software interrupt to vector 0

done:
HLT

; Test function
test_function:
    PUSH FP        ; Save frame pointer
    MOV FP, SP     ; Set new frame pointer

    ; Allocate local variables (simulate stack frame)
    PUSH P0        ; Save P0
    PUSH P1        ; Save P1

    ; Function body - modify locals
    MOV P0, 0x4444
    MOV P1, 0x5555

    POP P1         ; Restore P1
    POP P0         ; Restore P0

    MOV SP, FP     ; Restore stack pointer
    POP FP         ; Restore frame pointer
    RET

; Interrupt handler (at vector 0x0100)
ORG 0x0100
interrupt_handler:
    PUSH R0        ; Save working register

    ; Handle interrupt (just return for test)
    MOV R0, 0x01   ; Set a flag or something

    POP R0         ; Restore register
    IRET           ; Return from interrupt
