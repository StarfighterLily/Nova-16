"""Regression tests for the spilled-local storage region.

The hot-variable spill allocator previously carved per-function windows
upward from zero page (0x0080, 0x0100, 0x0180, ...). For multi-function
programs those windows marched straight into the emitted code segment
(ORG 0x1000+) and the running program overwrote its own instructions
(starfield's draw_stars corrupted its own loop and "halted" immediately).

Spill windows now live in the dedicated 0xC000-0xEFFF region, which is
clear of code, globals, string buffers, the sprite SCB, and the stack.
"""
import os
import re
import sys

# Path setup handled by tests/astrid/conftest.py

from nova_main import initialize_system
from astrid.codegen.codegen import CodeGenerator


def _compile_ast(path):
    """Compile a COPY of an existing .ast file; return (asm_path, tmp_source).

    Compiling a temporary copy keeps the shared example artifacts
    (astrid/<name>.asm/.bin/...) untouched; callers must remove both the
    generated files and tmp_source when done."""
    import shutil
    import tempfile
    fd, tmp_src = tempfile.mkstemp(suffix=".ast")
    os.close(fd)
    shutil.copyfile(path, tmp_src)
    from astrid_compiler import main as compiler_main
    out = tmp_src.replace(".ast", ".asm")
    old_argv = sys.argv
    sys.argv = [old_argv[0], tmp_src, "-o", out]
    try:
        compiler_main()
    finally:
        sys.argv = old_argv
    return out, tmp_src


def _cleanup(asm_path, tmp_source=None):
    paths = [asm_path.replace(".asm", ext) for ext in (".asm", ".bin", ".org", ".sym")]
    if tmp_source:
        paths.append(tmp_source)
    for p in paths:
        if os.path.exists(p):
            os.unlink(p)


def test_spill_region_constants_are_safe():
    """Region bounds must avoid every fixed system area."""
    start, end = CodeGenerator.SPILL_REGION_START, CodeGenerator.SPILL_REGION_END
    assert start >= 0x8000, "spill region would overlap code segments"
    assert end <= 0xF000, "spill region would overlap sprite SCB / stack"
    # Must not touch the ITOS (0xA000) / ITOB (0xA100) buffers.
    assert not (start <= 0xA000 < end)
    assert not (start <= 0xA100 < end)
    print("PASS test_spill_region_constants_are_safe")


def test_generated_direct_addresses_stay_out_of_code():
    """Every absolute memory operand in generated code must be >= 0x8000.

    Direct operands below 0x8000 can only be spills (now 0xC000+) -- any
    occurrence in 0x0120-0x7FFF means locals are being written over code
    or unmapped space."""
    astrid_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'astrid', 'progs')
    for name in ("starfield", "game", "simple", "screenflash"):
        src = os.path.join(astrid_dir, f"{name}.ast")
        if not os.path.exists(src):
            continue
        asm_path, tmp_src = _compile_ast(src)
        try:
            with open(asm_path, encoding="utf-8") as f:
                text = f.read()
            addrs = [int(m, 16) for m in re.findall(r"\[0x([0-9A-Fa-f]{4})\]", text)]
            bad = [a for a in addrs if 0x0120 <= a < 0x8000]
            assert not bad, (
                f"{name}: direct addresses inside code/low RAM: "
                f"{[hex(a) for a in sorted(set(bad))]}"
            )
            print(f"PASS test_generated_direct_addresses_stay_out_of_code ({name})")
        finally:
            _cleanup(asm_path, tmp_src)


def test_starfield_runs_without_self_corruption():
    """The starfield example must loop forever and render stars."""
    astrid_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'astrid', 'progs')
    src = os.path.join(astrid_dir, "starfield.ast")
    asm_path, tmp_src = _compile_ast(src)
    try:
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)
        bin_path = asm_path.replace(".asm", ".bin")
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(bin_path)
        c = 0
        while c < 150000 and not proc.halted:
            c += 1
            proc.step()
        assert not proc.halted, (
            f"starfield halted after {c} cycles (self-corruption regression)"
        )
        nz = int((gfx.screen != 0).sum())
        assert nz > 0, "starfield rendered no stars"
        print(f"PASS test_starfield_runs_without_self_corruption "
              f"(cycles={c}, pixels={nz})")
    finally:
        _cleanup(asm_path, tmp_src)


if __name__ == "__main__":
    test_spill_region_constants_are_safe()
    test_generated_direct_addresses_stay_out_of_code()
    test_starfield_runs_without_self_corruption()
    print("All spill-region regression tests passed!")
