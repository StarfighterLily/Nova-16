"""Phase 1 exit criteria 2 & 4: REPL command handling (HELP, PEEK, variables)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from conftest import boot_novados, type_cmd, run_until

# REPL_MAIN address (from kernel.sym); the REPL frames its loop around it.
REPL_MAIN = 0x0C03
VARS_BASE = 0xD000


def layer_pixels(gfx):
    return int((gfx._compositor.layers[0] != 0).sum())


def boot_baseline(proc, gfx, max_cycles=20000):
    """Step to the first GETLINE wait and return the banner pixel baseline."""
    run_until(proc, lambda p: REPL_MAIN <= p.pc <= REPL_MAIN + 0x30,
              max_cycles=max_cycles)
    return layer_pixels(gfx)


@pytest.mark.unit
@pytest.mark.integration
def test_help_prints_and_returns_to_repl():
    proc, mem, gfx, kbd = boot_novados()
    baseline = layer_pixels(gfx)
    type_cmd(proc, gfx, kbd, "HELP")
    ok = run_until(
        proc,
        lambda p: (layer_pixels(gfx) > baseline + 20
                   and REPL_MAIN <= p.pc <= REPL_MAIN + 0x30),
        max_cycles=60000)
    assert ok, f"HELP produced no visible text (pixels {baseline} -> {layer_pixels(gfx)}, PC=0x{proc.pc:04X})"
    # Cursor advanced past the banner rows (row >= 2)
    cursor_row = mem.read_byte(0x0025)
    assert cursor_row >= 2, f"cursor did not advance past banner (row={cursor_row})"


@pytest.mark.unit
@pytest.mark.integration
def test_assign_and_print():
    proc, mem, gfx, kbd = boot_novados()
    type_cmd(proc, gfx, kbd, "A = 5")
    type_cmd(proc, gfx, kbd, "PRINT A")
    # Wait until A holds 5 (big-endian at VARS_BASE) AND we're back in the
    # REPL loop (both lines processed; the predicate can otherwise fire
    # mid-instruction between the VAR_SET_AZ store and the loop return).
    ok = run_until(
        proc,
        lambda p: (mem.read_byte(VARS_BASE) == 0
                   and mem.read_byte(VARS_BASE + 1) == 5
                   and REPL_MAIN <= p.pc <= REPL_MAIN + 0x30),
        max_cycles=60000)
    assert ok, f"A = 5 never landed in the variable heap (0x{mem.read_byte(VARS_BASE):02X} {mem.read_byte(VARS_BASE+1):02X})"
    # '5' rendered on screen (a '5' glyph is 8x8; look for new pixels past row 2)
    rest = gfx._compositor.layers[0][16:, :]
    assert int((rest != 0).sum()) > 0, "PRINT A did not render a digit"


@pytest.mark.unit
@pytest.mark.integration
def test_assign_and_print_a_b():
    proc, mem, gfx, kbd = boot_novados()
    type_cmd(proc, gfx, kbd, "B = 7")
    type_cmd(proc, gfx, kbd, "PRINT B")
    ok = run_until(proc, lambda p: mem.read_byte(VARS_BASE + 3) == 7,
                   max_cycles=40000)
    assert ok, "B = 7 not stored (VARS_BASE+1 is A, +2/+3 is B)"
    assert mem.read_byte(VARS_BASE + 2) == 0


@pytest.mark.unit
@pytest.mark.integration
def test_peek_signature_prints_hex():
    proc, mem, gfx, kbd = boot_novados()
    baseline = layer_pixels(gfx)
    type_cmd(proc, gfx, kbd, "PEEK 0x0000")
    ok = run_until(
        proc,
        lambda p: (layer_pixels(gfx) > baseline
                   and REPL_MAIN <= p.pc <= REPL_MAIN + 0x30),
        max_cycles=60000)
    assert ok, f"PEEK produced no output (pixels {baseline} -> {layer_pixels(gfx)}, PC=0x{proc.pc:04X})"


@pytest.mark.unit
def test_unknown_command_prints_q():
    proc, mem, gfx, kbd = boot_novados()
    type_cmd(proc, gfx, kbd, "FOO BAR")
    ok = run_until(proc, lambda p: REPL_MAIN <= p.pc <= REPL_MAIN + 0x30,
                   max_cycles=40000)
    assert ok, "unknown command should not crash the REPL"