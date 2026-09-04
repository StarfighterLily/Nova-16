"""Regression tests for the Astrid `signed` type modifier.

`signed int` normalizes to the 'signed_int' type (instead of collapsing to
plain 'int'), which makes `_use_signed_comparison` emit the CPU's signed
jump family (JGT/JLT/JGE/JLE, overflow XOR sign) for relational comparisons
on such values. This is what lets the sprttest health field
(`signed int hit`) exit `while (Player.hit > 0)` after damage drives it
negative -- an unsigned compare would read 0xFFFC > 0 and spin forever.
"""
import os
import sys
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

SRC = """
struct S { int x; signed int hit; } g = {5, 3};
int main() {
    while (g.hit > 0) {
        g.hit -= 2;
    }
    return g.hit;
}
"""


def _parse(src):
    return Parser(Lexer(src).tokenize()).parse()


def test_signed_field_type_is_preserved():
    """`signed int hit` records field type 'signed_int'; plain int stays 'int'."""
    ast = _parse("struct P { int a; signed int hit; } p;")
    fields = dict(ast.structs["P"])
    assert fields["hit"] == "signed_int"
    assert fields["a"] == "int"


def test_signed_variable_type_is_preserved():
    """Local `signed int` variables also carry 'signed_int' into var_types."""
    src = "int main() { signed int h = -1; return h; }"
    ast = _parse(src)
    decl = ast.functions[0].body[0]
    assert decl.var_type == "signed_int"


def test_unsigned_variable_type_is_preserved():
    """`unsigned int` must keep its unsigned_int type instead of collapsing to plain int."""
    ast = _parse("int main() { unsigned int b = 655300; return b; }")
    decl = ast.functions[0].body[0]
    assert decl.var_type == "unsigned_int"


def test_unsigned_comparison_emits_unsigned_jump():
    """Two unsigned ints should select the unsigned compare family instead of signed JGT/JLT."""
    src = "int main() { unsigned int a = 40000; unsigned int b = 50000; return a < b; }"
    asm = "\n".join(CodeGenerator().generate(_parse(src)))
    assert "JC" in asm or "JNC" in asm, f"expected unsigned compare family, got:\n{asm}"
    for bad in ("JLT", "JGE", "JGT", "JLE"):
        assert bad not in asm, f"saw signed compare op {bad} in unsigned comparison output"


def _read_zero_terminated_string(mem, addr, max_len=32):
    chars = []
    for i in range(max_len):
        ch = mem.read_byte(addr + i)
        if ch == 0:
            break
        chars.append(chr(ch))
    return "".join(chars)


def test_signed_string_cast_keeps_signed_decimal_output():
    """A 16-bit signed overflow should print as signed decimal when cast to string."""
    from nova_assembler import Assembler
    from nova_main import initialize_system

    src = "void main() { signed int a = 655300; set_pos(0, 0); write_text((string)a, 0x1F); }"
    asm_path = os.path.join(os.environ.get("TEMP", "/tmp"), "astrid_signed_itos_test.asm")
    with open(asm_path, "w") as f:
        f.write("\n".join(CodeGenerator().generate(_parse(src))))
    try:
        Assembler().assemble(asm_path)
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(asm_path.replace(".asm", ".bin"))
        for _ in range(50000):
            proc.step()
            if proc.halted:
                break
        assert proc.halted, "signed cast-to-string program should halt"
        assert _read_zero_terminated_string(mem, 0xA000) == "-60"
    finally:
        for ext in (".asm", ".bin", ".org", ".sym"):
            path = asm_path.replace(".asm", ext)
            if os.path.exists(path):
                os.unlink(path)


def test_unsigned_string_cast_keeps_unsigned_decimal_output():
    """An unsigned 16-bit overflow should print the unsigned magnitude, not the signed wrap."""
    from nova_assembler import Assembler
    from nova_main import initialize_system

    src = "void main() { unsigned int b = 655300; set_pos(0, 0); write_text((string)b, 0x1F); }"
    asm_path = os.path.join(os.environ.get("TEMP", "/tmp"), "astrid_unsigned_itos_test.asm")
    with open(asm_path, "w") as f:
        f.write("\n".join(CodeGenerator().generate(_parse(src))))
    try:
        Assembler().assemble(asm_path)
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(asm_path.replace(".asm", ".bin"))
        for _ in range(50000):
            proc.step()
            if proc.halted:
                break
        assert proc.halted, "unsigned cast-to-string program should halt"
        assert _read_zero_terminated_string(mem, 0xA000) == "65476"
    finally:
        for ext in (".asm", ".bin", ".org", ".sym"):
            path = asm_path.replace(".asm", ext)
            if os.path.exists(path):
                os.unlink(path)


def test_signed_comparison_emits_signed_jump():
    """`g.hit > 0` must lower to CMP + JGT (signed), not the unsigned
    borrow-based JC family or a bare zero-test."""
    ast = _parse(SRC)
    asm = "\n".join(CodeGenerator().generate(ast))
    loop = asm[asm.index("while_start_0:"):]
    cond = loop[:loop.index("while_end_1:")]
    assert "JGT" in cond, f"expected signed JGT in loop condition, got:\n{cond}"
    # The unsigned family must not appear in the condition.
    for bad in ("\nJC ", "\nJNC "):
        assert bad not in cond, f"unsigned {bad.strip()} leaked into signed compare"


def test_signed_loop_exits_on_negative_value():
    """End-to-end: hit 5 -> 3 -> 1 -> -1. The loop must terminate at -1 and
    return 0xFFFF (an unsigned compare would loop forever instead)."""
    from nova_assembler import Assembler
    from nova_main import initialize_system

    ast = _parse(SRC)
    asm_path = os.path.join(os.environ.get("TEMP", "/tmp"),
                            "astrid_signed_test.asm")
    with open(asm_path, "w") as f:
        f.write("\n".join(CodeGenerator().generate(ast)))
    try:
        Assembler().assemble(asm_path)
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(asm_path.replace(".asm", ".bin"))
        for _ in range(50000):
            proc.step()
            if proc.halted:
                break
        assert proc.halted, "signed while-loop must terminate"
        hit = mem.read_word_fast(0x8002)
        assert hit == 0xFFFF, f"expected hit=-1 (0xFFFF), got 0x{hit:04X}"
        assert proc.p0 == 0xFFFF, f"return value must be -1, got 0x{proc.p0:04X}"
    finally:
        for ext in (".asm", ".bin", ".org", ".sym"):
            path = asm_path.replace(".asm", ext)
            if os.path.exists(path):
                os.unlink(path)


def test_typedef_signed_alias_preserves_signed_int():
    """typedef signed int alias; keeps the normalized signed_int type."""
    ast = _parse("typedef signed int health_t; int main() { health_t h = 3; return h; }")
    assert ast.type_aliases["health_t"] == "signed_int"

    src = """
typedef signed int health_t;
int main() {
    health_t h = 3;
    while (h > 0) {
        h -= 2;
    }
    return h;
}
"""
    asm = "\n".join(CodeGenerator().generate(_parse(src)))
    assert "JGT" in asm, "signed typedef alias should still emit signed comparisons"


def test_typedef_unsigned_alias_parses_and_compiles():
    """typedef unsigned int alias; preserves the unsigned_int type metadata."""
    ast = _parse("typedef unsigned int count_t; int main() { count_t x = 12; return x + 3; }")
    assert ast.type_aliases["count_t"] == "unsigned_int"

    source = """
typedef unsigned int count_t;
int main() {
    count_t total = 10;
    total += 5;
    return total;
}
"""
    from nova_assembler import Assembler
    from nova_main import initialize_system

    asm_path = os.path.join(os.environ.get("TEMP", "/tmp"), "astrid_unsigned_typedef_test.asm")
    with open(asm_path, "w") as f:
        f.write("\n".join(CodeGenerator().generate(_parse(source))))
    try:
        Assembler().assemble(asm_path)
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(asm_path.replace(".asm", ".bin"))
        for _ in range(20000):
            proc.step()
            if proc.halted:
                break
        assert proc.halted, "typedef unsigned int program should finish"
        assert proc.p0 == 15, f"expected total=15, got 0x{proc.p0:04X}"
    finally:
        for ext in (".asm", ".bin", ".org", ".sym"):
            path = asm_path.replace(".asm", ext)
            if os.path.exists(path):
                os.unlink(path)
