"""Tier-2 Item 5: `const` is now enforced (read-only) at compile time.

Before this work the lexer accepted ``const`` with the comment "treated as
a normal variable": nothing stopped ``const int table[] = {...}`` from
being reassigned.  Enforcement now covers every direct write form:

  * ``x = v`` / ``x += v`` (scalar, local, global, param)
  * ``arr[i] = v`` (const arrays) and ``p[i] = v`` / ``*p = v`` /
    ``(*p)++`` (writes through a ``const T *`` pointer)
  * ``s.f = v``, ``s.f += v``, ``s.f++`` (const structs, to any member
    depth, including through pointers ``q->f``)
  * ``++x`` / ``--x`` (prefix as well as postfix)

Declarations/initializers are NOT writes, so ``const int x = 5;`` (global,
local, and via hidden sret for struct returns) remains legal, as do reads,
``&x``, and rebinding a non-const pointer variable.  Locals and params
shadow globals per C scoping.

Item 5's second half -- emitting unplaced const globals into the code
region (ROM tables) -- lives in test_astrid_const_rom.py.
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

_ROOT = str(Path(__file__).resolve().parent.parent.parent)
_ASTRID = os.path.join(_ROOT, "astrid")
for p in (_ASTRID, _ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser
from astrid.codegen.codegen import CodeGenerator
from astrid.errors import CompileError
from nova_main import initialize_system


def compile_asm(source, enable_optimizations=True):
    """Compile Astrid source to assembly text."""
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    cg = CodeGenerator(enable_optimizations=enable_optimizations)
    return "\n".join(cg.generate(ast))


def compile_error(source):
    """Compile and return the CompileError raised (fails the test otherwise)."""
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


# ---------------------------------------------------------------------------
# Rejected: every direct write form
# ---------------------------------------------------------------------------

@pytest.mark.astrid
def test_const_global_scalar_assignment_rejected():
    err = compile_error("const int x = 5; int main() { x = 6; return x; }")
    assert "cannot assign to const variable 'x'" in str(err)


@pytest.mark.astrid
def test_const_global_compound_assignment_rejected():
    err = compile_error("const int x = 5; int main() { x += 1; return x; }")
    assert "const variable 'x'" in str(err)


@pytest.mark.astrid
def test_const_global_postfix_rejected():
    err = compile_error("const int x = 5; int main() { x++; return x; }")
    assert "const variable 'x'" in str(err)


@pytest.mark.astrid
def test_const_global_prefix_rejected():
    err = compile_error("const int x = 5; int main() { ++x; return x; }")
    assert "const variable 'x'" in str(err)


@pytest.mark.astrid
def test_const_local_scalar_assignment_rejected():
    err = compile_error(
        "int main() { const int c = 1; c = 2; return c; }")
    assert "const variable 'c'" in str(err)


@pytest.mark.astrid
def test_const_param_assignment_rejected():
    err = compile_error(
        "int f(const int a) { a = 2; return a; } int main() { return f(1); }")
    assert "const variable 'a'" in str(err)


@pytest.mark.astrid
def test_const_array_element_assignment_rejected():
    err = compile_error(
        "const int arr[3] = {1, 2, 3};"
        "int main() { arr[0] = 9; return arr[0]; }")
    assert "const variable 'arr'" in str(err)


@pytest.mark.astrid
def test_const_array_element_compound_rejected():
    err = compile_error(
        "const int arr[3] = {1, 2, 3};"
        "int main() { arr[1] += 9; return arr[1]; }")
    assert "const variable 'arr'" in str(err)


@pytest.mark.astrid
def test_const_local_array_element_assignment_rejected():
    err = compile_error(
        "int main() { const int arr[2] = {1, 2}; arr[0] = 3; return arr[0]; }")
    assert "const variable 'arr'" in str(err)


@pytest.mark.astrid
def test_const_struct_member_assignment_rejected():
    err = compile_error(
        "struct S { int x; }; const struct S s = {1};"
        "int main() { s.x = 2; return s.x; }")
    assert "const variable 's'" in str(err)


@pytest.mark.astrid
def test_const_struct_member_compound_rejected():
    err = compile_error(
        "struct S { int x; }; const struct S s = {1};"
        "int main() { s.x += 2; return s.x; }")
    assert "const variable 's'" in str(err)


@pytest.mark.astrid
def test_const_struct_member_postfix_rejected():
    err = compile_error(
        "struct S { int x; }; const struct S s = {1};"
        "int main() { s.x++; return s.x; }")
    assert "const variable 's'" in str(err)


@pytest.mark.astrid
def test_const_nested_struct_member_assignment_rejected():
    err = compile_error(
        "struct Inner { int v; }; struct Outer { struct Inner in; };"
        "const struct Outer o = {1};"
        "int main() { o.in.v = 2; return o.in.v; }")
    assert "const variable 'o'" in str(err)


@pytest.mark.astrid
def test_const_struct_array_element_member_assignment_rejected():
    err = compile_error(
        "struct S { int x; }; const struct S arr[2] = {1, 2};"
        "int main() { arr[0].x = 9; return arr[0].x; }")
    assert "const variable 'arr'" in str(err)


@pytest.mark.astrid
def test_const_struct_byval_param_member_assignment_rejected():
    err = compile_error(
        "struct S { int x; };"
        "int f(const struct S s) { s.x = 2; return s.x; }"
        "int main() { struct S a = {1}; return f(a); }")
    assert "const variable 's'" in str(err)

