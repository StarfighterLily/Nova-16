; NovaDOS — Kernel Entry Point
; Phase 1: Kernel Foundation.
; One .asm -> one .bin + .org + .sym via the legacy 2-pass assembler.
;
; The FIRST ORG directive becomes the PC entry point after load
; (verified in nova/memory/memory.py::load), so the kernel must begin:
;   ORG 0x0120 / JMP BOOT
;
; Build:  py -3.13 nova_assembler.py NovaDOS/src/kernel.asm
; Run:    py -3.13 nova_main.py --headless NovaDOS/build/kernel.bin

    ORG 0x0120

START:
    JMP BOOT

; Splice in the kernel parts (order matters: definitions before use).
    INCLUDE "ndefs.asm"
    INCLUDE "boot.asm"
    INCLUDE "console.asm"
    INCLUDE "parse.asm"
    INCLUDE "vars.asm"
    INCLUDE "sys.asm"
    INCLUDE "loader.asm"
    INCLUDE "commands.asm"
    INCLUDE "repl.asm"
