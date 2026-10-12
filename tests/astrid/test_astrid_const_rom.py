"""Tier-2 Item 5, second half: `const` data lands in the read-only image.

The enforcement half (every write form to a const object is a compile error)
lives in ``test_astrid_const_enforcement.py``.  This file covers the *storage*
half: an unplaced ``const`` global is emitted as initialized data inside the
program image's read-only window instead of consuming writable global RAM.

Why that matters on a Princeton machine: Nova-16 has one 64KB address space
shared by code and data, so a lookup table declared ``const`` can be emitted
alongside the code and simply *read* -- it needs no writable storage at all.
That both saves RAM and makes the read-only intent real: the only way to
change such a table would be to write to the code region.

Covered here:
  * the const window address range (above the interrupt vectors, below the
    entry stub at 0x1000) for tables, scalars and strings;
  * ``const`` tables and scalars are readable at run time;
  * a placed ``const`` (``@ addr``) keeps its own segment, not the window;
  * the const window does not overlap the writable global region, so a const
    table and a normal global can coexist;
  * ``const`` struct globals reserve their full (packed) footprint;
  * the window-overflow diagnostic names the offending object.
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

_ROOT = str(Path(__file__).resolve().parent.parent.parent)
_ASTRID = os.path.join(_ROOT, "astrid")
for _p in (_ASTRID, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser
from astrid.codegen.codegen import CodeGenerator
from astrid.errors import CompileError


def compile_asm(source, enable_optimizations=True):
    """Compile Astrid source to assembly text."""
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    cg = CodeGenerator(enable_optimizations=enable_optimizations)
    return "\n".join(cg.generate(ast))


def compile_error(source):
    with pytest.raises(CompileError) as exc_info:
        compile_asm(source)
    return exc_info.value


def run_source(source, max_cycles=2000000):
    """Compile + assemble + run headlessly; returns (proc, cycles, mem)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ast", delete=False,
                                     encoding="utf-8") as f:
        f.write(source)
        source_path = f.name
    try:
        asm_text = compile_asm(source)
        asm_path = source_path.replace(".ast", ".asm")
        bin_path = source_path.replace(".ast", ".bin")
        with open(asm_path, "w", encoding="utf-8") as f:
            f.write(asm_text)
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)
        from nova_main import initialize_system
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        entry = mem.load(bin_path)
        proc.pc = entry
        cycle = 0
        while cycle < max_cycles and not proc.halted:
            cycle += 1
            proc.step()
        assert proc.halted, "Program did not halt"
        return proc, cycle, mem
    finally:
        for suffix in (".ast", ".asm", ".bin", ".sym", ".org"):
            path = source_path.replace(".ast", suffix)
            if os.path.exists(path):
                os.remove(path)


def _org_before(asm, label):
    """Address of the ORG segment that emits ``label`` (as an int)."""
    lines = asm.splitlines()
    idx = next(i for i, l in enumerate(lines) if l.strip() == label + ":")
    orgs = [l for l in lines[:idx] if l.startswith("ORG")]
    assert orgs, f"no ORG precedes {label}"
    return int(orgs[-1].split()[1], 16)

    return int(orgs[-1].split()[1], 16)


# ---------------------------------------------------------------------------
# Const window placement (assembly-shape assertions)
# ---------------------------------------------------------------------------

@pytest.mark.astrid
def test_const_table_emitted_in_const_window():
    """An unplaced const table is emitted in the read-only window segment."""
    asm = compile_asm("const int table[4] = {10, 20, 30, 40};\n"
                      "int main() { return table[2]; }")
    assert "; Const data -- read-only program image" in asm
    assert "ORG 0x0120" in asm
    assert "gvar_table:" in asm
    assert "DW 10, 20, 30, 40" in asm


@pytest.mark.astrid
def test_const_scalar_emitted_in_const_window():
    """An unplaced const scalar constant uses the same window as tables."""
    asm = compile_asm("const int K = 7;\nint main() { return K; }")
    assert "; Const data -- read-only program image" in asm
    assert "gvar_K:" in asm


@pytest.mark.astrid
def test_const_window_is_above_interrupt_vectors():
    """The window must not collide with the 8 interrupt vectors at 0x0100."""
    asm = compile_asm("const int a[8] = {1,2,3,4,5,6,7,8};\n"
                      "int main() { return a[0]; }")
    addr = _org_before(asm, "gvar_a")
    assert 0x0120 <= addr < 0x1000, f"const table landed at 0x{addr:04X}"


@pytest.mark.astrid
def test_const_and_global_do_not_share_storage():
    """A const table and a writable global occupy different regions."""
    asm = compile_asm("const int table[4] = {1,2,3,4};\n"
                      "int data[4] = {5,6,7,8};\n"
                      "int main() { return table[0] + data[0]; }")
    const_addr = _org_before(asm, "gvar_table")
    data_addr = _org_before(asm, "gvar_data")
    assert const_addr < 0x1000, f"const table not in window: 0x{const_addr:04X}"
    assert data_addr >= 0x8000, \
        f"global not in writable region: 0x{data_addr:04X}"


@pytest.mark.astrid
def test_placed_const_keeps_its_own_segment():
    """`const int t @ 0x9000` is emitted at its own address, not the window."""
    asm = compile_asm("const int t[2] @ 0x9000 = {0xAAAA, 0xBBBB};\n"
                      "int main() { return t[0]; }")
    assert "ORG 0x9000" in asm
    assert "Placed global 't'" in asm
    # A placed const is not part of the read-only window segment.
    const_segment = asm.split("; Const data")[1] if "; Const data" in asm else ""
    assert "0x9000" not in const_segment


@pytest.mark.astrid
def test_const_string_global_emitted_in_const_window():
    """A const string global also lands in the read-only window."""
    asm = compile_asm("const char msg[6] = \"hello\";\n"
                      "int main() { return msg[0]; }")
    assert "; Const data -- read-only program image" in asm
    assert "gvar_msg:" in asm


@pytest.mark.astrid
def test_const_struct_global_reserves_full_footprint():
    """A const struct global reserves every word of its layout."""
    asm = compile_asm("struct S { int a; int b; int c; };\n"
                      "const struct S s = {1, 2, 3};\n"
                      "int main() { return s.a + s.b + s.c; }")
    assert "; Const data -- read-only program image" in asm
    lines = asm.splitlines()
    i = lines.index("gvar_s:")
    emitted = [l.strip() for l in lines[i + 1:i + 4]]
    assert any("1" in l and "2" in l and "3" in l for l in emitted), emitted
    assert any("1" in l and "2" in l and "3" in l for l in emitted), emitted


# ---------------------------------------------------------------------------
# Runtime behaviour
# ---------------------------------------------------------------------------

@pytest.mark.astrid
def test_const_table_readable_at_runtime():
    """A const table in the ROM window reads back its initializers."""
    proc, _cycles, _mem = run_source(
        "const int table[4] = {10, 20, 30, 40};\n"
        "int main() { return table[0] + table[1] + table[2] + table[3]; }")
    assert proc.p0 == 100


@pytest.mark.astrid
def test_const_scalar_readable_at_runtime():
    """A const scalar constant reads back its value."""
    proc, _cycles, _mem = run_source(
        "const int K = 77;\nint main() { return K; }")
    assert proc.p0 == 77


@pytest.mark.astrid
def test_const_string_readable_at_runtime():
    """A const string in the ROM window is readable byte by byte."""
    proc, _cycles, _mem = run_source(
        "const char msg[6] = \"hello\";\n"
        "int main() { return msg[0] + msg[4]; }")   # 'h' + 'o'
    assert proc.p0 == ord('h') + ord('o')


@pytest.mark.astrid
def test_const_lookup_table_drives_computation():
    """The classic lookup-table use: index a const table at run time."""
    proc, _cycles, _mem = run_source(
        "const int squares[5] = {0, 1, 4, 9, 16};\n"
        "int main() {\n"
        "    int total = 0;\n"
        "    for (int i = 0; i < 5; i++) { total += squares[i]; }\n"
        "    return total;\n"
        "}")
    assert proc.p0 == 0 + 1 + 4 + 9 + 16


@pytest.mark.astrid
def test_placed_const_readable_at_runtime():
    """A const table placed with `@ addr` reads back correctly."""
    proc, _cycles, _mem = run_source(
        "const int t[3] @ 0x9000 = {0x1111, 0x2222, 0x3333};\n"
        "int main() { return t[1]; }")
    assert proc.p0 == 0x2222


@pytest.mark.astrid
def test_const_and_global_coexist_at_runtime():
    """A const table plus a writable global both work in one program."""
    proc, _cycles, _mem = run_source(
        "const int table[3] = {100, 200, 300};\n"
        "int data[3] = {1, 2, 3};\n"
        "int main() {\n"
        "    data[0] = 7;\n"
        "    return table[0] + table[2] + data[0];\n"
        "}")
    assert proc.p0 == 100 + 300 + 7


@pytest.mark.astrid
def test_const_struct_readable_at_runtime():
    """A const struct global reads back all of its fields."""
    proc, _cycles, _mem = run_source(
        "struct S { int a; int b; int c; };\n"
        "const struct S s = {11, 22, 33};\n"
        "int main() { return s.a + s.b + s.c; }")
    assert proc.p0 == 11 + 22 + 33


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

@pytest.mark.astrid
def test_const_window_overflow_names_object():
    """Overflowing the read-only window names the object that did not fit."""
    err = compile_error(
        "const int big[4000] = {0};\nint main() { return big[0]; }")
    assert "const data does not fit" in str(err)
    assert "big" in str(err)

