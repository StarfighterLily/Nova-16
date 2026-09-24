"""Tier-2 Item 6: signed/unsigned division and C-conformant constant folds.

Astrid's hardware DIV/MOD are unsigned.  Before this work every '/' and
'%' went through them raw, so `-7 / 2` evaluated to 0x7FFD (32764)
instead of C's -3, and the constant folders disagreed with each other and
with C (ExpressionSimplifier floored to -4; Python's % gave 1 for -7 % 2).

Policy (mirrors _use_signed_comparison, so division and relational ops
agree on the same operands):

  * ``signed_int`` operand or a top-bit constant (negative literal)
    -> the sign-corrected CMP/JGE/NEG DIV sequence with C truncation
    toward zero; '%' takes the sign of the dividend.
  * ``unsigned_int`` / ``char`` / plain ``int`` -> raw hardware DIV/MOD.
    Plain int is historically unsigned on this machine (addresses live at
    0x8000+); for values < 0x8000 both interpretations agree bit-for-bit,
    so existing programs are byte-identical.
  * Folds for '/' and '%' now truncate toward zero / take the dividend's
    sign in ALL THREE folders (ExpressionSimplifier, codegen's inline
    fold, and _const_eval for global initializers), matching C and the
    preprocessor's own #if math.
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
from nova_main import initialize_system


def compile_asm(source, enable_optimizations=True):
    """Compile Astrid source to assembly text."""
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    cg = CodeGenerator(enable_optimizations=enable_optimizations)
    return "\n".join(cg.generate(ast))


def run_source(source, enable_optimizations=True, max_cycles=2000000):
    """Compile + assemble + run headlessly; returns (proc, cycles, mem)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ast", delete=False,
                                     encoding="utf-8") as f:
        f.write(source)
        source_path = f.name
    try:
        asm_text = compile_asm(source, enable_optimizations)
        asm_path = source_path.replace(".ast", ".asm")
        bin_path = source_path.replace(".ast", ".bin")
        with open(asm_path, "w", encoding="utf-8") as f:
            f.write(asm_text)
        from nova_assembler import Assembler
        asm = Assembler()
        asm.assemble(asm_path)
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
# Runtime semantics: signed division / remainder
# ---------------------------------------------------------------------------

@pytest.mark.astrid
@pytest.mark.parametrize("enable_optimizations", [True, False],
                         ids=["opts_on", "opts_off"])
def test_signed_div_truncates_toward_zero(enable_optimizations):
    """signed -7 / 2 == -3 (never the unsigned 0x7FFD = 32764)."""
    proc, _, _ = run_source(
        "int main() { signed int a = -7; return a / 2; }",
        enable_optimizations=enable_optimizations)
    assert proc.p0 == 0xFFFD  # -3


@pytest.mark.astrid
@pytest.mark.parametrize("enable_optimizations", [True, False],
                         ids=["opts_on", "opts_off"])
def test_signed_mod_takes_sign_of_dividend(enable_optimizations):
    """signed -7 % 2 == -1 (C), not Python's +1 or the unsigned pattern."""
    proc, _, _ = run_source(
        "int main() { signed int a = -7; return a % 2; }",
        enable_optimizations=enable_optimizations)
    assert proc.p0 == 0xFFFF  # -1


@pytest.mark.astrid
def test_signed_div_both_negative():
    """signed -7 / -2 == 3."""
    proc, _, _ = run_source(
        "int main() { signed int a = -7; signed int b = -2; return a / b; }")
    assert proc.p0 == 3


@pytest.mark.astrid
def test_signed_div_divisor_negative():
    """signed 7 / -2 == -3 (truncated, not floored to -4)."""
    proc, _, _ = run_source(
        "int main() { signed int a = 7; signed int b = -2; return a / b; }")
    assert proc.p0 == 0xFFFD  # -3


@pytest.mark.astrid
def test_signed_mod_divisor_negative():
    """signed -7 % -2 == -1: remainder always follows the dividend."""
    proc, _, _ = run_source(
        "int main() { signed int a = -7; signed int b = -2; return a % b; }")
    assert proc.p0 == 0xFFFF  # -1


# ---------------------------------------------------------------------------
# Runtime semantics: unsigned / plain int stay on the raw hardware path
# ---------------------------------------------------------------------------

@pytest.mark.astrid
def test_unsigned_div_uses_raw_hardware_div():
    """unsigned 40000 / 2 == 20000: the top-bit value must NOT be negated."""
    proc, _, _ = run_source(
        "int main() { unsigned int u = 40000; return u / 2; }")
    assert proc.p0 == 20000


@pytest.mark.astrid
def test_unsigned_mod_uses_raw_hardware_mod():
    """unsigned 40000 % 1024 == 64."""
    proc, _, _ = run_source(
        "int main() { unsigned int u = 40000; return u % 1024; }")
    assert proc.p0 == 64


@pytest.mark.astrid
def test_plain_int_division_behavior_unchanged():
    """Plain int keeps the historical raw DIV (status-quo regression guard)."""
    proc, _, _ = run_source(
        "int main() { int a = 40000; return a / 2; }")
    assert proc.p0 == 20000


@pytest.mark.astrid
def test_plain_int_division_unchanged_for_positive_values():
    """Plain int division of values < 0x8000 is identical under both rules."""
    proc, _, _ = run_source("int main() { int a = 999; return a / 10; }")
    assert proc.p0 == 99


@pytest.mark.astrid
def test_unsigned_comparison_still_reads_top_bit_as_unsigned():
    """40000 > 30000 unsigned: the compare policy is untouched by item 6."""
    proc, _, _ = run_source(
        "int main() { unsigned int a = 40000; unsigned int b = 30000;"
        " return a > b; }")
    assert proc.p0 == 1


# ---------------------------------------------------------------------------
# Compound assignment paths (scalar / array element / struct member)
# ---------------------------------------------------------------------------

@pytest.mark.astrid
def test_signed_scalar_compound_div_assign():
    """signed t /= 2 uses the sign-corrected sequence."""
    proc, _, _ = run_source(
        "int main() { signed int t = -7; t /= 2; return t; }")
    assert proc.p0 == 0xFFFD  # -3


@pytest.mark.astrid
def test_signed_scalar_compound_mod_assign():
    """signed t %= 2 takes the dividend's sign."""
    proc, _, _ = run_source(
        "int main() { signed int t = -7; t %= 2; return t; }")
    assert proc.p0 == 0xFFFF  # -1


@pytest.mark.astrid
def test_signed_array_element_compound_div_assign():
    """arr[0] /= 2 routes through generate_array_assignment's '/' site."""
    proc, _, _ = run_source(
        "int main() { signed int arr[2]; arr[0] = -7; arr[0] /= 2;"
        " return arr[0]; }")
    assert proc.p0 == 0xFFFD  # -3


@pytest.mark.astrid
def test_signed_struct_member_compound_div_assign():
    """s.hit /= 2 routes through generate_member_assignment's '/' site."""
    proc, _, _ = run_source(
        "struct S { signed int hit; };"
        "int main() { struct S s; s.hit = -7; s.hit /= 2; return s.hit; }")
    assert proc.p0 == 0xFFFD  # -3


@pytest.mark.astrid
def test_signed_struct_member_compound_mod_assign():
    """s.hit %= 2 routes through the member '%' site."""
    proc, _, _ = run_source(
        "struct S { signed int hit; };"
        "int main() { struct S s; s.hit = -7; s.hit %= 2; return s.hit; }")
    assert proc.p0 == 0xFFFF  # -1


# ---------------------------------------------------------------------------
# Constant folding: all three folders now truncate toward zero
# ---------------------------------------------------------------------------

@pytest.mark.astrid
def test_simplifier_fold_negative_division_is_minus_three():
    """ExpressionSimplifier folds -7 / 2 to -3 (C), never floor's -4."""
    asm = compile_asm("int main() { return -7 / 2; }",
                      enable_optimizations=True)
    assert " -3" in asm
    assert " -4" not in asm


@pytest.mark.astrid
def test_simplifier_fold_negative_mod_is_minus_one():
    """ExpressionSimplifier folds -7 % 2 to -1 (C), never Python's +1."""
    asm = compile_asm("int main() { return -7 % 2; }",
                      enable_optimizations=True)
    assert " -1" in asm
    assert "MOV P0, 1" not in asm and "MOV R0, 1" not in asm


@pytest.mark.astrid
def test_fold_mixed_sign_division():
    """7 / -2 folds to -3 with optimizations on."""
    proc, _, _ = run_source("int main() { return 7 / -2; }")
    assert proc.p0 == 0xFFFD  # -3


@pytest.mark.astrid
def test_fold_negative_division_runtime_opts_off():
    """With folds disabled the runtime signed path still yields -3."""
    proc, _, _ = run_source("int main() { return -7 / 2; }",
                            enable_optimizations=False)
    assert proc.p0 == 0xFFFD  # -3


@pytest.mark.astrid
def test_global_initializer_fold_uses_c_semantics():
    """`int g = -7 / 2` (_const_eval) stores -3, not the unsigned 32764."""
    proc, _, _ = run_source("int g = -7 / 2; int main() { return g; }")
    assert proc.p0 == 0xFFFD  # -3


@pytest.mark.astrid
def test_global_initializer_mod_fold_uses_c_semantics():
    """`int g = -7 % 2` stores -1."""
    proc, _, _ = run_source("int g = -7 % 2; int main() { return g; }")
    assert proc.p0 == 0xFFFF  # -1


@pytest.mark.astrid
def test_global_initializer_positive_division_unchanged():
    """40000 / 3 == 13333 as before: positive constants keep raw values."""
    proc, _, _ = run_source("int g = 40000 / 3; int main() { return g; }")
    assert proc.p0 == 13333


@pytest.mark.astrid
def test_simplifier_fold_positive_division_unchanged():
    """40000 / 3 folds to 13333 with optimizations on (no regression)."""
    proc, _, _ = run_source("int main() { return 40000 / 3; }")
    assert proc.p0 == 13333


@pytest.mark.astrid
def test_global_relational_fold_with_negative_literal():
    """`-7 < 2` folds to 1 in _const_eval (was 0 via masked 65529 < 2)."""
    proc, _, _ = run_source("int g = (-7 < 2); int main() { return g; }")
    assert proc.p0 == 1


# ---------------------------------------------------------------------------
# Emission shape: who gets the sign-corrected sequence?
# ---------------------------------------------------------------------------

@pytest.mark.astrid
def test_signed_division_emits_sign_correction_sequence():
    """A signed_int operand selects the CMP/JGE/NEG DIV sequence."""
    asm = compile_asm("signed int f(signed int a) { return a / 2; }")
    assert "sdiv_" in asm       # labels from _emit_signed_div
    assert asm.count("DIV") >= 1


@pytest.mark.astrid
def test_unsigned_division_emits_no_sign_correction():
    """An unsigned_int operand keeps a bare hardware DIV."""
    asm = compile_asm("unsigned int f(unsigned int a) { return a / 2; }")
    assert "sdiv_" not in asm
    assert asm.count("DIV") == 1


@pytest.mark.astrid
def test_plain_int_division_emits_no_sign_correction():
    """Plain int keeps the raw DIV (historical unsigned default)."""
    asm = compile_asm("int f(int a) { return a / 2; }")
    assert "sdiv_" not in asm
    assert asm.count("DIV") == 1


@pytest.mark.astrid
def test_signed_mod_emits_sign_correction_sequence():
    """A signed_int operand selects the signed MOD sequence."""
    asm = compile_asm("signed int f(signed int a) { return a % 2; }")
    assert "smod_" in asm


@pytest.mark.astrid
def test_negative_literal_divisor_selects_signed_path():
    """`a / -2` on plain int is signed: the top-bit constant flips it."""
    asm = compile_asm("int f(int a) { return a / -2; }")
    assert "sdiv_" in asm


@pytest.mark.astrid
def test_float_division_still_uses_fdiv():
    """Q8.8 '/' keeps FDIV; the signed policy never touches floats."""
    asm = compile_asm("float g(float a, float b) { return a / b; }")
    assert "FDIV" in asm
    assert "sdiv_" not in asm

