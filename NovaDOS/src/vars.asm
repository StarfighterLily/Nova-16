; NovaDOS — Variable System
; A-Z: 26 signed words at 0xD000 (52 bytes).
; Str0-Str9: 10 slots of 256 bytes starting at 0xD034.
;
; VAR_GET_AZ/VAR_SET_AZ pass the value in P0; index in R0 (0=A .. 25=Z).

; ---------------------------------------------------------------------------
; INIT_VARS — write VARS_BASE/VARS_END/PROG_BASE (big-endian words) and
; CUR_BANK to the zero page, then clear the A-Z heap. Called from BOOT.
; ---------------------------------------------------------------------------
INIT_VARS:
    ; Memory is big-endian: a word at 0x0008 reads (mem[8]<<8)|mem[9].
    MOV R0, 0xD0
    MOV [0x0008], R0    ; ZP_VARS_B high = 0xD0
    MOV R0, 0x00
    MOV [0x0009], R0    ; ZP_VARS_B low  = 0x00  => 0xD000
    MOV R0, 0xE8
    MOV [0x000A], R0    ; ZP_VARS_E high = 0xE8
    MOV R0, 0x00
    MOV [0x000B], R0    ; ZP_VARS_E low  = 0x00  => 0xE800
    MOV R0, 0x10
    MOV [0x000C], R0    ; ZP_PROG_B high = 0x10
    MOV R0, 0x00
    MOV [0x000D], R0    ; ZP_PROG_B low  = 0x00  => 0x1000
    MOV R0, 0
    MOV [0x000E], R0    ; ZP_CUR_ENT high
    MOV [0x000F], R0    ; ZP_CUR_ENT low
    MOV [0x0010], R0    ; ZP_CUR_BANK = 0
    ; Clear A-Z variables (26 words = 52 bytes)
    MOV P0, K_VARS
    MOV R0, 0
    MOV R1, 52
INIT_AZ_LOOP:
    CMP R1, 0
    JZ INIT_AZ_DONE
    MOV [P0], R0
    INC P0
    DEC R1
    JMP INIT_AZ_LOOP
INIT_AZ_DONE:
    RET

; ---------------------------------------------------------------------------
; VAR_GET_AZ — get an A-Z variable. In: R0 = index. Out: P0 = 16-bit value.
; Clobbers R0, R1.
; ---------------------------------------------------------------------------
VAR_GET_AZ:
    MOV R1, R0
    SHL R1, 1           ; index * 2
    MOV P0, K_VARS
    ADD P0, R1
    MOV R0, [P0]        ; high byte
    MOV R1, [P0+1]      ; low byte
    MOV P0:, R0
    MOV :P0, R1
    RET

; ---------------------------------------------------------------------------
; VAR_SET_AZ — set an A-Z variable. In: R0 = index, P0 = 16-bit value.
; Clobbers R0, R1.
; ---------------------------------------------------------------------------
VAR_SET_AZ:
    MOV R1, R0          ; save index
    MOV P1, P0          ; save value
    SHL R1, 1
    MOV P0, K_VARS
    ADD P0, R1
    MOV R0, P1:         ; high byte
    MOV [P0], R0
    MOV R0, :P1         ; low byte
    MOV [P0+1], R0
    RET

; ---------------------------------------------------------------------------
; VAR_GET_STR — address of string slot N. In: R0 = index (0-9).
; Out: P0 = address. Clobbers R0, R1.
; ---------------------------------------------------------------------------
VAR_GET_STR:
    MOV R1, R0
    MOV P0, K_VARS
    ADD P0, 52          ; skip the A-Z area
    CMP R1, 0
    JZ VGSTR_DONE
VGSTR_LOOP:
    ADD P0, 256         ; each slot is 256 bytes
    DEC R1
    CMP R1, 0
    JNZ VGSTR_LOOP
VGSTR_DONE:
    RET

; ---------------------------------------------------------------------------
; VAR_PARSE_NAME — classify a variable name at [P0].
; In: P0 = name ("A".."Z"/"a".."z" or "Str0".."Str9"/"str0".."str9").
; Out: R0 = type (0=real, 1=string), R1 = index (0-25 / 0-9),
;      R2 = 1 if invalid, 0 otherwise.
; Clobbers R0-R2, advances P0 through the name.
; ---------------------------------------------------------------------------
VAR_PARSE_NAME:
    MOV R2, 0
    MOV R0, [P0]
    CMP R0, 0
    JZ VPN_INVALID
    CMP R0, 0x53        ; 'S'
    JZ VPN_STRING
    CMP R0, 0x73        ; 's'
    JZ VPN_STRING
    CMP R0, 0x41        ; 'A'
    JC VPN_INVALID
    CMP R0, 0x5B        ; '[' (one past 'Z')
    JC VPN_AZ_UPPER
    CMP R0, 0x61        ; 'a'
    JC VPN_INVALID
    CMP R0, 0x7B        ; '{' (one past 'z')
    JC VPN_AZ_LOWER
    JMP VPN_INVALID
VPN_AZ_UPPER:
    SUB R0, 0x41
    MOV R1, R0
    MOV R0, 0           ; type = real
    RET
VPN_AZ_LOWER:
    SUB R0, 0x61
    MOV R1, R0
    MOV R0, 0
    RET
VPN_STRING:
    ; Match "Str" prefix (any of Str/str/StR/sTR...)
    INC P0
    MOV R0, [P0]
    CMP R0, 0x74        ; 't'
    JZ VPN_STR_OK
    CMP R0, 0x54        ; 'T'
    JZ VPN_STR_OK
    JMP VPN_INVALID
VPN_STR_OK:
    INC P0
    MOV R0, [P0]
    CMP R0, 0x72        ; 'r'
    JZ VPN_STR_OK2
    CMP R0, 0x52        ; 'R'
    JZ VPN_STR_OK2
    JMP VPN_INVALID
VPN_STR_OK2:
    INC P0
    MOV R0, [P0]        ; digit
    CMP R0, 0x30        ; '0'
    JC VPN_INVALID
    CMP R0, 0x3A        ; ':' (one past '9')
    JC VPN_STR_VALID
    JMP VPN_INVALID
VPN_STR_VALID:
    SUB R0, 0x30
    MOV R1, R0
    MOV R0, 1           ; type = string
    RET
VPN_INVALID:
    MOV R2, 1
    RET
