; Test CALLZ - when Z flag is NOT set

ORG 0x0000

    MOV P0, 1               ; P0 = 1
    CMP P0, 0               ; Compare 1 != 0 - clears Z flag
    
    MOV P1, subroutine_no
    CALLZ P1                ; Call if Z (should skip)
    
    ; Should reach here (call skipped)
    MOV P1, 0x0002          ; Mark success
    JMP done

subroutine_no:
    MOV P2, 0xBBBB          ; Should NOT be set
    RET

done:
    HLT
