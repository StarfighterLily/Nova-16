"""High-coverage tests for the systems-tier register/stack/flag builtins.

Covers the ten Tier-1 systems builtins added to Astrid:

    get_reg(n)  / set_reg(n, v)     16-bit P-register view (P0-P9)
    get_rreg(n) / set_rreg(n, v)    8-bit R-register view (R0-R9, zero-extended)
    get_sp()    / set_sp(v)         stack pointer (set_sp returns with SP == v)
    get_fp()    / set_fp(v)         frame pointer
    get_flags() / set_flags(f)      12-bit flag word (T,S,O,B,D,I,C,Z,P,H,A,E)

Both codegen-level behavior (table mapping, lazy emission, no constant
folding) and headless runtime semantics are verified against the real
emulator. The known scratch-hazard contract is pinned here too: P0-P7
are compiler expression scratch (round-robin, P3 excluded), so
set_reg/get_reg round-trips are only asserted on P3, which is never used
as an expression temporary. R1-R9 are never compiler scratch, so rreg
round-trips may include intervening expressions.
"""
import os
import re
import sys

import pytest

# Path setup handled by tests/astrid/conftest.py

from nova_main import initialize_system
from astrid.codegen.codegen import CodeGenerator
from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser
from astrid.codegen.optimizations import ExpressionSimplifier


REGSTACK_BUILTINS = {
    'get_reg': 'builtin_get_reg',
    'set_reg': 'builtin_set_reg',
    'get_rreg': 'builtin_get_rreg',
    'set_rreg': 'builtin_set_rreg',
    'get_sp': 'builtin_get_sp',
    'set_sp': 'builtin_set_sp',
    'get_fp': 'builtin_get_fp',
    'set_fp': 'builtin_set_fp',
    'get_flags': 'builtin_get_flags',
    'set_flags': 'builtin_set_flags',
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


def compile_and_run(source, max_cycles=500000):
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

def test_builtin_table_mappings():
    gen = CodeGenerator()
    for name, label in REGSTACK_BUILTINS.items():
        assert gen.builtin_functions[name] == label, name
        assert label in CodeGenerator.BUILTIN_IMPLEMENTATIONS, name
    print('PASS test_builtin_table_mappings')

@pytest.mark.parametrize('name,label', list(REGSTACK_BUILTINS.items()),
                         ids=list(REGSTACK_BUILTINS))
def test_lazy_emission(name, label):
    """Unused builtins are not emitted; used builtins are (lazy linking)."""
    unused_src = 'int main() { return 42; }'
    asm, path = _compile_to_asm(unused_src)
    try:
        with open(asm, encoding='utf-8') as f:
            text = f.read()
        assert f'{label}:' not in text, f'{label} emitted though unused'
    finally:
        _cleanup(path)

    used_src = {
        'get_reg': 'int main() { return get_reg(3); }',
        'set_reg': 'int main() { set_reg(3, 5); return 0; }',
        'get_rreg': 'int main() { return get_rreg(0); }',
        'set_rreg': 'int main() { set_rreg(0, 5); return 0; }',
        'get_sp': 'int main() { return get_sp() != 0; }',
        'set_sp': 'int main() { set_sp(get_sp()); return 0; }',
        'get_fp': 'int main() { return get_fp() != 0; }',
        'set_fp': 'int main() { set_fp(get_fp()); return 0; }',
        'get_flags': 'int main() { return get_flags() != 0; }',
        'set_flags': 'int main() { set_flags(0); return 0; }',
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
    'get_reg(3)', 'set_reg(3, 1)', 'get_rreg(0)', 'set_rreg(0, 5)',
    'get_sp()', 'set_sp(0xFF00)', 'get_fp()', 'set_fp(0xFF00)',
    'get_flags()', 'set_flags(0x0080)',
])
def test_never_constant_folded(expr):
    """Volatile hardware views must never fold to a literal."""
    from astrid.parser.parser import FuncCall
    result = _simplify_expr(expr)
    assert isinstance(result, FuncCall), (
        f'{expr}: folded to {type(result).__name__}, expected FuncCall')
    print(f'PASS not folded: {expr}')


# ---------------------------------------------------------------------------
# Runtime semantics
# ---------------------------------------------------------------------------

def test_get_reg_out_of_range_returns_zero():
    source = 'int main() { return get_reg(12); }'
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 0, f'out-of-range get_reg expected 0, got {proc.p0}'
    print('PASS get_reg out of range -> 0')


def test_get_rreg_out_of_range_returns_zero():
    source = 'int main() { return get_rreg(15); }'
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 0, f'out-of-range get_rreg expected 0, got {proc.p0}'
    print('PASS get_rreg out of range -> 0')

def test_set_get_reg_p3_roundtrip():
    """P3 is never compiler expression scratch, so a set/get pair on it
    must read back exactly -- even with intervening expressions."""
    source = """
int main() {
    set_reg(3, 0xBEEF);
    int a = 7;
    int b = 6;
    int noise = a * b;        // MUL never touches P3
    int x = get_reg(3);
    return x == 0xBEEF ? 1000 + noise : 0;
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 1042, f'P3 roundtrip broken: {proc.p0:#06x}'
    print('PASS set_reg/get_reg P3 roundtrip (survives expressions)')


def test_get_reg3_observes_div_remainder():
    """The CPU's DIV writes its remainder to P3; get_reg(3) must observe
    the live hardware value (100 / 7 = 14 remainder 2)."""
    source = """
int main() {
    int a = 100;
    int q = a / 7;            // runtime DIV -> P3 = 2
    int r = get_reg(3);
    return r == 2 ? 77 : r;
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 77, f'DIV remainder observation failed: {proc.p0}'
    print('PASS get_reg(3) observes live DIV remainder')


def test_set_reg3_persists_across_statements():
    """set_reg(3, v) is a legitimate way to plant a value in P3; the stub
    must return correctly afterward (return address rides in R0)."""
    source = """
int main() {
    set_reg(3, 0x0F0F);
    set_reg(3, 0x1234);       // second write must also return safely
    int x = get_reg(3);
    return x == 0x1234 ? 55 : 0;
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 55, f'set_reg(3) persistence failed: {proc.p0:#06x}'
    print('PASS set_reg(3) persists and returns safely')


def test_set_rreg_truncates_to_low_byte():
    source = """
int main() {
    set_rreg(7, 0x0134);
    int a = 3;
    int b = 4;
    int noise = a * b;        // R registers are never compiler scratch
    int x = get_rreg(7);
    return x == 0x34 ? 60 + noise : x;
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 72, f'set_rreg truncation failed: {proc.p0:#06x}'
    print('PASS set_rreg truncates 16-bit arg to low byte')


def test_rreg_full_byte_range():
    source = """
int main() {
    set_rreg(2, 0xFF);
    int lo = get_rreg(2);
    set_rreg(2, 0x00);
    int hi = get_rreg(2);
    return lo == 0xFF && hi == 0 ? 88 : 0;
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 88, f'8-bit range failed: {proc.p0:#06x}'
    print('PASS get/set_rreg 8-bit range')


def test_sp_roundtrip_is_exact():
    source = """
int main() {
    int sp1 = get_sp();
    set_sp(sp1);
    int sp2 = get_sp();
    int sp3 = get_sp();       // observation is non-destructive
    return (sp1 == sp2 && sp2 == sp3) ? 0x600D : 0;
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 0x600D, f'SP roundtrip failed: {proc.p0:#06x}'
    print(f'PASS get/set_sp exact roundtrip (SP=0x{proc.Pregisters[8]:04X})')

def test_fp_roundtrip_is_exact():
    source = """
int main() {
    int fp1 = get_fp();
    set_fp(fp1);
    int fp2 = get_fp();
    return fp1 == fp2 ? 0xF00D : 0;
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 0xF00D, f'FP roundtrip failed: {proc.p0:#06x}'
    print(f'PASS get/set_fp exact roundtrip (FP=0x{proc.Pregisters[9]:04X})')


def test_flags_z_bit_is_bit_seven():
    """Validate the documented flag-word bit layout empirically: an equal
    comparison sets Z, and Z must surface as bit 7 (0x0080)."""
    source = """
int main() {
    int a = 1;
    int b = 1;
    int eq = (a == b);        // CMP equal -> Z=1
    int f = get_flags();
    return f & 0x0080;
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 0x0080, f'Z bit layout wrong: {proc.p0:#06x}'
    print('PASS Z surfaces at bit 7 of get_flags()')


def test_set_flags_replace_and_restore():
    """set_flags wholesale-replaces the word; saving/restoring brackets it."""
    source = """
int main() {
    int f0 = get_flags();
    set_flags(0x0080);        // Z only (no D/H/T side effects)
    int f1 = get_flags();
    set_flags(f0);
    int f2 = get_flags();
    return (f1 == 0x0080 && f2 == f0) ? 0x0AA0 : f1;
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 0x0AA0, (
        f'flags replace/restore failed: f1={proc.p0:#06x}')
    print('PASS set_flags replace + save/restore bracketing')


def test_set_flags_zero_word():
    source = """
int main() {
    set_flags(0);
    return get_flags();
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 0, f'set_flags(0) did not clear the word: {proc.p0:#06x}'
    print('PASS set_flags(0) clears the flag word')


def test_flag_word_roundtrip_wide():
    """A multi-bit word (Z=bit7, H=bit9, E=bit11) round-trips bit-exactly.
    Deliberately avoids T (single-step) and D (BCD mode)."""
    source = """
int main() {
    int f0 = get_flags();
    set_flags(0x0A80);
    int f1 = get_flags();
    set_flags(f0);
    return f1;
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 0x0A80, f'wide flag word mismatch: {proc.p0:#06x}'
    print('PASS wide flag word (Z/H/E) roundtrip bit-exact')


if __name__ == '__main__':
    test_builtin_table_mappings()
    for name, label in REGSTACK_BUILTINS.items():
        test_lazy_emission(name, label)
    for expr in ('get_reg(3)', 'set_reg(3, 1)', 'get_rreg(0)',
                 'set_rreg(0, 5)', 'get_sp()', 'set_sp(0xFF00)',
                 'get_fp()', 'set_fp(0xFF00)', 'get_flags()',
                 'set_flags(0x0080)'):
        test_never_constant_folded(expr)
    test_get_reg_out_of_range_returns_zero()
    test_get_rreg_out_of_range_returns_zero()
    test_set_get_reg_p3_roundtrip()
    test_get_reg3_observes_div_remainder()
    test_set_reg3_persists_across_statements()
    test_set_rreg_truncates_to_low_byte()
    test_rreg_full_byte_range()
    test_sp_roundtrip_is_exact()
    test_fp_roundtrip_is_exact()
    test_flags_z_bit_is_bit_seven()
    test_set_flags_replace_and_restore()
    test_set_flags_zero_word()
    test_flag_word_roundtrip_wide()
    print('All regstack-builtin tests passed!')
