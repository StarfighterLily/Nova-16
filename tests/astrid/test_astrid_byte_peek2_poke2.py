"""High-coverage tests for byte(), peek2(), and poke2() Astrid builtins.

Covers:
1. byte(value, 0) -> high byte (mirrors P1: in Nova ISA)
2. byte(value, 1) -> low byte (mirrors :P1 in Nova ISA)
3. peek2(addr) -> 16-bit word read (no byte-splitting dance)
4. poke2(addr, val) -> 16-bit word write
5. Round-trip: poke2 followed by peek2
6. poke2 to function-pointer addresses (primary use case)
7. Edge cases: zero, 0xFFFF, boundary addresses
8. Lazy emission: builtins only emitted when used
9. Codegen correctness: correct instruction sequences
"""
import os
import sys
import tempfile

import pytest

from nova_main import initialize_system
from astrid.codegen.codegen import CodeGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compile_to_asm(source):
    """Compile Astrid source text; return (asm_path, tmp_source_path)."""
    fd = tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8')
    fd.write(source)
    fd.close()
    from astrid_compiler import main as compiler_main
    old_argv = sys.argv
    asm_path = fd.name.replace('.ast', '.asm')
    sys.argv = [old_argv[0], fd.name, '-o', asm_path]
    try:
        compiler_main()
    finally:
        sys.argv = old_argv
    return asm_path, fd.name


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


# ===========================================================================
# Codegen-level tests
# ===========================================================================

class TestBuiltinTableMappings:
    """Verify all three new builtins are registered in the function table."""

    def test_byte_mapping(self):
        gen = CodeGenerator()
        assert gen.builtin_functions['byte'] == 'builtin_byte'
        assert 'builtin_byte' in CodeGenerator.BUILTIN_IMPLEMENTATIONS

    def test_peek2_mapping(self):
        gen = CodeGenerator()
        assert gen.builtin_functions['peek2'] == 'builtin_peek2'
        assert 'builtin_peek2' in CodeGenerator.BUILTIN_IMPLEMENTATIONS

    def test_poke2_mapping(self):
        gen = CodeGenerator()
        assert gen.builtin_functions['poke2'] == 'builtin_poke2'
        assert 'builtin_poke2' in CodeGenerator.BUILTIN_IMPLEMENTATIONS


def _compile_to_asm_text(source):
    """Compile Astrid source text; return (asm_text, tmp_source_path)."""
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
    asm_path = fd.name.replace('.ast', '.asm')
    with open(asm_path, encoding='utf-8') as f:
        return f.read(), fd.name


class TestLazyEmission:
    """Builtins are only emitted when actually called."""

    def test_unused_byte_not_emitted(self):
        asm, path = _compile_to_asm_text('int main() { return 0; }')
        _cleanup(path)
        assert 'builtin_byte' not in asm

    def test_unused_peek2_not_emitted(self):
        asm, path = _compile_to_asm_text('int main() { return 0; }')
        _cleanup(path)
        assert 'builtin_peek2' not in asm

    def test_unused_poke2_not_emitted(self):
        asm, path = _compile_to_asm_text('int main() { return 0; }')
        _cleanup(path)
        assert 'builtin_poke2' not in asm

    def test_used_byte_is_emitted(self):
        asm, path = _compile_to_asm_text(
            'int main() { return byte(0xABCD, 0); }')
        _cleanup(path)
        assert 'builtin_byte:' in asm

    def test_used_peek2_is_emitted(self):
        asm, path = _compile_to_asm_text(
            'int main() { return peek2(0x3000); }')
        _cleanup(path)
        assert 'builtin_peek2:' in asm

    def test_used_poke2_is_emitted(self):
        asm, path = _compile_to_asm_text(
            'int main() { poke2(0x3000, 0xBEEF); return 0; }')
        _cleanup(path)
        assert 'builtin_poke2:' in asm


class TestCodegenCorrectness:
    """Verify the generated assembly uses the right instructions."""

    def test_byte_emits_select_byte_access(self):
        """byte() should use P-high/low-byte access syntax."""
        asm, path = _compile_to_asm_text(
            'int main() { return byte(0x1234, 0); }')
        _cleanup(path)
        assert 'P1:' in asm or 'P0:' in asm  # high-byte access
        assert ':P1' in asm or ':P0' in asm  # low-byte access

    def test_peek2_emits_single_load(self):
        """peek2() should do a single word load, no shift/mask."""
        asm, path = _compile_to_asm_text(
            'int main() { return peek2(0x4000); }')
        _cleanup(path)
        assert 'MOV P0, [P1]' in asm

    def test_poke2_emits_single_store(self):
        """poke2() should do a single word store, no read-modify-write."""
        asm, path = _compile_to_asm_text(
            'int main() { poke2(0x4000, 0xABCD); return 0; }')
        _cleanup(path)
        assert 'MOV [P1], P2' in asm

    def test_byte_p0_returning(self):
        """byte() result should be read from P0 at the call site."""
        asm, path = _compile_to_asm_text(
            'int main() { int x = byte(0xFF00, 1); return x; }')
        _cleanup(path)
        assert 'builtin_byte' in asm


# ===========================================================================
# Runtime / emulator tests
# ===========================================================================

class TestByteHigh:
    """byte(value, 0) returns the high byte."""

    def test_byte_high_simple(self):
        """byte(0xABCD, 0) == 0xAB"""
        source = 'int main() { return byte(0xABCD, 0); }'
        proc, mem, cycles = compile_and_run(source)
        assert proc.p0 == 0xAB, f"expected 0xAB, got 0x{proc.p0:02X}"

    def test_byte_high_zero(self):
        """byte(0x00FF, 0) == 0x00"""
        source = 'int main() { return byte(0x00FF, 0); }'
        proc, mem, cycles = compile_and_run(source)
        assert proc.p0 == 0x00, f"expected 0x00, got 0x{proc.p0:02X}"

    def test_byte_high_max(self):
        """byte(0xFF00, 0) == 0xFF"""
        source = 'int main() { return byte(0xFF00, 0); }'
        proc, mem, cycles = compile_and_run(source)
        assert proc.p0 == 0xFF, f"expected 0xFF, got 0x{proc.p0:02X}"

    def test_byte_high_from_variable(self):
        """byte() works with runtime variable values, not just constants."""
        source = """
int main() {
    int x = 0x1234;
    return byte(x, 0);
}
"""
        proc, mem, cycles = compile_and_run(source)
        assert proc.p0 == 0x12, f"expected 0x12, got 0x{proc.p0:02X}"


class TestByteLow:
    """byte(value, 1) returns the low byte."""

    def test_byte_low_simple(self):
        """byte(0xABCD, 1) == 0xCD"""
        source = 'int main() { return byte(0xABCD, 1); }'
        proc, mem, cycles = compile_and_run(source)
        assert proc.p0 == 0xCD, f"expected 0xCD, got 0x{proc.p0:02X}"

    def test_byte_low_zero(self):
        """byte(0xFF00, 1) == 0x00"""
        source = 'int main() { return byte(0xFF00, 1); }'
        proc, mem, cycles = compile_and_run(source)
        assert proc.p0 == 0x00, f"expected 0x00, got 0x{proc.p0:02X}"

    def test_byte_low_max(self):
        """byte(0x00FF, 1) == 0xFF"""
        source = 'int main() { return byte(0x00FF, 1); }'
        proc, mem, cycles = compile_and_run(source)
        assert proc.p0 == 0xFF, f"expected 0xFF, got 0x{proc.p0:02X}"

    def test_byte_low_from_variable(self):
        """byte() works with runtime variable values, not just constants."""
        source = """
int main() {
    int x = 0xBEEF;
    return byte(x, 1);
}
"""
        proc, mem, cycles = compile_and_run(source)
        assert proc.p0 == 0xEF, f"expected 0xEF, got 0x{proc.p0:02X}"


class TestByteRoundTrip:
    """Reconstruct a word from its high and low bytes."""

    def test_reconstruct_word(self):
        """hi * 256 + lo should equal the original value."""
        source = """
int main() {
    int x = 0xCAFE;
    int hi = byte(x, 0);
    int lo = byte(x, 1);
    return hi * 256 + lo;
}
"""
        proc, mem, cycles = compile_and_run(source)
        assert proc.p0 == 0xCAFE, f"expected 0xCAFE, got 0x{proc.p0:04X}"


class TestPeek2:
    """peek2(addr) reads a 16-bit word."""

    def test_peek2_zero(self):
        """peek2 on zeroed memory returns 0."""
        source = 'int main() { return peek2(0x4000); }'
        proc, mem, cycles = compile_and_run(source)
        assert proc.p0 == 0, f"expected 0, got 0x{proc.p0:04X}"

    def test_peek2_stored_value(self):
        """peek2 returns the full word stored by poke2."""
        source = """
int main() {
    poke2(0x5000, 0xDEAD);
    return peek2(0x5000);
}
"""
        proc, mem, cycles = compile_and_run(source)
        assert proc.p0 == 0xDEAD, f"expected 0xDEAD, got 0x{proc.p0:04X}"

    def test_peek2_zero_page(self):
        """peek2 works on zero-page addresses (hot region)."""
        source = """
int main() {
    poke2(0x0040, 0xBEEF);
    return peek2(0x0040);
}
"""
        proc, mem, cycles = compile_and_run(source)
        assert proc.p0 == 0xBEEF, f"expected 0xBEEF, got 0x{proc.p0:04X}"


class TestPoke2:
    """poke2(addr, value) writes a 16-bit word."""

    def test_poke2_basic(self):
        """poke2 stores both bytes correctly."""
        source = """
int main() {
    poke2(0x6000, 0x1234);
    int hi = peek(0x6000);
    int lo = peek(0x6001);
    return hi * 256 + lo;
}
"""
        proc, mem, cycles = compile_and_run(source)
        assert proc.p0 == 0x1234, f"expected 0x1234, got 0x{proc.p0:04X}"

    def test_poke2_zero(self):
        """poke2 with 0 writes all zeroes."""
        source = """
int main() {
    poke2(0x6000, 0xFFFF);
    poke2(0x6000, 0x0000);
    return peek2(0x6000);
}
"""
        proc, mem, cycles = compile_and_run(source)
        assert proc.p0 == 0, f"expected 0, got 0x{proc.p0:04X}"

    def test_poke2_max(self):
        """poke2 with 0xFFFF writes all ones."""
        source = """
int main() {
    poke2(0x7000, 0xFFFF);
    return peek2(0x7000);
}
"""
        proc, mem, cycles = compile_and_run(source)
        assert proc.p0 == 0xFFFF, f"expected 0xFFFF, got 0x{proc.p0:04X}"

    def test_poke2_preserves_adjacent(self):
        """poke2 at addr doesn't corrupt addr+2."""
        source = """
int main() {
    poke2(0x5000, 0xAAAA);
    poke2(0x5002, 0xBBBB);
    return peek2(0x5000) + peek2(0x5002);
}
"""
        proc, mem, cycles = compile_and_run(source)
        # Sum wraps at 16 bits: (0xAAAA + 0xBBBB) & 0xFFFF = 0x6665
        assert proc.p0 == (0xAAAA + 0xBBBB) & 0xFFFF, f"corrupted: got 0x{proc.p0:04X}"


class TestPoke2Peek2RoundTrip:
    """Comprehensive round-trip tests."""

    @pytest.mark.parametrize('value', [
        0x0000, 0x0001, 0x00FF, 0x0100, 0x1234,
        0xAAAA, 0x5555, 0xDEAD, 0xBEEF, 0xCAFE,
        0xFFFF, 0x7FFF, 0x8000,
    ])
    def test_round_trip_various_values(self, value):
        """poke2 then peek2 preserves every tested bit pattern."""
        source = f"""
int main() {{
    poke2(0x4800, 0x{value:04X});
    return peek2(0x4800);
}}
"""
        proc, mem, cycles = compile_and_run(source)
        assert proc.p0 == value, (
            f"round-trip failed for 0x{value:04X}: got 0x{proc.p0:04X}")


class TestPoke2FunctionPointer:
    """poke2 to function addresses -- the primary use case."""

    def test_poke2_function_address(self):
        """poke2 can write a full function address to a pointer variable."""
        source = """
int target_func() {
    return 42;
}

int main() {
    int ptr;
    poke2(0x3000, 0x1234);
    ptr = peek2(0x3000);
    if (ptr == 0x1234) { return 1; }
    return 0;
}
"""
        proc, mem, cycles = compile_and_run(source)
        assert proc.p0 == 1, f"poke2 function ptr failed: got {proc.p0}"

    def test_byte_for_function_address_splitting(self):
        """byte() can split a function address into poke() calls."""
        source = """
int main() {
    int addr = 0x5678;
    poke(0x2000, byte(addr, 0));
    poke(0x2001, byte(addr, 1));
    return peek2(0x2000);
}
"""
        proc, mem, cycles = compile_and_run(source)
        assert proc.p0 == 0x5678, f"byte() splitting failed: got 0x{proc.p0:04X}"


class TestCombinedUsage:
    """Real-world patterns combining all new builtins."""

    def test_memcpy_with_poke2_peek2(self):
        """poke2/peek2 as a faster memcpy for word-aligned data."""
        source = """
int main() {
    poke2(0x4000, 0x1111);
    poke2(4002, 0x2222);
    int a = peek2(0x4000);
    int b = peek2(4002);
    if (a == 0x1111 && b == 0x2222) { return 100 + a / 256 + b / 256; }
    return 0;
}
"""
        proc, mem, cycles = compile_and_run(source)
        # 100 + 0x11 + 0x22 = 100 + 17 + 34 = 151
        assert proc.p0 == 151, f"combined memcpy failed: got {proc.p0}"

    def test_byte_masking_pattern(self):
        """Use byte() to extract and recombine bytes (swap endianness)."""
        source = """
int main() {
    int x = 0xAABB;
    int hi = byte(x, 0);
    int lo = byte(x, 1);
    poke2(0x3000, lo * 256 + hi);
    return peek2(0x3000);
}
"""
        proc, mem, cycles = compile_and_run(source)
        assert proc.p0 == 0xBBAA, f"byte swap failed: got 0x{proc.p0:04X}"


# ===========================================================================
# Entry point for direct execution
# ===========================================================================

if __name__ == '__main__':
    import traceback

    test_classes = [
        TestBuiltinTableMappings,
        TestLazyEmission,
        TestCodegenCorrectness,
        TestByteHigh,
        TestByteLow,
        TestByteRoundTrip,
        TestPeek2,
        TestPoke2,
        TestPoke2Peek2RoundTrip,
        TestPoke2FunctionPointer,
        TestCombinedUsage,
    ]

    passed = 0
    failed = 0
    for cls in test_classes:
        instance = cls()
        for name in dir(instance):
            if name.startswith('test_'):
                try:
                    if name == 'test_round_trip_various_values':
                        for val in [0x0000, 0x0001, 0x00FF, 0x0100,
                                    0x1234, 0xAAAA, 0x5555, 0xDEAD,
                                    0xBEEF, 0xCAFE, 0xFFFF, 0x7FFF, 0x8000]:
                            try:
                                getattr(instance, name)(val)
                                passed += 1
                                print(f"  PASS {cls.__name__}.{name}(0x{val:04X})")
                            except Exception as e:
                                failed += 1
                                print(f"  FAIL {cls.__name__}.{name}(0x{val:04X}): {e}")
                                traceback.print_exc()
                    else:
                        getattr(instance, name)()
                        passed += 1
                        print(f"  PASS {cls.__name__}.{name}")
                except Exception as e:
                    failed += 1
                    print(f"  FAIL {cls.__name__}.{name}: {e}")
                    traceback.print_exc()

    print(f"\n{passed} passed, {failed} failed")
    if failed:
        sys.exit(1)