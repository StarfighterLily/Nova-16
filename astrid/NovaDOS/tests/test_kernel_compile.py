"""NovaDOS kernel image and boot tests.

WHAT: compiles astrid/NovaDOS/src/kernel/kernel.ast with the bank-safe
layout and checks the image (segments, vectors, placed data, memory budget),
a keyless boot, and the build-setting variants.

WHY: these guard the compiler contract NovaDOS depends on. History:
* "Unknown opcode: F8" -- ISR code once grew over the entry stub at 0x1000.
* 2026-10-15 -- the function inliner grew the code to 16 KB, past the
  globals at 0x4200; the loader then wrote globals over the code tail.
"""
import os

import pytest

from novados_harness import (
    build_kernel, boot, load_syms, load_segments, KERNEL_SRC,
)

CODE_BASE = 0x1100
CODE_LIMIT = 0x4200      # bank-safe: globals start here
KHEAP_START = 0x5000     # kdos.ast Memory.KHEAP_START
ROM_WINDOW = (0x0120, 0x1000)


@pytest.fixture(scope="module")
def kernel(tmp_path_factory):
    return build_kernel(tmp_path_factory.mktemp("novados_kernel"))


@pytest.fixture(scope="module")
def diskless(tmp_path_factory):
    return build_kernel(tmp_path_factory.mktemp("novados_diskless"),
                        defines={"NOVADOS_ENABLE_NDF": 0})


@pytest.fixture(scope="module")
def keyless_run(kernel):
    return boot(kernel)


# ---------------------------------------------------------------------------
# Image layout
# ---------------------------------------------------------------------------

def test_entry_stub_is_intact(keyless_run):
    stub = bytes(keyless_run.mem._mem[0x1000:0x100F])
    # MOV SP,0xFFFF / MOV FP,0xFFFF / CALL func_main / HLT
    assert stub[0] == 0x06 and stub[3:5] == b"\xFF\xFF"
    assert stub[5] == 0x06 and stub[8:10] == b"\xFF\xFF"
    assert stub[10] == 0x2F
    assert stub[14] == 0x00


def test_segments_do_not_overlap(kernel):
    segments = sorted(load_segments(kernel))
    for (_, end), (next_start, _) in zip(segments, segments[1:]):
        assert end <= next_start, (
            f"segment ending at 0x{end:04X} overlaps 0x{next_start:04X}")


def test_code_fits_below_globals(kernel):
    code = [s for s in load_segments(kernel) if s[0] == CODE_BASE]
    assert len(code) == 1
    start, end = code[0]
    assert end <= CODE_LIMIT, (
        f"kernel code ends at 0x{end:04X}, past the globals at 0x{CODE_LIMIT:04X}")


def test_globals_end_below_kernel_heap(kernel):
    """kmalloc owns KHEAP_START..: no global may reach into it."""
    for start, end in load_segments(kernel):
        if CODE_LIMIT <= start < 0x8000:
            assert end <= KHEAP_START, f"globals run to 0x{end:04X}"


def test_read_only_data_lives_in_rom_window(kernel):
    """Command table, hex digits, the HI program and string literals are
    emitted below the entry stub, not in code space."""
    syms = load_syms(kernel)
    for name in ("gvar_commands", "gvar_hex_digits", "gvar_hi_prog"):
        assert ROM_WINDOW[0] <= syms[name] < ROM_WINDOW[1], name
    lo, hi = ROM_WINDOW
    rom = [s for s in load_segments(kernel) if lo <= s[0] < hi]
    assert rom and all(end <= hi for _, end in rom)


def test_bank_window_is_free_for_ndf_disks(kernel):
    """Selecting a disk bank swaps 0x8000-0xBFFF: nothing of the kernel may
    live there."""
    for start, end in load_segments(kernel):
        assert end <= 0x8000 or start >= 0xC000, (
            f"segment [0x{start:04X}-0x{end:04X}] overlaps the bank window")
    for name, addr in load_syms(kernel).items():
        assert not (0x8000 <= addr < 0xC000), f"{name} at 0x{addr:04X}"


def test_vectors_point_at_handlers(keyless_run):
    syms = keyless_run.syms
    assert keyless_run.mem.read_word(0x0100) == syms["func_timer_isr"]
    assert keyless_run.mem.read_word(0x0110) == syms["func_sys_isr"]   # INT 4


def test_placed_signature_and_mailbox(kernel, keyless_run):
    """The OS signature and SYS mailbox are @-placed globals: the loader
    writes them, no boot code does."""
    syms = load_syms(kernel)
    assert syms["gvar_os_signature"] == 0x0000
    assert syms["gvar_sys_num"] == 0x0012
    assert syms["gvar_sys_arg0"] == 0x0016
    assert bytes(keyless_run.mem._mem[0:4]) == b"ND\x01\x00"


def test_unused_functions_are_not_emitted(kernel):
    syms = load_syms(kernel)
    assert "func_kfree" not in syms          # never called
    assert "func_cmd_help" in syms           # reachable only via the table


# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------

def test_keyless_boot_halts_cleanly(keyless_run):
    keyless_run.assert_clean_halt()
    assert keyless_run.text == ["NovaDOS v0.2", "Astrid kernel - type HELP",
                                ">", "System halted."]


def test_background_task_runs_once_per_poll(keyless_run):
    """The shell yields to the background task every poll iteration; a
    keyless boot runs the whole poll budget (200)."""
    assert keyless_run.word("bg_runs") == 200


def test_boot_volume_is_built(keyless_run):
    page = keyless_run.mem._bank_pages[1]
    assert bytes(page[:4]) == b"NDF1"
    assert (page[4] << 8) | page[5] == 2                     # BOOT and HI
    assert bytes(page[0x10:0x18]) == b"BOOT\x00\x00\x00\x00"
    assert bytes(page[0x400:0x405]) == b"HELLO"
    assert bytes(page[0x20:0x28]) == b"HI\x00\x00\x00\x00\x00\x00"
    assert page[0x28] == 1                                   # NDF_PROG
    assert keyless_run.mem.current_bank == 0


# ---------------------------------------------------------------------------
# Build settings
# ---------------------------------------------------------------------------

def test_diskless_build_drops_ndf(kernel, diskless):
    syms = load_syms(diskless)
    assert not any(n.startswith(("func_ndf_", "func_cmd_dir", "func_cmd_load"))
                   for n in syms)
    assert "builtin_set_bank" not in syms
    assert os.path.getsize(diskless) < os.path.getsize(kernel)
    run = boot(diskless, "HELP\nDIR\nPEEK\n")
    run.assert_clean_halt()
    assert "HELP CLS PEEK POKE MEM TIME" in run.text
    assert "ECHO PRINT LIST RUN CALL NEW" in run.text
    assert "bad command" in run.text              # DIR is not compiled in
    assert "4E 44" in run.text
    assert 1 not in run.mem._bank_pages


def test_timer_and_syscalls_can_be_compiled_out(tmp_path):
    binary = build_kernel(tmp_path, defines={"NOVADOS_ENABLE_TIMER": 0,
                                             "NOVADOS_ENABLE_SYSCALLS": 0})
    syms = load_syms(binary)
    assert "func_timer_isr" not in syms and "func_sys_isr" not in syms
    run = boot(binary, "TIME\n")
    run.assert_clean_halt()
    assert run.mem.read_word(0x0100) == 0 and run.mem.read_word(0x0110) == 0
    assert "TIME 0000" in run.text


@pytest.mark.parametrize("limit, expected_lines", [(1, 0), (3, 1)])
def test_poll_limit_bounds_keyboard_iterations(tmp_path, limit, expected_lines):
    binary = build_kernel(tmp_path, defines={"NOVADOS_ENABLE_NDF": 0,
                                             "NOVADOS_POLL_LIMIT": limit})
    run = boot(binary, "M\n")
    run.assert_clean_halt()
    assert run.word("cmd_count") == expected_lines
    assert run.word("bg_runs") == limit


@pytest.mark.parametrize("name, value", [
    ("NOVADOS_ENABLE_NDF", -1), ("NOVADOS_ENABLE_NDF", 2),
    ("NOVADOS_POLL_LIMIT", 0), ("NOVADOS_POLL_LIMIT", -1),
    ("NOVADOS_POLL_LIMIT", 32768), ("NOVADOS_ENABLE_SYSCALLS", 2),
    ("NOVADOS_ENABLE_TIMER", 2), ("NOVADOS_MAX_TASKS", 17),
    ("NOVADOS_TASK_STACK_WORDS", 16),
])
def test_invalid_build_settings_fail_before_output(tmp_path, name, value):
    from astrid.compiler_api import compile_astrid
    from astrid.preprocessor import PreprocessorError
    output = tmp_path / "invalid.asm"
    with pytest.raises(PreprocessorError, match=name):
        compile_astrid(KERNEL_SRC, str(output), log=None, defines={name: value})
    assert not output.exists()


def test_maximum_poll_limit_compiles(tmp_path):
    from astrid.compiler_api import compile_astrid
    output = tmp_path / "maximum.asm"
    assert compile_astrid(KERNEL_SRC, str(output), log=None, memory_layout="bank-safe",
                          defines={"NOVADOS_POLL_LIMIT": 32767})


def test_full_scheduler_build_fits(tmp_path):
    """The opt-in multi-task tables still compile, fit the memory map, and
    boot."""
    binary = build_kernel(tmp_path, defines={"NOVADOS_ENABLE_FULL_SCHEDULER": 1})
    test_code_fits_below_globals(binary)
    test_globals_end_below_kernel_heap(binary)
    syms = load_syms(binary)
    assert "gvar_task_stacks" in syms
    boot(binary).assert_clean_halt()
