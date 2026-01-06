; Test CALLZ instruction - call when zero flag IS set
; Expected: Call executes because Z flag is set

ORG 0x0000

    MOV P0, 0               ; P0 = 0
    CMP P0, P0              ; Compare 0 with 0 - sets Z flag
    
    MOV P1, subroutine_yes
    CALLZ P1                ; Call if Z (should execute)
    
    ; Continue here if call worked
    MOV P2, 0x0001          ; Mark success
    JMP done

subroutine_yes:
    MOV P3, 0xAAAA          ; Mark subroutine was called
    RET

done:
    HLT
