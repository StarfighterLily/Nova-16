"""Tests for the Astrid-based NovaDOS kernel (astrid/NovaDOS/src/kernel/).

WHAT: compiles the Astrid kernel sources to assembly + binary, then runs them
headlessly on the real Nova-16 emulator and asserts structural properties of
the generated binary (memory layout, vector table, entry stub).

WHY: the Astrid NovaDOS is compiled with the Astrid->Nova-16 codegen, not the
legacy assembly pipeline. These tests guard the *compiler* contract for NovaDOS
specifically -- that the codegen lays out segments so the entry stub at 0x1000
is never overwritten by the ISR code/data region. This is the regression guard
for the "Unknown opcode: F8" bug (see docs/notes/start.md, 2026-09-15).
"""
import os
import subprocess
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, _REPO_ROOT)

from nova_main import initialize_system  # noqa: E402

_KERNEL_SRC = os.path.join(_REPO_ROOT, "astrid", "NovaDOS", "src", "kernel", "kernel.ast")


def _run(cmd, **kw):
    res = subprocess.run(cmd, capture_output=True, text=True, **kw)
    return res.returncode, res.stdout, res.stderr


def _load_syms(bin_path):
    sym_path = bin_path.replace(".bin", ".sym")
    syms = {}
    with open(sym_path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                syms[parts[0].lower()] = int(parts[1], 16)
    return syms


@pytest.fixture(scope="module")
def kernel_binary(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("novedos_kernel")
    asm_path = str(tmp / "kernel.asm")
    bin_path = str(tmp / "kernel.bin")
    rc, out, err = _run([
        sys.executable,
        os.path.join(_REPO_ROOT, "astrid", "astrid_compiler.py"),
        _KERNEL_SRC, "-o", asm_path,
    ])
    assert rc == 0, f"Astrid compile failed:\n{out}\n{err}"
    assert os.path.exists(asm_path)
    from nova_assembler import Assembler
    ok = Assembler(log=None, trace=False).assemble(asm_path)
    assert ok, "Assembler failed"
    assert os.path.exists(bin_path)
    return bin_path


def test_entry_stub_is_intact(kernel_binary):
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry = mem.load(kernel_binary)
    assert entry == 0x1000
    stub = bytes(mem._mem[0x1000:0x100F])
    # Stub layout (15 bytes): MOV SP,0xFFFF / MOV FP,0xFFFF / CALL func_main / HLT
    assert stub[0] == 0x06, f"expected MOV opcode at 0x1000, got 0x{stub[0]:02X}"
    assert stub[1] == 0x08, "expected mode byte (reg+imm16) at 0x1001"
    assert stub[3:5] == bytes([0xFF, 0xFF]), "SP immediate should be 0xFFFF"
    assert stub[5] == 0x06, f"expected MOV opcode at 0x1005, got 0x{stub[5]:02X}"
    assert stub[8:10] == bytes([0xFF, 0xFF]), "FP immediate should be 0xFFFF"
    assert stub[10] == 0x2F, f"expected CALL opcode at 0x100A, got 0x{stub[10]:02X}"
    assert stub[14] == 0x00, f"expected HLT (0x00) at 0x100E, got 0x{stub[14]:02X}"


def test_vector_table_points_into_kernel_code(kernel_binary):
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    mem.load(kernel_binary)
    syms = _load_syms(kernel_binary)
    timer_handler = syms.get("func_timer_isr")
    assert timer_handler is not None
    vec0 = mem.read_word(0x0100)
    assert vec0 == timer_handler, (
        f"IVT vector 0 points to 0x{vec0:04X}, "
        f"expected func_timer_isr 0x{timer_handler:04X}")


def test_code_does_not_overlap_stub(kernel_binary):
    org_path = kernel_binary.replace(".bin", ".org")
    with open(org_path) as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    segments = []
    for line in lines:
        parts = line.split()
        assert len(parts) == 3
        start = int(parts[0], 16)
        length = int(parts[1])
        segments.append((start, length))
    stub_seg = (0x1000, 15)
    assert stub_seg in segments
    for start, length in segments:
        end = start + length
        if start != 0x1000:
            assert end <= 0x1000 or start >= 0x100F, (
                f"segment [{start:#x}-{end:#x}] overlaps stub [0x1000-0x100F]")


def test_kernel_runs_without_opcode_crash(kernel_binary):
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry = mem.load(kernel_binary)
    proc.pc = entry
    syms = _load_syms(kernel_binary)
    main_addr = syms.get("func_main")
    assert main_addr is not None
    cycles = 0
    max_cycles = 20000
    error = None
    while cycles < max_cycles and not proc.halted:
        cycles += 1
        try:
            proc.step()
        except Exception as e:
            error = e
            break
    # Must NOT fail with "Unknown opcode" -- that was the bug being fixed.
    assert error is None or "Unknown opcode" not in str(error), (
        f"Kernel crashed with opcode error at PC 0x{proc.pc:04X}: {error}")
    assert cycles > 100, (
        f"Kernel exited too early after {cycles} cycles (PC=0x{proc.pc:04X})")


def test_boot_slice_completes_cleanly(kernel_binary):
    """End-to-end: the cooperative scheduler demo must finish and RET to the
    stub's HLT with the original SP/FP, having run all three task resumptions.

    WHY: this proves the whole boot slice works -- entry stub -> main ->
    task_spawn/task_switch ping-pong -> main completes -> RET into HLT. A task
    that falls off the end of its entry function would pop garbage off the
    fabricated task stack and jump to junk (previously halt at 0x0181).
    demo_hits == 1 + 10 + 100 == 111 is the scheduler's fingerprint.
    """
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry = mem.load(kernel_binary)
    proc.pc = entry
    syms = _load_syms(kernel_binary)
    hits_addr = syms.get("gvar_demo_hits")
    assert hits_addr is not None, "gvar_demo_hits missing from symbol table"

    cycles = 0
    while cycles < 200000 and not proc.halted:
        cycles += 1
        proc.step()

    assert proc.halted, f"kernel never halted (PC=0x{proc.pc:04X})"
    # The stub's HLT lives at 0x100E; PC is one past it once halted.
    assert proc.pc in (0x100E, 0x100F), (
        f"kernel halted at 0x{proc.pc:04X}, expected the entry stub HLT "
        f"at 0x100E (stale .bin, or a task returned off its own stack?)")
    # main's frame must be fully unwound back to the stub's SP/FP.
    assert proc.sp == 0xFFFF, f"SP not unwound: 0x{proc.sp:04X}"
    assert proc.fp == 0xFFFF, f"FP not unwound: 0x{proc.fp:04X}"
    # Scheduler fingerprint: demo_task resumed three times.
    hits = mem.read_word(hits_addr)
    assert hits == 111, f"demo_hits = {hits}, expected 111 (1 + 10 + 100)"


# ---------------------------------------------------------------------------
# Phase-1 shell slice: line editor + command dispatch (HELP/CLS/PEEK/BYE).
# Keys are seeded exactly the way the GUI produces them: printable ASCII and
# Enter=0x0A, Backspace=0x08 (see NovaDOS/docs/notes/start.md GUI-path note).
# ---------------------------------------------------------------------------

ENTER = 0x0A
BACKSPACE = 0x08
ESC = 0x1B


def boot_with_keys(kernel_binary, keys, max_cycles=300000):
    """Load the kernel, pre-seed key scan codes, and run to halt.

    WHY pre-seed: the shell drains a bounded poll loop, so keys injected
    before stepping sit in the FIFO and are consumed one per iteration --
    the same contract the assembly-phase tests rely on.
    """
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry = mem.load(kernel_binary)
    proc.pc = entry
    for k in keys:
        kbd.add_key(k)
    cycles = 0
    while cycles < max_cycles and not proc.halted:
        proc.step()
        cycles += 1
    return proc, mem, gfx, kbd, cycles


def _assert_clean_halt(proc):
    assert proc.halted, f"kernel never halted (PC=0x{proc.pc:04X})"
    assert proc.pc in (0x100E, 0x100F), (
        f"kernel halted at 0x{proc.pc:04X}, expected the entry stub HLT")
    assert proc.sp == 0xFFFF and proc.fp == 0xFFFF, (
        f"frames not unwound: SP=0x{proc.sp:04X} FP=0x{proc.fp:04X}")


def test_shell_boot_signature_written(kernel_binary):
    """Boot writes the OS signature "ND\\x01\\x00" at 0x0000 (memory-map.md §2),
    so PEEK 0x0000 has something real to print."""
    proc, mem, gfx, kbd, cycles = boot_with_keys(kernel_binary, ())
    _assert_clean_halt(proc)
    assert bytes(mem._mem[0x0000:0x0004]) == bytes([0x4E, 0x44, 0x01, 0x00])


def test_shell_help_and_peek_commands(kernel_binary):
    """"H"+Enter prints the command list, "P"+Enter prints the signature as
    hex glyphs; both record their command id for the test to observe."""
    proc, mem, gfx, kbd, cycles = boot_with_keys(
        kernel_binary, (ord('H'), ENTER, ord('P'), ENTER))
    _assert_clean_halt(proc)
    syms = _load_syms(kernel_binary)
    assert mem.read_word(syms["gvar_cmd_count"]) == 2
    assert mem.read_word(syms["gvar_shell_cmd"]) == 3  # last dispatched = PEEK
    assert mem.read_word(syms["gvar_line_len"]) == 0   # line buffer reset
    layer0 = gfx._compositor.layers[0]
    # Row trace (8x8-glyph cells, 32 cols x 32 rows per memory-map.md §4):
    #   banner title  -> cell row 1, y=8..15
    #   banner subtitle -> cell row 2, y=16..23
    #   initial prompt  -> cell row 3, y=24..31
    #   prompt after demo+newline -> cell row 4, y=32..39
    #   HELP output     -> cell row 5, y=40..47 (18 glyphs, ~236 px)
    #   prompt after HELP -> cell row 6, y=48..55
    #   PEEK output     -> cell row 7, y=56..63 (5 glyphs, ~81 px)
    #   prompt after PEEK -> cell row 8, y=64..71
    # Both HELP and PEEK bands must hold glyph pixels.
    help_band = int((layer0[40:48, :] != 0).sum())
    peek_band = int((layer0[56:64, :] != 0).sum())
    assert help_band > 0, "HELP output produced no visible glyphs"
    assert peek_band > 0, "PEEK output produced no visible glyphs"


def test_shell_backspace_edits_line(kernel_binary):
    """Backspace removes the previous character from the line buffer, so
    "X",BS,"H",Enter dispatches HELP (not the unknown command "XH")."""
    proc, mem, gfx, kbd, cycles = boot_with_keys(
        kernel_binary, (ord('X'), BACKSPACE, ord('H'), ENTER))
    _assert_clean_halt(proc)
    syms = _load_syms(kernel_binary)
    # The Enter handler resets line_len, so the buffer state is proven by the
    # DISPATCH OUTCOME: without the backspace, "XH" would be an unknown
    # command (shell_cmd stays 0); with it, "H" dispatches HELP.
    assert mem.read_word(syms["gvar_line_len"]) == 0
    assert mem.read_word(syms["gvar_shell_cmd"]) == 1  # HELP ran
    assert mem.read_word(syms["gvar_cmd_count"]) == 1


def test_shell_unknown_command_is_swallowed(kernel_binary):
    """An unknown first character must not crash the shell: the line is
    counted, no command id is set, and the kernel still halts cleanly."""
    proc, mem, gfx, kbd, cycles = boot_with_keys(
        kernel_binary, (ord('Q'), ENTER, ESC))
    _assert_clean_halt(proc)
    syms = _load_syms(kernel_binary)
    assert mem.read_word(syms["gvar_cmd_count"]) == 1
    assert mem.read_word(syms["gvar_shell_cmd"]) == 0


def test_shell_cls_command(kernel_binary):
    """"C"+Enter clears the console layer and repaints the prompt."""
    proc, mem, gfx, kbd, cycles = boot_with_keys(
        kernel_binary, (ord('C'), ENTER))
    _assert_clean_halt(proc)
    syms = _load_syms(kernel_binary)
    assert mem.read_word(syms["gvar_shell_cmd"]) == 2
    assert mem.read_word(syms["gvar_cmd_count"]) == 1
    # CLS wiped everything except the fresh prompt (banner included), so the
    # layer must hold some pixels ("> " glyphs) but far fewer than a full run.
    pixels = int((gfx._compositor.layers[0] != 0).sum())
    assert 0 < pixels < 2000, f"expected prompt-only layer, got {pixels} px"


def test_shell_bye_exits_early(kernel_binary):
    """"B"+Enter sets the exit flag: the poll loop is abandoned immediately
    (visible in a much lower cycle count) and the kernel halts cleanly."""
    proc, mem, gfx, kbd, cycles = boot_with_keys(
        kernel_binary, (ord('B'), ENTER))
    _assert_clean_halt(proc)
    syms = _load_syms(kernel_binary)
    assert mem.read_word(syms["gvar_shell_cmd"]) == 4
    assert mem.read_word(syms["gvar_shell_exit"]) == 1
    # The keyless boot slice runs ~99.7k cycles; BYE skips most of the poll
    # loop, so a fresh build must land well below that.
    assert cycles < 80000, f"BYE did not exit early ({cycles} cycles)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
