"""Semantics of fused compare-and-branch conditions (if / while / do / for).

Statement conditions no longer materialize a 0/1 value and test it against
zero; a relational condition lowers to CMP + one conditional jump (with an
immediate when the right side is a literal), && / || lower to branch
chains, and ! flips the branch sense. Each case below runs on the emulator
and is checked against Python's evaluation of the same condition.
"""
import itertools
import os
import tempfile

import pytest

# Path setup is handled by tests/astrid/conftest.py
from nova_main import initialize_system

OPS = ['==', '!=', '<', '>', '<=', '>=']


def _run(source, max_cycles=400000):
    from astrid.compiler_api import compile_astrid
    from nova_assembler import Assembler
    tmpdir = tempfile.mkdtemp(prefix='astrid_condbr_')
    src = os.path.join(tmpdir, 'prog.ast')
    asm = os.path.join(tmpdir, 'prog.asm')
    with open(src, 'w', encoding='utf-8') as f:
        f.write(source)
    compile_astrid(src, asm, log=lambda m: None,
                   assemble_callback=lambda p, v, e: bool(Assembler().assemble(str(p))))
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    proc.pc = mem.load(asm[:-4] + '.bin')
    cycles = 0
    while not proc.halted and cycles < max_cycles:
        proc.step()
        cycles += 1
    assert proc.halted, 'program did not terminate'
    syms = {}
    with open(asm[:-4] + '.sym') as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2:
                syms[parts[0].lower()] = int(parts[1], 16)
    with open(asm, encoding='utf-8') as f:
        text = f.read()
    return mem, syms, text


def _py(a, op, b):
    return {'==': a == b, '!=': a != b, '<': a < b, '>': a > b,
            '<=': a <= b, '>=': a >= b}[op]


def _bits(mem, addr, n):
    return [mem.read_word(addr + 2 * i) for i in range(n)]


def test_unsigned_relations_with_immediates_and_registers():
    # Values around the interesting edges: 0, small, high bit, 0xFFFF.
    values = [0, 1, 72, 0x7FFF, 0x8000, 0xFFFE, 0xFFFF]
    consts = [0, 1, 72, 0x8000, 0xFFFE, 0xFFFF]
    cases = []
    for a, op, k in itertools.product(values, OPS, consts):
        cases.append((a, op, k))
    lines = []
    expected = []
    for idx, (a, op, k) in enumerate(cases):
        lines.append(f'    x = {a}; y = {k};')
        lines.append(f'    if (x {op} {k}) {{ ri[{idx}] = 1; }}')      # immediate form
        lines.append(f'    if (x {op} y) {{ rr[{idx}] = 1; }}')        # register form
        expected.append(1 if _py(a, op, k) else 0)
    n = len(cases)
    source = (f'unsigned int x;\nunsigned int y;\nint ri[{n}];\nint rr[{n}];\n'
              'void main() {\n' + '\n'.join(lines) + '\n}\n')
    mem, syms, text = _run(source)
    got_imm = _bits(mem, syms['gvar_ri'], n)
    got_reg = _bits(mem, syms['gvar_rr'], n)
    bad = [(cases[i], expected[i], got_imm[i], got_reg[i])
           for i in range(n) if (got_imm[i], got_reg[i]) != (expected[i],) * 2]
    assert not bad, f'mismatches (case, want, imm, reg): {bad[:10]}'


def test_signed_relations_with_negative_values():
    values = [-32768, -300, -1, 0, 1, 300, 32767]
    consts = [-300, -1, 0, 1, 300]
    cases = list(itertools.product(values, OPS, consts))
    lines = []
    expected = []
    for idx, (a, op, k) in enumerate(cases):
        lines.append(f'    x = {a}; y = {k};')
        lines.append(f'    if (x {op} {k}) {{ ri[{idx}] = 1; }}')
        lines.append(f'    if (x {op} y) {{ rr[{idx}] = 1; }}')
        expected.append(1 if _py(a, op, k) else 0)
    n = len(cases)
    source = (f'signed int x;\nsigned int y;\nint ri[{n}];\nint rr[{n}];\n'
              'void main() {\n' + '\n'.join(lines) + '\n}\n')
    mem, syms, text = _run(source)
    got_imm = _bits(mem, syms['gvar_ri'], n)
    got_reg = _bits(mem, syms['gvar_rr'], n)
    bad = [(cases[i], expected[i], got_imm[i], got_reg[i])
           for i in range(n) if (got_imm[i], got_reg[i]) != (expected[i],) * 2]
    assert not bad, f'mismatches (case, want, imm, reg): {bad[:10]}'


def test_logical_combinations_and_negation():
    combos = [
        ('a && b', lambda a, b, c: a and b),
        ('a || b', lambda a, b, c: a or b),
        ('!a', lambda a, b, c: not a),
        ('!(a && b)', lambda a, b, c: not (a and b)),
        ('a && !b', lambda a, b, c: a and not b),
        ('(a || b) && c', lambda a, b, c: (a or b) and c),
        ('a || (b && c)', lambda a, b, c: a or (b and c)),
        ('!(a || b) || c', lambda a, b, c: (not (a or b)) or c),
        ('a == 1 && b != 0 || c > 0', lambda a, b, c: (a == 1 and b != 0) or c > 0),
    ]
    lines = []
    expected = []
    idx = 0
    for text, fn in combos:
        for a, b, c in itertools.product((0, 1), repeat=3):
            lines.append(f'    a = {a}; b = {b}; c = {c};')
            lines.append(f'    if ({text}) {{ r[{idx}] = 1; }} else {{ r[{idx}] = 2; }}')
            expected.append(1 if fn(a, b, c) else 2)
            idx += 1
    source = (f'int a;\nint b;\nint c;\nint r[{idx}];\n'
              'void main() {\n' + '\n'.join(lines) + '\n}\n')
    mem, syms, _ = _run(source)
    assert _bits(mem, syms['gvar_r'], idx) == expected


def test_short_circuit_still_skips_right_operand():
    mem, syms, _ = _run("""
int calls = 0;
int hit() { calls = calls + 1; return 1; }
void main() {
    int zero = 0;
    int one = 1;
    if (zero && hit()) { calls = calls + 100; }
    if (one || hit()) { calls = calls + 10; }
    while (zero && hit()) { }
}
""")
    assert mem.read_word(syms['gvar_calls']) == 10


def test_simplifier_keeps_logical_operand_order_and_side_effects():
    # The ExpressionSimplifier used to treat && / || as commutative (so
    # `zero && hit()` became `hit() && zero`) and folded `f() && 0` to 0
    # without calling f().
    mem, syms, _ = _run("""
int calls = 0;
int r[4];
int hit() { calls = calls + 1; return 1; }
void main() {
    int zero = 0;
    r[0] = zero && hit();
    r[1] = hit() && 0;
    r[2] = hit() || 1;
    r[3] = 1 && 5;
}
""")
    assert mem.read_word(syms['gvar_calls']) == 2
    assert _bits(mem, syms['gvar_r'], 4) == [0, 0, 1, 1]


def test_loops_use_fused_conditions():
    mem, syms, text = _run("""
int w = 0;
int d = 0;
int f = 0;
int k = 0;
void main() {
    int i = 0;
    while (i < 7) { w = w + 1; i = i + 1; }
    i = 10;
    do { d = d + 1; i = i - 1; } while (i > 3 && i != 5);
    for (i = 0; i <= 4; i = i + 1) { f = f + 1; }
    i = 0;
    while (1) { i = i + 1; if (i >= 3) { break; } }
    k = i;
}
""")
    assert mem.read_word(syms['gvar_w']) == 7
    assert mem.read_word(syms['gvar_d']) == 5      # 10,9,8,7,6 -> stops at 5
    assert mem.read_word(syms['gvar_f']) == 5
    assert mem.read_word(syms['gvar_k']) == 3
    body = text[text.index('func_main:'):]
    assert 'cmp_true' not in body, 'statement conditions should not materialize 0/1'


def test_char_literal_comparison_uses_immediate():
    mem, syms, text = _run("""
int r = 0;
void main() {
    int c = 72;
    if (c == 'H' || c == 'h') { r = 1; }
}
""")
    assert mem.read_word(syms['gvar_r']) == 1
    assert 'CMP' in text and ', 72' in text
