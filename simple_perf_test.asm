; Simple performance test for memory operations
; Just runs the operations and stores cycle counts

ORG 0x1000

start:
    ; MEMSET test
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

    ; MEMTEST test
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

    ; MEMMOVE test
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

    ; Halt
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