"""Phase 2 layer discipline: scrolling, banner retention, CLS, backspace wipe."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from conftest import boot_novados, type_cmd, run_until, in_repl


def layer_pixels(gfx, layer):
    return int((gfx._compositor.layers[layer] != 0).sum())


@pytest.mark.unit
@pytest.mark.integration
def test_boot_banner_on_static_layer_console_empty():
    """Banner lives on layer 2; console layer has no boot-row junk."""
    proc, mem, gfx, kbd = boot_novados()
    ok = run_until(proc, in_repl, max_cycles=20000)
    assert ok, f"boot did not reach the REPL; PC=0x{proc.pc:04X}"
    # Banner rows 0-1 on the static layer 2
    top_static = gfx._compositor.layers[2][0:16, :]
    assert int((top_static != 0).sum()) > 0, "banner missing on static layer 2"
    # Console cursor starts below the banner (row 3)
    assert mem.read_byte(0x0025) == 3, f"cursor row should be 3, got {mem.read_byte(0x0025)}"
    assert mem.read_byte(0x0024) == 0


@pytest.mark.unit
@pytest.mark.integration
def test_bottom_row_newline_scrolls_instead_of_wrapping():
    """Cursor at the last row + newline must scroll, never wrap to row 0."""
    proc, mem, gfx, kbd = boot_novados()
    assert run_until(proc, in_repl, max_cycles=20000)
    # Park the cursor on the bottom row and emit a newline through NEWLINE
    mem.write_byte(0x0024, 0)
    mem.write_byte(0x0025, 31)
    type_cmd(proc, gfx, kbd, "")
    ok = run_until(proc, lambda p: in_repl(p) and mem.read_byte(0x0025) == 31,
                   max_cycles=40000)
    assert ok, f"bottom newline wrapped (row={mem.read_byte(0x0025)}, PC=0x{proc.pc:04X})"
    assert mem.read_byte(0x0025) == 31, "cursor must clamp to the last row"
    # Static banner survived the scroll
    top_static = gfx._compositor.layers[2][0:16, :]
    assert int((top_static != 0).sum()) > 0, "scroll erased the static banner"


@pytest.mark.unit
@pytest.mark.integration
def test_help_scrolls_and_keeps_banner():
    """HELP output lands on the volatile layer; banner layer intact."""
    proc, mem, gfx, kbd = boot_novados()
    assert run_until(proc, in_repl, max_cycles=20000)
    banner_before = layer_pixels(gfx, 2)
    assert banner_before > 0
    type_cmd(proc, gfx, kbd, "HELP")
    ok = run_until(proc, lambda p: layer_pixels(gfx, 1) > 0 and in_repl(p),
                   max_cycles=60000)
    assert ok, "HELP produced no console-layer pixels"
    assert layer_pixels(gfx, 2) == banner_before, "HELP disturbed the static banner"
    # Cursor stayed in the scroll region, never wrapped to the top
    assert mem.read_byte(0x0025) >= 3, f"cursor wrapped above console (row={mem.read_byte(0x0025)})"


@pytest.mark.unit
@pytest.mark.integration
def test_cls_clears_console_but_keeps_banner():
    """CLS wipes layer 1, keeps banner layer 2, resets cursor to row 3."""
    proc, mem, gfx, kbd = boot_novados()
    assert run_until(proc, in_repl, max_cycles=20000)
    type_cmd(proc, gfx, kbd, "HELP")
    assert run_until(proc, lambda p: layer_pixels(gfx, 1) > 0 and in_repl(p),
                     max_cycles=60000)
    banner_before = layer_pixels(gfx, 2)
    type_cmd(proc, gfx, kbd, "CLS")
    ok = run_until(proc, lambda p: in_repl(p) and layer_pixels(gfx, 1) == 0,
                   max_cycles=60000)
    assert ok, f"CLS did not clear the console layer (pixels={layer_pixels(gfx, 1)})"
    assert layer_pixels(gfx, 2) == banner_before, "CLS erased the static banner"
    assert mem.read_byte(0x0024) == 0 and mem.read_byte(0x0025) == 3, \
        f"CLS cursor should be (0,3), got ({mem.read_byte(0x0024)},{mem.read_byte(0x0025)})"


@pytest.mark.unit
@pytest.mark.integration
def test_backspace_visually_erases_echo():
    """Backspace must erase the echoed glyph cell, not just the buffer."""
    proc, mem, gfx, kbd = boot_novados()
    assert run_until(proc, in_repl, max_cycles=20000)

    # Wait for the "> " prompt to finish rendering so we have a stable
    # baseline (the '>' glyph al.one is ~16 pixels).
    assert run_until(
        proc,
        lambda p: (int((gfx._compositor.layers[1] != 0).sum()) >= 16
                   and mem.read_byte(0x0024) >= 2),
        max_cycles=40000), "prompt never rendered"
    prompt_pixels = int((gfx._compositor.layers[1] != 0).sum())

    # Type one char (no Enter yet); wait for its glyph to appear *in addition*
    # to the prompt baseline.  The glyph is 8x8 = 64 cells but may not all
    # light up; "prompt_pixels + 8" is a conservative lower bound.
    kbd.add_key(ord("Q"))
    assert run_until(
        proc,
        lambda p: int((gfx._compositor.layers[1] != 0).sum())
                   > prompt_pixels + 8,
        max_cycles=40000), "Q did not echo"
    before = int((gfx._compositor.layers[1] != 0).sum())

    # Backspace the char; the echo cell must go blank again.
    kbd.add_key(0x08)
    assert run_until(
        proc,
        lambda p: int((gfx._compositor.layers[1] != 0).sum()) < before,
        max_cycles=40000), \
        f"backspace left ghost pixels ({before} -> {int((gfx._compositor.layers[1] != 0).sum())})"

    # Finish the (now empty) line so the REPL returns cleanly.
    kbd.add_key(0x93)
    assert run_until(proc, in_repl, max_cycles=40000)
