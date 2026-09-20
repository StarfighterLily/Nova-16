"""High-coverage tests for Astrid by-value struct/union parameters.

The caller's PUSH of the aggregate words IS the callee's private copy:
writes through the parameter do not touch the caller's original, and the
caller cleans up exactly the number of words it pushed (cdecl).
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

def test_parser_accepts_byvalue_struct_param():
    ast = parse_source(
        'struct Point { int x; int y; };\n'
        'int sum(struct Point p) { return p.x + p.y; }\n'
        'void main() { }\n')
    params = ast.functions[0].params
    assert len(params) == 1
    assert params[0].struct_tag == 'Point'
    assert params[0].pointer_depth == 0
    assert not params[0].is_array_param


def test_parser_accepts_byvalue_union_param():
    ast = parse_source(
        'union U { int i; char c; };\n'
        'int f(union U u) { return u.i; }\n'
        'void main() { }\n')
    params = ast.functions[0].params
    assert params[0].struct_tag == 'U'
    assert params[0].pointer_depth == 0


def test_parser_rejects_undefined_byvalue_struct_param():
    with pytest.raises(Exception):
        parse_source(
            'int f(struct Missing m) { return 1; }\n'
            'void main() { }\n')


# --- Runtime: core semantics --------------------------------------------

def test_byvalue_struct_param_read():
    source = """
struct Point { int x; int y; };
int sum(struct Point p) { return p.x + p.y; }
int main() {
    struct Point a;
    a.x = 10;
    a.y = 20;
    return sum(a);
}
"""
    compile_and_run(source, expected_r0=30)


def test_byvalue_is_a_private_copy():
    """Callee writes must not reach the caller's original."""
    source = """
struct Point { int x; int y; };
void bump(struct Point p) { p.x = 99; p.y = 99; }
int main() {
    struct Point a;
    a.x = 1;
    a.y = 2;
    bump(a);
    return a.x + a.y;
}
"""
    compile_and_run(source, expected_r0=3)


def test_byvalue_write_then_read_in_callee():
    source = """
struct Point { int x; int y; };
int f(struct Point p) { p.x = 100; return p.x + p.y; }
int main() {
    struct Point a;
    a.x = 1;
    a.y = 2;
    return f(a);
}
"""
    compile_and_run(source, expected_r0=102)


def test_byvalue_between_scalar_params():
    """Param offsets stay correct when a multi-word slot sits mid-list."""
    source = """
struct Point { int x; int y; };
int f(int a, struct Point p, int b) { return a + p.x * 10 + b; }
int main() {
    struct Point a;
    a.x = 2;
    a.y = 7;
    return f(1, a, 3);
}
"""
    compile_and_run(source, expected_r0=24)


def test_byvalue_two_struct_params():
    source = """
struct Point { int x; int y; };
int dot(struct Point p, struct Point q) { return p.x * q.x + p.y * q.y; }
int main() {
    struct Point a;
    struct Point b;
    a.x = 2; a.y = 3;
    b.x = 4; b.y = 5;
    return dot(a, b);
}
"""
    compile_and_run(source, expected_r0=23)


def test_byvalue_nested_struct_param():
    source = """
struct Inner { int a; int b; };
struct Wrap { struct Inner inner; int z; };
int total(struct Wrap w) { return w.inner.a + w.inner.b + w.z; }
int main() {
    struct Wrap v;
    v.inner.a = 5;
    v.inner.b = 6;
    v.z = 7;
    return total(v);
}
"""
    compile_and_run(source, expected_r0=18)


def test_byvalue_array_element_argument():
    source = """
struct Point { int x; int y; };
int sum(struct Point p) { return p.x + p.y; }
int main() {
    struct Point arr[3];
    arr[0].x = 1; arr[0].y = 2;
    arr[1].x = 3; arr[1].y = 4;
    arr[2].x = 5; arr[2].y = 6;
    return sum(arr[2]);
}
"""
    compile_and_run(source, expected_r0=11)


def test_byvalue_nested_member_argument():
    """Passing r.br by value copies only that nested Point."""
    source = """
struct Point { int x; int y; };
struct Rect { struct Point tl; struct Point br; };
int sum(struct Point p) { return p.x + p.y; }
int main() {
    struct Rect r;
    r.tl.x = 8; r.tl.y = 9;
    r.br.x = 1; r.br.y = 2;
    return sum(r.br);
}
"""
    compile_and_run(source, expected_r0=3)


def test_byvalue_union_param():
    source = """
union U { int i; char c; };
int f(union U u) { return u.i; }
int main() {
    union U v;
    v.i = 42;
    return f(v);
}
"""
    compile_and_run(source, expected_r0=42)


def test_byvalue_chain_pass_through():
    """A by-value param can itself be passed by value to another function."""
    source = """
struct Point { int x; int y; };
int inner(struct Point p) { return p.x + p.y; }
int outer(struct Point q) { return inner(q) + 1; }
int main() {
    struct Point a;
    a.x = 4;
    a.y = 6;
    return outer(a);
}
"""
    compile_and_run(source, expected_r0=11)


def test_byvalue_recursion():
    source = """
struct Point { int x; int y; };
int walk(struct Point p) {
    if (p.x <= 0) { return 0; }
    p.x = p.x - 1;
    return 1 + walk(p);
}
int main() {
    struct Point a;
    a.x = 5;
    a.y = 0;
    return walk(a);
}
"""
    compile_and_run(source, expected_r0=5)


def test_byvalue_address_of_param():
    """`&p` points at the callee's private copy, not the caller's original."""
    source = """
struct Point { int x; int y; };
int f(struct Point p) {
    struct Point *q;
    q = &p;
    q->x = 77;
    return p.x;
}
int main() {
    struct Point a;
    a.x = 1;
    a.y = 2;
    return f(a);
}
"""
    compile_and_run(source, expected_r0=77)


def test_byvalue_impl_method_arg():
    """Method calls push by-value args with the same multi-word layout."""
    source = """
struct Point { int x; int y; };
impl Point {
    int plus(self, struct Point o) { return self.x + o.x; }
}
int main() {
    struct Point a;
    struct Point b;
    a.x = 30; a.y = 0;
    b.x = 7;  b.y = 0;
    return a.plus(b);
}
"""
    compile_and_run(source, expected_r0=37)


def test_byvalue_no_stack_leak():
    """Caller cleans up multi-word args so loops do not walk SP."""
    source = """
struct Point { int x; int y; };
int sum(struct Point p) { return p.x + p.y; }
int main() {
    struct Point a;
    int i;
    int t;
    a.x = 1;
    a.y = 2;
    t = 0;
    for (i = 0; i < 50; i = i + 1) { t = t + sum(a); }
    return t;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=150)
    # SP restored to the top of memory after main returns through HLT.
    assert proc.sp >= 0xFFF0, f'SP leaked: {proc.sp:#x}'


def test_byvalue_loop_many_iterations_p0():
    """200 iterations * 7 = 1400; assert via 16-bit P0 (R0 would truncate)."""
    source = """
struct Point { int x; int y; };
int sum(struct Point p) { return p.x + p.y; }
int main() {
    struct Point a;
    int i;
    int t;
    a.x = 3;
    a.y = 4;
    t = 0;
    for (i = 0; i < 200; i = i + 1) { t = t + sum(a); }
    return t;
}
"""
    compile_and_run(source, expected_p0=1400)


# --- Error cases ---------------------------------------------------------

def test_error_scalar_where_struct_expected():
    with pytest.raises(Exception):
        compile_and_run("""
struct Point { int x; int y; };
int f(struct Point p) { return p.x; }
int main() { int n; n = 1; return f(n); }
""")


def test_error_wrong_struct_type():
    with pytest.raises(Exception):
        compile_and_run("""
struct Point { int x; int y; };
struct Other { int z; };
int f(struct Point p) { return p.x; }
int main() { struct Other o; o.z = 1; return f(o); }
""")
