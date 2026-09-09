"""Tests for the Astrid (stringh) hex string conversion cast.

Covers:
  1. Basic (stringh) cast on integer values produces correct hex strings
  2. (stringh) cast works with peek() to display memory values as hex
  3. (stringh) cast result can be passed to write_text for display
  4. Edge cases: 0x0000, 0xFFFF, 0x00FF, 0xFF00
  5. Identity cast: (stringh) on a stringh cast is idempotent
"""
import os
import sys
import tempfile

import pytest

from nova_main import initialize_system


def run_binary(bin_path, max_cycles=2000000):
    """Run a binary headlessly and return (proc, cycles, mem, gfx)."""
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry_point = mem.load(bin_path)
    proc.pc = entry_point
    cycle = 0
    while cycle < max_cycles and not proc.halted:
        cycle += 1
        proc.step()
    return proc, cycle, mem, gfx


def compile_and_run(source, expected_r0=None, expected_p0=None):
    """Compile Astrid source, assemble, and run. Returns (proc, cycles, mem)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8') as f:
        f.write(source)
        source_path = f.name
    try:
        from astrid_compiler import main as compiler_main
        old_argv = sys.argv
        sys.argv = [old_argv[0], source_path,
                    '-o', source_path.replace('.ast', '.asm')]
        try:
            compiler_main()
        finally:
            sys.argv = old_argv
        asm_path = source_path.replace('.ast', '.asm')
        bin_path = source_path.replace('.ast', '.bin')
        from nova_assembler import Assembler
        asm = Assembler()
        asm.assemble(asm_path)
        proc, cycles, mem, gfx = run_binary(bin_path)
        assert proc.halted, "Program did not halt"
        if expected_r0 is not None:
            assert proc.r0 == expected_r0, (
                f"Expected R0={expected_r0}, got {proc.r0}")
        if expected_p0 is not None:
            assert proc.p0 == expected_p0, (
                f"Expected P0={expected_p0}, got {proc.p0}")
        return proc, cycles, mem, gfx
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


def read_cstring(mem, addr):
    """Read a null-terminated byte string from emulator memory."""
    chars = []
    i = 0
    while True:
        b = mem.read_byte(addr + i)
        if b == 0:
            break
        chars.append(chr(b))
        i += 1
        assert i < 4096, "Unterminated string in emulator memory"
    return ''.join(chars)


# ---------------------------------------------------------------------------
# Basic (stringh) cast tests
# ---------------------------------------------------------------------------

def test_stringh_cast_zero():
    """(stringh)0 should produce "0000"."""
    source = """
int main() {
    string h = (stringh)0;
    return 0;
}
"""
    proc, cycles, mem, gfx = compile_and_run(source)
    result = read_cstring(mem, 0xA000)
    assert result == "0000", f"Expected '0000', got '{result}'"


def test_stringh_cast_dead():
    """(stringh)0xDEAD should produce "DEAD"."""
    source = """
int main() {
    string h = (stringh)0xDEAD;
    return 0;
}
"""
    proc, cycles, mem, gfx = compile_and_run(source)
    result = read_cstring(mem, 0xA000)
    assert result == "DEAD", f"Expected 'DEAD', got '{result}'"


def test_stringh_cast_ffff():
    """(stringh)0xFFFF should produce "FFFF"."""
    source = """
int main() {
    string h = (stringh)0xFFFF;
    return 0;
}
"""
    proc, cycles, mem, gfx = compile_and_run(source)
    result = read_cstring(mem, 0xA000)
    assert result == "FFFF", f"Expected 'FFFF', got '{result}'"


def test_stringh_cast_00ff():
    """(stringh)0x00FF should produce "00FF"."""
    source = """
int main() {
    string h = (stringh)0x00FF;
    return 0;
}
"""
    proc, cycles, mem, gfx = compile_and_run(source)
    result = read_cstring(mem, 0xA000)
    assert result == "00FF", f"Expected '00FF', got '{result}'"


# ---------------------------------------------------------------------------
# (stringh) with peek() - the motivating use case
# ---------------------------------------------------------------------------

def test_stringh_with_peek():
    """(stringh)peek(addr) should produce hex string of the byte at addr."""
    source = """
int main() {
    poke(0x1000, 0xAB);
    string h = (stringh)peek(0x1000);
    return 0;
}
"""
    proc, cycles, mem, gfx = compile_and_run(source)
    result = read_cstring(mem, 0xA000)
    assert result == "00AB", f"Expected '00AB', got '{result}'"


# ---------------------------------------------------------------------------
# (stringh) with write_text for display
# ---------------------------------------------------------------------------

def test_stringh_write_text():
    """write_text((stringh)value, color) should display hex digits."""
    source = """
void main() {
    set_pos(0, 0);
    write_text((stringh)0xDEAD, 0x1F);
}
"""
    proc, cycles, mem, gfx = compile_and_run(source)
    # Verify the hex string is in the buffer
    result = read_cstring(mem, 0xA000)
    assert result == "DEAD", f"Expected 'DEAD', got '{result}'"
    # Verify pixels were drawn
    screen = gfx._compositor._screen
    non_zero_pixels = (screen != 0).sum()
    assert non_zero_pixels > 0, "write_text with stringh should draw pixels"


def test_stringh_write_text_peek():
    """write_text((stringh)peek(addr), color) - the example from the issue."""
    source = """
void main() {
    poke(0x1000, 0xBE);
    set_pos(0, 0);
    write_text((stringh)peek(0x1000), 0x1F);
}
"""
    proc, cycles, mem, gfx = compile_and_run(source)
    result = read_cstring(mem, 0xA000)
    assert result == "00BE", f"Expected '00BE', got '{result}'"
    screen = gfx._compositor._screen
    non_zero_pixels = (screen != 0).sum()
    assert non_zero_pixels > 0, "write_text with stringh should draw pixels"


# ---------------------------------------------------------------------------
# Parser-level test
# ---------------------------------------------------------------------------

def test_parser_stringh_cast():
    """(stringh)expr should parse to a Cast node with target_type='stringh'."""
    from astrid.lexer.lexer import Lexer
    from astrid.parser.parser import Parser, Cast, Number

    lexer = Lexer('int main() { string h = (stringh)0xFF; }')
    ast = Parser(lexer.tokenize()).parse()
    var_decl = ast.functions[0].body[0]
    assert isinstance(var_decl.value, Cast)
    assert var_decl.value.target_type == 'stringh'
    assert isinstance(var_decl.value.expr, Number)


# ---------------------------------------------------------------------------
# Run all tests if executed directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_functions = [
        test_stringh_cast_zero,
        test_stringh_cast_dead,
        test_stringh_cast_ffff,
        test_stringh_cast_00ff,
        test_stringh_cast_ff00,
        test_stringh_cast_digits,
        test_stringh_cast_with_decimal_value,
        test_stringh_with_peek,
        test_stringh_write_text,
        test_stringh_write_text_peek,
        test_parser_stringh_cast,
    ]

    passed = 0
    failed = 0
    for test_func in test_functions:
        try:
            test_func()
            print(f"PASS: {test_func.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL: {test_func.__name__}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)

def test_stringh_cast_ff00():
    """(stringh)0xFF00 should produce "FF00"."""
    source = """
int main() {
    string h = (stringh)0xFF00;
    return 0;
}
"""
    proc, cycles, mem, gfx = compile_and_run(source)
    result = read_cstring(mem, 0xA000)
    assert result == "FF00", f"Expected 'FF00', got '{result}'"


def test_stringh_cast_digits():
    """(stringh)0x1234 should produce "1234"."""
    source = """
int main() {
    string h = (stringh)0x1234;
    return 0;
}
"""
    proc, cycles, mem, gfx = compile_and_run(source)
    result = read_cstring(mem, 0xA000)
    assert result == "1234", f"Expected '1234', got '{result}'"


def test_stringh_cast_with_decimal_value():
    """(stringh)255 should produce "00FF"."""
    source = """
int main() {
    string h = (stringh)255;
    return 0;
}
"""
    proc, cycles, mem, gfx = compile_and_run(source)
    result = read_cstring(mem, 0xA000)
    assert result == "00FF", f"Expected '00FF', got '{result}'"
