"""High-coverage tests for the systems-tier stack/task builtins.

Covers the six Tier-2 systems builtins added to Astrid:

    push(v) / pop()                 raw stack words
    alloca(bytes)                   frame-lifetime stack scratch
    stack_free()                    headroom between SP and 0x8000
    task_spawn(ctx, base, words, entry)   fabricate an initial context
    task_switch(save, restore)      symmetric coroutine switch

The centerpiece is a two-task ping-pong test: main and a spawned task
interleave through three full context switches, proving that registers,
frame pointers, stack pointers, and per-task locals all survive the
round trip on the real emulator.

A context is 22 ints (44 bytes):
    word 0: flags        words 4-13:  R0-R9
    word 1: FP           words 14-21: P0-P7
    word 2: SP-resume (points at a stack word holding the resume PC)
    word 3: unused
"""
import os
import sys

import pytest

# Path setup handled by tests/astrid/conftest.py

from nova_main import initialize_system
from astrid.codegen.codegen import CodeGenerator
from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser
from astrid.codegen.optimizations import ExpressionSimplifier


TASK_BUILTINS = {
    'push': 'builtin_push',
    'pop': 'builtin_pop',
    'alloca': 'builtin_alloca',
    'stack_free': 'builtin_stack_free',
    'task_spawn': 'builtin_task_spawn',
    'task_switch': 'builtin_task_switch',
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compile_to_asm(source):
    """Compile Astrid source text; return asm path. Caller must _cleanup()."""
    import tempfile
    fd = tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8')
    fd.write(source)
    fd.close()
    from astrid_compiler import main as compiler_main
    old_argv = sys.argv
    sys.argv = [old_argv[0], fd.name, '-o', fd.name.replace('.ast', '.asm')]
    try:
        compiler_main()
    finally:
        sys.argv = old_argv
    return fd.name.replace('.ast', '.asm'), fd.name


def _cleanup(asm_path, tmp_source=None):
    paths = [asm_path.replace('.asm', ext)
             for ext in ('.asm', '.bin', '.org', '.sym')]
    if tmp_source:
        paths.append(tmp_source)
    for p in paths:
        if os.path.exists(p):
            os.unlink(p)


def compile_and_run(source, max_cycles=2000000):
    """Compile, assemble, run to halt. Returns (proc, mem, cycles)."""
    asm_path, tmp_src = _compile_to_asm(source)
    try:
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(asm_path.replace('.asm', '.bin'))
        cycles = 0
        while cycles < max_cycles and not proc.halted:
            cycles += 1
            proc.step()
        assert proc.halted, f'program did not halt (cycles={cycles})'
        return proc, mem, cycles
    finally:
        _cleanup(asm_path, tmp_src)


def _simplify_expr(source_expr):
    """Parse a single expression and run it through ExpressionSimplifier."""
    lexer = Lexer(f"int main() {{ int x = {source_expr}; return x; }}")
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    main_func = ast.functions[0]
    var_decl = main_func.body[0]
    simplifier = ExpressionSimplifier()
    return simplifier.simplify(var_decl.value)


# ---------------------------------------------------------------------------
# Codegen-level
# ---------------------------------------------------------------------------
# Codegen-level
# ---------------------------------------------------------------------------

def test_builtin_table_mappings():
    gen = CodeGenerator()
    for name, label in TASK_BUILTINS.items():
        assert gen.builtin_functions[name] == label, name
        assert label in CodeGenerator.BUILTIN_IMPLEMENTATIONS, name
    print('PASS test_builtin_table_mappings')


@pytest.mark.parametrize('name,label', list(TASK_BUILTINS.items()),
                         ids=list(TASK_BUILTINS))
def test_lazy_emission(name, label):
    """Unused builtins are not emitted; used builtins are (lazy linking)."""
    asm, path = _compile_to_asm('int main() { return 42; }')
    try:
        with open(asm, encoding='utf-8') as f:
            text = f.read()
        assert f'{label}:' not in text, f'{label} emitted though unused'
    finally:
        _cleanup(path)

    used_src = {
        'push': 'int main() { push(5); return 0; }',
        'pop': 'int main() { push(5); return pop(); }',
        'alloca': 'int main() { return alloca(8) != 0; }',
        'stack_free': 'int main() { return stack_free() != 0; }',
        'task_spawn': ('int c[22]; int s[8];\n'
                       'void t() { }\n'
                       'int main() { task_spawn(&c, s, 8, &t); return 0; }'),
        'task_switch': ('int a[22]; int b[22];\n'
                        'int main() { task_switch(&a, &a); return 0; }'),
    }[name]
    asm, path = _compile_to_asm(used_src)
    try:
        with open(asm, encoding='utf-8') as f:
            text = f.read()
        assert f'{label}:' in text, f'{label} missing though used'
    finally:
        _cleanup(path)
    print(f'PASS lazy emission: {name}')


@pytest.mark.parametrize('expr', [
    'push(1)', 'pop()', 'alloca(8)', 'stack_free()',
    'task_switch(0, 0)', 'task_spawn(0, 0, 4, 0)',
])
def test_never_constant_folded(expr):
    """Side-effecting builtins must never fold to a literal."""
    from astrid.parser.parser import FuncCall
    result = _simplify_expr(expr)
    assert isinstance(result, FuncCall), (
        f'{expr}: folded to {type(result).__name__}, expected FuncCall')
    print(f'PASS not folded: {expr}')


# ---------------------------------------------------------------------------
# Raw stack words
# ---------------------------------------------------------------------------

def test_push_pop_roundtrip():
    source = """
int main() {
    push(0x1234);
    push(0x5678);
    int b = pop();
    int a = pop();
    return (a == 0x1234 && b == 0x5678) ? 0x0D0D : 1;
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 0x0D0D, f'push/pop roundtrip failed: {proc.p0:#06x}'
    print('PASS push/pop LIFO roundtrip')


def test_push_pop_interleaved_with_calls():
    """Raw stack words must not confuse normal CALL/RET traffic."""
    source = """
int twice(int v) { return v * 2; }

int main() {
    push(0x00AA);
    int x = twice(21);        // callee frames come and go underneath
    int v = pop();
    return (x == 42 && v == 0x00AA) ? 0x0D1D : 2;
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 0x0D1D, f'push/pop vs calls failed: {proc.p0:#06x}'
    print('PASS push/pop isolated from call frames')


# ---------------------------------------------------------------------------
# alloca / stack_free
# ---------------------------------------------------------------------------

def test_alloca_scratch_block():
    source = """
int twice_help(int v) { return v * 2; }

int main() {
    int p = alloca(8);
    poke2(p, 0xCAFE);
    poke2(p + 2, 0xBEEF);
    int ok = (peek2(p) == 0xCAFE && peek2(p + 2) == 0xBEEF) ? 1 : 0;
    int q = twice_help(ok);          // callee runs below the alloca block
    return (ok == 1 && q == 2) ? 0x0D2D : 3;
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 0x0D2D, f'alloca scratch failed: {proc.p0:#06x}'
    print('PASS alloca grants writable frame-lifetime scratch')


def test_stack_free_tracks_pushes():
    source = """
int main() {
    int f1 = stack_free();
    push(0);
    int f2 = stack_free();
    int v = pop();
    return (f1 == f2 + 2 && v == 0 && f1 > 0) ? 0x0D3D : 4;
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 0x0D3D, f'stack_free tracking failed: {proc.p0:#06x}'
    print('PASS stack_free decreases by 2 per pushed word')


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

def test_spawn_initializes_context():
    source = """
int ctx_b[22];
int bstack[16];
void task_b() { }

int main() {
    task_spawn(&ctx_b, bstack, 16, &task_b);
    if (ctx_b[4] != 0) return 1;      // R0 slot zeroed
    if (ctx_b[14] != 0) return 2;     // P0 slot zeroed
    if (ctx_b[2] == 0) return 3;      // SP-resume parked
    if (ctx_b[1] == 0) return 4;      // FP set
    return 0x0D4D;
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 0x0D4D, f'spawn ctx fields wrong: {proc.p0:#06x}'
    print('PASS task_spawn initializes a clean context')


def test_ping_pong_three_switches():
    """Two tasks interleave through three full context switches. The
    sequence buffer proves exact control-flow ordering across the
    register/SP/FP/PC round trips."""
    source = """
int ctx_main[22];
int ctx_b[22];
int bstack[64];
int seq[8];
int n = 0;

void task_b() {
    seq[n] = 20; n = n + 1;
    task_switch(&ctx_b, &ctx_main);
    seq[n] = 21; n = n + 1;
    task_switch(&ctx_b, &ctx_main);
    seq[n] = 22; n = n + 1;
    task_switch(&ctx_b, &ctx_main);
}

int main() {
    task_spawn(&ctx_b, bstack, 64, &task_b);
    task_switch(&ctx_main, &ctx_b);
    seq[n] = 10; n = n + 1;
    task_switch(&ctx_main, &ctx_b);
    seq[n] = 11; n = n + 1;
    task_switch(&ctx_main, &ctx_b);
    seq[n] = 12; n = n + 1;
    if (n != 6) return 1;
    if (seq[0] != 20) return 2;
    if (seq[1] != 10) return 3;
    if (seq[2] != 21) return 4;
    if (seq[3] != 11) return 5;
    if (seq[4] != 22) return 6;
    if (seq[5] != 12) return 7;
    return 0x0D5D;
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 0x0D5D, (
        f'ping-pong failed at step {proc.p0:#06x}')
    print(f'PASS two-task ping-pong, 3 switches ({cycles} cycles)')


def test_task_local_survives_switch():
    """A task's FP-frame local must keep its value across a yield/resume,
    while the OTHER task's locals stay untouched the whole time."""
    source = """
int ctx_main[22];
int ctx_b[22];
int bstack[64];
int marks[4];
int mi = 0;

void task_b() {
    int mine = 0x1234;                // lives in B's own frame
    marks[mi] = mine; mi = mi + 1;
    task_switch(&ctx_b, &ctx_main);
    marks[mi] = mine; mi = mi + 1;    // marks[1] = still 0x1234?
    task_switch(&ctx_b, &ctx_main);
}

int main() {
    int main_local = 0xB00B;
    task_spawn(&ctx_b, bstack, 64, &task_b);
    marks[mi] = main_local; mi = mi + 1;   // marks[0]: main pre-switch
    task_switch(&ctx_main, &ctx_b);
    marks[mi] = main_local; mi = mi + 1;   // marks[2]: main post-resume
    task_switch(&ctx_main, &ctx_b);
    if (marks[0] != 0xB00B) return 1;
    if (marks[1] != 0x1234) return 2;
    if (marks[2] != 0xB00B) return 3;
    if (marks[3] != 0x1234) return 4;      // B's local after B's resume
    if (mi != 4) return 5;
    return 0x0D6D;
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 0x0D6D, (
        f'task local isolation failed at step {proc.p0:#06x}')
    print('PASS per-task frame locals survive switches (both directions)')


def test_switch_preserves_p3_div_remainder():
    """P3 (the DIV remainder) is explicitly saved/restored by
    task_switch; task B computes a division, yields, and reads
    get_reg(3) after resume -- it must observe ITS OWN remainder."""
    source = """
int ctx_main[22];
int ctx_b[22];
int bstack[64];
int slot = 0;

void task_b() {
    set_rreg(0, 100);
    int a = get_rreg(0);          // opaque to constant folding
    int q = a / 7;                // runtime DIV -> P3 = 2 (B's context)
    task_switch(&ctx_b, &ctx_main);
    slot = get_reg(3);            // after resume: B's own remainder?
    task_switch(&ctx_b, &ctx_main);
}

int main() {
    set_rreg(1, 50);
    int m = get_rreg(1);
    int mq = m / 7;               // main's remainder = 1 (discriminator)
    task_spawn(&ctx_b, bstack, 64, &task_b);
    task_switch(&ctx_main, &ctx_b);
    task_switch(&ctx_main, &ctx_b);
    // Both tasks have yielded once and resumed once: main must see ITS
    // remainder (1) and B must have recorded ITS remainder (2) in slot.
    int own = get_reg(3);
    if (slot != 2) return slot;
    if (own != 1) return 9;
    return 0x0D7D;
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 0x0D7D, f'P3 across switch wrong: {proc.p0:#06x}'
    print('PASS P3 (DIV remainder) preserved across task switches')


if __name__ == '__main__':
    test_builtin_table_mappings()
    for name, label in TASK_BUILTINS.items():
        test_lazy_emission(name, label)
    for expr in ('push(1)', 'pop()', 'alloca(8)', 'stack_free()',
                 'task_switch(0, 0)', 'task_spawn(0, 0, 4, 0)'):
        test_never_constant_folded(expr)
    test_push_pop_roundtrip()
    test_push_pop_interleaved_with_calls()
    test_alloca_scratch_block()
    test_stack_free_tracks_pushes()
    test_spawn_initializes_context()
    test_ping_pong_three_switches()
    test_task_local_survives_switch()
    test_switch_preserves_p3_div_remainder()
    print('All task/stack builtin tests passed!')

