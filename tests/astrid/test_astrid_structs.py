"""High-coverage tests for Astrid struct support.

Covers:
1. Parser: struct definitions (ast.structs), scalar/array/pointer variable
   declarations, member access nodes (dot and arrow), member assignments
   (simple + compound decomposition), sizeof(struct Tag).
2. Codegen/layout: every field occupies one 16-bit word slot; field i lives
   at byte offset i*2; arrays of structs stride by the whole struct size.
3. Runtime (headless execution against the Nova-16 emulator):
   - Local structs: member load/store, initializer lists, independence.
   - Global structs: zero-default storage, DW initializers, shared mutation.
   - Arrays of structs: indexed members with variable indices, isolation.
   - Pointers: &struct, &struct.member, ->member (local + global pointers).
   - Compound assignment on members, postfix/prefix ++/--, address-of.
   - sizeof(struct Tag) == sizeof(scalarVar) == fields*2.
4. Error cases: unknown field, duplicate field, struct parameters, struct
   return values, excess initializers.
5. Multi-file: include merges struct definitions; conflicting layouts are
   rejected; identical layouts tolerated.
6. Graphics integration: struct fields driving set_pos/write_screen produce
   verifiable emulator pixels.
"""
import os
import shutil
import sys
import tempfile

import pytest

# Path setup handled by tests/astrid/conftest.py

from nova_main import initialize_system
from astrid.lexer.lexer import Lexer
from astrid.parser.parser import (
    Parser, VarDecl, MemberAccess, MemberAssignment,
    PrefixOp, PostfixOp, SizeofExpr, AddressOf, BinaryOp, ArrayAccess,
)


def run_binary(bin_path, max_cycles=2000000):
    """Run a binary headlessly and return (proc, cycles, mem)."""
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry_point = mem.load(bin_path)
    proc.pc = entry_point
    cycle = 0
    while cycle < max_cycles and not proc.halted:
        cycle += 1
        proc.step()
    return proc, cycle, mem


def compile_and_run(source, expected_r0=None, expected_p0=None):
    """Compile Astrid source, assemble, and run headlessly."""
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
    """Parse source text and return the Program AST."""
    return Parser(Lexer(src).tokenize()).parse()


# ---------------------------------------------------------------------------
# Parser-level tests
# ---------------------------------------------------------------------------

def test_parser_struct_definition_recorded():
    ast = parse_source(
        'struct Point { int x; int y; };' + chr(10) +
        'void main() { }')
    assert ast.structs == {'Point': [('x', 'int'), ('y', 'int')]}


def test_parser_struct_multi_name_fields():
    ast = parse_source(
        'struct S { int a, b; char c; };' + chr(10) +
        'void main() { }')
    assert ast.structs == {'S': [('a', 'int'), ('b', 'int'), ('c', 'char')]}


def test_parser_struct_definition_inside_function():
    ast = parse_source(
        'int main() {' + chr(10) +
        '    struct Inner { int v; };' + chr(10) +
        '    return 0;' + chr(10) +
        '}')
    assert ast.structs == {'Inner': [('v', 'int')]}


def test_parser_member_access_node():
    ret = parse_source('int main() { return p.x; }').functions[0].body[0]
    assert isinstance(ret.value, MemberAccess)
    assert ret.value.field == 'x'
    assert ret.value.arrow is False


def test_parser_arrow_member_access_node():
    ret = parse_source('int main() { return pp->x; }').functions[0].body[0]
    assert isinstance(ret.value, MemberAccess)
    assert ret.value.arrow is True
    assert ret.value.field == 'x'


def test_parser_array_element_member_access():
    ret = parse_source('int main() { return pts[i].x; }').functions[0].body[0]
    assert isinstance(ret.value, MemberAccess)
    assert isinstance(ret.value.base, ArrayAccess)
    assert ret.value.base.name == 'pts'


def test_parser_member_assignment_node():
    stmt = parse_source('int main() { p.x = 5; }').functions[0].body[0]
    assert isinstance(stmt, MemberAssignment)
    assert stmt.target.field == 'x'


def test_parser_compound_member_assignment_decomposes():
    stmt = parse_source('int main() { p.x += 5; }').functions[0].body[0]
    assert isinstance(stmt, MemberAssignment)
    assert isinstance(stmt.value, BinaryOp)
    assert stmt.value.op == '+'
    assert isinstance(stmt.value.left, MemberAccess)
    assert stmt.value.left.field == 'x'


def test_parser_global_struct_decl_records_tag():
    ast = parse_source(
        'struct Point { int x; int y; };' + chr(10) +
        'struct Point origin;' + chr(10) +
        'void main() { }')
    assert len(ast.globals) == 1
    g = ast.globals[0]
    assert isinstance(g, VarDecl)
    assert g.name == 'origin'
    assert g.var_type == 'struct'
    assert g.struct_tag == 'Point'
    assert not g.is_array


def test_parser_global_struct_array_decl():
    ast = parse_source(
        'struct Point { int x; int y; };' + chr(10) +
        'struct Point pts[4];' + chr(10) +
        'void main() { }')
    g = ast.globals[0]
    assert g.is_array
    assert g.struct_tag == 'Point'


def test_parser_sizeof_struct_type():
    src = ('struct Pair { int a; int b; int c; };' + chr(10) +
           'int main() { return sizeof(struct Pair); }')
    ret = parse_source(src).functions[0].body[0]
    assert isinstance(ret.value, SizeofExpr)
    assert ret.value.target == ('struct', 'Pair')


def test_parser_postfix_on_member_node():
    stmt = parse_source('int main() { p.x++; }').functions[0].body[0]
    assert isinstance(stmt, PostfixOp)
    assert isinstance(stmt.left, MemberAccess)
    assert stmt.op == '++'


def test_parser_prefix_on_member_node():
    # body[0] is the Return statement; the expression is its .value
    ret = parse_source('int main() { return ++p.x; }').functions[0].body[0]
    assert isinstance(ret.value, PrefixOp)
    assert isinstance(ret.value.operand, MemberAccess)


def test_parser_address_of_member_node():
    decl = parse_source('int main() { int *q = &p.x; }').functions[0].body[0]
    assert isinstance(decl.value, AddressOf)
    assert isinstance(decl.value.operand, MemberAccess)


# ---------------------------------------------------------------------------
# Runtime: scalar structs (local + global)
# ---------------------------------------------------------------------------

def test_local_struct_member_roundtrip():
    source = chr(10).join([
        'struct Point { int x; int y; };',
        'int main() {',
        '    struct Point p;',
        '    p.x = 30;',
        '    p.y = 12;',
        '    return p.x * 10 + p.y;   // 312',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_p0=312)
    print(f'PASS test_local_struct_member_roundtrip (cycles={cycles})')


def test_local_struct_initializer_list():
    source = chr(10).join([
        'struct Point { int x; int y; };',
        'int main() {',
        '    struct Point p = {10, 20};',
        '    return p.x + p.y;   // 30',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=30)
    print(f'PASS test_local_struct_initializer_list (R0={proc.r0})')


def test_two_locals_same_tag_independent():
    source = chr(10).join([
        'struct Point { int x; int y; };',
        'int main() {',
        '    struct Point a;',
        '    struct Point b;',
        '    a.x = 1; a.y = 2;',
        '    b.x = 10; b.y = 20;',
        '    return (a.x + a.y) * 100 + (b.x + b.y);   // 330',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_p0=330)
    print(f'PASS test_two_locals_same_tag_independent (P0={proc.p0})')


def test_global_struct_default_zero_then_write():
    source = chr(10).join([
        'struct Point { int x; int y; };',
        'struct Point origin;',
        'int peek_y() { return origin.y; }',
        'int main() {',
        '    if (origin.x != 0 || origin.y != 0) { return 255; }',
        '    origin.x = 44;',
        '    origin.y = 11;',
        '    return origin.x + peek_y();   // 55',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=55)
    print(f'PASS test_global_struct_default_zero_then_write (R0={proc.r0})')


def test_global_struct_initializer_list():
    source = chr(10).join([
        'struct Point { int x; int y; };',
        'struct Point origin = {120, 64};',
        'int main() {',
        '    return origin.x * 2 + origin.y;   // 304',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_p0=304)
    print(f'PASS test_global_struct_initializer_list (P0={proc.p0})')


def test_char_field_word_slot_semantics():
    """char fields are full word slots: they hold any 16-bit value."""
    source = chr(10).join([
        'struct Mix { char tag; int val; };',
        'int main() {',
        '    struct Mix m;',
       "    m.tag = 'A';",
        '    m.val = 1000;',
        '    return m.tag + m.val;   // 65 + 1000 = 1065',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_p0=1065)
    print(f'PASS test_char_field_word_slot_semantics (P0={proc.p0})')


# ---------------------------------------------------------------------------
# Runtime: compound assignment, inc/dec, address-of on members
# ---------------------------------------------------------------------------

COMPOUND_OPS = [
    ('+=', 5, 15),
    ('-=', 5, 5),
    ('*=', 3, 30),
    ('/=', 2, 5),
    ('%=', 3, 1),
]


@pytest.mark.parametrize('op,rhs,expected', COMPOUND_OPS,
                         ids=[c[0] for c in COMPOUND_OPS])
def test_member_arithmetic_compound_ops(op, rhs, expected):
    source = chr(10).join([
        'struct Point { int x; int y; };',
        'int main() {',
        '    struct Point p;',
        '    p.x = 10;',
        '    p.y = 0;',
        '    p.x ' + op + ' ' + str(rhs) + ';',
        '    p.y = p.x;',
        '    return p.y;',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=expected)
    print(f'PASS test_member_compound {op} -> {expected}')


def test_member_bitwise_compound_ops():
    source = chr(10).join([
        'struct Flags { int bits; int more; };',
        'int main() {',
        '    struct Flags f;',
        '    f.bits = 0xF0;',
        '    f.more = 0;',
        '    f.bits |= 0x0F;',
        '    f.bits &= 0x3C;',
        '    f.bits ^= 0xFF;',
        '    f.more = 3;',
        '    f.more <<= 2;',
        '    f.more >>= 1;',
        '    return f.bits + f.more;   // 195 + 6 = 201',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=201)
    print(f'PASS test_member_bitwise_compound_ops (R0={proc.r0})')


def test_member_postfix_increment_returns_old():
    source = chr(10).join([
        'struct Counter { int n; int total; };',
        'int main() {',
        '    struct Counter c;',
        '    c.n = 41;',
        '    c.total = 0;',
        '    c.total = c.n++;',
        '    return c.total * 100 + c.n;   // 4142',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_p0=4142)
    print(f'PASS test_member_postfix_increment (P0={proc.p0})')


def test_member_prefix_increment_returns_new():
    source = chr(10).join([
        'struct Counter { int m; int spare; };',
        'int main() {',
        '    struct Counter c;',
        '    c.m = 41;',
        '    c.spare = ++c.m;',
        '    return c.spare * 100 + c.m;   // 4242',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_p0=4242)
    print(f'PASS test_member_prefix_increment (P0={proc.p0})')


def test_address_of_member_via_pointer():
    source = chr(10).join([
        'struct Point { int x; int y; };',
        'int main() {',
        '    struct Point p;',
        '    p.x = 1;',
        '    p.y = 2;',
        '    int *py = &p.y;',
        '    *py = 99;',
        '    return p.x * 100 + p.y;   // 1*100 + 99 = 199',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=199)
    print(f'PASS test_address_of_member_via_pointer (R0={proc.r0})')


# ---------------------------------------------------------------------------
# Runtime: arrays of structs
# ---------------------------------------------------------------------------

def test_struct_array_indexed_members_loop():
    source = chr(10).join([
        'struct Cell { int val; int mark; };',
        'int main() {',
        '    struct Cell cells[4];',
        '    int i;',
        '    for (i = 0; i < 4; i++) {',
        '        cells[i].val = i * 3;',
        '        cells[i].mark = 100;',
        '    }',
        '    int sum = 0;',
        '    for (i = 0; i < 4; i++) {',
        '        sum += cells[i].val + cells[i].mark;',
        '    }',
        '    return sum;   // (0+3+6+9) + 400 = 418',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_p0=418)
    print(f'PASS test_struct_array_indexed_members_loop (P0={proc.p0})')


def test_struct_array_elements_do_not_alias():
    source = chr(10).join([
        'struct Wide { int a; int b; int c; };',
        'int main() {',
        '    struct Wide ws[3];',
        '    int i;',
        '    for (i = 0; i < 3; i++) {',
        '        ws[i].a = 0;',
        '        ws[i].b = 0;',
        '        ws[i].c = 0;',
        '    }',
        '    ws[1].b = 777;',
        '    return ws[0].b + ws[2].b + ws[1].b / 7;   // 111',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=111)
    print(f'PASS test_struct_array_elements_do_not_alias (R0={proc.r0})')


def test_global_struct_array_with_flat_init():
    source = chr(10).join([
        'struct Point { int x; int y; };',
        'struct Point tri[3] = {1, 2, 3, 4, 5, 6};',
        'int main() {',
        '    return tri[0].x + tri[1].y + tri[2].x + tri[2].y;   // 16',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=16)
    print(f'PASS test_global_struct_array_with_flat_init (R0={proc.r0})')


def test_local_struct_array_initializer_list():
    source = chr(10).join([
        'struct Point { int x; int y; };',
        'int main() {',
        '    struct Point pts[2] = {10, 20, 30, 40};',
        '    return pts[0].y + pts[1].x;   // 50',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=50)
    print(f'PASS test_local_struct_array_initializer_list (R0={proc.r0})')


# ---------------------------------------------------------------------------
# Runtime: struct pointers and -> member access
# ---------------------------------------------------------------------------

def test_arrow_through_pointer_to_local_struct():
    source = chr(10).join([
        'struct Point { int x; int y; };',
        'int main() {',
        '    struct Point p;',
        '    struct Point *pp = &p;',
        '    p.x = 8;',
        '    pp->y = 13;',
        '    pp->x += 1;',
        '    return p.x * 100 + p.y;   // 913',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_p0=913)
    print(f'PASS test_arrow_through_pointer_to_local_struct (P0={proc.p0})')


def test_arrow_to_struct_array_element():
    source = chr(10).join([
        'struct Item { int id; int qty; };',
        'int main() {',
        '    struct Item items[3];',
        '    int i;',
        '    for (i = 0; i < 3; i++) {',
        '        items[i].id = i;',
        '        items[i].qty = 0;',
        '    }',
        '    struct Item *p = &items[1];',
        '    p->qty = 55;',
        '    return items[1].qty + items[0].qty + items[2].qty;   // 55',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=55)
    print(f'PASS test_arrow_to_struct_array_element (R0={proc.r0})')


def test_global_struct_pointer_arrow():
    source = chr(10).join([
        'struct Sensor { int reading; int scale; };',
        'struct Sensor s1;',
        'struct Sensor *cursor;',
        'int main() {',
        '    cursor = &s1;',
        '    cursor->reading = 250;',
        '    cursor->scale = 4;',
        '    return cursor->reading * cursor->scale / 100;   // 10',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=10)
    print(f'PASS test_global_struct_pointer_arrow (R0={proc.r0})')


# ---------------------------------------------------------------------------
# Runtime: sizeof, members as arguments, conditions, multiple tags
# ---------------------------------------------------------------------------

def test_sizeof_struct_forms_agree():
    source = chr(10).join([
        'struct Quad { int a; int b; int c; int d; };',
        'int main() {',
        '    struct Quad q;',
        '    struct Quad qs[5];',
        '    int by_type = sizeof(struct Quad);',
        '    int by_var = sizeof(q);',
        '    int per_elem = sizeof(qs) / 5;',
        '    return by_type * 100 + by_var * 10 + per_elem;   // 8*100+8*10+8 = 888',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=120)
    assert proc.p0 == 888
    print(f'PASS test_sizeof_struct_forms_agree (P0={proc.p0})')


def test_members_as_function_arguments():
    source = chr(10).join([
        'struct Vec { int dx; int dy; };',
        'int bump(int v) { v += 100; return v; }',
        'int main() {',
        '    struct Vec v;',
        '    v.dx = 3;',
        '    v.dy = 4;',
        '    int r = bump(v.dx) + v.dy;',
        '    return r * 10 + v.dx;   // 1073',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_p0=1073)
    print(f'PASS test_members_as_function_arguments (P0={proc.p0})')


def test_member_in_condition_and_loop():
    source = chr(10).join([
        'struct Acc { int i; int sum; };',
        'int main() {',
        '    struct Acc a;',
        '    a.i = 0;',
        '    a.sum = 0;',
        '    while (a.i < 5) {',
        '        a.sum += a.i;',
        '        a.i++;',
        '    }',
        '    if (a.sum == 10) { return 200 + a.sum; }',
        '    return 0;',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=210)
    print(f'PASS test_member_in_condition_and_loop (R0={proc.r0})')


def test_multiple_tags_same_program():
    source = chr(10).join([
        'struct A { int one; int two; int three; };',
        'struct B { int alpha; };',
        'int main() {',
        '    struct A a;',
        '    struct B b;',
        '    a.one = 1; a.two = 2; a.three = 3;',
        '    b.alpha = 40;',
        '    return b.alpha + a.one + a.two + a.three;   // 46',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=46)
    print(f'PASS test_multiple_tags_same_program (R0={proc.r0})')


# ---------------------------------------------------------------------------
# Graphics integration: struct-driven rendering verified via pixels
# ---------------------------------------------------------------------------

def test_struct_driven_graphics_headless():
    """Struct fields drive set_pos/write_screen; pixels appear exactly where
    the struct coordinates say they must (headless pixel report)."""
    source = chr(10).join([
        'struct Sprite { int x; int y; int color; };',
        'int main() {',
        '    struct Sprite sp;',
        '    sp.x = 40;',
        '    sp.y = 60;',
        '    sp.color = 0x0F;',
        '    set_layer(0);',
        '    set_pos(sp.x, sp.y);',
        '    write_screen(sp.color);',
        '    set_pos(sp.x + 8, sp.y);',
        '    write_screen(sp.color - 5);',
        '    return 0;',
        '}',
    ])
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
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(source_path.replace('.ast', '.bin'))
        cycles = 0
        while cycles < 500000 and not proc.halted:
            cycles += 1
            proc.step()
        assert proc.halted, 'graphics program did not halt'
        screen = gfx.screen
        assert screen[60, 40] == 0x0F, f'got {screen[60, 40]} at (40,60)'
        assert screen[60, 48] == 0x0A, f'got {screen[60, 48]} at (48,60)'
        nz = int((screen != 0).sum())
        assert nz >= 2
        print(f'PASS test_struct_driven_graphics_headless '
              f'(cycles={cycles}, non_zero_pixels={nz})')
    finally:
        for ext in ['.ast', '.asm', '.bin', '.org', '.sym']:
            p = source_path.replace('.ast', ext)
            if os.path.exists(p):
                os.unlink(p)


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

def test_unknown_field_is_compile_error():
    source = chr(10).join([
        'struct Point { int x; int y; };',
        'int main() {',
        '    struct Point p;',
        '    p.z = 1;',
        '    return 0;',
        '}',
    ])
    # The CLI entry point catches compiler exceptions internally, so drive
    # the Parser + CodeGenerator directly to observe the raise.
    from astrid.codegen.codegen import CodeGenerator
    with pytest.raises((NameError, TypeError)):
        CodeGenerator().generate(parse_source(source))
    print('PASS test_unknown_field_is_compile_error')


def test_duplicate_field_rejected():
    src = 'struct S { int a; int a; };' + chr(10) + 'void main() { }'
    with pytest.raises(SyntaxError, match='Duplicate field'):
        parse_source(src)
    print('PASS test_duplicate_field_rejected')


def test_struct_parameter_rejected():
    src = chr(10).join([
        'struct P { int x; };',
        'void f(struct P v) { }',
        'void main() { }',
    ])
    with pytest.raises(SyntaxError, match='Struct parameters'):
        parse_source(src)
    print('PASS test_struct_parameter_rejected')


def test_struct_return_rejected():
    src = chr(10).join([
        'struct P { int x; };',
        'struct P make() { }',
        'void main() { }',
    ])
    with pytest.raises(SyntaxError, match='Returning structs'):
        parse_source(src)
    print('PASS test_struct_return_rejected')


def test_excess_initializers_rejected():
    source = chr(10).join([
        'struct Point { int x; int y; };',
        'struct Point g = {1, 2, 3};',
        'int main() { return 0; }',
    ])
    from astrid.codegen.codegen import CodeGenerator
    with pytest.raises(TypeError, match='initializers'):
        CodeGenerator().generate(parse_source(source))
    print('PASS test_excess_initializers_rejected')


# ---------------------------------------------------------------------------
# Multi-file compilation units: include merges struct definitions
# ---------------------------------------------------------------------------

class _Unit:
    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix='astrid_struct_')

    def write(self, name, text):
        path = os.path.join(self.dir, name)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        return path

    def parse(self, name):
        path = os.path.join(self.dir, name)
        with open(path, encoding='utf-8') as f:
            src = f.read()
        return Parser(Lexer(src).tokenize(), source_path=path).parse()

    def compile_and_run(self, name):
        from astrid_compiler import main as compiler_main
        path = os.path.join(self.dir, name)
        old_argv = sys.argv
        sys.argv = [old_argv[0], path]
        try:
            compiler_main()
        finally:
            sys.argv = old_argv
        from nova_assembler import Assembler
        Assembler().assemble(path.replace('.ast', '.asm'))
        proc, cycles, mem = run_binary(path.replace('.ast', '.bin'))
        assert proc.halted, name + ': did not halt'
        return proc, cycles, mem

    def cleanup(self):
        shutil.rmtree(self.dir, ignore_errors=True)


@pytest.fixture
def unit():
    u = _Unit()
    yield u
    u.cleanup()


def test_include_merges_struct_definitions(unit):
    unit.write('geom.ast', 'struct Vec { int dx; int dy; };' + chr(10))
    unit.write('main.ast', chr(10).join([
        'include "geom.ast";',
        'int main() {',
        '    struct Vec v;',
        '    v.dx = 21;',
        '    v.dy = 21;',
        '    return v.dx + v.dy;',
        '}',
    ]))
    ast = unit.parse('main.ast')
    assert ast.structs == {'Vec': [('dx', 'int'), ('dy', 'int')]}
    proc, cycles, mem = unit.compile_and_run('main.ast')
    assert proc.r0 == 42
    print(f'PASS test_include_merges_struct_definitions (R0={proc.r0})')


def test_include_conflicting_struct_layout_rejected(unit):
    unit.write('a.ast', 'struct S { int x; int y; };' + chr(10))
    unit.write('b.ast',
               'include "a.ast";' + chr(10) +
               'struct S { int z; };' + chr(10))
    unit.write('main.ast', 'include "b.ast";' + chr(10) + 'void main() { }')
    with pytest.raises(SyntaxError, match='redefined'):
        unit.parse('main.ast')
    print('PASS test_include_conflicting_struct_layout_rejected')


def test_include_identical_layout_tolerated(unit):
    unit.write('a.ast', 'struct S { int x; int y; };' + chr(10))
    unit.write('b.ast',
               'include "a.ast";' + chr(10) +
               'struct S { int x; int y; };' + chr(10))
    unit.write('main.ast', chr(10).join([
        'include "b.ast";',
        'int main() { struct S s; s.x = 4; s.y = 5; return s.x + s.y; }',
    ]))
    proc, cycles, mem = unit.compile_and_run('main.ast')
    assert proc.r0 == 9
    print(f'PASS test_include_identical_layout_tolerated (R0={proc.r0})')






# ---------------------------------------------------------------------------
# C-style definition-footer declarators: struct Tag { ... } inst, arr[2], *p;
# ---------------------------------------------------------------------------

def test_parser_footer_declarators_recorded():
    ast = parse_source(
        'struct P { int x; int y; } a, b[2], *c;' + chr(10) +
        'void main() { }')
    assert ast.structs == {'P': [('x', 'int'), ('y', 'int')]}
    names = [(g.name, g.struct_tag) for g in ast.globals]
    assert names == [('a', 'P'), ('b', 'P'), ('c', 'P')]
    assert not ast.globals[0].is_array
    assert ast.globals[1].is_array
    assert ast.globals[2].pointer_depth == 1


def test_footer_declarator_variable_shares_tag_name():
    """Like in C, an instance may share its struct's tag name."""
    source = chr(10).join([
        'struct Player { int x; int y; } Player;',
        'int main() {',
        '    Player.x = 30;',
        '    Player.y = 12;',
        '    return Player.x * 10 + Player.y;   // 312',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_p0=312)
    print(f'PASS test_footer_declarator_variable_shares_tag_name (P0={proc.p0})')


def test_footer_declarators_with_initializers_runtime():
    source = chr(10).join([
        'struct P { int x; int y; } g = {7, 9};',
        'int main() {',
        '    struct P loc = {1, 2};',
        '    return g.x * 100 + g.y * 10 + loc.x + loc.y;',
        '}',
    ])
    # 700 + 90 + 3 = 793
    proc, cycles, mem = compile_and_run(source, expected_p0=793)
    print(f'PASS test_footer_declarators_with_initializers (P0={proc.p0})')


def test_footer_struct_array_and_pointer_runtime():
    source = chr(10).join([
        'struct Cell { int v; int w; } cells[3], *cursor;',
        'int main() {',
        '    int i;',
        '    for (i = 0; i < 3; i++) {',
        '        cells[i].v = i;',
        '        cells[i].w = 10;',
        '    }',
        '    cursor = &cells[2];',
        '    cursor->v += 40;',
        '    return cells[2].v * 100 + cells[0].w;   // (42)*100 + 10',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_p0=4210)
    print(f'PASS test_footer_struct_array_and_pointer_runtime (P0={proc.p0})')


def test_local_footer_declarator_inside_function():
    source = chr(10).join([
        'struct T { int a; int b; };',
        'int main() {',
        '    struct U { int p; int q; } u = {5, 6};',
        '    return u.p * 10 + u.q;   // 56',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=56)
    print(f'PASS test_local_footer_declarator_inside_function (R0={proc.r0})')


def test_footer_duplicate_global_rejected():
    src = chr(10).join([
        'struct S { int x; } dup;',
        'int dup;',
        'void main() { }',
    ])
    with pytest.raises(SyntaxError, match='Duplicate definition of global'):
        parse_source(src)
    print('PASS test_footer_duplicate_global_rejected')
