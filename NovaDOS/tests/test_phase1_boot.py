"""Phase 1 exit criterion 1: kernel boots, prints banner, reaches the REPL."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from conftest import KERNEL, boot_novados, run_until


@pytest.mark.unit
@pytest.mark.integration
def test_boot_reaches_repl():
    proc, mem, gfx, kbd = boot_novados()
    ok = run_until(proc, lambda p: p.pc == 0x0421 or 0x0C03 <= p.pc <= 0x0C30,
                   max_cycles=20000)
    assert ok, f"boot did not reach the REPL; PC=0x{proc.pc:04X}"
    # OS signature "ND" written at boot
    assert mem.read_bytes_direct(0x0000, 2) == [0x4E, 0x44], "signature missing"
    # VARS_BASE word (big-endian) init to 0xD000
    assert mem.read_word(0x0008) == 0xD000
    # PROG_BASE word = 0x1000
    assert mem.read_word(0x000C) == 0x1000


@pytest.mark.unit
@pytest.mark.graphics
def test_boot_banner_pixels_on_layer0():
    proc, mem, gfx, kbd = boot_novados()
    run_until(proc, lambda p: 0x0C03 <= p.pc <= 0x0C30, max_cycles=20000)
    # Banner glyphs ("NOVADOS" / "READY.") drawn on layer 0 buffer
    non_zero = int((gfx._compositor.layers[0] != 0).sum())
    assert non_zero > 0, "banner produced no pixels on layer 0"

    # The glyphs live near the top rows (row 0 and row 1)
    top_rows = gfx._compositor.layers[0][0:16, :]
    assert int((top_rows != 0).sum()) > 0, "no banner glyphs in top rows"


@pytest.mark.unit
def test_boot_wires_ivt_vectors():
    proc, mem, gfx, kbd = boot_novados()
    run_until(proc, lambda p: 0x0C03 <= p.pc <= 0x0C30, max_cycles=20000)
    # Vector handlers copied into the IVT (0x0100 + v*4: word addresses)
    v0 = mem.read_word(0x0100)
    v4 = mem.read_word(0x0110)
    assert v0 != 0, "timer vector not wired"
    assert v4 != 0, "SYS vector not wired"
    # All vectors should point into kernel code (0x0120-0x1000)
    for v in range(8):
        addr = mem.read_word(0x0100 + v * 4)
        assert 0x0120 <= addr < 0x1000, f"vector {v} points outside the kernel: 0x{addr:04X}"