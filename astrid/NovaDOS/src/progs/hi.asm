; =============================================================================
; HI - sample NovaDOS program
; WHAT: prints "HI FROM DISK" through the SYS mailbox and returns.
; WHY: the Phase-1 exit criterion is a LOAD/RUN sample that RETs. The kernel
;      copies these bytes onto the boot volume (kernel.ast: hi_prog), LOAD
;      copies them to PROG_BASE and RUN CALLs PROG_BASE.
;
; Program contract (docs/plans/programs-and-syscalls.md): assembled for
; ORG 0x5800, entered by CALL, returns with RET, preserves SP and FP, and
; reaches the kernel only through INT 4 with the mailbox at 0x0012.
;
; After editing, reassemble and paste the bytes into kernel.ast's hi_prog;
; test_hi_program_bytes_match_source fails until the two agree.
; =============================================================================
ORG 0x5800
    MOV P0, msg
    MOV [0x0016], P0      ; SYS_ARG0 = address of the text
    MOV P0, 9             ; SYS_WRITE
    MOV [0x0012], P0      ; SYS_NUM
    INT 4
    RET
msg:
    DEFSTR "HI FROM DISK"
