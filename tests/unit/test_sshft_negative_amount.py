"""SSHFT negative shift amount is signed (StarSys1 console scrolling).

The assembler encodes negative immediates as two's-complement imm16
(test_new_assembler_negative_immediate.py), and the ISA reference lists
SSHFT's shift amount among the operands that are read as a raw
immediate.  A negative amount must therefore reach the handler as -N,
not 65536-N: without sign handling, ``SSHFT 1, -8`` -- the
scroll-one-text-row primitive Star System 1 uses to scroll its console
window -- is interpreted as a +65528 shift, which numpy executes as
"copy an empty slice, then zero the whole layer", wiping the console
layer instead of scrolling it one glyph row upward.
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from nova.assembler import Assembler


def _run_program(cpu, memory, source):
    """Assemble *source*, load it at 0x0000 and run it to completion."""
    with tempfile.TemporaryDirectory() as tmpdir:
        asm_path = os.path.join(tmpdir, "prog.asm")
        with open(asm_path, "w", encoding="utf-8") as f:
            f.write(source)
        assembler = Assembler(log=None)
        assert assembler.assemble(asm_path)
        with open(os.path.join(tmpdir, "prog.bin"), "rb") as f:
            machine_code = f.read()
    for offset, byte in enumerate(machine_code):
        memory.write_byte(offset, byte)
    cpu.pc = 0
    while not cpu.halted:
        cpu.step()


@pytest.mark.unit
@pytest.mark.cpu
@pytest.mark.graphics
def test_sshft_negative_amount_shifts_active_layer_up(cpu, memory):
    """SSHFT 1, -8 must move layer content up 8px, not wipe the layer."""
    layer = cpu.gfx.get_layer_buffer_by_num(2)
    layer[56:64, 0:64] = 0x1F  # an 8px-tall ink band (one glyph row)

    _run_program(cpu, memory, "MOV VL, 2\nSSHFT 1, -8\nHLT\n")

    # The band landed one glyph row higher; the source row is now blank.
    assert int((layer[48:56, 0:64] != 0).sum()) == 64 * 8
    assert int((layer[56:64, 0:64] != 0).sum()) == 0
    # The rest of the layer was not zeroed by the shift.
    assert int((layer[72:80, 128:192] != 0).sum()) == 0  # still blank region


@pytest.mark.unit
@pytest.mark.cpu
@pytest.mark.graphics
def test_sshft_positive_amount_still_shifts_down(cpu, memory):
    """Positive amounts keep their existing downward-shift semantics."""
    layer = cpu.gfx.get_layer_buffer_by_num(3)
    layer[56:64, 0:64] = 0x1F

    _run_program(cpu, memory, "MOV VL, 3\nSSHFT 1, 8\nHLT\n")

    assert int((layer[64:72, 0:64] != 0).sum()) == 64 * 8
    assert int((layer[56:64, 0:64] != 0).sum()) == 0
