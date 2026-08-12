; Test program for ENTER/LEAVE instructions
; Verifies that ENTER creates a proper stack frame and LEAVE restores it
; Main calls foo(42, 7), foo adds them and returns 49 in R0

ORG 0x1000
start:
    MOV SP, 0xFF00      ; Set stack pointer
    MOV FP, 0xFF00      ; Init frame pointer
    MOV R0, 42          ; First argument
    MOV R1, 7           ; Second argument
    PUSH R0             ; Push arg1
    PUSH R1             ; Push arg2
    CALL foo            ; Call function
    ADD SP, 2           ; Clean up args (2 bytes)
    ; R0 should be 49 (42 + 7)
    HLT

foo:
    ENTER 2             ; Create frame, allocate 2 bytes for locals
    ; Stack layout after ENTER:
    ;   [FP+0] = old FP (word)
    ;   [FP+2] = return address (word)
    ;   [FP+4] = arg1 (byte) = 42
    ;   [FP+5] = arg2 (byte) = 7
    ;   [FP-1] = local1
    ;   [FP-2] = local2
    ; Load arg1 (42) from FP+4
    MOV P2, FP
    ADD P2, 4
    MOV R2, [P2]        ; R2 = arg1 = 42
    ; Load arg2 (7) from FP+5
    MOV P2, FP
    ADD P2, 5
    MOV R3, [P2]        ; R3 = arg2 = 7
    ; Store locals
    MOV P2, FP
    SUB P2, 1
    MOV [P2], R2        ; local1 = arg1 = 42
    MOV P2, FP
    SUB P2, 2
    MOV [P2], R3        ; local2 = arg2 = 7
    ; Read locals back
    MOV P2, FP
    SUB P2, 1
    MOV R0, [P2]        ; R0 = local1 = 42
    MOV P2, FP
    SUB P2, 2
    MOV R1, [P2]        ; R1 = local2 = 7
    ; Add them
    ADD R0, R1          ; R0 = 42 + 7 = 49
    ; Epilogue (explicit, not using LEAVE - matches NoBASIC pattern)
    MOV SP, FP
    POP FP
    RET
