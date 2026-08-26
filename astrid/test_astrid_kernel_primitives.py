"""High-coverage tests for the Star System kernel primitives in Astrid.

Covers the four low-level builtins added for Star System 1
(docs/starsystem.md sec1/sec3):

1. peek(addr): byte-granular reads over the word-granular big-endian bus.
2. poke(addr, val): read-modify-write byte stores that preserve the
   neighbor byte at addr+1 and drop value bits above bit 7.
3. set_bank(n) / read_bank(): bracketed bank-window excursions; hardware
   clamping; base RAM never shadowed by banked writes.

Both codegen-level behavior (lazy emission, P0-returning call sites,
correct two-operand SHL encoding) and headless runtime semantics are
verified against the real emulator.
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nova_main import initialize_system
from astrid.codegen.codegen import CodeGenerator


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


PRIMITIVE_SOURCES = {
    'peek': 'int main() { return peek(0x3000); }',
    'poke': 'int main() { poke(0x3000, 7); return 0; }',
    'set_bank': 'int main() { set_bank(1); return 0; }',
    'read_bank': 'int main() { return read_bank(); }',
}
# ---------------------------------------------------------------------------
# Codegen-level
# ---------------------------------------------------------------------------

def test_builtin_table_mappings():
    gen = CodeGenerator()
    for name in ('peek', 'poke', 'set_bank', 'read_bank'):
        label = gen.builtin_functions[name]
        assert label in CodeGenerator.BUILTIN_IMPLEMENTATIONS, name
    print('PASS test_builtin_table_mappings')


@pytest.mark.parametrize('name,label', [
    ('peek', 'builtin_peek'),
    ('poke', 'builtin_poke'),
    ('set_bank', 'builtin_set_bank'),
    ('read_bank', 'builtin_read_bank'),
])
def test_lazy_emission(name, label):
    asm_path, tmp_src = _compile_to_asm(PRIMITIVE_SOURCES[name])
    try:
        with open(asm_path, encoding='utf-8') as f:
            text = f.read()
        assert f'{label}:' in text, f'{label} not emitted for {name} call'
        print(f'PASS lazy emission {name} -> {label}')
    finally:
        _cleanup(asm_path, tmp_src)


def test_unused_primitives_not_emitted():
    asm_path, tmp_src = _compile_to_asm('int main() { return 5; }')
    try:
        with open(asm_path, encoding='utf-8') as f:
            text = f.read()
        for label in ('builtin_peek:', 'builtin_poke:',
                      'builtin_set_bank:', 'builtin_read_bank:'):
            assert label not in text, f'{label} linked without any call'
        print('PASS test_unused_primitives_not_emitted')
    finally:
        _cleanup(asm_path, tmp_src)


def test_poke_uses_two_operand_shifts():
    """The bare 'SHL Px' form mis-encodes on this ISA (dst,count required).

    Regression guard: the poke stub must emit 'SHL Px, 1'.
    """
    stub_lines = CodeGenerator.BUILTIN_IMPLEMENTATIONS['builtin_poke']
    shl_lines = [line for line in stub_lines if line.startswith('SHL')]
    assert len(shl_lines) == 8, f'expected 8 unrolled shifts, got {shl_lines}'
    for line in shl_lines:
        assert re.fullmatch(r'SHL P\d, 1', line), (
            f'mis-encoded shift {line!r}: bare SHL corrupts the stream')
    print('PASS test_poke_uses_two_operand_shifts')


def test_primitives_return_in_p0():
    """peek results must be taken from P0 at call sites."""
    asm_path, tmp_src = _compile_to_asm(PRIMITIVE_SOURCES['peek'])
    try:
        with open(asm_path, encoding='utf-8') as f:
            text = f.read()
        body = text.split('func_main:')[1].split('; Built-in')[0]
        assert re.search(
            r'CALL builtin_peek\b.*\n(?:\s*;[^\n]*\n)*\s*MOV P\d+, P0\b',
            body), 'peek result must be read from P0'
        print('PASS test_primitives_return_in_p0')
    finally:
        _cleanup(asm_path, tmp_src)


# ---------------------------------------------------------------------------
# Runtime: peek/poke byte semantics
# ---------------------------------------------------------------------------

BYTE_CASES = [0x00, 0x01, 0x7F, 0x80, 0xAB, 0xFE, 0xFF]


@pytest.mark.parametrize('value', BYTE_CASES)
def test_poke_peek_roundtrip(value):
    source = f"""
int main() {{
    poke(0x3000, {value});
    return peek(0x3000);
}}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == value, f'roundtrip {value:#x} failed, got {proc.p0:#x}'
    assert mem.read_byte(0x3000) == value
    print(f'PASS roundtrip {value:#04x} (cycles={cycles})')


def test_poke_preserves_neighbor_byte():
    """Byte stores must not clobber the byte at addr+1 (RMW contract)."""
    source = """
int main() {
    poke(0x3010, 0xCD);
    poke(0x3011, 0xEF);
    int hi = peek(0x3010);
    int lo = peek(0x3011);
    return hi * 256 + lo;
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 0xCDEF
    assert mem.read_byte(0x3010) == 0xCD
    assert mem.read_byte(0x3011) == 0xEF
    print(f'PASS neighbor preservation (P0=0x{proc.p0:04X})')


def test_poke_drops_high_bits():
    """Only the low byte of val is stored (hardware has no 16-bit bytes)."""
    source = """
int main() {
    poke(0x3020, 0x1234);
    return peek(0x3020);
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 0x34, f'expected low byte 0x34, got {proc.p0:#x}'
    print('PASS high-bit truncation')


def test_peek_zero_page_hot_region():
    """Zero page reads work through the hot view (kernel mount tables)."""
    source = """
int main() {
    poke(0x0016, 'S');
    return peek(0x0016);
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == ord('S')
    print('PASS zero-page peek/poke')


# ---------------------------------------------------------------------------
# Runtime: bank-window control
# ---------------------------------------------------------------------------

def test_read_bank_defaults_to_passthrough():
    proc, mem, cycles = compile_and_run(
        'int main() { return read_bank(); }')
    assert proc.p0 == 0, f'bank 0 expected at boot, got {proc.p0}'
    print('PASS read_bank default 0')


def test_set_bank_then_restore_bracketing():
    source = """
int main() {
    int prev = read_bank();
    set_bank(5);
    int during = read_bank();
    set_bank(prev);
    int after = read_bank();
    return prev * 100 + during * 10 + after;
}
"""
    # 0*100 + 5*10 + 0 = 50
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 50, f'bracketing broken: {proc.p0}'
    assert mem.current_bank == 0
    print('PASS save/restore bracketing')


def test_banked_write_never_touches_base_ram():
    """Writes while a nonzero page is visible land ONLY in the bank page."""
    source = """
int gvar_guard;

int main() {
    gvar_guard = 0x77;
    set_bank(3);
    poke(0x8020, 0xEE);
    set_bank(0);
    return peek(0x8020);
}
"""
    proc, mem, cycles = compile_and_run(source)
    # Base RAM untouched by the banked excursion...
    assert mem.read_byte(0x8020) == 0, 'banked write leaked into base RAM'
    # ...and landed in page 3 instead.
    assert mem._bank_pages[3][0x20] == 0xEE, 'banked write lost'
    assert proc.p0 == 0
    print('PASS banked write isolation')


def test_set_bank_clamps_out_of_range():
    """MOV BANK clamps to 0-15; set_bank(200) must read back as 15."""
    source = """
int main() {
    set_bank(200);
    int b = read_bank();
    set_bank(0);
    return b;
}
"""
    proc, mem, cycles = compile_and_run(source)
    assert proc.p0 == 15, f'clamp failed: {proc.p0}'
    print('PASS out-of-range clamp')


def test_ramdisk_driver_pattern_matches_spec():
    """The spec's r_read pattern works verbatim as an Astrid function."""
    source = """
int r_read(int n, int off) {
    int prev = read_bank();
    set_bank(n);
    int v = peek(0x8000 + off);
    set_bank(prev);
    return v;
}

void r_write(int n, int off, int val) {
    int prev = read_bank();
    set_bank(n);
    poke(0x8000 + off, val);
    set_bank(prev);
}

int main() {
    r_write(2, 0, 'S');
    r_write(2, 1, '1');
    int ok = 1;
    if (r_read(2, 0) != 'S') { ok = 0; }
    if (r_read(2, 1) != '1') { ok = 0; }
    if (read_bank() != 0) { ok = 0; }
    return ok * 10 + r_read(2, 1) - '0';
}
"""
    proc, mem, cycles = compile_and_run(source)
    # ok=1, last digit read back = 1 -> 11
    assert proc.p0 == 11, f'R: driver pattern failed: {proc.p0}'
    assert mem._bank_pages[2][0] == ord('S')
    assert mem._bank_pages[2][1] == ord('1')
    assert mem.current_bank == 0
    print(f'PASS spec ramdisk-driver pattern (cycles={cycles})')


if __name__ == '__main__':
    test_builtin_table_mappings()
    for name in ('peek', 'poke', 'set_bank', 'read_bank'):
        test_lazy_emission(name, name)
    test_unused_primitives_not_emitted()
    test_poke_uses_two_operand_shifts()
    test_primitives_return_in_p0()
    for value in BYTE_CASES:
        test_poke_peek_roundtrip(value)
    test_poke_preserves_neighbor_byte()
    test_poke_drops_high_bits()
    test_peek_zero_page_hot_region()
    test_read_bank_defaults_to_passthrough()
    test_set_bank_then_restore_bracketing()
    test_banked_write_never_touches_base_ram()
    test_set_bank_clamps_out_of_range()
    test_ramdisk_driver_pattern_matches_spec()
    print('All kernel-primitive tests passed!')
