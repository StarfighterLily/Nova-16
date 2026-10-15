"""Both assemblers reject ORG segments that overlap.

The loader writes segments in address order, so an overlap used to assemble
cleanly and corrupt memory at load time: the Astrid NovaDOS kernel grew past
its globals at 0x4200 (2026-10-15) and the globals were loaded over the tail
of its code.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

OVERLAPPING = """
ORG 0x1000
    MOV P0, 1
    MOV P1, 2
    HLT
ORG 0x1004
    DW 0x1234
"""

ADJACENT = """
ORG 0x1000
    HLT
ORG 0x1001
    DW 0x1234
"""


def _new(path):
    from nova_assembler import Assembler
    asm = Assembler(log=None, trace=False)
    return asm.assemble(str(path)), asm.errors


def _legacy(path):
    from nova_assembler1 import Assembler
    asm = Assembler()
    asm.log = None
    return asm.assemble(str(path)), asm.errors


@pytest.mark.parametrize("assemble", [_new, _legacy], ids=["new", "legacy"])
def test_overlapping_segments_are_an_error(tmp_path, assemble):
    src = tmp_path / "overlap.asm"
    src.write_text(OVERLAPPING)
    ok, errors = assemble(src)
    assert not ok
    assert any("ORG segments overlap: 0x1000-" in e and "0x1004-0x1005" in e
               for e in errors), errors


@pytest.mark.parametrize("assemble", [_new, _legacy], ids=["new", "legacy"])
def test_adjacent_segments_are_fine(tmp_path, assemble):
    src = tmp_path / "adjacent.asm"
    src.write_text(ADJACENT)
    ok, errors = assemble(src)
    assert ok, errors
