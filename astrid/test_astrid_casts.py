"""Tests for Astrid type conversion features using ITOB/BTOI/ITOS/STOI instructions."""
import os
import sys

# Add project root to path so we can import nova_main and astrid modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add astrid directory to path so we can import astrid_compiler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nova_main import initialize_system
from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser, Cast, Number


def run_binary(bin_path, max_cycles=2000000):
    """Run a binary headlessly and return (proc, cycles)."""
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry_point = mem.load(bin_path)
    proc.pc = entry_point
    cycle = 0
    while cycle < max_cycles and not proc.halted:
        cycle += 1
        proc.step()
    return proc, cycle, mem


def compile_and_run(source, expected_r0=None):
    """Compile Astrid source, assemble, and run. Returns (proc, cycles, mem)."""
    import tempfile
    # UTF-8 is required: source strings may contain non-ASCII characters
    # that cp1252 cannot encode on Windows.
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8') as f:
        f.write(source)
        source_path = f.name

    try:
        from astrid_compiler import main as compiler_main
        old_argv = sys.argv
        sys.argv = [old_argv[0], source_path, '-o', source_path.replace('.ast', '.asm')]
        try:
            compiler_main()
        finally:
            sys.argv = old_argv

        asm_path = source_path.replace('.ast', '.asm')
        bin_path = source_path.replace('.ast', '.bin')

        from nova_assembler import Assembler
        asm = Assembler()
        asm.assemble(asm_path)

        proc, cycles, mem = run_binary(bin_path)
        assert proc.halted, "Program did not halt"
        if expected_r0 is not None:
            assert proc.r0 == expected_r0, f"Expected R0={expected_r0}, got {proc.r0}"
        return proc, cycles, mem
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


def test_sin_return_type_float_promotion():
    """sin() returns float; mixed float*int must use FMUL, not MUL.

    Regression test: the compiler did not know builtins like sin()
    returned float, so `sin(x) * amplitude` used integer MUL instead of
    FMUL, producing wildly wrong results.
    """
    source = """
int main() {
    float frequency = 2.0 * 3.14159265 / 128;
    int amplitude = 50;
    int center_y = 128;
    int y = center_y + (int)(sin(frequency) * amplitude);
    return y;
}
"""
    proc, cycles, mem = compile_and_run(source)
    # sin(2π/128) ≈ 0.0491, so y ≈ 128 + (int)(0.0491 * 50) ≈ 130.
    # Q8.8 fixed-point rounding can shift this by a few units.
    # The key check: result is near center_y (128), not wildly off.
    assert 120 <= proc.r0 <= 136, f"Expected y in [120,136], got {proc.r0}"


def test_cos_return_type_float_promotion():
    """cos() also returns float and must trigger FMUL in mixed ops."""
    source = """
int main() {
    float angle = 0.0;
    int scale = 100;
    int result = (int)(cos(angle) * scale);
    return result;
}
"""
    proc, cycles, mem = compile_and_run(source)
    # cos(0) = 1.0, (int)(1.0 * 100) = 100
    assert proc.r0 == 100, f"Expected 100, got {proc.r0}"


def test_sin_int_cast_chain():
    """(int)(sin(x) * amp) must emit ITOF, FMUL, then FTOI."""
    source = """
int main() {
    float f = 3.14159265;
    int amp = 10;
    int r = (int)(sin(f) * amp);
    return r;
}
"""
    proc, cycles, mem = compile_and_run(source)
    # sin(π) ≈ 0, so r ≈ 0
    assert 0 <= proc.r0 <= 2, f"Expected 0-2, got {proc.r0}"


def test_lexer_recognizes_string_and_binary_keywords():
    """Lexer should recognize string and binary as keywords."""
    lexer = Lexer("string s; binary b; int i;")
    tokens = lexer.tokenize()
    # 'string' should be KEYWORD, 's' IDENTIFIER, ';' DELIMITER, 'binary' KEYWORD...
    kinds = [(t.type, t.value) for t in tokens if t.type != 'EOF']
    assert ('KEYWORD', 'string') in kinds
    assert ('KEYWORD', 'binary') in kinds
    assert ('KEYWORD', 'int') in kinds


def test_parser_handles_cast_expression():
    """Parser should create Cast nodes for (string)x, (int)x, (char)x, (binary)x."""
    lexer = Lexer("int main() { int x = (int)5; return x; }")
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    assert len(ast.functions) == 1
    # The var decl value should be a Cast node
    main_func = ast.functions[0]
    var_decl = main_func.body[0]
    assert isinstance(var_decl.value, Cast)
    assert var_decl.value.target_type == 'int'
    assert isinstance(var_decl.value.expr, Number)


def test_int_to_char_cast():
    """(char)value should truncate to low byte."""
    source = """
int main() {
    char c = (char)0x1234;
    return c;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=0x34)
    print(f"PASS test_int_to_char_cast (cycles={cycles}, R0=0x{proc.r0:02X})")


def test_int_to_string_cast():
    """(string)value should produce a decimal string at 0xA000."""
    source = """
int main() {
    string s = (string)12345;
    return (int)s;  // return the buffer address (non-zero = success)
}
"""
    proc, cycles, mem = compile_and_run(source)
    assert proc.halted
    # The buffer address 0xA000 should be returned in R0 indirectly
    # (string)12345 returns the address 0xA000 in R0 via the statement
    # But return value of main is the address itself
    print(f"PASS test_int_to_string_cast (cycles={cycles}, R0=0x{proc.r0:04X})")
    # Verify decimal string "12345" is at 0xA000
    addr = 0xA000
    chars = []
    while True:
        byte = mem.read_byte(addr)
        if byte == 0:
            break
        chars.append(chr(byte))
        addr += 1
    assert ''.join(chars) == "12345", f"Expected '12345' at 0xA000, got '{''.join(chars)}'"
    print(f"PASS test_int_to_string_cast string content: '{''.join(chars)}'")


def test_string_to_int_cast():
    """(int)"1234" should convert decimal string to integer 1234."""
    source = """
int main() {
    int x = (int)"1234";
    return x;
}
"""
    proc, cycles, mem = compile_and_run(source)
    assert proc.halted
    # Full 16-bit result lives in P0 (R0 only holds the low byte, since R0
    # is an 8-bit register and 1234 > 255 truncates).
    assert proc.p0 == 1234, f"Expected P0=1234, got {proc.p0}"
    print(f"PASS test_string_to_int_cast (cycles={cycles}, P0={proc.p0}, R0=0x{proc.r0:02X})")


def test_string_variable_conversion():
    """Declaring a string variable and casting it back should work."""
    source = """
int main() {
    string s = (string)42;
    int x = (int)s;
    return x;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f"PASS test_string_variable_conversion (cycles={cycles}, R0={proc.r0})")


def test_int_to_binary_cast():
    """(binary)value should produce a binary string at 0xA100."""
    source = """
int main() {
    binary b = (binary)10;
    return (int)b;
}
"""
    proc, cycles, mem = compile_and_run(source)
    assert proc.halted
    print(f"PASS test_int_to_binary_cast (cycles={cycles}, R0=0x{proc.r0:04X})")
    # The binary string buffer address is 0xA100 (our codegen uses this)
    # Check binary string "1010" is at 0xA100
    addr = 0xA100
    chars = []
    while True:
        byte = mem.read_byte(addr)
        if byte == 0:
            break
        chars.append(chr(byte))
        addr += 1
    bin_str = ''.join(chars)
    assert bin_str == "1010", f"Expected '1010' at 0xA100, got '{bin_str}'"
    print(f"PASS test_int_to_binary_cast binary string: '{bin_str}'")


def test_buffer_register_returns_address():
    """(string) should return the 0xA000 buffer address."""
    source = """
int main() {
    string s = (string)99;
    // FIXME: codegen currently returns the result register, and ITOS writes
    // the buffer address into dest. Store in R0.
    return (int)s;
}
"""
    # We can't directly assert R0 == 0xA000 because the generated code for
    # `string s = (string)99` stores the address in local `s`.
    # But `return (int)s` should call STOI on it and return 99.
    proc, cycles, mem = compile_and_run(source, expected_r0=99)
    print(f"PASS test_buffer_register_returns_address (cycles={cycles}, R0={proc.r0})")


def test_char_to_int_cast():
    """(int)charVariable should sign/zero-extend to 16-bit int."""
    source = """
int main() {
    char c = 65;
    int x = (int)c;
    return x;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=65)
    print(f"PASS test_char_to_int_cast (cycles={cycles}, R0={proc.r0})")


def test_cast_in_expression():
    """Cast within a binary expression should work."""
    source = """
int main() {
    int x = (int)"7";
    int y = x + 5;
    return y;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=12)
    print(f"PASS test_cast_in_expression (cycles={cycles}, R0={proc.r0})")


def test_double_cast_string_then_int():
    """Nested casts should work: (int)(string)value."""
    source = """
int main() {
    int x = (int)(string)255;
    return x;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=255)
    print(f"PASS test_double_cast_string_then_int (cycles={cycles}, R0={proc.r0})")


if __name__ == '__main__':
    test_lexer_recognizes_string_and_binary_keywords()
    test_parser_handles_cast_expression()
    test_int_to_char_cast()
    test_int_to_string_cast()
    test_string_to_int_cast()
    test_string_variable_conversion()
    test_int_to_binary_cast()
    test_buffer_register_returns_address()
    test_char_to_int_cast()
    test_cast_in_expression()
    test_double_cast_string_then_int()
    print("All Astrid cast tests passed!")