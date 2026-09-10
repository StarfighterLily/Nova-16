"""Phase 1 exit criteria 2 & 4: REPL command handling (HELP, PEEK, variables)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from conftest import boot_novados, type_cmd, run_until, in_repl

VARS_BASE = 0xD000


def layer_pixels(gfx):
    return int((gfx._compositor.layers[0] != 0).sum())


@pytest.mark.unit
@pytest.mark.integration
def test_help_prints_and_returns_to_repl():
    proc, mem, gfx, kbd = boot_novados()
    baseline = layer_pixels(gfx)
    type_cmd(proc, gfx, kbd, "HELP")
    ok = run_until(
        proc,
        lambda p: layer_pixels(gfx) > baseline + 20 and in_repl(p),
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
                   and in_repl(p)),
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
        lambda p: (layer_pixels(gfx) > baseline and in_repl(p)
                   and mem.read_byte(0x0025) >= 4),
        max_cycles=60000)
    assert ok, f"PEEK produced no output (pixels {baseline} -> {layer_pixels(gfx)}, PC=0x{proc.pc:04X})"
    # Layout after "PEEK 0x0000<Enter>": row 2 holds the echoed command,
    # row 3 holds the hex output "4E 44" (the OS signature bytes).
    row2 = int((gfx._compositor.layers[0][16:24, :] != 0).sum())
    row3 = int((gfx._compositor.layers[0][24:32, :] != 0).sum())
    assert row2 > 0, "echoed command not rendered on row 2"
    assert row3 > 0, "hex output '4E 44' not rendered on row 3"
    # Signature bytes really are the ND signature in memory
    assert mem.read_bytes_direct(0x0000, 2) == [0x4E, 0x44]


@pytest.mark.unit
def test_unknown_command_prints_q():
    proc, mem, gfx, kbd = boot_novados()
    type_cmd(proc, gfx, kbd, "FOO BAR")
    ok = run_until(proc, in_repl, max_cycles=40000)
    assert ok, "unknown command should not crash the REPL"


# ---------------------------------------------------------------------------
# GUI-path regressions: nova_gui.py maps physical Enter -> kbd.press_key(
# 'enter') -> scan code 0x0A, and Backspace -> 'backspace' -> 0x08. The
# design docs' 0x93/0x92 codes are never produced by the emulator's
# keyboard path. These tests inject keys exactly the way the GUI does.
# ---------------------------------------------------------------------------

def type_cmd_gui(kbd, cmd):
    """Type a command through the real GUI path (press_key per character)."""
    for ch in cmd:
        kbd.press_key(ch)
    kbd.press_key('enter')


@pytest.mark.unit
@pytest.mark.integration
def test_gui_path_typing_executes_commands():
    """Regression: commands typed the way the GUI sends them must execute.
    (Enter arrives as 0x0A here, not the 0x93 the old GETLINE expected.)"""
    proc, mem, gfx, kbd = boot_novados()
    baseline = layer_pixels(gfx)
    type_cmd_gui(kbd, "HELP")
    ok = run_until(
        proc,
        lambda p: layer_pixels(gfx) > baseline + 20 and in_repl(p),
        max_cycles=60000)
    assert ok, f"GUI-path typing did not execute HELP (pixels {baseline} -> {layer_pixels(gfx)}, PC=0x{proc.pc:04X})"


@pytest.mark.unit
@pytest.mark.integration
def test_gui_control_codes_swallowed_and_backspace_edits():
    """Regression: Tab/Backspace-from-empty-line must be swallowed (no glyph
    garbage, no corruption), Backspace must delete the previous character,
    and GUI Enter (0x0A) must terminate the line.
    Types: Tab, BS(empty), 'A = 6', BS, '5', Enter -> A must be 5."""
    proc, mem, gfx, kbd = boot_novados()
    kbd.press_key('tab')            # 0x09 -> ignored
    kbd.press_key('backspace')      # 0x08 -> no-op on empty line
    # Build the line char-by-char with NO premature Enter: 'A = 6', then
    # backspace the '6', type the corrected '5', then terminate once.
    for ch in "A = 6":
        kbd.press_key(ch)
    kbd.press_key('backspace')      # delete '6' from the line buffer
    kbd.press_key('5')              # correct digit
    kbd.press_key('enter')          # 0x0A terminates (GUI code)
    ok = run_until(
        proc,
        lambda p: (mem.read_byte(VARS_BASE) == 0
                   and mem.read_byte(VARS_BASE + 1) == 5
                   and in_repl(p)),
        max_cycles=60000)
    assert ok, (f"A never became 5 (line editing failed: A=0x{mem.read_byte(VARS_BASE+1):02X}); "
                f"PC=0x{proc.pc:04X}")