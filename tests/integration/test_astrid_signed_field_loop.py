"""Signed struct-field comparison codegen, pinned without a user program.

Derived from the old sprttest.ast integration test: a global struct field
used as a `while (field > 0)` condition must be compared with SIGNED
semantics.  When the field goes negative (0xFFFC = -4), an unsigned
compare would read 0xFFFC > 0 and spin forever -- the loop must instead
terminate and the field's signed value (-4) must survive the return.

The runtime assertion is the strong check: a signed-compare regression
turns this test into a hang caught by the step cap, never a clean fail.
"""
import os
import sys
from pathlib import Path

import pytest

from nova_main import initialize_system

# astrid_compiler lives under <root>/astrid; the astrid test package adds it
# via its own conftest, but integration tests must add it themselves.
_ASTRID_DIR = str(Path(__file__).resolve().parent.parent.parent / "astrid")
if _ASTRID_DIR not in sys.path:
    sys.path.insert(0, _ASTRID_DIR)

SRC = """
struct Player {
    int hit;
};
struct Player p;

int main() {
    p.hit = 4;
    while (p.hit > 0) {
        p.hit -= 8;
    }
    return p.hit;
}
"""


def _compile_source(source, name):
    """Compile Astrid source text; return the generated .asm path."""
    from astrid_compiler import main as compiler_main
    base = os.path.join(os.environ.get("TEMP", "/tmp"), name)
    src_path = base + ".ast"
    with open(src_path, "w", encoding="utf-8") as f:
        f.write(source)
    old_argv = sys.argv
    sys.argv = [old_argv[0], src_path, "-o", base + ".asm"]
    try:
        assert compiler_main() == 0, "Astrid compilation failed"
    finally:
        sys.argv = old_argv
    return base + ".asm"


def _cleanup(asm_path):
    for ext in (".ast", ".asm", ".bin", ".org", ".sym"):
        path = asm_path.replace(".asm", ext)
        if os.path.exists(path):
            os.unlink(path)


@pytest.mark.integration
def test_signed_struct_field_loop_exits_on_negative_value():
    """`while (p.hit > 0)` on a global struct field must use a signed
    comparison: 4 -> -4 exits the loop, an unsigned compare would spin."""
    from nova_assembler import Assembler

    asm_path = _compile_source(SRC, "astrid_signed_field_loop")
    try:
        assert Assembler().assemble(asm_path), "assembly failed"

        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(asm_path.replace(".asm", ".bin"))
        for _ in range(50000):
            proc.step()
            if proc.halted:
                break

        assert proc.halted, (
            "signed struct-field loop must terminate (4 -> -4); an unsigned "
            "comparison would read 0xFFFC > 0 and spin forever")
        assert proc.p0 == 0xFFFC, (
            f"return value must be -4 (0xFFFC), got 0x{proc.p0:04X}")

        print("PASS signed struct-field loop: p.hit 4 -> -4, loop exited")
    finally:
        _cleanup(asm_path)
