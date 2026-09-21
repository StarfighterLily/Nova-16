"""High-coverage tests for Astrid by-value struct/union returns.

Hidden-sret convention: the caller pushes a destination address as the first
argument (last on the stack); the callee copies the returned aggregate through
that pointer and leaves the address in P0.  Assignment / init of a matching
struct variable (`p = make(...)`, `struct Point p = make(...)`) pass `&p`
directly so no intermediate copy is needed.
"""
import os
import sys
import tempfile

import pytest

from nova_main import initialize_system
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
        for ext in ['.ast', '.asm', '.bin', '.org', '.sym', '.nex']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


def parse_source(src):
    return Parser(Lexer(src).tokenize()).parse()


# --- Parser --------------------------------------------------------------

def test_parser_accepts_struct_return():
    ast = parse_source(
        'struct Point { int x; int y; };\n'
        'struct Point make(int x, int y) { struct Point p; return p; }\n'
        'void main() { }\n')
    f = ast.functions[0]
    assert f.name == 'make'
    assert f.return_struct_tag == 'Point'
    assert f.return_type == 'struct'


def test_parser_accepts_union_return():
    ast = parse_source(
        'union U { int a; int b; };\n'
        'union U make() { union U u; return u; }\n'
        'void main() { }\n')
    assert ast.functions[0].return_struct_tag == 'U'


def test_parser_rejects_undefined_return_tag():
    with pytest.raises(SyntaxError, match='Undefined struct'):
        parse_source(
            'struct Point make() { }\n'
            'void main() { }\n')


def test_parser_pointer_return_is_not_sret():
    """struct Point *f() is a scalar address return, not by-value sret."""
    ast = parse_source(
        'struct Point { int x; };\n'
        'struct Point *get(struct Point *p) { return p; }\n'
        'void main() { }\n')
    f = ast.functions[0]
    assert f.return_struct_tag is None
    assert getattr(f, 'return_pointer_depth', 0) == 1

# --- Runtime: basic return + assignment ---------------------------------

def test_return_assign_to_local():
    src = chr(10).join([
        'struct Point { int x; int y; };',
        'struct Point make(int x, int y) {',
        '    struct Point p;',
        '    p.x = x;',
        '    p.y = y;',
        '    return p;',
        '}',
        'int main() {',
        '    struct Point a;',
        '    a = make(10, 20);',
        '    return a.x + a.y;',
        '}',
    ])
    compile_and_run(src, expected_p0=30)


def test_return_init_local():
    src = chr(10).join([
        'struct Point { int x; int y; };',
        'struct Point make(int x, int y) {',
        '    struct Point p;',
        '    p.x = x;',
        '    p.y = y;',
        '    return p;',
        '}',
        'int main() {',
        '    struct Point a = make(7, 8);',
        '    return a.x * 10 + a.y;',
        '}',
    ])
    compile_and_run(src, expected_p0=78)


def test_return_assign_to_global():
    src = chr(10).join([
        'struct Point { int x; int y; };',
        'struct Point g;',
        'struct Point make(int x, int y) {',
        '    struct Point p;',
        '    p.x = x;',
        '    p.y = y;',
        '    return p;',
        '}',
        'int main() {',
        '    g = make(3, 4);',
        '    return g.x * 10 + g.y;',
        '}',
    ])
    compile_and_run(src, expected_p0=34)


def test_return_no_args():
    src = chr(10).join([
        'struct Point { int x; int y; };',
        'struct Point origin() {',
        '    struct Point p;',
        '    p.x = 0;',
        '    p.y = 0;',
        '    return p;',
        '}',
        'int main() {',
        '    struct Point a;',
        '    a = origin();',
        '    a.x = 5;',
        '    return a.x + a.y;',
        '}',
    ])
    compile_and_run(src, expected_p0=5)


def test_return_is_a_copy():
    src = chr(10).join([
        'struct Point { int x; int y; };',
        'struct Point flip(struct Point p) {',
        '    struct Point q;',
        '    q.x = p.y;',
        '    q.y = p.x;',
        '    return q;',
        '}',
        'int main() {',
        '    struct Point a;',
        '    struct Point b;',
        '    a.x = 1; a.y = 2;',
        '    b = flip(a);',
        '    return a.x * 1000 + a.y * 100 + b.x * 10 + b.y;',
        '}',
    ])
    compile_and_run(src, expected_p0=1221)


def test_return_byval_param():
    src = chr(10).join([
        'struct Point { int x; int y; };',
        'struct Point id(struct Point p) { return p; }',
        'int main() {',
        '    struct Point a;',
        '    struct Point b;',
        '    a.x = 9; a.y = 8;',
        '    b = id(a);',
        '    a.x = 0;',
        '    return b.x * 10 + b.y;',
        '}',
    ])
    compile_and_run(src, expected_p0=98)

def test_return_nested_struct():
    src = chr(10).join([
        'struct Point { int x; int y; };',
        'struct Rect { struct Point tl; struct Point br; };',
        'struct Rect make_rect(int a, int b, int c, int d) {',
        '    struct Rect r;',
        '    r.tl.x = a; r.tl.y = b;',
        '    r.br.x = c; r.br.y = d;',
        '    return r;',
        '}',
        'int main() {',
        '    struct Rect r;',
        '    r = make_rect(1, 2, 3, 4);',
        '    return r.tl.x + r.tl.y * 10 + r.br.x * 100 + r.br.y * 1000;',
        '}',
    ])
    compile_and_run(src, expected_p0=4321)


def test_return_union():
    src = chr(10).join([
        'union U { int a; int b; };',
        'union U make(int v) {',
        '    union U u;',
        '    u.a = v;',
        '    return u;',
        '}',
        'int main() {',
        '    union U u;',
        '    u = make(42);',
        '    return u.b;',
        '}',
    ])
    compile_and_run(src, expected_p0=42)


def test_return_nested_member():
    src = chr(10).join([
        'struct Point { int x; int y; };',
        'struct Rect { struct Point tl; struct Point br; };',
        'struct Point bottom_right(struct Rect r) { return r.br; }',
        'int main() {',
        '    struct Rect r;',
        '    struct Point p;',
        '    r.br.x = 11; r.br.y = 22;',
        '    p = bottom_right(r);',
        '    return p.x * 10 + p.y;',
        '}',
    ])
    compile_and_run(src, expected_p0=132)


def test_return_array_element():
    src = chr(10).join([
        'struct Point { int x; int y; };',
        'struct Point pick(struct Point arr[3], int i) { return arr[i]; }',
        'int main() {',
        '    struct Point arr[3];',
        '    struct Point p;',
        '    arr[0].x = 1; arr[0].y = 2;',
        '    arr[1].x = 3; arr[1].y = 4;',
        '    arr[2].x = 5; arr[2].y = 6;',
        '    p = pick(arr, 2);',
        '    return p.x * 10 + p.y;',
        '}',
    ])
    compile_and_run(src, expected_p0=56)


def test_return_chain():
    src = chr(10).join([
        'struct Point { int x; int y; };',
        'struct Point make(int x, int y) {',
        '    struct Point p; p.x = x; p.y = y; return p;',
        '}',
        'struct Point add_one(struct Point p) {',
        '    p.x = p.x + 1;',
        '    p.y = p.y + 1;',
        '    return p;',
        '}',
        'int main() {',
        '    struct Point a;',
        '    struct Point b;',
        '    a = make(5, 6);',
        '    b = add_one(a);',
        '    return a.x * 1000 + a.y * 100 + b.x * 10 + b.y;',
        '}',
    ])
    compile_and_run(src, expected_p0=5667)


def test_return_with_scalar_args_mixed():
    src = chr(10).join([
        'struct Point { int x; int y; };',
        'struct Point scale(int k, struct Point p, int b) {',
        '    p.x = p.x * k + b;',
        '    p.y = p.y * k + b;',
        '    return p;',
        '}',
        'int main() {',
        '    struct Point a;',
        '    struct Point b;',
        '    a.x = 3; a.y = 4;',
        '    b = scale(2, a, 1);',
        '    return b.x * 10 + b.y;',
        '}',
    ])
    compile_and_run(src, expected_p0=79)


def test_method_returns_struct():
    src = chr(10).join([
        'struct Point { int x; int y; };',
        'impl Point {',
        '    struct Point doubled(self) {',
        '        struct Point q;',
        '        q.x = self.x * 2;',
        '        q.y = self.y * 2;',
        '        return q;',
        '    }',
        '}',
        'int main() {',
        '    struct Point a;',
        '    struct Point b;',
        '    a.x = 3; a.y = 5;',
        '    b = a.doubled();',
        '    return b.x * 10 + b.y;',
        '}',
    ])
    compile_and_run(src, expected_p0=70)


def test_return_loop_no_stack_leak():
    src = chr(10).join([
        'struct Point { int x; int y; };',
        'struct Point make(int n) {',
        '    struct Point p; p.x = n; p.y = n; return p;',
        '}',
        'int main() {',
        '    struct Point a;',
        '    int i;',
        '    int sum;',
        '    sum = 0;',
        '    for (i = 0; i < 50; i = i + 1) {',
        '        a = make(i);',
        '        sum = sum + a.x;',
        '    }',
        '    return sum;',
        '}',
    ])
    compile_and_run(src, expected_p0=1225)


def test_return_type_mismatch_rejected():
    src = chr(10).join([
        'struct A { int x; };',
        'struct B { int y; };',
        'struct A make() {',
        '    struct B b;',
        '    return b;',
        '}',
        'int main() { return 0; }',
    ])
    with pytest.raises(Exception):
        compile_and_run(src, expected_p0=0)


def test_assign_wrong_return_tag_rejected():
    src = chr(10).join([
        'struct A { int x; };',
        'struct B { int y; };',
        'struct A make() {',
        '    struct A a; a.x = 1; return a;',
        '}',
        'int main() {',
        '    struct B b;',
        '    b = make();',
        '    return 0;',
        '}',
    ])
    with pytest.raises(Exception):
        compile_and_run(src, expected_p0=0)
