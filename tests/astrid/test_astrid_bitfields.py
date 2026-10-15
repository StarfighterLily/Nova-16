"""Tier-2 Item 7: struct/union bit-fields (`unsigned flags : 3;`).

Before this work a bit-field declarator was a parse error -- the struct
grammar had no notion of a `: width` suffix at all.  Astrid now packs
bit-fields into the low bits of their containing 16-bit word, the same
"a bit-field that doesn't fit moves to the next unit" rule C uses, so a
flag pack inside a struct costs a fraction of the RAM it would as separate
`char`/`int` members.  On a 64KB machine under real memory pressure that is
a genuine space saver, not a curiosity.

Covered here:
  * parsing: widths on struct and union members, comma lists, and the
    diagnostics for width 0, width > 16 and a non-constant width;
  * layout: greedy low-bit packing, spilling into a new word when a field
    does not fit, and the fact that `sizeof` reflects the packed size;
  * isolation: writing one member never disturbs its word-mates (the reason
    every store is a read-modify-write rather than a plain word store);
  * reads: extraction and masking, truncation of an over-wide assignment;
  * compound assignment and `++` / `--` operating on the field value;
  * sign extension for a `signed` bit-field;
  * interaction with ordinary members, arrays of packed structs, nested
    aggregates, by-value parameters/returns, unions, and `const`.
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


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


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


def signed16(value):
    """Interpret a raw 16-bit result as two's-complement."""
    value &= 0xFFFF
    return value - 0x10000 if value >= 0x8000 else value

def signed16(value):
    """Interpret a raw 16-bit result as two's-complement."""
    value &= 0xFFFF
    return value - 0x10000 if value >= 0x8000 else value


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

@pytest.mark.astrid
def test_parser_records_bitfield_width():
    """A `: width` suffix is recorded as that member's bit width."""
    ast = parse("struct F { unsigned int a : 3; unsigned int b : 5; };\n"
                "int main() { return 0; }")
    assert ast.struct_bitfields["F"] == {"a": 3, "b": 5}


@pytest.mark.astrid
def test_parser_bitfield_in_comma_list():
    """A bit-field width applies to the declarator it follows, not the type."""
    ast = parse("struct F { unsigned int a : 3, b : 9; };\n"
                "int main() { return 0; }")
    assert ast.struct_bitfields["F"] == {"a": 3, "b": 9}


@pytest.mark.astrid
def test_parser_bitfield_only_when_declared():
    """Structs with no bit-fields report an empty table (layout unchanged)."""
    ast = parse("struct P { int x; int y; };\nint main() { return 0; }")
    assert ast.struct_bitfields == {}


@pytest.mark.astrid
def test_parser_union_bitfield_width():
    """Unions accept bit-field members too."""
    ast = parse("union U { unsigned int a : 4; int whole; };\n"
                "int main() { return 0; }")
    assert ast.union_bitfields["U"] == {"a": 4}


@pytest.mark.astrid
def test_parser_bitfield_hex_and_octal_width():
    """The width literal accepts the same integer forms as any constant."""
    ast = parse("struct F { unsigned int a : 0x4; unsigned int b : 0o5; };\n"
                "int main() { return 0; }")
    assert ast.struct_bitfields["F"] == {"a": 4, "b": 5}


@pytest.mark.astrid
def test_parser_full_width_bitfield_is_legal():
    """A 16-bit bit-field fills exactly one word."""
    ast = parse("struct F { unsigned int a : 16; };\nint main() { return 0; }")
    assert ast.struct_bitfields["F"] == {"a": 16}


@pytest.mark.astrid
def test_zero_width_bitfield_rejected():
    """Width 0 is C's unnamed-padding form, which Astrid has no syntax for."""
    err = compile_error("struct F { unsigned int a : 0; };\n"
                        "int main() { return 0; }")
    assert "width 0" in str(err)


@pytest.mark.astrid
def test_oversize_bitfield_rejected():
    """A field wider than the machine's 16-bit word cannot be laid out."""
    err = compile_error("struct F { unsigned int a : 17; };\n"
                        "int main() { return 0; }")
    assert "at most 16" in str(err)


@pytest.mark.astrid
def test_non_constant_bitfield_width_rejected():
    """The width must be a literal, not an expression."""
    err = compile_error("int w = 3;\nstruct F { unsigned int a : w; };\n"
                        "int main() { return 0; }")
    assert "constant" in str(err)

    assert "constant" in str(err)


# ---------------------------------------------------------------------------
# Layout: packing, spilling, and sizeof
# ---------------------------------------------------------------------------

def _struct_size(source, tag):
    """Compile-time byte size of `tag` according to the code generator."""
    cg = CodeGenerator()
    cg.generate(parse(source))
    return cg._struct_size(tag)


@pytest.mark.astrid
def test_bitfields_pack_into_one_word():
    """3 + 5 bits share a single 16-bit word instead of two."""
    assert _struct_size(
        "struct F { unsigned int a : 3; unsigned int b : 5; };\n"
        "int main() { return 0; }", "F") == 2


@pytest.mark.astrid
def test_exactly_filling_word_stays_one_word():
    """8 + 8 bits exactly fill a word with no spill."""
    assert _struct_size(
        "struct F { unsigned int a : 8; unsigned int b : 8; };\n"
        "int main() { return 0; }", "F") == 2


@pytest.mark.astrid
def test_bitfield_spills_into_next_word():
    """A field that does not fit starts a new word (C's unit rule)."""
    # 9 + 9 = 18 bits cannot share one 16-bit word.
    assert _struct_size(
        "struct F { unsigned int a : 9; unsigned int b : 9; };\n"
        "int main() { return 0; }", "F") == 4


@pytest.mark.astrid
def test_partial_trailing_word_still_counts():
    """A word holding even one bit is fully reserved."""
    assert _struct_size(
        "struct F { unsigned int a : 1; };\nint main() { return 0; }", "F") == 2


@pytest.mark.astrid
def test_bitfield_offsets_within_shared_word():
    """Members sharing a word report the same byte offset; bits differ."""
    cg = CodeGenerator()
    cg.generate(parse(
        "struct F { unsigned int a : 3; unsigned int b : 5; };\n"
        "int main() { return 0; }"))
    assert cg._struct_field_offset("F", "a") == 0
    assert cg._struct_field_offset("F", "b") == 0
    assert cg._struct_field_bits("F", "a") == (0, 3)
    assert cg._struct_field_bits("F", "b") == (3, 5)


@pytest.mark.astrid
def test_bitfield_offsets_after_spill():
    """After a spill the second word's members report offset 2."""
    cg = CodeGenerator()
    cg.generate(parse(
        "struct F { unsigned int a : 9; unsigned int b : 9; };\n"
        "int main() { return 0; }"))
    assert cg._struct_field_offset("F", "a") == 0
    assert cg._struct_field_offset("F", "b") == 2
    assert cg._struct_field_bits("F", "b") == (0, 9)


@pytest.mark.astrid
def test_ordinary_member_after_bitfields_starts_new_word():
    """A full-width member never shares a word with packed bits."""
    cg = CodeGenerator()
    cg.generate(parse(
        "struct F { unsigned int a : 3; int whole; };\n"
        "int main() { return 0; }"))
    assert cg._struct_field_offset("F", "a") == 0
    assert cg._struct_field_offset("F", "whole") == 2
    assert cg._struct_field_bits("F", "whole") is None
    assert cg._struct_size("F") == 4


@pytest.mark.astrid
def test_ordinary_member_between_bitfield_runs():
    """A full-width member separates two independent bit-field words."""
    cg = CodeGenerator()
    cg.generate(parse(
        "struct F { unsigned int a : 3; int whole; unsigned int b : 5; };\n"
        "int main() { return 0; }"))
    assert cg._struct_field_bits("F", "a") == (0, 3)
    assert cg._struct_field_bits("F", "b") == (0, 5)
    assert cg._struct_field_offset("F", "b") == 4


@pytest.mark.astrid
def test_sizeof_reflects_packed_layout():
    """`sizeof` reports the packed size, not one word per member."""
    proc, _cycles, _mem = run_source(
        "struct F { unsigned int a : 3; unsigned int b : 5; };\n"
        "int main() { return sizeof(struct F); }")
    assert proc.p0 == 2


@pytest.mark.astrid
def test_sizeof_reflects_spill_layout():
    """`sizeof` of a spilling layout counts both words."""
    proc, _cycles, _mem = run_source(
        "struct F { unsigned int a : 9; unsigned int b : 9; };\n"
        "int main() { return sizeof(struct F); }")
    assert proc.p0 == 4


@pytest.mark.astrid
def test_packed_layout_is_stable_across_queries():
    """Repeated layout queries agree (the memoized pass is consistent)."""
    cg = CodeGenerator()
    cg.generate(parse(
        "struct F { unsigned int a : 3; unsigned int b : 5; };\n"
        "int main() { return 0; }"))
    first = cg._packed_layout("F")
    for _ in range(3):
        assert cg._packed_layout("F") == first
    first = cg._packed_layout("F")
    for _ in range(3):
        assert cg._packed_layout("F") == first


# ---------------------------------------------------------------------------
# Runtime: reads, writes, and isolation between word-mates
# ---------------------------------------------------------------------------

@pytest.mark.astrid
def test_write_and_read_bitfield():
    """A stored bit-field reads back the value that was written."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 3; unsigned int b : 5; };\n"
        "int main() { struct F f; f.a = 5; f.b = 20; return f.a + f.b; }")
    assert proc.p0 == 25


@pytest.mark.astrid
def test_write_does_not_disturb_word_mate():
    """Writing one member leaves its word-mate untouched (read-modify-write)."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 3; unsigned int b : 5; };\n"
        "int main() {\n"
        "    struct F f;\n"
        "    f.a = 7;\n"
        "    f.b = 31;\n"
        "    f.a = 1;              /* must not clear b */\n"
        "    return f.b;\n"
        "}")
    assert proc.p0 == 31


@pytest.mark.astrid
def test_write_upper_member_does_not_disturb_lower():
    """The mirror case: writing the high member preserves the low one."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 3; unsigned int b : 5; };\n"
        "int main() {\n"
        "    struct F f;\n"
        "    f.a = 6;\n"
        "    f.b = 9;\n"
        "    f.b = 17;\n"
        "    return f.a;\n"
        "}")
    assert proc.p0 == 6


@pytest.mark.astrid
def test_over_wide_assignment_truncates_to_width():
    """Assigning 0x1F to a 3-bit field keeps only the low 3 bits."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 3; };\n"
        "int main() { struct F f; f.a = 0x1F; return f.a; }")
    assert proc.p0 == 7


@pytest.mark.astrid
def test_over_wide_assignment_does_not_bleed_into_mate():
    """Truncation is masked, so neighbouring bits stay clear."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 3; unsigned int b : 5; };\n"
        "int main() {\n"
        "    struct F f;\n"
        "    f.b = 5;\n"
        "    f.a = 0xFFFF;         /* only low 3 bits may land */\n"
        "    return f.b;\n"
        "}")
    assert proc.p0 == 5


@pytest.mark.astrid
def test_max_value_fills_field_exactly():
    """The largest representable value round-trips."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 4; };\n"
        "int main() { struct F f; f.a = 15; return f.a; }")
    assert proc.p0 == 15


@pytest.mark.astrid
def test_single_bit_field():
    """A 1-bit field behaves as a boolean-ish flag."""
    proc, _c, _m = run_source(
        "struct F { unsigned int on : 1; };\n"
        "int main() { struct F f; f.on = 1; return f.on; }")
    assert proc.p0 == 1


@pytest.mark.astrid
def test_single_bit_field_truncates():
    """A 1-bit field masks anything above bit 0."""
    proc, _c, _m = run_source(
        "struct F { unsigned int on : 1; };\n"
        "int main() { struct F f; f.on = 0xFF; return f.on; }")
    assert proc.p0 == 1


@pytest.mark.astrid
def test_full_width_bitfield_round_trips():
    """A 16-bit bit-field holds any word value."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 16; };\n"
        "int main() { struct F f; f.a = 0xBEEF; return f.a; }")
    assert proc.p0 == 0xBEEF


@pytest.mark.astrid
def test_bitfield_mixed_with_ordinary_members():
    """Packed bits and full-width members coexist in one struct."""
    proc, _c, _m = run_source(
        "struct F { int x; unsigned int a : 3; unsigned int b : 5; int y; };\n"
        "int main() {\n"
        "    struct F f;\n"
        "    f.x = 1000; f.a = 5; f.b = 20; f.y = 2000;\n"
        "    return f.x + f.a + f.b + f.y;\n"
        "}")
    assert proc.p0 == 3025


@pytest.mark.astrid
def test_spilled_bitfields_are_independent():
    """Members in different words do not interfere."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 9; unsigned int b : 9; };\n"
        "int main() { struct F f; f.a = 400; f.b = 300; return f.a + f.b; }")
    assert proc.p0 == 700


@pytest.mark.astrid
def test_many_bitfields_in_one_word():
    """Eight 2-bit fields all pack into a single word."""
    assert _struct_size(
        "struct F { unsigned int a:2, b:2, c:2, d:2, e:2, f:2, g:2, h:2; };\n"
        "int main() { return 0; }", "F") == 2


@pytest.mark.astrid
def test_eight_packed_fields_round_trip():
    """All eight packed fields read back independently."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a:2, b:2, c:2, d:2, e:2, f:2, g:2, h:2; };\n"
        "int main() {\n"
        "    struct F v;\n"
        "    v.a=1; v.b=2; v.c=3; v.d=0; v.e=1; v.f=2; v.g=3; v.h=0;\n"
        "    return v.a + v.b*4 + v.c*16 + v.d + v.e + v.f*4 + v.g*16 + v.h;\n"
        "}")
    # 1 + 8 + 48 + 0 + 1 + 8 + 48 + 0
    assert proc.p0 == 114

# ---------------------------------------------------------------------------
# Runtime: compound assignment and ++/-- on bit-field values
# ---------------------------------------------------------------------------

@pytest.mark.astrid
def test_bitfield_compound_add():
    """`f.a += v` reads the field, adds, and merges back."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 4; unsigned int b : 4; };\n"
        "int main() { struct F f; f.a = 3; f.b = 9; f.a += 10; return f.a + f.b; }")
    assert proc.p0 == 13 + 9


@pytest.mark.astrid
def test_bitfield_compound_add_preserves_mate():
    """A compound update must not clobber the other member of the word."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 4; unsigned int b : 4; };\n"
        "int main() { struct F f; f.a = 3; f.b = 9; f.b += 1; return f.a + f.b; }")
    assert proc.p0 == 3 + 10


@pytest.mark.astrid
def test_bitfield_compound_bitwise():
    """`&=`, `|=`, `^=` apply to the field value itself."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 4; };\n"
        "int main() {\n"
        "    struct F f;\n"
        "    f.a = 0b1100; f.a &= 0b1010;\n"   # -> 0b1000
        "    f.a |= 0b0001;\n"                 # -> 0b1001
        "    f.a ^= 0b1111;\n"                 # -> 0b0110
        "    return f.a;\n"
        "}")
    assert proc.p0 == 0b0110


@pytest.mark.astrid
def test_bitfield_postfix_inc():
    """`f.a++` increments the field and leaves its mate alone."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 4; unsigned int b : 4; };\n"
        "int main() { struct F f; f.a = 14; f.b = 7; f.a++; return f.a + f.b; }")
    assert proc.p0 == 15 + 7


@pytest.mark.astrid
def test_bitfield_postfix_dec():
    """`f.a--` decrements the field and leaves its mate alone."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 4; unsigned int b : 4; };\n"
        "int main() { struct F f; f.a = 5; f.b = 7; f.b--; return f.a + f.b; }")
    assert proc.p0 == 5 + 6
@pytest.mark.astrid
def test_bitfield_prefix_inc_returns_new_value():
    """Prefix `++f.a` yields the new value (C semantics)."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 4; };\n"
        "int main() { struct F f; f.a = 6; return ++f.a; }")
    assert proc.p0 == 7


@pytest.mark.astrid
def test_bitfield_postfix_yields_old_value():
    """Postfix `f.a++` yields the old value, then the field advances."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 4; };\n"
        "int main() { struct F f; f.a = 6; int x = f.a++; return x + f.a; }")
    assert proc.p0 == 6 + 7


# ---------------------------------------------------------------------------
# Runtime: signed bit-fields sign-extend on read
# ---------------------------------------------------------------------------

@pytest.mark.astrid
def test_signed_bitfield_negative_reads_back_negative():
    """A `signed` bit-field holding -3 reads back as -3, not 29."""
    proc, _c, _m = run_source(
        "struct F { signed int d : 5; };\n"
        "int main() { struct F f; f.d = -3; return f.d; }")
    assert signed16(proc.p0) == -3


@pytest.mark.astrid
def test_signed_bitfield_min_value():
    """The most negative value of a 5-bit field round-trips."""
    proc, _c, _m = run_source(
        "struct F { signed int d : 5; };\n"
        "int main() { struct F f; f.d = -16; return f.d; }")
    assert signed16(proc.p0) == -16


@pytest.mark.astrid
def test_signed_bitfield_max_positive():
    """The largest positive 5-bit value round-trips unchanged."""
    proc, _c, _m = run_source(
        "struct F { signed int d : 5; };\n"
        "int main() { struct F f; f.d = 15; return f.d; }")
    assert proc.p0 == 15


@pytest.mark.astrid
def test_unsigned_bitfield_same_bits_stay_positive():
    """An `unsigned` field holding top-bit-set bits is NOT sign-extended."""
    proc, _c, _m = run_source(
        "struct F { unsigned int u : 5; };\n"
        "int main() { struct F f; f.u = 29; return f.u; }")

# ---------------------------------------------------------------------------
# Runtime: bit-fields across the whole aggregate feature set
# ---------------------------------------------------------------------------

@pytest.mark.astrid
def test_bitfield_through_pointer_arrow():
    """`pp->flags` resolves through the pointee layout like any member."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 3; unsigned int b : 5; };\n"
        "int main() {\n"
        "    struct F f; struct F *p = &f;\n"
        "    p->a = 6; p->b = 25;\n"
        "    return p->a + p->b;\n"
        "}")
    assert proc.p0 == 31


@pytest.mark.astrid
def test_bitfield_in_run_time_indexed_array():
    """`pts[i].flags` works for run-time indices (not just element 0)."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 3; unsigned int b : 5; };\n"
        "int main() {\n"
        "    struct F pts[3];\n"
        "    pts[0].a = 1; pts[1].a = 2; pts[2].a = 3;\n"
        "    pts[0].b = 4; pts[1].b = 5; pts[2].b = 6;\n"
        "    int i = 2;\n"
        "    return pts[i].a + pts[i].b + pts[0].a;\n"
        "}")
    assert proc.p0 == 3 + 6 + 1


@pytest.mark.astrid
def test_union_bitfield_and_whole_member_overlap():
    """Union overlap: writing the bit-field is visible through `whole`."""
    proc, _c, _m = run_source(
        "union U { unsigned int a : 4; int whole; };\n"
        "int main() {\n"
        "    union U u;\n"
        "    u.a = 9;\n"
        "    return u.whole;\n"          # low 4 bits set, rest zero
        "}")
    assert proc.p0 == 9


@pytest.mark.astrid
def test_union_whole_member_write_visible_through_bitfield():
    """The mirror: `whole = 0x1234` leaves the low 4 bits as 0x4."""
    proc, _c, _m = run_source(
        "union U { unsigned int a : 4; int whole; };\n"
        "int main() {\n"
        "    union U u;\n"
        "    u.whole = 0x1234;\n"
        "    return u.a;\n"
        "}")
    assert proc.p0 == 4


@pytest.mark.astrid
def test_nested_aggregate_with_bitfields_has_packed_size():
    """An outer struct inherits the inner packed footprint (1 word here)."""
    assert _struct_size(
        "struct Inner { unsigned int a : 3; unsigned int b : 5; };\n"
        "struct Outer { struct Inner inner; int total; };\n"
        "int main() { return 0; }", "Outer") == 4


@pytest.mark.astrid
def test_array_of_packed_structs_uses_packed_stride():
    """Three 1-word packed structs occupy exactly 3 words."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 3; unsigned int b : 5; };\n"
        "int main() {\n"
        "    struct F arr[3];\n"
        "    arr[0].a = 1; arr[1].a = 2; arr[2].a = 3;\n"
        "    arr[0].b = 10; arr[1].b = 20; arr[2].b = 30;\n"
        "    return arr[2].a + arr[2].b - arr[1].a;\n"
        "}")
    assert proc.p0 == 3 + 30 - 2


@pytest.mark.astrid
def test_bitfield_in_nested_aggregate():
    """A nested `o.inner.flags` chain reaches a packed member at depth 2."""
    proc, _c, _m = run_source(
        "struct Inner { unsigned int flags : 3; };\n"
        "struct Outer { struct Inner inner; int total; };\n"
        "int main() {\n"
        "    struct Outer o;\n"
        "    o.inner.flags = 5; o.total = 40;\n"
        "    return o.inner.flags + o.total;\n"
        "}")
    assert proc.p0 == 45


@pytest.mark.astrid
def test_bitfield_struct_passed_by_value():
    """By-value aggregate params carry the packed word, not just fields."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 3; unsigned int b : 5; };\n"
        "int sum(struct F v) { return v.a + v.b; }\n"
        "int main() { struct F f; f.a = 4; f.b = 12; return sum(f); }")
    assert proc.p0 == 16


@pytest.mark.astrid
def test_bitfield_struct_returned_by_value():
    """By-value aggregate returns write the packed word through sret."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 3; unsigned int b : 5; };\n"
        "struct F make() { struct F v; v.a = 2; v.b = 8; return v; }\n"
        "int main() { struct F f; f = make(); return f.a + f.b; }")
    assert proc.p0 == 10


@pytest.mark.astrid
def test_global_bitfield_struct_reads_and_writes():
    """Global instances of packed structs address the right words."""
    proc, _c, _m = run_source(
        "struct F { unsigned int a : 3; unsigned int b : 5; };\n"
        "struct F g;\n"
        "int main() { g.a = 3; g.b = 11; return g.a + g.b; }")
    assert proc.p0 == 14


@pytest.mark.astrid
def test_const_bitfield_struct_rejects_member_write():
    """A `const` packed struct is no more writable than a `const` plain one."""
    err = compile_error(
        "struct F { unsigned int a : 3; };\n"
        "const struct F f = {1};\n"
        "int main() { f.a = 2; return f.a; }")
    assert "const variable 'f'" in str(err)


@pytest.mark.astrid
def test_signed_bitfield_in_unsigned_comparison():
    """A `signed` 5-bit -3 still compares signed (JLT, not JC)."""
    asm = compile_asm(
        "struct F { signed int d : 5; };\n"
        "int main() { struct F f; f.d = -3; if (f.d < 0) return 1; return 0; }")
    cond = asm.split("func_main:")[1]
    # A false-branch tests the negated relation, so < may lower to JGE.
    assert "JLT" in cond or "JGE" in cond
    assert "\nJC " not in cond and "\nJNC " not in cond


