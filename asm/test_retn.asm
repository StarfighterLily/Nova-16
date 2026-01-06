; Test RETN - return with value

ORG 0x0000

    CALL subroutine         ; Call subroutine
    
    ; Should return here with R0 = 0x42
    MOV P0, R0              ; P0 = return value
    JMP done

subroutine:
    MOV R0, 0x42            ; R0 = return value
    RETN R0                 ; Return with value
    
    MOV P1, 0xFFFF          ; Should not reach
    RET

done:
    HLT
