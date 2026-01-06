; Test CALLNZ - call when Z flag is NOT set

ORG 0x0000

    MOV P0, 5               ; P0 = 5
    CMP P0, 0               ; Compare 5 != 0 - clears Z flag
    
    MOV P1, subroutine_yes
    CALLNZ P1               ; Call if NZ (should execute)
    
    ; Continue here
    MOV P1, 0x0003          ; Mark success
    JMP done

subroutine_yes:
    MOV P2, 0xCCCC          ; Mark subroutine was called
    RET

done:
    HLT
