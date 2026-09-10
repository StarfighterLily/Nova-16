; NovaDOS — Parser Utilities
; Whitespace/token handling and decimal/hex number parsing.
; All comparisons are unsigned (JC = "value < threshold" after CMP).

; ---------------------------------------------------------------------------
; SKIP_SPACE — advance P0 past spaces/tabs (not past the null terminator).
; Clobbers R0.
; ---------------------------------------------------------------------------
SKIP_SPACE:
    MOV R0, [P0]
    CMP R0, 0x20        ; space
    JZ SKIP_ADV
    CMP R0, 0x09        ; tab
    JZ SKIP_ADV
    RET
SKIP_ADV:
    INC P0
    JMP SKIP_SPACE

; ---------------------------------------------------------------------------
; TOKENIZE — copy the next whitespace-delimited token from [P0] to [P1].
; Output: R0 = token length; P0 = first char after the token.
; Clobbers R0, R2, P0, P1.
; ---------------------------------------------------------------------------
TOKENIZE:
    CALL SKIP_SPACE
    MOV R0, 0
TOK_LOOP:
    MOV R2, [P0]
    CMP R2, 0
    JZ TOK_DONE
    CMP R2, 0x20
    JZ TOK_DONE
    CMP R2, 0x09
    JZ TOK_DONE
    MOV [P1], R2
    INC P0
    INC P1
    INC R0
    JMP TOK_LOOP
TOK_DONE:
    MOV R2, 0
    MOV [P1], R2        ; null-terminate the token
    RET

; ---------------------------------------------------------------------------
; PARSE_UINT8 — parse an ASCII decimal byte from [P0].
; Input: P0 = buffer, R1 = max chars. Output: R0 = value, R2 = chars consumed.
; Clobbers R0-R4.
; ---------------------------------------------------------------------------
PARSE_UINT8:
    MOV R2, 0
    MOV R0, 0
PU_LOOP:
    CMP R2, R1
    JZ PU_DONE
    MOV R3, [P0]
    CMP R3, 0
    JZ PU_DONE
    CMP R3, 0x30        ; '0'
    JC PU_DONE          ; below '0' -> stop
    CMP R3, 0x3A        ; ':' (one past '9')
    JC PU_CONT          ; '0'-'9' -> continue
    JMP PU_DONE         ; above '9' -> stop
PU_CONT:
    SUB R3, 0x30
    ; R0 = R0*10 + digit, via shifts (8x + 2x = 10x)
    MOV R4, R0
    SHL R0, 3
    ADD R0, R4          ; 9x
    ADD R0, R4          ; 10x
    ADD R0, R3
    INC P0
    INC R2
    JMP PU_LOOP
PU_DONE:
    RET

; ---------------------------------------------------------------------------
; PARSE_HEX8 — parse an ASCII hex byte (up to 4 digits) from [P0].
; Input: P0 = buffer, R1 = max chars. Output: R0 = value, R2 = chars consumed.
; Stops at the first invalid character. Clobbers R0-R3.
; ---------------------------------------------------------------------------
PARSE_HEX8:
    MOV R2, 0
    MOV R0, 0
PH_LOOP:
    CMP R2, R1
    JZ PH_DONE
    MOV R3, [P0]
    CMP R3, 0
    JZ PH_DONE
    CALL HEXCHAR_TO_NIBBLE
    CMP R3, 0xFF        ; invalid marker?
    JZ PH_DONE
    SHL R0, 4
    OR R0, R3
    INC P0
    INC R2
    JMP PH_LOOP
PH_DONE:
    RET

; ---------------------------------------------------------------------------
; HEXCHAR_TO_NIBBLE — ASCII hex char (in R3) to nibble value.
; Output: R3 = 0-15, or 0xFF if not a hex digit. Clobbers R3.
; ---------------------------------------------------------------------------
HEXCHAR_TO_NIBBLE:
    CMP R3, 0x30        ; '0'
    JC HEX_INVALID
    CMP R3, 0x3A        ; ':' (one past '9')
    JC HEX_DIGIT
    CMP R3, 0x41        ; 'A'
    JC HEX_INVALID      ; between '9' and 'A'
    CMP R3, 0x47        ; 'G' (one past 'F')
    JC HEX_UPPER
    CMP R3, 0x61        ; 'a'
    JC HEX_INVALID      ; between 'F' and 'a'
    CMP R3, 0x67        ; 'g' (one past 'f')
    JC HEX_LOWER
    JMP HEX_INVALID
HEX_DIGIT:
    SUB R3, 0x30
    RET
HEX_UPPER:
    SUB R3, 0x37        ; 'A' -> 10
    RET
HEX_LOWER:
    SUB R3, 0x57        ; 'a' -> 10
    RET
HEX_INVALID:
    MOV R3, 0xFF
    RET
