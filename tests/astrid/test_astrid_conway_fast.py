"""End-to-end test for the fast, full-screen Astrid Game of Life.

Compiles astrid/progs/conway_fast.ast in CONWAY_TEST mode (a fixed pattern
of gliders, blinkers, an R-pentomino and a block placed on the screen edges
and the 16-cell word boundaries), runs N generations, then checks against an
independent Python Game-of-Life reference on a 256x256 board with dead
cells beyond the edges:

* the bit-packed board in RAM (the kernel's own state), and
* layer 0 of the screen (what the diff-only redraw painted).

Comparing both catches kernel bugs and redraw bugs separately.
"""
import os
import tempfile
from collections import Counter

import pytest

# Path setup handled by tests/astrid/conftest.py

from nova_main import initialize_system


SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",
                                   "astrid", "progs", "conway_fast.ast"))

SIZE = 256
ROW0 = 0x5022       # board row 0 (see the memory map in conway_fast.ast)
ROW_BYTES = 34
ALIVE = 0x0F

# Must match the CONWAY_TEST branch of conway_fast.ast, as (x, y).
INITIAL_CELLS = {
    (1, 0), (2, 1), (0, 2), (1, 2), (2, 2),
    (15, 40), (16, 40), (17, 40),
    (255, 100), (255, 101), (255, 102),
    (128, 127), (129, 127), (127, 128), (128, 128), (128, 129),
    (253, 252), (254, 253), (252, 254), (253, 254), (254, 254),
    (31, 254), (32, 254), (31, 255), (32, 255),
}


def _life_reference(cells, generations):
    live = set(cells)
    for _ in range(generations):
        counts = Counter()
        for (x, y) in live:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx or dy:
                        counts[(x + dx, y + dy)] += 1
        live = {pos for pos, n in counts.items()
                if (n == 3 or (n == 2 and pos in live))
                and 0 <= pos[0] < SIZE and 0 <= pos[1] < SIZE}
    return live


_cache = {}


def _run(generations, max_cycles=50_000_000):
    if generations in _cache:
        return _cache[generations]
    from astrid.compiler_api import compile_astrid
    from nova_assembler import Assembler

    tmpdir = tempfile.mkdtemp(prefix="conway_fast_test_")
    asm_path = os.path.join(tmpdir, "conway_fast.asm")
    compile_astrid(SRC, asm_path, log=lambda m: None,
                   defines={"CONWAY_TEST": generations})
    Assembler().assemble(asm_path)

    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    proc.pc = mem.load(asm_path.replace(".asm", ".bin"))
    cycles = 0
    while cycles < max_cycles and not proc.halted:
        proc.step()
        cycles += 1
    assert proc.halted, f"conway_fast did not halt (cycles={cycles})"

    board = set()
    for y in range(SIZE):
        for k in range(16):
            word = mem.read_word(ROW0 + y * ROW_BYTES + 2 * k)
            for bit in range(16):
                if word & (0x8000 >> bit):
                    board.add((16 * k + bit, y))
    layer0 = gfx._compositor.layers[0]
    screen = {(x, y) for y in range(SIZE) for x in range(SIZE)
              if layer0[y, x]}
    bad_colour = {(x, y) for (x, y) in screen if layer0[y, x] != ALIVE}
    _cache[generations] = (board, screen, bad_colour, cycles)
    return _cache[generations]


def _diff(expected, actual):
    return (f"missing: {sorted(expected - actual)[:20]}\n"
            f"  extra:   {sorted(actual - expected)[:20]}")


@pytest.mark.integration
@pytest.mark.parametrize("generations", [0, 1, 2, 5, 12])
def test_board_matches_reference(generations):
    board, _, _, _ = _run(generations)
    expected = _life_reference(INITIAL_CELLS, generations)
    assert board == expected, (
        f"gen {generations}: board RAM differs\n  {_diff(expected, board)}")


@pytest.mark.integration
@pytest.mark.parametrize("generations", [0, 1, 2, 5, 12])
def test_screen_matches_reference(generations):
    _, screen, bad_colour, _ = _run(generations)
    expected = _life_reference(INITIAL_CELLS, generations)
    assert screen == expected, (
        f"gen {generations}: screen differs\n  {_diff(expected, screen)}")
    assert not bad_colour, f"cells not drawn ALIVE: {sorted(bad_colour)[:10]}"


@pytest.mark.integration
def test_generation_cost_is_bounded():
    """One generation over the full 256x256 board stays far below the
    ~16M steps/s budget (the old per-cell version needed tens of millions)."""
    _, _, _, c1 = _run(1)
    _, _, _, c2 = _run(2)
    per_gen = c2 - c1
    assert per_gen < 300_000, f"one generation took {per_gen} steps"
