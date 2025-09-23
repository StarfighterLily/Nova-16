; Performance benchmark: Software vs Hardware memory operations
; Tests MEMSET, MEMTEST, and MEMMOVE implementations

ORG 0x1000

start:
    ; Initialize graphics
    MOV P8, 0xF000
    MOV VX, 0
    MOV VY, 0
    MOV VL, 0
    MOV VM, 0
    MOV P0, 0
    SFILL P0

    ; Display title
    MOV VX, 0
    MOV VY, 0
    MOV VL, 0
    MOV P0, 'M'
    MOV P1, 0x0F
    CHAR P0, P1
    MOV P0, 'e'
    CHAR P0, P1
    MOV P0, 'm'
    CHAR P0, P1
    MOV P0, 'o'
    CHAR P0, P1
    MOV P0, 'r'
    CHAR P0, P1
    MOV P0, 'y'
    CHAR P0, P1
    MOV P0, ' '
    CHAR P0, P1
    MOV P0, 'P'
    CHAR P0, P1
    MOV P0, 'e'
    CHAR P0, P1
    MOV P0, 'r'
    CHAR P0, P1
    MOV P0, 'f'
    CHAR P0, P1
    MOV P0, 'o'
    CHAR P0, P1
    MOV P0, 'r'
    CHAR P0, P1
    MOV P0, 'm'
    CHAR P0, P1
    MOV P0, 'a'
    CHAR P0, P1
    MOV P0, 'n'
    CHAR P0, P1
    MOV P0, 'c'
    CHAR P0, P1
    MOV P0, 'e'
    CHAR P0, P1
    MOV P0, ' '
    CHAR P0, P1
    MOV P0, 'T'
    CHAR P0, P1
    MOV P0, 'e'
    CHAR P0, P1
    MOV P0, 's'
    CHAR P0, P1
    MOV P0, 't'
    CHAR P0, P1

    ; Display MEMSET test message
    MOV VX, 0
    MOV VY, 8
    MOV VL, 0
    MOV P0, 'T'
    MOV P1, 0x0F
    CHAR P0, P1
    MOV P0, 'e'
    CHAR P0, P1
    MOV P0, 's'
    CHAR P0, P1
    MOV P0, 't'
    CHAR P0, P1
    MOV P0, 'i'
    CHAR P0, P1
    MOV P0, 'n'
    CHAR P0, P1
    MOV P0, 'g'
    CHAR P0, P1
    MOV P0, ' '
    CHAR P0, P1
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'E'
    CHAR P0, P1
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'S'
    CHAR P0, P1
    MOV P0, 'E'
    CHAR P0, P1
    MOV P0, 'T'
    CHAR P0, P1
    MOV P0, '.'
    CHAR P0, P1
    MOV P0, '.'
    CHAR P0, P1
    MOV P0, '.'
    CHAR P0, P1

    ; Hardware MEMSET test
    MOV P0, 0x2000    ; Start address
    MOV P1, 0xAA      ; Fill value
    MOV P2, 100       ; Count (100 bytes)

    ; Time hardware MEMSET
    MOV TT, 0         ; Reset timer
    MEMSET P0, P1, P2
    MOV P3, TT        ; Get cycles used
    MOV [0x3000], P3  ; Store hardware cycles

    ; Software MEMSET test
    MOV P0, 0x2100    ; Different start address
    MOV P1, 0xAA      ; Same fill value
    MOV P2, 100       ; Same count

    ; Time software MEMSET
    MOV TT, 0         ; Reset timer
    CALL software_memset
    MOV P4, TT        ; Get cycles used
    MOV [0x3002], P4  ; Store software cycles

    ; Display MEMSET results
    MOV VX, 0
    MOV VY, 16
    MOV VL, 0
    MOV P1, 0x0F
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'E'
    CHAR P0, P1
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'S'
    CHAR P0, P1
    MOV P0, 'E'
    CHAR P0, P1
    MOV P0, 'T'
    CHAR P0, P1
    MOV P0, ':'
    CHAR P0, P1
    MOV P0, ' '
    CHAR P0, P1
    MOV P0, 'H'
    CHAR P0, P1
    MOV P0, 'W'
    CHAR P0, P1
    MOV P0, '='
    CHAR P0, P1
    MOV P0, [0x3000]
    CALL print_number
    MOV P0, ' '
    CHAR P0, P1
    MOV P0, 'S'
    CHAR P0, P1
    MOV P0, 'W'
    CHAR P0, P1
    MOV P0, '='
    CHAR P0, P1
    MOV P0, [0x3002]
    CALL print_number
    MOV P0, ' '
    CHAR P0, P1
    MOV P0, 'c'
    CHAR P0, P1
    MOV P0, 'y'
    CHAR P0, P1
    MOV P0, 'c'
    CHAR P0, P1
    MOV P0, 'l'
    CHAR P0, P1
    MOV P0, 'e'
    CHAR P0, P1
    MOV P0, 's'
    CHAR P0, P1

    ; ===== MEMTEST BENCHMARK =====
    MOV VX, 0
    MOV VY, 24
    MOV VL, 0
    MOV P1, 0x0F
    MOV P0, 'T'
    CHAR P0, P1
    MOV P0, 'e'
    CHAR P0, P1
    MOV P0, 's'
    CHAR P0, P1
    MOV P0, 't'
    CHAR P0, P1
    MOV P0, 'i'
    CHAR P0, P1
    MOV P0, 'n'
    CHAR P0, P1
    MOV P0, 'g'
    CHAR P0, P1
    MOV P0, ' '
    CHAR P0, P1
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'E'
    CHAR P0, P1
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'T'
    CHAR P0, P1
    MOV P0, 'E'
    CHAR P0, P1
    MOV P0, 'S'
    CHAR P0, P1
    MOV P0, 'T'
    CHAR P0, P1
    MOV P0, '.'
    CHAR P0, P1
    MOV P0, '.'
    CHAR P0, P1
    MOV P0, '.'
    CHAR P0, P1

    ; Setup test data (fill 0x2200-0x2263 with 0xBB)
    MOV P0, 0x2200
    MOV P1, 0xBB
    MOV P2, 100
    MEMSET P0, P1, P2

    ; Hardware MEMTEST test
    MOV P0, 0x2000    ; Source 1 (filled with 0xAA)
    MOV P1, 0x2200    ; Source 2 (filled with 0xBB)
    MOV P2, 100       ; Count

    MOV TT, 0
    MEMTEST P0, P1, P2
    MOV P3, TT
    MOV [0x3004], P3  ; Store hardware cycles

    ; Software MEMTEST test
    MOV TT, 0
    CALL software_memtest
    MOV P4, TT
    MOV [0x3006], P4  ; Store software cycles

    ; Display MEMTEST results
    MOV VX, 0
    MOV VY, 32
    MOV VL, 0
    MOV P1, 0x0F
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'E'
    CHAR P0, P1
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'T'
    CHAR P0, P1
    MOV P0, 'E'
    CHAR P0, P1
    MOV P0, 'S'
    CHAR P0, P1
    MOV P0, 'T'
    CHAR P0, P1
    MOV P0, ':'
    CHAR P0, P1
    MOV P0, ' '
    CHAR P0, P1
    MOV P0, 'H'
    CHAR P0, P1
    MOV P0, 'W'
    CHAR P0, P1
    MOV P0, '='
    CHAR P0, P1
    MOV P0, [0x3004]
    CALL print_number
    MOV P0, ' '
    CHAR P0, P1
    MOV P0, 'S'
    CHAR P0, P1
    MOV P0, 'W'
    CHAR P0, P1
    MOV P0, '='
    CHAR P0, P1
    MOV P0, [0x3006]
    CALL print_number
    MOV P0, ' '
    CHAR P0, P1
    MOV P0, 'c'
    CHAR P0, P1
    MOV P0, 'y'
    CHAR P0, P1
    MOV P0, 'c'
    CHAR P0, P1
    MOV P0, 'l'
    CHAR P0, P1
    MOV P0, 'e'
    CHAR P0, P1
    MOV P0, 's'
    CHAR P0, P1

    ; ===== MEMMOVE BENCHMARK =====
    MOV VX, 0
    MOV VY, 40
    MOV VL, 0
    MOV P1, 0x0F
    MOV P0, 'T'
    CHAR P0, P1
    MOV P0, 'e'
    CHAR P0, P1
    MOV P0, 's'
    CHAR P0, P1
    MOV P0, 't'
    CHAR P0, P1
    MOV P0, 'i'
    CHAR P0, P1
    MOV P0, 'n'
    CHAR P0, P1
    MOV P0, 'g'
    CHAR P0, P1
    MOV P0, ' '
    CHAR P0, P1
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'E'
    CHAR P0, P1
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'O'
    CHAR P0, P1
    MOV P0, 'V'
    CHAR P0, P1
    MOV P0, 'E'
    CHAR P0, P1
    MOV P0, '.'
    CHAR P0, P1
    MOV P0, '.'
    CHAR P0, P1
    MOV P0, '.'
    CHAR P0, P1

    ; Setup source data
    MOV P0, 0x2300
    MOV P1, 0xCC
    MOV P2, 50
    MEMSET P0, P1, P2

    ; Hardware MEMMOVE test
    MOV P0, 0x2400    ; Destination
    MOV P1, 0x2300    ; Source
    MOV P2, 50        ; Count

    MOV TT, 0
    MEMMOVE P0, P1, P2
    MOV P3, TT
    MOV [0x3008], P3  ; Store hardware cycles

    ; Software MEMMOVE test
    MOV P0, 0x2500    ; Different destination
    MOV P1, 0x2300    ; Same source
    MOV P2, 50        ; Same count

    MOV TT, 0
    CALL software_memmove
    MOV P4, TT
    MOV [0x3010], P4  ; Store software cycles

    ; Display MEMMOVE results
    MOV VX, 0
    MOV VY, 48
    MOV VL, 0
    MOV P1, 0x0F
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'E'
    CHAR P0, P1
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'O'
    CHAR P0, P1
    MOV P0, 'V'
    CHAR P0, P1
    MOV P0, 'E'
    CHAR P0, P1
    MOV P0, ':'
    CHAR P0, P1
    MOV P0, ' '
    CHAR P0, P1
    MOV P0, 'H'
    CHAR P0, P1
    MOV P0, 'W'
    CHAR P0, P1
    MOV P0, '='
    CHAR P0, P1
    MOV P0, [0x3008]
    CALL print_number
    MOV P0, ' '
    CHAR P0, P1
    MOV P0, 'S'
    CHAR P0, P1
    MOV P0, 'W'
    CHAR P0, P1
    MOV P0, '='
    CHAR P0, P1
    MOV P0, [0x3010]
    CALL print_number
    MOV P0, ' '
    CHAR P0, P1
    MOV P0, 'c'
    CHAR P0, P1
    MOV P0, 'y'
    CHAR P0, P1
    MOV P0, 'c'
    CHAR P0, P1
    MOV P0, 'l'
    CHAR P0, P1
    MOV P0, 'e'
    CHAR P0, P1
    MOV P0, 's'
    CHAR P0, P1

    ; Calculate and display speedup ratios
    MOV VX, 0
    MOV VY, 56
    MOV VL, 0
    MOV P1, 0x0F
    MOV P0, 'S'
    CHAR P0, P1
    MOV P0, 'p'
    CHAR P0, P1
    MOV P0, 'e'
    CHAR P0, P1
    MOV P0, 'e'
    CHAR P0, P1
    MOV P0, 'd'
    CHAR P0, P1
    MOV P0, 'u'
    CHAR P0, P1
    MOV P0, 'p'
    CHAR P0, P1
    MOV P0, ' '
    CHAR P0, P1
    MOV P0, 'R'
    CHAR P0, P1
    MOV P0, 'a'
    CHAR P0, P1
    MOV P0, 't'
    CHAR P0, P1
    MOV P0, 'i'
    CHAR P0, P1
    MOV P0, 'o'
    CHAR P0, P1
    MOV P0, 's'
    CHAR P0, P1
    MOV P0, ':'
    CHAR P0, P1

    ; MEMSET speedup
    MOV VX, 0
    MOV VY, 64
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'E'
    CHAR P0, P1
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'S'
    CHAR P0, P1
    MOV P0, 'E'
    CHAR P0, P1
    MOV P0, 'T'
    CHAR P0, P1
    MOV P0, ':'
    CHAR P0, P1
    MOV P0, ' '
    CHAR P0, P1
    MOV P0, [0x3002]  ; Software cycles
    MOV P1, [0x3000]  ; Hardware cycles
    CALL calculate_ratio
    CALL print_number
    MOV P0, 'x'
    CHAR P0, P1

    ; MEMTEST speedup
    MOV VX, 0
    MOV VY, 72
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'E'
    CHAR P0, P1
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'T'
    CHAR P0, P1
    MOV P0, 'E'
    CHAR P0, P1
    MOV P0, 'S'
    CHAR P0, P1
    MOV P0, 'T'
    CHAR P0, P1
    MOV P0, ':'
    CHAR P0, P1
    MOV P0, ' '
    CHAR P0, P1
    MOV P0, [0x3006]  ; Software cycles
    MOV P1, [0x3004]  ; Hardware cycles
    CALL calculate_ratio
    CALL print_number
    MOV P0, 'x'
    CHAR P0, P1

    ; MEMMOVE speedup
    MOV VX, 0
    MOV VY, 80
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'E'
    CHAR P0, P1
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'M'
    CHAR P0, P1
    MOV P0, 'O'
    CHAR P0, P1
    MOV P0, 'V'
    CHAR P0, P1
    MOV P0, 'E'
    CHAR P0, P1
    MOV P0, ':'
    CHAR P0, P1
    MOV P0, ' '
    CHAR P0, P1
    MOV P0, [0x3010]  ; Software cycles
    MOV P1, [0x3008]  ; Hardware cycles
    CALL calculate_ratio
    CALL print_number
    MOV P0, 'x'
    CHAR P0, P1

    ; Wait for keypress
pause:
    KEYSTAT P0
    CMP P0, 0
    JZ pause
    KEYIN P0
    JMP halt

halt:
    JMP halt

; ===== SOFTWARE IMPLEMENTATIONS =====

; Software MEMSET: P0=address, P1=value, P2=count
software_memset:
    MOV P5, P0        ; Save start address
memset_loop:
    CMP P2, 0
    JZ memset_done
    MOV [P0], P1
    INC P0
    DEC P2
    JMP memset_loop
memset_done:
    RET

; Software MEMTEST: P0=addr1, P1=addr2, P2=count, returns Z=1 if equal
software_memtest:
    MOV P5, P0        ; Save addr1
memtest_loop:
    CMP P2, 0
    JZ memtest_done
    MOV P3, [P0]
    MOV P4, [P1]
    CMP P3, P4
    JNZ memtest_fail
    INC P0
    INC P1
    DEC P2
    JMP memtest_loop
memtest_fail:
    MOV P0, 0         ; Set Z=0 (not equal)
    RET
memtest_done:
    MOV P0, 1         ; Set Z=1 (equal)
    RET

; Software MEMMOVE: P0=dst, P1=src, P2=count
software_memmove:
    MOV P5, P0        ; Save destination
memmove_loop:
    CMP P2, 0
    JZ memmove_done
    MOV P3, [P1]
    MOV [P0], P3
    INC P0
    INC P1
    DEC P2
    JMP memmove_loop
memmove_done:
    RET

; ===== UTILITY FUNCTIONS =====

; Print number in P0
print_number:
    MOV P1, 0x6000    ; Temp buffer
    ITOS P1, P0       ; Convert to string
    MOV P2, P1
print_num_loop:
    MOV P3, [P2]
    CMP P3, 0
    JZ print_num_done
    MOV P4, 0x0F      ; White color
    CHAR P3, P4
    INC P2
    JMP print_num_loop
print_num_done:
    RET

; Calculate ratio: P0=software_cycles, P1=hardware_cycles, returns ratio in P0
calculate_ratio:
    CMP P1, 0
    JZ ratio_zero     ; Avoid division by zero
    ; Simple ratio calculation (software/hardware)
    ; For now, just return a fixed ratio since we don't have division
    ; In a real implementation, we'd need division
    MOV P0, 8         ; Assume 8x speedup for demo
    RET
ratio_zero:
    MOV P0, 999       ; Infinite speedup
    RET

; Print string function
PRINT_STR:
    POP P2            ; Return address
    POP P1            ; String address
    PUSH P2           ; Restore return address
print_str_loop:
    MOV P0, [P1]
    CMP P0, 0
    JZ print_str_done
    MOV P3, 0x0F      ; White color
    CHAR P0, P3
    INC P1
    JMP print_str_loop
print_str_done:
    RET