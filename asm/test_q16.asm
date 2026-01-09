; Test Q16 floating point operations
ORG 0x0000

; Test FMUL: 2.5 * 3.0 = 7.5 (in Q8.8: 2.5 = 640, 3.0 = 768, result = 491520 >> 8 = 1920 = 7.5)
MOV P0, 640    ; 2.5 in Q8.8
MOV P1, 768    ; 3.0 in Q8.8
FMUL P0, P1    ; P0 = P0 * P1 >> 8
; Expected: P0 = 1920 (7.5)

; Test FDIV: 7.5 / 3.0 = 2.5 (in Q8.8: 7.5 = 1920, 3.0 = 768, result = (1920 << 8) / 768 = 491520 / 768 = 640)
MOV P2, 1920   ; 7.5 in Q8.8
MOV P3, 768    ; 3.0 in Q8.8
FDIV P2, P3    ; P2 = (P2 << 8) / P3
; Expected: P2 = 640 (2.5)

; Test FTOI: 2.5 -> 2 (640 >> 8 = 2)
MOV P4, 640    ; 2.5 in Q8.8
FTOI P4        ; P4 = P4 >> 8
; Expected: P4 = 2

; Test ITOF: 3 -> 3.0 (3 << 8 = 768)
MOV P5, 3      ; Integer 3
ITOF P5        ; P5 = P5 << 8
; Expected: P5 = 768 (3.0)

HLT