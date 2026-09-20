"""High-coverage tests for Astrid nested struct member access (a.b.c).
"""
import os
import sys
import tempfile

import pytest

from nova_main import initialize_system
from astrid.errors import CodeGenError
from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser


def run_binary(bin_path, max_cycles=2000000):
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry_point = mem.load(bin_path)
    proc.pc = entry_point
    cycle = 0
    while cycle < max_cycles and not proc.halted:
        cycle += 1
        proc.step()
    return proc, cycle, mem


def compile_and_run(source, expected_r0=None, expected_p0=None):
    fd = tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8')
    fd.write(source)
    fd.close()
    source_path = fd.name
    try:
        from astrid_compiler import main as compiler_main
        old_argv = sys.argv
        sys.argv = [old_argv[0], source_path, '-o',
                    source_path.replace('.ast', '.asm')]
        try:
            compiler_main()
        finally:
            sys.argv = old_argv

        from nova_assembler import Assembler
        Assembler().assemble(source_path.replace('.ast', '.asm'))

        proc, cycles, mem = run_binary(source_path.replace('.ast', '.bin'))
        assert proc.halted, 'Program did not halt'
        if expected_r0 is not None:
            assert proc.r0 == expected_r0, \
                f'Expected R0={expected_r0}, got {proc.r0}'
        if expected_p0 is not None:
            assert proc.p0 == expected_p0, \
                f'Expected P0={expected_p0}, got {proc.p0}'
        return proc, cycles, mem
    finally:
        for ext in ['.ast', '.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


def parse_source(src):
    return Parser(Lexer(src).tokenize()).parse()


def test_parser_nested_struct_definition():
    ast = parse_source(
        'struct Point { int x; int y; };\n'
        'struct Rect { struct Point topLeft; struct Point botRight; };\n'
        'void main() { }')
    assert ast.structs['Rect'] == [
        ('topLeft', 'struct Point'), ('botRight', 'struct Point')]
    assert ast.structs['Point'] == [('x', 'int'), ('y', 'int')]


def test_parser_three_level_nested_struct():
    ast = parse_source(
        'struct A { int a; };\n'
        'struct B { struct A inner; int b; };\n'
        'struct C { struct B deep; int c; };\n'
        'void main() { }')
    assert ast.structs['C'] == [('deep', 'struct B'), ('c', 'int')]
    assert ast.structs['B'] == [('inner', 'struct A'), ('b', 'int')]


# --- Runtime tests ------------------------------------------------------

def test_nested_struct_member_write_read():
    source = """
struct Point { int x; int y; };
struct Rect { struct Point topLeft; struct Point botRight; };

int main() {
    struct Rect r;
    r.topLeft.x = 10;
    r.topLeft.y = 20;
    r.botRight.x = 30;
    r.botRight.y = 40;
    return r.topLeft.x + r.topLeft.y + r.botRight.x + r.botRight.y;
}
"""
    compile_and_run(source, expected_r0=100)


def test_nested_struct_three_levels():
    source = """
struct A { int a; };
struct B { struct A inner; int b; };
struct C { struct B deep; int c; };

int main() {
    struct C obj;
    obj.deep.inner.a = 1;
    obj.deep.b = 2;
    obj.c = 3;
    return obj.deep.inner.a + obj.deep.b + obj.c;
}
"""
    compile_and_run(source, expected_r0=6)


def test_nested_struct_global():
    # 600 does not fit in the 8-bit R0, so assert the 16-bit P0 return value.
    source = """
struct Point { int x; int y; };
struct Rect { struct Point topLeft; struct Point botRight; };

struct Rect g_rect;

int main() {
    g_rect.topLeft.x = 100;
    g_rect.topLeft.y = 200;
    g_rect.botRight.x = 300;
    return g_rect.topLeft.x + g_rect.topLeft.y + g_rect.botRight.x;
}
"""
    compile_and_run(source, expected_p0=600)


def test_nested_struct_global_layout():
    """A nested global struct must reserve its full nested byte size.

    `struct Rect` is four words (8 bytes), not two.  Pinning both globals at
    known addresses and reading the emulator's memory afterwards catches a
    too-small allocation as an overlap between g_rect's tail and g_sentinel.
    """
    source = """
struct Point { int x; int y; };
struct Rect { struct Point topLeft; struct Point botRight; };

struct Rect g_rect @ 0x8800;
int g_sentinel @ 0x8900;

int main() {
    g_rect.topLeft.x = 111;
    g_rect.topLeft.y = 222;
    g_rect.botRight.x = 333;
    g_rect.botRight.y = 444;
    g_sentinel = 999;
    return 0;
}
"""
    proc, cycles, mem = compile_and_run(source)
    assert proc.halted, 'Program did not halt'
    # 16-bit big-endian word reads via the memory API.
    rect_words = [mem.read_word(0x8800 + i * 2) for i in range(4)]
    assert rect_words == [111, 222, 333, 444], rect_words
    assert mem.read_word(0x8900) == 999


def test_nested_struct_array():
    source = """
struct Inner { int x; int y; };
struct Wrap { struct Inner inner; int z; };

int main() {
    struct Wrap arr[2];
    arr[0].inner.x = 1;
    arr[0].inner.y = 2;
    arr[0].z = 3;
    arr[1].inner.x = 4;
    arr[1].inner.y = 5;
    arr[1].z = 6;
    return arr[1].inner.x + arr[0].inner.x;
}
"""
    compile_and_run(source, expected_r0=5)


def test_nested_struct_array_variable_index():
    source = """
struct Inner { int x; int y; };
struct Wrap { struct Inner inner; int z; };

int main() {
    struct Wrap arr[3];
    int i;
    for (i = 0; i < 3; i = i + 1) {
        arr[i].inner.x = i;
        arr[i].inner.y = i * 10;
        arr[i].z = i * 100;
    }
    return arr[2].inner.x + arr[2].inner.y + arr[2].z;
}
"""
    compile_and_run(source, expected_r0=222)



def test_nested_struct_pointer():
    source = """
struct Point { int x; int y; };
struct Rect { struct Point topLeft; struct Point botRight; };

int main() {
    struct Rect r;
    struct Rect *rp;
    rp = &r;
    rp->topLeft.x = 11;
    rp->topLeft.y = 22;
    rp->botRight.x = 33;
    return rp->topLeft.x + rp->topLeft.y + rp->botRight.x;
}
"""
    compile_and_run(source, expected_r0=66)


def test_nested_struct_compound_assignment():
    source = """
struct Point { int x; int y; };
struct Rect { struct Point topLeft; struct Point botRight; };

int main() {
    struct Rect r;
    r.topLeft.x = 5;
    r.topLeft.x += 10;
    r.topLeft.y = 7;
    r.topLeft.y *= 2;
    r.botRight.x = 3;
    r.botRight.x++;
    return r.topLeft.x + r.topLeft.y + r.botRight.x;
}
"""
    compile_and_run(source, expected_r0=33)


def test_nested_struct_copy():
    source = """
struct Point { int x; int y; };
struct Rect { struct Point a; struct Point b; };

int main() {
    struct Rect r1;
    r1.a.x = 10;
    r1.a.y = 20;
    r1.b.x = 30;
    r1.b.y = 40;
    struct Rect r2;
    r2 = r1;
    return r2.a.x + r2.a.y + r2.b.x + r2.b.y;
}
"""
    compile_and_run(source, expected_r0=100)


def test_nested_struct_independent_fields():
    source = """
struct Point { int x; int y; };
struct Rect { struct Point topLeft; struct Point botRight; };

int main() {
    struct Rect r;
    r.topLeft.x = 5;
    r.botRight.y = 10;
    return r.topLeft.x + r.botRight.y;
}
"""
    compile_and_run(source, expected_r0=15)


def test_nested_struct_with_char_field():
    source = """
struct Point { int x; char flag; };
struct Rect { struct Point tl; int y; };

int main() {
    struct Rect r;
    r.tl.x = 42;
    r.tl.flag = 7;
    r.y = 99;
    return r.tl.x + r.tl.flag + r.y;
}
"""
    compile_and_run(source, expected_r0=148)


def test_nested_struct_via_typedef_alias_field():
    """A typedef alias naming a struct is a valid nested field type."""
    source = """
struct Point { int x; int y; };
typedef struct Point Coord;
struct Line { Coord from; Coord to; };

int main() {
    struct Line l;
    l.from.x = 7;
    l.from.y = 11;
    l.to.x = 100;
    return l.from.x + l.from.y + l.to.x;
}
"""
    compile_and_run(source, expected_r0=118)


def test_nested_member_through_union_field():
    """A union member that is a struct must keep its declared type.

    Regression: the union branch of the field-type lookup used to report the
    member type as plain 'int', so `u.p.a` failed with
    "Undefined struct type 'int'" instead of resolving through `struct Pair`.
    """
    source = """
struct Pair { int a; int b; };
union U { struct Pair p; int whole; };

int main() {
    union U u;
    u.p.a = 5;
    u.p.b = 12;
    return u.p.a + u.p.b;
}
"""
    compile_and_run(source, expected_r0=17)


def test_union_field_offsets_overlap():
    """All union members share offset 0, including nested aggregates."""
    source = """
struct Pair { int a; int b; };
union U { struct Pair p; int whole; };

int main() {
    union U u;
    u.p.a = 1;
    u.p.b = 2;
    u.p.a = 9;
    return u.p.a;
}
"""
    compile_and_run(source, expected_r0=9)


# --- Error cases --------------------------------------------------------

def test_error_unknown_nested_field():
    with pytest.raises(Exception):
        source = """
struct Point { int x; int y; };
struct Rect { struct Point topLeft; };

int main() {
    struct Rect r;
    r.topLeft.z = 1;
}
"""
        compile_and_run(source)


def test_error_non_struct_field_member_access():
    with pytest.raises(Exception):
        source = """
struct Point { int x; int y; };
struct Rect { struct Point topLeft; };

int main() {
    struct Rect r;
    r.topLeft.x.y = 1;
}
"""
        compile_and_run(source)


def test_error_undefined_nested_field_type():
    """A by-value nested field needs a complete type defined earlier."""
    with pytest.raises(Exception):
        compile_and_run(
            'struct Outer { struct Nope n; };\n'
            'int main() { return 0; }\n')


def test_error_self_referential_struct():
    """A struct may not contain itself, directly or indirectly."""
    with pytest.raises(Exception):
        compile_and_run(
            'struct A { struct A inner; };\n'
            'int main() { return 0; }\n')
    with pytest.raises(Exception):
        compile_and_run(
            'struct A { struct B b; };\n'
            'struct B { struct A a; };\n'
            'int main() { return 0; }\n')
