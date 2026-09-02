"""High-coverage tests for Astrid `impl` blocks (Rust-style method blocks).

Covers:
1. Parser: impl-block AST (ImplBlock / MethodCall nodes), receiver `self`
   typed as `struct Tag *`, method namespaced labels, method-call detection
   after the member-access chain in parse_primary.
2. Codegen/layout: namespaced method labels (func_Tag_method), receiver
   address pushed as the implicit first argument, cdecl-style cleanup, two
   structs sharing a method name without label collision.
3. Runtime (headless execution against the Nova-16 emulator):
   - Local struct receiver: read/write fields via self, extra args, return.
   - Global struct receiver.
   - Array-of-structs receiver (pts[i].method()).
   - Pointer receiver (pp->method()).
   - Union receiver.
   - Method calling another method on self (chained self.method()).
   - Control flow inside methods (if/while/for, early return).
   - Two structs with identically-named methods (namespacing).
4. Error cases: method without `self`, impl on undefined type, duplicate
   method, empty impl, redefining an included method.
5. Multi-file: include splices impl blocks (with diamond dedupe); inherits
   uses the base method when the child doesn't override and lets the child
   override it.
"""
import os
import shutil
import sys
import tempfile

import pytest

from nova_main import initialize_system
from astrid.lexer.lexer import Lexer
from astrid.parser.parser import (
    Parser, VarDecl, MemberAccess, MemberAssignment,
    FunctionDef, ImplBlock, MethodCall, ArrayAccess,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def compile_and_run(source, expected_r0=None, expected_p0=None,
                    max_cycles=2000000):
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

        proc, cycles, mem = run_binary(source_path.replace('.ast', '.bin'),
                                       max_cycles=max_cycles)
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


def compile_and_run_multi(main_src, files=None, expected_r0=None,
                          expected_p0=None):
    """Compile a main source that includes/inherits helper files."""
    work = tempfile.mkdtemp()
    try:
        if files:
            for name, body in files.items():
                with open(os.path.join(work, name), 'w',
                          encoding='utf-8') as f:
                    f.write(body)
        sp = os.path.join(work, 'prog.ast')
        with open(sp, 'w', encoding='utf-8') as f:
            f.write(main_src)
        from astrid.compiler_api import compile_astrid
        compile_astrid(sp)
        from nova_assembler import Assembler
        Assembler().assemble(os.path.join(work, 'prog.asm'))
        proc, cycles, mem = run_binary(os.path.join(work, 'prog.bin'))
        assert proc.halted, 'Program did not halt'
        if expected_r0 is not None:
            assert proc.r0 == expected_r0, \
                f'Expected R0={expected_r0}, got {proc.r0}'
        if expected_p0 is not None:
            assert proc.p0 == expected_p0, \
                f'Expected P0={expected_p0}, got {proc.p0}'
        return proc, cycles, mem
    finally:
        shutil.rmtree(work, ignore_errors=True)


def parse_source(src):
    """Parse source text and return the Program AST."""
    return Parser(Lexer(src).tokenize()).parse()


BASE_POINT = ('struct Point { int x; int y; };' + chr(10) +
              'impl Point { int sum(self, int b){ return self.x + self.y + b; } }')

# ---------------------------------------------------------------------------
# Parser-level tests
# ---------------------------------------------------------------------------

def test_parser_impl_block_node():
    ast = parse_source(
        'struct Point { int x; int y; };' + chr(10) +
        'impl Point {' + chr(10) +
        '    int sum(self, int b) { return self.x + self.y + b; }' + chr(10) +
        '}' + chr(10) +
        'void main() { }')
    assert len(ast.impl_blocks) == 1
    block = ast.impl_blocks[0]
    assert isinstance(block, ImplBlock)
    assert block.tag == 'Point'
    assert len(block.methods) == 1
    method = block.methods[0]
    assert isinstance(method, FunctionDef)
    assert method.name == 'sum'
    assert method.impl_tag == 'Point'


def test_parser_self_is_struct_pointer():
    """The receiver `self` is implicitly `struct Tag *`."""
    ast = parse_source(
        'struct Point { int x; int y; };' + chr(10) +
        'impl Point { int sum(self, int b) { return self.x + self.y + b; } }' + chr(10) +
        'void main() { }')
    method = ast.impl_blocks[0].methods[0]
    assert len(method.params) == 2
    self_param = method.params[0]
    assert isinstance(self_param, VarDecl)
    assert self_param.name == 'self'
    assert self_param.var_type == 'struct'
    assert self_param.pointer_depth == 1
    assert self_param.struct_tag == 'Point'


def test_parser_method_call_node():
    """p.method(args) parses as a MethodCall whose base is a MemberAccess."""
    src = ('struct P { int x; };' + chr(10) +
           'impl P { int m(self){ return 1; } }' + chr(10) +
           'int main() { struct P p; return p.m(7); }')
    main = [f for f in parse_source(src).functions if f.name == 'main'][0]
    ret = main.body[-1]
    assert isinstance(ret.value, MethodCall)
    call = ret.value
    assert isinstance(call.base, MemberAccess)
    assert call.base.field == 'm'
    assert call.base.arrow is False
    assert len(call.args) == 1


def test_parser_arrow_method_call_node():
    """pp->method(args) parses as a MethodCall with arrow=True."""
    src = ('struct P { int x; };' + chr(10) +
           'impl P { int m(self){ return 1; } }' + chr(10) +
           'int main() { struct P p; struct P *pp = &p; return pp->m(); }')
    main = [f for f in parse_source(src).functions if f.name == 'main'][0]
    call = main.body[-1].value
    assert isinstance(call, MethodCall)
    assert call.base.arrow is True
    assert call.base.field == 'm'


def test_parser_array_element_method_call_node():
    """pts[i].method() parses as MethodCall whose base is an ArrayAccess."""
    src = ('struct P { int x; };' + chr(10) +
           'impl P { int m(self){ return 1; } }' + chr(10) +
           'int main() { struct P pts[3]; int i; i = 1; return pts[i].m(); }')
    main = [f for f in parse_source(src).functions if f.name == 'main'][0]
    call = main.body[-1].value
    assert isinstance(call, MethodCall)
    assert isinstance(call.base, MemberAccess)
    assert isinstance(call.base.base, ArrayAccess)
    assert call.base.base.name == 'pts'


def test_parser_two_structs_same_method_name():
    """Two structs may define the same method name without collision."""
    ast = parse_source(
        'struct A { int x; };' + chr(10) +
        'struct B { int x; };' + chr(10) +
        'impl A { int m(self){ return self.x; } }' + chr(10) +
        'impl B { int m(self){ return self.x; } }' + chr(10) +
        'void main() { }')
    assert len(ast.impl_blocks) == 2
    assert {b.tag for b in ast.impl_blocks} == {'A', 'B'}
    for b in ast.impl_blocks:
        assert b.methods[0].name == 'm'
        assert b.methods[0].impl_tag == b.tag


def test_parser_method_call_as_statement():
    """A method call used as a statement (value discarded) parses cleanly."""
    src = ('struct P { int x; };' + chr(10) +
           'impl P { void set(self, int v){ self.x = v; } }' + chr(10) +
           'int main() { struct P p; p.set(5); return p.x; }')
    main = [f for f in parse_source(src).functions if f.name == 'main'][0]
    stmt = main.body[1]
    assert isinstance(stmt, MethodCall)


# ---------------------------------------------------------------------------
# Runtime: local struct receiver
# ---------------------------------------------------------------------------

def test_runtime_local_struct_method_read_write():
    source = chr(10).join([
        'struct Point { int x; int y; };',
        'impl Point {',
        '    void set(self, int x, int y) { self.x = x; self.y = y; }',
        '    int sum(self, int b) { return self.x + self.y + b; }',
        '}',
        'int main() {',
        '    struct Point p;',
        '    p.set(10, 20);',
        '    return p.sum(5);   // 35',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=35)
    print(f'PASS test_runtime_local_struct_method_read_write (cycles={cycles})')


def test_runtime_local_struct_method_with_control_flow():
    source = chr(10).join([
        'struct Vec { int x; int y; };',
        'impl Vec {',
        '    int max(self) {',
        '        if (self.x > self.y) return self.x;',
        '        return self.y;',
        '    }',
        '}',
        'int main() {',
        '    struct Vec v;',
        '    v.x = 42; v.y = 17;',
        '    return v.max();   // 42',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f'PASS test_runtime_local_struct_method_with_control_flow (cycles={cycles})')


def test_runtime_method_calls_method_on_self():
    source = chr(10).join([
        'struct Counter { int n; };',
        'impl Counter {',
        '    void inc(self) { self.n = self.n + 1; }',
        '    int count_to(self, int m) {',
        '        int i;',
        '        for (i = 0; i < m; i = i + 1) self.inc();',
        '        return self.n;',
        '    }',
        '}',
        'int main() {',
        '    struct Counter c;',
        '    c.n = 0;',
        '    return c.count_to(7);   // 7',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=7)
    print(f'PASS test_runtime_method_calls_method_on_self (cycles={cycles})')


# ---------------------------------------------------------------------------
# Runtime: global struct receiver
# ---------------------------------------------------------------------------

def test_runtime_global_struct_method():
    source = chr(10).join([
        'struct Point { int x; int y; };',
        'impl Point {',
        '    int sum(self, int b) { return self.x + self.y + b; }',
        '    void set(self, int x, int y) { self.x = x; self.y = y; }',
        '}',
        'struct Point gp;',
        'int main() {',
        '    gp.set(6, 7);',
        '    return gp.sum(0);   // 13',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=13)
    print(f'PASS test_runtime_global_struct_method (cycles={cycles})')


# ---------------------------------------------------------------------------
# Runtime: array-of-structs receiver
# ---------------------------------------------------------------------------

def test_runtime_array_element_method():
    source = chr(10).join([
        'struct Point { int x; int y; };',
        'impl Point {',
        '    int mag(self) { return self.x * self.x + self.y * self.y; }',
        '    void set(self, int x, int y) { self.x = x; self.y = y; }',
        '}',
        'int main() {',
        '    struct Point pts[3];',
        '    pts[1].set(3, 4);',
        '    return pts[1].mag();   // 25',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=25)
    print(f'PASS test_runtime_array_element_method (cycles={cycles})')


# ---------------------------------------------------------------------------
# Runtime: pointer receiver
# ---------------------------------------------------------------------------

def test_runtime_pointer_method():
    source = chr(10).join([
        'struct Point { int x; int y; };',
        'impl Point {',
        '    int mag(self) { return self.x * self.x + self.y * self.y; }',
        '    void set(self, int x, int y) { self.x = x; self.y = y; }',
        '}',
        'int main() {',
        '    struct Point p;',
        '    struct Point *pp = &p;',
        '    pp->set(3, 4);',
        '    return pp->mag();   // 25',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=25)
    print(f'PASS test_runtime_pointer_method (cycles={cycles})')


# ---------------------------------------------------------------------------
# Runtime: union receiver
# ---------------------------------------------------------------------------

def test_runtime_union_method():
    source = chr(10).join([
        'union U { int i; char c; };',
        'impl U {',
        '    int get(self) { return self.i; }',
        '    void put(self, int v) { self.i = v; }',
        '}',
        'int main() {',
        '    union U u;',
        '    u.put(99);',
        '    return u.get();   // 99',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=99)
    print(f'PASS test_runtime_union_method (cycles={cycles})')


# ---------------------------------------------------------------------------
# Runtime: two structs sharing a method name (namespacing)
# ---------------------------------------------------------------------------

def test_runtime_namespaced_methods():
    source = chr(10).join([
        'struct Point { int x; int y; };',
        'struct Rect { int w; int h; };',
        'impl Point { int area(self) { return self.x * self.y; } }',
        'impl Rect  { int area(self) { return self.w * self.h; } }',
        'struct Point gp;',
        'int main() {',
        '    gp.x = 6; gp.y = 7;',
        '    struct Rect r;',
        '    r.w = 3; r.h = 9;',
        '    return gp.area() + r.area();   // 42 + 27 = 69',
        '}',
    ])
    proc, cycles, mem = compile_and_run(source, expected_r0=69)
    print(f'PASS test_runtime_namespaced_methods (cycles={cycles})')


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

def test_error_method_without_self():
    src = ('struct P { int x; }; impl P { int m(int a){ return a; } }' + chr(10) +
           'void main() { struct P p; p.m(1); }')
    with pytest.raises(SyntaxError, match='must take `self`'):
        parse_source(src)
    print('PASS test_error_method_without_self')


def test_error_impl_on_undefined_type():
    src = 'impl Ghost { int m(self){ return 1; } } void main(){}'
    with pytest.raises(SyntaxError, match='no struct or union named'):
        parse_source(src)
    print('PASS test_error_impl_on_undefined_type')


def test_error_duplicate_method():
    src = ('struct P { int x; };' + chr(10) +
           'impl P { int a(self){return 0;} int a(self){return 1;} }' + chr(10) +
           'void main(){}')
    with pytest.raises(SyntaxError, match='Duplicate method'):
        parse_source(src)
    print('PASS test_error_duplicate_method')


def test_error_empty_impl():
    src = 'struct P { int x; }; impl P { } void main(){}'
    with pytest.raises(SyntaxError, match='has no methods'):
        parse_source(src)
    print('PASS test_error_empty_impl')


# ---------------------------------------------------------------------------
# Multi-file: include / inherits
# ---------------------------------------------------------------------------

def test_multi_include_splices_impl():
    proc, cycles, mem = compile_and_run_multi(
        'include "point.ast"; int main() { struct Point p; p.x = 3; p.y = 4; return p.sum(0); }',
        files={'point.ast': BASE_POINT},
        expected_r0=7)
    print(f'PASS test_multi_include_splices_impl (cycles={cycles})')


def test_multi_include_diamond_dedupe():
    proc, cycles, mem = compile_and_run_multi(
        'include "point.ast"; include "point.ast"; int main() { struct Point p; p.x=5; p.y=5; return p.sum(1); }',
        files={'point.ast': BASE_POINT},
        expected_r0=11)
    print(f'PASS test_multi_include_diamond_dedupe (cycles={cycles})')


def test_multi_inherits_base_method():
    proc, cycles, mem = compile_and_run_multi(
        'inherits "base.ast"; int main() { struct Point p; p.x=4; p.y=4; return p.sum(0); }',
        files={'base.ast': BASE_POINT},
        expected_r0=8)
    print(f'PASS test_multi_inherits_base_method (cycles={cycles})')


def test_multi_inherits_override():
    # Child overrides sum; base version (x+y+b) must NOT be used.
    # base sum(0) would give 8; override (x*10+y+b) gives 44.
    proc, cycles, mem = compile_and_run_multi(
        'inherits "base.ast";' + chr(10) +
        'impl Point { int sum(self, int b){ return self.x * 10 + self.y + b; } }' + chr(10) +
        'int main() { struct Point p; p.x=4; p.y=4; return p.sum(0); }',
        files={'base.ast': BASE_POINT},
        expected_r0=44)
    print(f'PASS test_multi_inherits_override (cycles={cycles})')


def test_multi_include_method_redef_is_error():
    work = tempfile.mkdtemp()
    try:
        with open(os.path.join(work, 'point.ast'), 'w', encoding='utf-8') as f:
            f.write(BASE_POINT)
        with open(os.path.join(work, 'prog.ast'), 'w', encoding='utf-8') as f:
            f.write('include "point.ast"; impl Point { int sum(self,int b){ return 999; } } int main(){}')
        from astrid.compiler_api import compile_astrid
        with pytest.raises(SyntaxError, match='Duplicate method'):
            compile_astrid(os.path.join(work, 'prog.ast'))
        print('PASS test_multi_include_method_redef_is_error')
    finally:
        shutil.rmtree(work, ignore_errors=True)
