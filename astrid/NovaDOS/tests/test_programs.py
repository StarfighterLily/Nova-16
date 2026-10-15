"""NovaDOS program tests: LOAD/RUN/SAVE/CALL/NEW and the INT 4 SYS mailbox.

Programs are assembled for PROG_BASE (0x5800), entered with CALL, and reach
the kernel only through the zero-page mailbox (docs/plans/
programs-and-syscalls.md). This is the Phase-1 exit criterion: a LOAD/RUN
sample that returns.
"""
import os

import pytest

from novados_harness import build_kernel, boot, HI_ASM

PROG_BASE = 0x5800


@pytest.fixture(scope="module")
def kernel(tmp_path_factory):
    return build_kernel(tmp_path_factory.mktemp("novados_progs"),
                        defines={"NOVADOS_POLL_LIMIT": 600})


def assemble(tmp_path, source, name="prog"):
    from nova_assembler import Assembler
    path = tmp_path / f"{name}.asm"
    path.write_text(source, encoding="utf-8")
    assert Assembler(log=None, trace=False).assemble(str(path))
    return (tmp_path / f"{name}.bin").read_bytes()


def boot_with_program(kernel, program, keys):
    """Boot with `program` already in the program area (as if LOADed)."""
    from novados_harness import Run, initialize_system, ENTER
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    proc.pc = mem.load(kernel)
    for i, b in enumerate(program):
        mem._mem[PROG_BASE + i] = b
    pending = [ENTER if ch == "\n" else ord(ch) for ch in keys][::-1]
    cycles = 0
    while cycles < 2_000_000 and not proc.halted:
        if pending and len(kbd._buffer) < 4:
            kbd.add_key(pending.pop())
        proc.step()
        cycles += 1
    run = Run(kernel, proc, mem, gfx, kbd, cycles)
    run.assert_clean_halt()
    return run


def test_hi_program_bytes_match_source(tmp_path, kernel):
    """kernel.ast embeds hi.asm as bytes; they must stay in sync."""
    with open(HI_ASM, encoding="utf-8") as f:
        expected = assemble(tmp_path, f.read(), "hi")
    run = boot(kernel)
    addr = run.syms["gvar_hi_prog"]
    assert bytes(run.mem._mem[addr:addr + len(expected)]) == expected


def test_load_and_run_the_sample(kernel):
    run = boot(kernel, "LOAD HI\nRUN\nPEEK\n")
    run.assert_clean_halt()
    text = run.text
    assert text[text.index("> LOAD HI") + 1] == "36 bytes loaded"
    assert text[text.index("> RUN") + 1] == "HI FROM DISK"
    # The shell is intact after the program returned.
    assert text[text.index("> PEEK") + 1] == "4E 44"
    assert run.word("sys_calls") == 1
    assert run.word("prog_size") == 36


def test_run_without_a_program(kernel):
    run = boot(kernel, "RUN\nLOAD NOPE\n")
    run.assert_clean_halt()
    assert run.text[run.text.index("> RUN") + 1] == "no program loaded"
    assert run.text[run.text.index("> LOAD NOPE") + 1] == "file not found"


def test_save_new_and_reload(kernel):
    run = boot(kernel, "LOAD HI\nSAVE HI2\nNEW\nRUN\nLOAD HI2\nRUN\nDIR\n")
    run.assert_clean_halt()
    text = run.text
    assert text[text.index("> SAVE HI2") + 1] == "36 bytes saved"
    runs = [i for i, line in enumerate(text) if line == "> RUN"]
    assert text[runs[0] + 1] == "no program loaded"        # NEW cleared it
    assert text[runs[1] + 1] == "HI FROM DISK"
    assert "HI2       PRG 36" in text
    assert "3 files, 15283 free" in text


def test_save_errors(kernel):
    run = boot(kernel, "SAVE\nSAVE X 0x6000\nSAVE HI 0x6000 4\n"
                       "SAVE X 0x9000 4\nSAVE TOOLONGNAME 0x6000 4\nSAVE X\n"
                       "SAVE X zz 4\n")
    run.assert_clean_halt()
    text = run.text

    def after(cmd):
        return text[text.index(f"> {cmd}") + 1]

    assert after("SAVE") == "usage: SAVE name [addr len]"
    assert after("SAVE X 0x6000") == "usage: SAVE name [addr len]"
    assert after("SAVE HI 0x6000 4") == "file exists"
    assert after("SAVE X 0x9000 4") == "can't save the bank window"
    assert after("SAVE TOOLONGNAME 0x6000 4") == "bad name"
    assert after("SAVE X") == "usage: SAVE name [addr len]"   # nothing loaded
    assert after("SAVE X zz 4") == "usage: SAVE name [addr len]"


SYSCALL_PROBE = """
ORG 0x5800
    MOV P5, 0x1234        ; must survive every INT 4
    MOV P0, 65            ; SYS_PUTC 'A'
    MOV [0x0016], P0
    MOV P0, 12
    MOV [0x0012], P0
    INT 4
    MOV P0, [0x0014]
    MOV [0x6000], P0      ; RET of PUTC
    MOV P0, 24            ; SYS_TIME
    MOV [0x0012], P0
    INT 4
    MOV P0, [0x0014]
    MOV [0x6002], P0
    MOV P0, 11            ; SYS_GETC
    MOV [0x0012], P0
    INT 4
    MOV P0, [0x0014]
    MOV [0x6004], P0
    MOV P0, 99            ; unknown operation
    MOV [0x0012], P0
    INT 4
    MOV P0, [0x0014]
    MOV [0x6006], P0
    MOV [0x6008], P5
    RET
"""


def test_syscalls(tmp_path, kernel):
    program = assemble(tmp_path, SYSCALL_PROBE)
    # "Z" is typed right after the CALL line, so SYS_GETC finds it waiting.
    run = boot_with_program(kernel, program, "CALL 0x5800\nZ")
    words = [run.mem.read_word(0x6000 + 2 * i) for i in range(5)]
    assert words[0] == 0                       # SYS_OK
    assert words[1] > 0                        # ticks since boot
    assert words[2] == ord("Z")                # the waiting key
    assert words[3] == 0xFFFF                  # SYS_EBADOP
    assert words[4] == 0x1234                  # registers preserved
    assert run.word("sys_calls") == 4
    assert run.text[run.text.index("> CALL 0x5800") + 1] == "A"


def test_call_validates_its_argument(kernel):
    run = boot(kernel, "CALL\nCALL xyz\n")
    run.assert_clean_halt()
    assert run.text.count("usage: CALL addr") == 2
