; Test CALLNZ - when Z flag IS set

ORG 0x0000

    MOV P0, 0               ; P0 = 0
    CMP P0, P0              ; Compare 0 == 0 - sets Z flag
    
    MOV P1, subroutine_no
    CALLNZ P1               ; Call if NZ (should skip)
    
    ; Should reach here
    MOV P1, 0x0004          ; Mark success
    JMP done

subroutine_no:
    MOV P2, 0xDDDD          ; Should NOT be set
    RET

done:
    HLT
