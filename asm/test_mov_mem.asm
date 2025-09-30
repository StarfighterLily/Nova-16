; Test MOV instructions with memory operands
ORG 0x0200

; Test 1: MOV immediate to memory
MOV [0x0100], 0xABCD  ; Store word 0xABCD at 0x0100

; Test 2: MOV byte immediate to memory (should this work?)
; MOV [0x0102], 0xEF    ; Store byte 0xEF at 0x0102

; Test 3: MOV register to memory (R register - byte)
MOV R0, 0x42
MOV [0x0104], R0      ; Store byte 0x42 at 0x0104

; Test 4: MOV register to memory (P register - word)
MOV P0, 0x1234
MOV [0x0106], P0      ; Store word 0x1234 at 0x0106

; Test 5: MOV memory to register (byte to R)
MOV R1, [0x0104]      ; Load byte from 0x0104 to R1 (should be 0x42)

; Test 6: MOV memory to register (word to P)
MOV P1, [0x0100]      ; Load word from 0x0100 to P1 (should be 0xABCD)

; Test 7: MOV memory to memory (via register)
MOV R2, [0x0107]      ; Load byte from 0x0107 to R2 (should be 0x34, low byte)
MOV [0x0108], R2      ; Store to 0x0108

; Test 8: Check if values are correct
; R0 should be 0x42
; R1 should be 0x42
; P0 should be 0x1234
; P1 should be 0xABCD
; R2 should be 0x34
; Memory 0x0100-0x0101 should be 0xABCD
; Memory 0x0104 should be 0x42
; Memory 0x0106-0x0107 should be 0x1234
; Memory 0x0108 should be 0x34

HLT