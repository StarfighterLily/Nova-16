"""End-to-end test for the Astrid Conway's Game of Life demo.

Compiles astrid/progs/conway.ast in its deterministic CONWAY_TEST mode (a
seeded glider advanced N generations, then HLT) and checks the resulting
layer-0 pixels against an independent Python Game-of-Life reference.

This exercises the real SREAD/read_screen + SWRITE/write_screen path that the
in-place, two-bit update relies on, and guards the out-of-range read clamp in
GFX.get_screen_val (edge cells read their dead border neighbours).
"""
import os
from collections import Counter

import pytest

# Path setup handled by tests/astrid/conftest.py

from nova_main import initialize_system


CONWAY_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "astrid",
                          "progs", "conway.ast")
CONWAY_SRC = os.path.abspath(CONWAY_SRC)

# The program's live region is [1, BOARD_HI] with a dead border; the test
# compiles with a small BOARD_HI so a full Python-emulated run stays fast.
BOARD_HI = 12
LO, HI = 1, BOARD_HI

# Glider seeded by conway.ast's CONWAY_TEST branch (x, y) with y as the row.
INITIAL_CELLS = {(2, 1), (3, 2), (1, 3), (2, 3), (3, 3)}


def _life_reference(cells, generations):
    """Standard bounded Game of Life: cells outside [LO, HI] are dead."""
    live = set(cells)
    for _ in range(generations):
        counts = Counter()
        for (x, y) in live:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx or dy:
                        counts[(x + dx, y + dy)] += 1
        nxt = set()
        for pos, n in counts.items():
            if n == 3 or (n == 2 and pos in live):
                if LO <= pos[0] <= HI and LO <= pos[1] <= HI:
                    nxt.add(pos)
        live = nxt
    return live


def _compile_and_run(generations, max_cycles=20_000_000):
    """Compile conway.ast with CONWAY_TEST=generations, assemble, run to halt."""
    import tempfile
    from astrid.compiler_api import compile_astrid
    from nova_assembler import Assembler

    tmpdir = tempfile.mkdtemp(prefix="conway_test_")
    asm_path = os.path.join(tmpdir, "conway.asm")
    compile_astrid(CONWAY_SRC, asm_path, log=lambda m: None,
                   defines={"CONWAY_TEST": generations, "BOARD_HI": BOARD_HI})
    Assembler().assemble(asm_path)

    bin_path = asm_path.replace(".asm", ".bin")
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    proc.pc = mem.load(bin_path)
    cycles = 0
    while cycles < max_cycles and not proc.halted:
        proc.step()
        cycles += 1
    return proc, gfx, cycles


def _live_cells(gfx):
    layer0 = gfx._compositor.layers[0]
    return {(x, y)
            for y in range(LO, HI + 1)
            for x in range(LO, HI + 1)
            if layer0[y, x]}


@pytest.mark.integration
@pytest.mark.parametrize("generations", [1, 2, 4])
def test_conway_glider_matches_reference(generations):
    """After N generations the emulator's live cells equal the reference."""
    proc, gfx, cycles = _compile_and_run(generations)
    assert proc.halted, f"conway did not halt (cycles={cycles})"

    expected = _life_reference(INITIAL_CELLS, generations)
    actual = _live_cells(gfx)
    assert actual == expected, (
        f"generation {generations}: emulator live cells differ from reference\n"
        f"  missing: {sorted(expected - actual)}\n"
        f"  extra:   {sorted(actual - expected)}"
    )


@pytest.mark.integration
def test_conway_glider_is_a_period_4_glider():
    """A glider returns to its own shape after 4 generations, shifted by (1,1).

    This is the signature property of a glider: period 4 with a one-cell
    diagonal translation, which only holds if the neighbour counts are exact.
    """
    proc, gfx, cycles = _compile_and_run(4)
    assert proc.halted
    after4 = _live_cells(gfx)
    # The glider must map onto itself under a single diagonal step.
    shifted = {(x + 1, y + 1) for (x, y) in INITIAL_CELLS}
    assert after4 == shifted, (
        f"glider did not translate by (1,1) after 4 gens: {sorted(after4)}"
    )
