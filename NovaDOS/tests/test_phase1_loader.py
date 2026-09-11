"""Phase 1 exit criterion 3: NDF LOAD / RUN from a banked volume."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from conftest import boot_novados, type_cmd, run_until, seed_bank, in_repl

# Built from NovaDOS/src/sample.asm (ORG 0x1000)
SAMPLE_BIN = Path(__file__).resolve().parent.parent / "build" / "sample.bin"


@pytest.fixture(scope="module")
def sample_payload():
    assert SAMPLE_BIN.exists(), f"missing {SAMPLE_BIN} — run nova_assembler.py first"
    return SAMPLE_BIN.read_bytes()


@pytest.mark.unit
@pytest.mark.integration
def test_load_runs_sample_returns_to_repl(sample_payload):
    proc, mem, gfx, kbd = boot_novados()
    seed_bank(mem, 3, b"SAMPLE", sample_payload, entry_addr=0x1000)
    type_cmd(proc, gfx, kbd, "BANK 3")
    type_cmd(proc, gfx, kbd, "LOAD SAMPLE")
    type_cmd(proc, gfx, kbd, "RUN")
    # The sample sets marker bytes at 0x00E0/0x00E1 and RETs to the REPL.
    ok = run_until(
        proc,
        lambda p: mem.read_byte(0x00E0) == 0x42 and in_repl(p),
        max_cycles=60000)
    assert ok, f"sample marker byte never set (mem[0x00E0]=0x{mem.read_byte(0x00E0):02X})"
    assert mem.read_byte(0x00E1) == 0x2A


@pytest.mark.unit
@pytest.mark.integration
def test_bank_command_switches_bank(sample_payload):
    proc, mem, gfx, kbd = boot_novados()
    seed_bank(mem, 3, b"SAMPLE", sample_payload, entry_addr=0x1000)
    type_cmd(proc, gfx, kbd, "BANK 3")
    ok = run_until(
        proc,
        lambda p: mem.read_byte(0x0010) == 3 and mem.current_bank == 3,
        max_cycles=40000)
    assert ok, "CUR_BANK not set to 3"
    assert mem.current_bank == 3, "emulator BANK register not switched"


@pytest.mark.unit
@pytest.mark.integration
def test_dir_lists_volume(sample_payload):
    proc, mem, gfx, kbd = boot_novados()
    baseline = int((gfx._compositor.layers[1] != 0).sum())
    seed_bank(mem, 3, b"SAMPLE", sample_payload, entry_addr=0x1000)
    type_cmd(proc, gfx, kbd, "BANK 3")
    type_cmd(proc, gfx, kbd, "DIR")
    ok = run_until(
        proc,
        lambda p: (int((gfx._compositor.layers[1] != 0).sum()) > baseline
                   and in_repl(p)),
        max_cycles=60000)
    assert ok, f"DIR printed no file name (pixels {baseline} -> {int((gfx._compositor.layers[1] != 0).sum())})"