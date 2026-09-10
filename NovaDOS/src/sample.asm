; NovaDOS — Phase 1 sample user program (NDF-loadable)
;
; Loaded into PROG_BASE (0x1000) by the loader. Entry point = its ORG,
; which must equal the load address the loader copies to (K_PROG).
; Sets marker bytes in zero page then returns to the REPL via RET.

    ORG 0x1000

SAMPLE_START:
    MOV R0, 0x42        ; 'B' marker
    MOV [0x00E0], R0    ; marker byte 1
    MOV R0, 0x2A        ; '*' marker
    MOV [0x00E1], R0    ; marker byte 2
    RET                 ; return to the REPL