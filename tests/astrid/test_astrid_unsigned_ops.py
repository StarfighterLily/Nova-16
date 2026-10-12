"""Tier-2 Item 6, closing gaps: `unsigned` means unsigned *everywhere*.

The comparison/division machinery already existed, but two operand shapes
silently lost their unsignedness and fell back to the signed jump family:

  * ``*p`` (deref) -- `_cast_source_type` knew identifiers, member accesses
    (`p.x`) and array subscripts (`a[i]`), but not the dereference itself,
    so `unsigned int *p; *p > 40000` lowered to signed JGT instead of JC;
  * postfix on anything but a bare identifier -- `a++` was typed, but
    `s.u++`, `a[i]++` and `(*p)++` were not, so they compared signed too.

Both are the exact failure mode Item 6 warns about ("real behavioral
consequences for mixed sign/pointer code"), except here the casualty was
unsigned rather than signed.  These tests pin the jump family for every
value shape, in both directions (signed must stay signed as well).
"""
import os
import sys
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


def jumps_in(source, fn="func_main:"):
    """Conditional jumps emitted for `fn`'s body, as stripped mnemonics."""
    asm = "\n".join(CodeGenerator().generate(Parser(Lexer(source).tokenize()).parse()))
    body = asm.split(fn)[1]
    return [line.strip() for line in body.splitlines()
            if line.strip()
            and line.strip().split()[0] in ("JC", "JNC", "JLT", "JGE", "JGT", "JLE")]


SIGNED = {"JLT", "JGE", "JGT", "JLE"}
UNSIGNED = {"JC", "JNC"}


def assert_unsigned(source):
    jumps = jumps_in(source)
    assert jumps, f"no conditional jumps emitted for:\n{source}"
    assert any(j.split()[0] in UNSIGNED for j in jumps), \
        f"expected an unsigned (JC/JNC) comparison in {jumps}"
    assert not any(j.split()[0] in SIGNED for j in jumps), \
        f"signed jump leaked into an unsigned comparison: {jumps}"


def assert_signed(source):
    jumps = jumps_in(source)
    assert jumps, f"no conditional jumps emitted for:\n{source}"
    assert any(j.split()[0] in SIGNED for j in jumps), \
        f"expected a signed (JLT/JGE/JGT/JLE) comparison in {jumps}"
    assert not any(j.split()[0] in UNSIGNED for j in jumps), \
        f"unsigned jump leaked into a signed comparison: {jumps}"


# ---------------------------------------------------------------------------
# Deref keeps the pointee's signedness
# ---------------------------------------------------------------------------

@pytest.mark.astrid
def test_deref_of_unsigned_pointer_compares_unsigned():
    """`*p > 40000` with `unsigned int *p` lowers to JC, not JGT."""
    assert_unsigned(
        "int main() { unsigned int v = 60000; unsigned int *p = &v;"
        " if (*p > 40000) return 1; return 0; }")


@pytest.mark.astrid
def test_deref_of_signed_pointer_compares_signed():
    """`*p > 7` with `signed int *p` lowers to JGT, not JC."""
    assert_signed(
        "int main() { signed int v = 3; signed int *p = &v;"
        " if (*p > 7) return 1; return 0; }")


@pytest.mark.astrid
def test_deref_of_signed_pointer_negative_constant():
    """`*p < 0` on a signed pointee is a signed comparison."""
    assert_signed(
        "int main() { signed int v = -5; signed int *p = &v;"
        " if (*p < 0) return 1; return 0; }")


@pytest.mark.astrid
def test_deref_of_global_unsigned_pointer():
    """Pointee typing also works for file-scope pointers."""
    assert_unsigned(
        "unsigned int *g;\n"
        "int main() { if (*g > 40000) return 1; return 0; }")


@pytest.mark.astrid
def test_deref_of_char_pointer_compares_unsigned():
    """`char` is byte-oriented: `*cp > 7` stays unsigned."""
    assert_unsigned(
        "int main() { char v = 3; char *p = &v;"
        " if (*p > 7) return 1; return 0; }")


@pytest.mark.astrid
def test_deref_of_plain_int_pointer_compares_unsigned():
    """Plain `int *` keeps the machine's historical unsigned default."""
    assert_unsigned(
        "int main() { int v = 3; int *p = &v;"
        " if (*p > 7) return 1; return 0; }")


# ---------------------------------------------------------------------------
# Postfix keeps the operand's signedness on every shape
# ---------------------------------------------------------------------------

@pytest.mark.astrid
def test_postfix_on_unsigned_struct_field():
    """`s.u++ > 40000` compares the unsigned field value unsigned."""
    assert_unsigned(
        "struct S { unsigned int u; };\n"
        "int main() { struct S s; s.u = 1;"
        " if (s.u++ > 40000) return 1; return 0; }")


@pytest.mark.astrid
def test_postfix_on_unsigned_array_element():
    """`a[0]++ > 40000` compares the unsigned element value unsigned."""
    assert_unsigned(
        "int main() { unsigned int a[2]; a[0] = 1;"
        " if (a[0]++ > 40000) return 1; return 0; }")


@pytest.mark.astrid
def test_postfix_on_unsigned_deref():
    """`(*p)++ > 40000` compares the unsigned pointee value unsigned."""
    assert_unsigned(
        "int main() { unsigned int v = 1; unsigned int *p = &v;"
        " if ((*p)++ > 40000) return 1; return 0; }")


@pytest.mark.astrid
def test_postfix_on_signed_struct_field():
    """`s.s++ > 7` keeps relying on the signed family."""
    assert_signed(
        "struct S { signed int s; };\n"
        "int main() { struct S s; s.s = 1;"
        " if (s.s++ > 7) return 1; return 0; }")


@pytest.mark.astrid
def test_postfix_on_plain_identifier_unchanged():
    """The previously-typed shape (`a++` on a local) is unaffected."""
    assert_unsigned(
        "int main() { unsigned int a = 60000;"
        " if (a++ > 40000) return 1; return 0; }")
