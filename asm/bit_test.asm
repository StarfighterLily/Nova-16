; Comprehensive test program for Nova-16 bit instructions
; Tests all bitwise operations, shifts, rotates, and bit manipulation

; Initialize test data
MOV R0, 0xAA    ; 10101010
MOV R1, 0x55    ; 01010101
MOV R2, 0xFF    ; 11111111
MOV R3, 0x00    ; 00000000
MOV R4, 0x0F    ; 00001111
MOV R5, 0xF0    ; 11110000

; Test bitwise AND
; R0 & R1 = 0xAA & 0x55 = 0x00 (should set zero flag)
MOV R6, R0
AND R6, R1
; Expected: R6 = 0x00, Z=1

; R0 & R2 = 0xAA & 0xFF = 0xAA (should not set zero flag)
MOV R7, R0
AND R7, R2
; Expected: R7 = 0xAA, Z=0

; Test bitwise OR
; R0 | R1 = 0xAA | 0x55 = 0xFF (should not set zero flag)
MOV R8, R0
OR R8, R1
; Expected: R8 = 0xFF, Z=0

; R3 | R3 = 0x00 | 0x00 = 0x00 (should set zero flag)
MOV R9, R3
OR R9, R3
; Expected: R9 = 0x00, Z=1

; Test bitwise XOR
; R0 ^ R1 = 0xAA ^ 0x55 = 0xFF (should not set zero flag)
MOV P0, R0
XOR P0, R1
; Expected: P0 = 0xFF, Z=0

; R0 ^ R0 = 0xAA ^ 0xAA = 0x00 (should set zero flag)
MOV P1, R0
XOR P1, R0
; Expected: P1 = 0x00, Z=1

; Test bitwise NOT
; ~R0 = ~0xAA = 0x55 (in 8-bit, but should be handled as 16-bit)
MOV P2, R0
NOT P2
; Expected: P2 = 0xFF55 (if 16-bit) or 0x55 (if 8-bit), Z=0

; ~R2 = ~0xFF = 0x00 (in 8-bit)
MOV P3, R2
NOT P3
; Expected: P3 = 0xFF00 (if 16-bit) or 0x00 (if 8-bit), Z=1

; Test shift left
; R4 << 4 = 0x0F << 4 = 0xF0
MOV P4, R4
MOV P5, 4
SHL P4, P5
; Expected: P4 = 0xF0, Z=0

; R4 << 8 = 0x0F << 8 = 0x0F00
MOV P6, R4
MOV P7, 8
SHL P6, P7
; Expected: P6 = 0x0F00, Z=0

; Test shift right
; R5 >> 4 = 0xF0 >> 4 = 0x0F
MOV P8, R5
MOV P9, 4
SHR P8, P9
; Expected: P8 = 0x0F, Z=0

; R5 >> 8 = 0xF0 >> 8 = 0x00
MOV P0, R5
MOV P1, 8
SHR P0, P1
; Expected: P0 = 0x00, Z=1

; Test rotate left
; R4 ROL 4 = 0x0F ROL 4 = 0xF0
MOV P2, R4
MOV P3, 4
ROL P2, P3
; Expected: P2 = 0xF0, Z=0

; Test rotate right
; R5 ROR 4 = 0xF0 ROR 4 = 0x0F
MOV P4, R5
MOV P5, 4
ROR P4, P5
; Expected: P4 = 0x0F, Z=0

; Test bit test operations
MOV P6, 0xAA    ; 10101010

; Test bit 0 (should be 0)
BTST P6, 0
; Expected: Z=1 (bit is 0)

; Test bit 1 (should be 1)
BTST P6, 1
; Expected: Z=0 (bit is 1)

; Test bit 7 (should be 1)
BTST P6, 7
; Expected: Z=0 (bit is 1)

; Test bit set
MOV P7, 0x00
BSET P7, 0      ; Set bit 0
; Expected: P7 = 0x01, Z=0

BSET P7, 7      ; Set bit 7
; Expected: P7 = 0x81, Z=0

; Test bit clear
MOV P8, 0xFF
BCLR P8, 0      ; Clear bit 0
; Expected: P8 = 0xFE, Z=0

BCLR P8, 7      ; Clear bit 7
; Expected: P8 = 0x7E, Z=0

; Test bit flip
MOV P9, 0xAA
BFLIP P9, 0     ; Flip bit 0 (0->1)
; Expected: P9 = 0xAB, Z=0

BFLIP P9, 1     ; Flip bit 1 (1->0)
; Expected: P9 = 0xA9, Z=0

; Test edge cases for shifts and rotates
MOV P0, 0x8000  ; Test sign bit
MOV P1, 15
SHL P0, P1      ; Should shift sign bit out
; Expected: P0 = 0x0000, Z=1, C=1 (carry should be set)

MOV P2, 0x0001
MOV P3, 15
SHR P2, P3      ; Should shift LSB out
; Expected: P2 = 0x0000, Z=1

; Test rotate with amounts >= 16
MOV P4, 0x1234
MOV P5, 16
ROL P4, P5      ; Should be same as rotate by 0
; Expected: P4 = 0x1234, Z=0

MOV P6, 0x5678
MOV P7, 17      ; 17 mod 16 = 1
ROR P6, P7
; Expected: P6 = 0xAB3C (rotate right by 1)

; Test with zero shift/rotate amounts
MOV P8, 0xFFFF
MOV P9, 0
SHL P8, P9      ; No shift
; Expected: P8 = 0xFFFF, Z=0

; Test boundary conditions for bit operations
MOV P0, 0xFFFF
BTST P0, 15     ; Test bit 15
; Expected: Z=0 (bit is 1)

MOV P1, 0x0000
BTST P1, 15     ; Test bit 15 in zero
; Expected: Z=1 (bit is 0)

; Test bit operations with bit position > 15 (should mask to 0-15)
MOV P2, 0x0001
MOV P3, 16      ; Should be treated as bit 0
BSET P2, P3
; Expected: P2 = 0x0001 (bit 0 already set)

MOV P4, 0xFFFF
MOV P5, 32      ; Should be treated as bit 0
BCLR P4, P5
; Expected: P4 = 0xFFFE (bit 0 cleared)

; End of test program
HLT