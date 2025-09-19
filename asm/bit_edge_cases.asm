; Focused test for bit instruction edge cases and flags
MOV R0, 0x8000  ; Test sign bit
MOV R1, 15      ; Shift by 15
SHL R0, R1      ; Should result in 0, Z=1
; Expected: R0 = 0x0000

MOV R2, 0x0001
MOV R3, 15
SHR R2, R3      ; Should result in 0, Z=1
; Expected: R2 = 0x0000

MOV R4, 0xFFFF
MOV R5, 16      ; Shift by 16 (should be treated as 0)
SHL R4, R5      ; Should result in no change
; Expected: R4 = 0xFFFF

MOV R6, 0xAAAA
MOV R7, 17      ; Rotate by 17 (should be 17 % 16 = 1)
ROL R6, R7
; Expected: R6 = 0x5555 (rotate left by 1)

MOV R8, 0x5555
MOV R9, 18      ; Rotate by 18 (should be 18 % 16 = 2)
ROR R8, R9
; Expected: R8 = 0x5555 (rotate right by 2, back to original)

; Test NOT with different values
MOV P0, 0x0000
NOT P0          ; ~0x0000 = 0xFFFF
; Expected: P0 = 0xFFFF

MOV P1, 0xFFFF
NOT P1          ; ~0xFFFF = 0x0000
; Expected: P1 = 0x0000

MOV P2, 0xAA55
NOT P2          ; ~0xAA55 = 0x55AA
; Expected: P2 = 0x55AA

; Test BTST flag behavior
MOV P3, 0x0001  ; Bit 0 set
BTST P3, 0      ; Test bit 0 (should be set, Z=0)
; Expected: Z=0

BTST P3, 1      ; Test bit 1 (should be clear, Z=1)
; Expected: Z=1

MOV P4, 0x8000  ; Bit 15 set
BTST P4, 15     ; Test bit 15 (should be set, Z=0)
; Expected: Z=0

BTST P4, 14     ; Test bit 14 (should be clear, Z=1)
; Expected: Z=1

; Test bit position masking
MOV P5, 0x0001
MOV P6, 16      ; Bit position 16 (should be treated as 0)
BTST P5, P6     ; Should test bit 0
; Expected: Z=0 (bit 0 is set)

MOV P7, 0x0001
MOV P8, 32      ; Bit position 32 (should be treated as 0)
BCLR P7, P8     ; Should clear bit 0
; Expected: P7 = 0x0000

HLT