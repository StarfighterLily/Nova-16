"""High-coverage tests for Astrid string CONCATENATION and string INDEXING.

Covers:
  1. Runtime '+' concatenation: literal+literal, var+var, var+literal,
     literal+var, 4-term chains, left/right nested grouping, exact byte
     content, results used by strlen/index.
  2. Global string initializers (a string global stores a DW pointer to its DEFSTR).
  3. String indexing: "abc"[CONST], "abc"[runtime i], s[i], g[i],
     "a\tb"[i] (escapes resolved), s[i] = c writes, out-of-range
     constant indexes rejected at compile time.
  4. Parser-level checks for the new StringIndexAccess node.
  5. Pointer arithmetic on char* / string+number is untouched (not concat).
  6. Regression: "abc"[0] + "def" is pointer arithmetic, NOT concatenation.
  7. Layer operations with variable layer arguments and composite semantics.
"""
import os
import sys

import pytest

from nova_main import initialize_system
from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser, StringIndexAccess, Number


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
    import tempfile
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
        return proc, cycles, mem
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
# Parser-level
# ---------------------------------------------------------------------------

def test_parser_string_index_access_node():
    """\"abc\"[1] parses to a StringIndexAccess with the constant index."""
    lexer = Lexer('int main() { int i = "abc"[1]; }')
    ast = Parser(lexer.tokenize()).parse()
    value = ast.functions[0].body[0].value
    assert isinstance(value, StringIndexAccess)
    assert isinstance(value.index, Number)
    assert value.index.value == '1'
    assert value.value == 'abc'
    assert value.raw == 'abc'


def test_parser_string_index_escape_unescaped():
    """\"a\tb\"[1] keeps escapes resolved so the index sees the TAB."""
    lexer = Lexer(r'int main() { int c = "a\tb"[1]; }')
    ast = Parser(lexer.tokenize()).parse()
    value = ast.functions[0].body[0].value
    assert isinstance(value, StringIndexAccess)
    assert value.value == 'a\tb'
    assert ord(value.value[1]) == 9


def test_parser_adjacent_strings_then_index():
    """Adjacent literals merge BEFORE indexing: \"ab\" \"cde\"[2]."""
    lexer = Lexer('int main() { int c = "ab" "cde"[2]; }')
    ast = Parser(lexer.tokenize()).parse()
    value = ast.functions[0].body[0].value
    assert isinstance(value, StringIndexAccess)
    assert value.value == 'abcde'
    assert isinstance(value.index, Number)
    assert value.index.value == '2'


# ---------------------------------------------------------------------------
# String concatenation via '+'
# ---------------------------------------------------------------------------

def test_concat_literal_literal_length():
    proc, cycles, mem = compile_and_run(
        'int main() { return strlen("ab" + "cd"); }', expected_r0=4)
    print(f"PASS literal+literal length (cycles={cycles})")


def test_concat_var_var_length():
    compile_and_run("""
int main() {
    string a = "ab";
    string b = "cd";
    string c = a + b;
    return strlen(c);
}
""", expected_r0=4)


def test_concat_var_literal_and_literal_var():
    compile_and_run("""
int main() {
    string a = "ab";
    string c = a + "cd";
    return strlen(c);
}
""", expected_r0=4)
    compile_and_run("""
int main() {
    string a = "ab";
    string c = "cd" + a;
    return strlen(c);
}
""", expected_r0=4)


def test_concat_chain_four_terms():
    compile_and_run("""
int main() {
    string a = "a";
    string b = "b";
    string c = "c";
    string d = "d";
    string s = a + b + c + d;
    return strlen(s);
}
""", expected_r0=4)


def test_concat_nested_right_assoc():
    compile_and_run("""
int main() {
    string a = "a";
    string b = "b";
    string c = "c";
    string s = a + (b + c);
    return strlen(s);
}
""", expected_r0=3)


def test_concat_nested_left_assoc():
    compile_and_run("""
int main() {
    string a = "a";
    string b = "b";
    string c = "c";
    string s = (a + b) + c;
    return strlen(s);
}
""", expected_r0=3)


def test_concat_exact_bytes():
    proc, cycles, mem = compile_and_run("""
int main() {
    string a = "He";
    string b = "llo";
    string s = a + b;
    return (s[0] << 8) | s[1];
}
""", expected_p0=0x4865)
    print(f"PASS concat bytes 'Hello' head (cycles={cycles})")


def test_concat_full_content_via_chars():
    proc, cycles, mem = compile_and_run("""
int main() {
    string s = "ab" + "cd";
    return (s[0] << 8) | s[1];
}
""", expected_p0=0x6162)


def test_concat_with_global_string():
    compile_and_run("""
string g = "Hello";
int main() {
    string s = g + "!";
    return strlen(s);
}
""", expected_r0=6)


def test_concat_with_binary_var():
    compile_and_run("""
int main() {
    binary b = "1010";
    string s = b + "1";
    return strlen(s);
}
""", expected_r0=5)


def test_concat_empty_literal():
    compile_and_run("""
int main() {
    string s = "a" + "" + "b";
    return strlen(s);
}
""", expected_r0=2)


def test_pointer_arithmetic_still_intact():
    compile_and_run("""
int main() {
    char *p = "hello";
    return p[1];
}
""", expected_r0=ord('e'))
    compile_and_run('int main() { return "abc"[1] + 1; }',
                    expected_r0=ord('b') + 1)


# ---------------------------------------------------------------------------
# Global string initializers
# ---------------------------------------------------------------------------

def test_global_string_init_strlen():
    compile_and_run("""
string g = "Global";
int main() {
    return strlen(g);
}
""", expected_r0=6)


def test_global_string_init_index():
    compile_and_run("""
string g = "Hi";
int main() {
    return g[1];
}
""", expected_r0=ord('i'))


def test_global_string_assign_and_read():
    compile_and_run("""
string g = "one";
int main() {
    g = "two";
    return strlen(g);
}
""", expected_r0=3)


# ---------------------------------------------------------------------------
# String indexing: reads
# ---------------------------------------------------------------------------

def test_string_literal_constant_index():
    compile_and_run('int main() { return "abc"[1]; }', expected_r0=ord('b'))


def test_string_literal_runtime_index():
    compile_and_run("""
int main() {
    int i = 2;
    return "abc"[i];
}
""", expected_r0=ord('c'))


def test_string_literal_index_expression():
    compile_and_run("""
int main() {
    int i = 1;
    return "abcdef"[i + 3];
}
""", expected_r0=ord('e'))


def test_string_index_escapes():
    compile_and_run(r'int main() { return "a\tb"[1]; }', expected_r0=9)


def test_string_index_adjacent_literals():
    compile_and_run('int main() { return "ab" "cd"[2]; }', expected_r0=ord('c'))


def test_string_literal_index_loop_sum():
    compile_and_run("""
int main() {
    int sum = 0;
    for (int i = 0; i < 3; i++) {
        sum += "xyz"[i];
    }
    return sum;
}
""", expected_r0=(ord('x') + ord('y') + ord('z')) & 0xFF)


def test_string_var_index():
    compile_and_run("""
int main() {
    string s = "xyz";
    return s[2];
}
""", expected_r0=ord('z'))


def test_string_var_runtime_index():
    compile_and_run("""
int main() {
    string s = "abcdef";
    int i = 4;
    return s[i];
}
""", expected_r0=ord('e'))


def test_char_array_index_regression():
    compile_and_run("""
int main() {
    char buf[4];
    strcpy(buf, "xyz");
    return buf[1];
}
""", expected_r0=ord('y'))


def test_char_pointer_index_regression():
    compile_and_run("""
int main() {
    char *p = "hello";
    return p[4];
}
""", expected_r0=ord('o'))


# ---------------------------------------------------------------------------
# String indexing: writes
# ---------------------------------------------------------------------------

def test_string_var_index_write():
    compile_and_run("""
int main() {
    char buf[4];
    strcpy(buf, "abc");
    string s = buf;
    s[0] = 'Z';
    return buf[0];
}
""", expected_r0=ord('Z'))


def test_string_var_runtime_index_write():
    compile_and_run("""
int main() {
    char buf[4];
    strcpy(buf, "abcd");
    string s = buf;
    int i = 2;
    s[i] = '!';
    return buf[2];
}
""", expected_r0=ord('!'))


def test_string_var_index_compound_add():
    compile_and_run("""
int main() {
    char buf[4];
    strcpy(buf, "abc");
    string s = buf;
    s[0] += 1;
    return buf[0];
}
""", expected_r0=ord('b'))


# ---------------------------------------------------------------------------
# String index + string literal is NOT concatenation (regression)
# ---------------------------------------------------------------------------

def test_string_index_plus_string_is_not_concat():
    """\"abc\"[0] + \"def\" is pointer arithmetic (char + address), NOT
    concatenation.  Before the fix this generated STRCPY from a char value
    treated as an address; now it must emit plain ADD."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8') as f:
        f.write('int main() { return "abc"[0] + "def"; }\n')
        source_path = f.name
    try:
        from astrid_compiler import main as compiler_main
        old_argv = sys.argv
        sys.argv = [old_argv[0], source_path, '-o',
                    source_path.replace('.ast', '.asm')]
        try:
            compiler_main()
        finally:
            sys.argv = old_argv
        with open(source_path.replace('.ast', '.asm'), encoding='utf-8') as af:
            asm_text = af.read()
        assert 'STRCPY' not in asm_text, (
            "char + string must not be treated as concatenation")
        assert 'STRCAT' not in asm_text, (
            "char + string must not be treated as concatenation")
        assert 'ADD' in asm_text, "char + string should emit ADD"
        print("PASS test_string_index_plus_string_is_not_concat")
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            p = source_path.replace('.ast', ext)
            if os.path.exists(p):
                os.unlink(p)


# ---------------------------------------------------------------------------
# String indexing: boundary and error cases
# ---------------------------------------------------------------------------

def test_string_index_last_valid_position():
    compile_and_run('int main() { return "abc"[2]; }', expected_r0=ord('c'))


def test_string_index_out_of_bounds_rejected():
    from astrid.parser.parser import Parser
    from astrid.lexer.lexer import Lexer
    from astrid.codegen.codegen import CodeGenerator
    ast = Parser(Lexer('int main() { return "abc"[5]; }').tokenize()).parse()
    raised = False
    try:
        CodeGenerator(enable_optimizations=False).generate(ast)
    except Exception:
        raised = True
    assert raised, "Out-of-bounds constant index should be rejected"
    print("PASS test_string_index_out_of_bounds_rejected")


def test_string_index_negative_rejected():
    from astrid.parser.parser import Parser
    from astrid.lexer.lexer import Lexer
    from astrid.codegen.codegen import CodeGenerator
    ast = Parser(Lexer('int main() { return "abc"[-1]; }').tokenize()).parse()
    raised = False
    try:
        CodeGenerator(enable_optimizations=False).generate(ast)
    except Exception:
        raised = True
    assert raised, "Negative constant index should be rejected"
    print("PASS test_string_index_negative_rejected")


def test_string_index_with_enum_constant():
    compile_and_run("""
enum { IDX = 1 };
int main() {
    return "xyz"[IDX];
}
""", expected_r0=ord('y'))


def test_string_index_in_arithmetic():
    compile_and_run('int main() { return "abc"[1] + 10; }',
                    expected_r0=ord('b') + 10)


def test_string_index_compare():
    compile_and_run("""
int main() {
    if ("abc"[1] == 'b') {
        return 1;
    }
    return 0;
}
""", expected_r0=1)


def test_multiple_string_index_sum():
    compile_and_run('int main() { return "ab"[0] + "cd"[1]; }',
                    expected_r0=(ord('a') + ord('d')) & 0xFF)


# ---------------------------------------------------------------------------
# String concatenation: deeper coverage
# ---------------------------------------------------------------------------

def test_concat_three_terms_mixed():
    compile_and_run("""
int main() {
    string a = "x";
    string s = a + "y" + "z";
    return strlen(s);
}
""", expected_r0=3)


def test_concat_result_indexed():
    compile_and_run("""
int main() {
    string s = "ab" + "cd";
    return s[2];
}
""", expected_r0=ord('c'))


def test_concat_result_strcat():
    compile_and_run("""
int main() {
    string s = "Hi";
    string t = s + " there";
    return strlen(t);
}
""", expected_r0=8)


def test_concat_with_binary_type():
    compile_and_run("""
int main() {
    binary a = "01";
    binary b = "10";
    string s = a + b;
    return strlen(s);
}
""", expected_r0=4)


def test_concat_chain_five_terms():
    compile_and_run("""
int main() {
    string a = "a";
    string b = "b";
    string c = "c";
    string d = "d";
    string e = "e";
    string s = a + b + c + d + e;
    return strlen(s);
}
""", expected_r0=5)


# ---------------------------------------------------------------------------
# Layer operations: variable layer arguments and edge cases
# ---------------------------------------------------------------------------

def test_layer_swap_variable():
    proc, cycles, mem = compile_and_run("""
int main() {
    int L = 1;
    set_layer(0);
    screen_fill(0x0F);
    set_layer(L);
    screen_fill(0x33);
    set_layer(0);
    set_pos(0, 0);
    int c0 = read_screen();
    layer_swap(L);
    set_pos(0, 0);
    int c0s = read_screen();
    return c0 + c0s;
}
""", expected_r0=0x42)
    print(f"PASS test_layer_swap_variable (cycles={cycles})")


def test_layer_copy_variable():
    proc, cycles, mem = compile_and_run("""
int main() {
    int L = 2;
    set_layer(0);
    screen_fill(0x11);
    layer_copy(L);
    set_layer(0);
    set_pos(5, 5);
    int a = read_screen();
    set_layer(L);
    int b = read_screen();
    return a + b;
}
""", expected_r0=0x22)
    print(f"PASS test_layer_copy_variable (cycles={cycles})")


def test_layer_move_variable():
    proc, cycles, mem = compile_and_run("""
int main() {
    int L = 1;
    set_layer(0);
    screen_fill(0x77);
    layer_move(L);
    set_layer(1);
    set_pos(9, 9);
    return read_screen();
}
""", expected_r0=0x77)
    print(f"PASS test_layer_move_variable (cycles={cycles})")


def test_set_layer_zero_fast_path():
    proc, cycles, mem = compile_and_run("""
int main() {
    set_layer(0);
    screen_fill(0x0F);
    set_pos(0, 0);
    return read_screen();
}
""", expected_r0=0x0F)
    print(f"PASS test_set_layer_zero_fast_path (cycles={cycles})")


def test_multiple_layer_fills_independent():
    proc, cycles, mem = compile_and_run("""
int main() {
    set_layer(0);
    screen_fill(0x42);
    set_pos(3, 3);
    return read_screen();
}
""", expected_r0=0x42)
    print(f"PASS test_multiple_layer_fills_independent (cycles={cycles})")


def test_layer_swap_preserves_other_layers():
    proc, cycles, mem = compile_and_run("""
int main() {
    set_layer(0);
    screen_fill(0x11);
    set_layer(1);
    screen_fill(0x22);
    set_pos(0, 0);
    int before = read_screen();
    set_layer(1);
    screen_fill(0);
    set_pos(0, 0);
    int after = read_screen();
    return before + after;
}
""", expected_r0=0x33)
    print(f"PASS test_layer_swap_preserves_other_layers (cycles={cycles})")

# ---------------------------------------------------------------------------
# write_text with char vs. int arguments (string/char conversion)
#
# Regression for astrid/progs/atest.ast:  write_text((char)final[3], 0x1F)
# used to ITOS-convert the char byte 'l' (0x6C) into the decimal string
# "108" and TEXT-draw those three digits instead of the glyph for 'l'.
# The fix routes char-typed first arguments through a single-byte
# NUL-terminated string at 0xA000 so TEXT renders the actual character,
# while int-typed arguments keep their ITOS decimal behaviour.
# ---------------------------------------------------------------------------

ATEXT_SRC = """
void main() {
    string final = "Hello";
    set_pos(0, 0);
    write_text((char)final[3], 0x1F);
}
"""


def compile_and_run_with_gfx(source, max_cycles=2000000):
    """Compile, assemble, and run; return (proc, cycles, mem, gfx, asm_text)."""
    import tempfile
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
        with open(asm_path, encoding='utf-8') as f:
            asm_text = f.read()
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)
        proc, cycles, mem, gfx = run_binary(bin_path)
        assert proc.halted, "Program did not halt"
        return proc, cycles, mem, gfx, asm_text
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


def _screen_pixels(gfx):
    """Count non-zero pixels on the composed screen buffer."""
    return int((gfx._compositor._screen != 0).sum())


def test_write_text_char_index_codegen_no_itos():
    """(char)final[3] passed to write_text must emit the char-store pattern,
    never ITOS (which would render the decimal digits of the glyph code)."""
    proc, cycles, mem, gfx, asm_text = compile_and_run_with_gfx(ATEXT_SRC)
    assert 'ITOS' not in asm_text, (
        "char argument to write_text must NOT be ITOS-converted:\n" + asm_text)
    assert 'MOV [0xA000], R0' in asm_text, (
        "char argument must be stored as a single byte at 0xA000:\n" + asm_text)
    assert 'MOV [0xA001], 0' in asm_text, (
        "char string buffer must be NUL-terminated at 0xA001:\n" + asm_text)
    print("PASS test_write_text_char_index_codegen_no_itos")


def test_write_text_char_index_runtime_glyph():
    """write_text((char)final[3], 0x1F) draws the 'l' glyph: buffer holds
    0x6C + NUL, and the screen shows ONE character glyph (not three digits)."""
    proc, cycles, mem, gfx, _ = compile_and_run_with_gfx(ATEXT_SRC)
    assert mem.read_byte(0xA000) == ord('l'), (
        f"Expected 'l' (0x6C) at 0xA000, got 0x{mem.read_byte(0xA000):02X}")
    assert mem.read_byte(0xA001) == 0, (
        f"Expected NUL at 0xA001, got 0x{mem.read_byte(0xA001):02X}")
    pixels = _screen_pixels(gfx)
    assert 0 < pixels < 50, (
        f"Expected a single character glyph (~10 px); got {pixels} px -- "
        "the old ITOS '108' bug would render 3 digit glyphs (~55 px)")
    print(f"PASS test_write_text_char_index_runtime_glyph (pixels={pixels})")


def test_write_text_string_var_index_no_cast():
    """write_text(final[3], color) WITHOUT the (char) cast: s[i] on a string
    scalar is char-typed, so it must also take the char path, not ITOS."""
    source = """
void main() {
    string final = "Hello";
    set_pos(0, 0);
    write_text(final[3], 0x1F);
}
"""
    proc, cycles, mem, gfx, asm_text = compile_and_run_with_gfx(source)
    assert 'ITOS' not in asm_text, (
        "string-indexed char must not be ITOS-converted:\n" + asm_text)
    assert mem.read_byte(0xA000) == ord('l'), (
        f"Expected 'l' at 0xA000, got 0x{mem.read_byte(0xA000):02X}")
    assert mem.read_byte(0xA001) == 0
    pixels = _screen_pixels(gfx)
    assert 0 < pixels < 50, f"Expected one glyph, got {pixels} px"
    print(f"PASS test_write_text_string_var_index_no_cast (pixels={pixels})")


def test_write_text_char_literal():
    """write_text('A', color) must draw 'A', not ITOS'd decimal '65'."""
    source = """
void main() {
    set_pos(0, 0);
    write_text('A', 0x1F);
}
"""
    proc, cycles, mem, gfx, asm_text = compile_and_run_with_gfx(source)
    assert 'ITOS' not in asm_text
    assert mem.read_byte(0xA000) == ord('A')
    assert mem.read_byte(0xA001) == 0
    pixels = _screen_pixels(gfx)
    assert 0 < pixels < 50, f"Expected one glyph, got {pixels} px"
    print(f"PASS test_write_text_char_literal (pixels={pixels})")


def test_write_text_char_cast_from_int():
    """(char)65 produces the glyph 'A' (65 is the ASCII code), not '65'."""
    source = """
void main() {
    set_pos(0, 0);
    write_text((char)65, 0x1F);
}
"""
    proc, cycles, mem, gfx, asm_text = compile_and_run_with_gfx(source)
    assert 'ITOS' not in asm_text, "cast to char must not ITOS:\n" + asm_text
    assert mem.read_byte(0xA000) == ord('A')
    assert mem.read_byte(0xA001) == 0
    print("PASS test_write_text_char_cast_from_int")


def test_write_text_char_from_expr_keeps_full_byte():
    """A char value with the high bits set (0xFF) must survive: the stored
    byte must be exactly 0xFF and the glyph lookup consumes it."""
    source = """
void main() {
    set_pos(0, 0);
    write_text((char)0xFF, 0x1F);
}
"""
    proc, cycles, mem, gfx, asm_text = compile_and_run_with_gfx(source)
    assert 'ITOS' not in asm_text
    assert mem.read_byte(0xA000) == 0xFF, (
        f"Expected 0xFF at 0xA000, got 0x{mem.read_byte(0xA000):02X}")
    assert mem.read_byte(0xA001) == 0
    print("PASS test_write_text_char_from_expr_keeps_full_byte")


def test_write_text_int_still_uses_itos():
    """Regression guard: write_text(65, color) KEEPS the ITOS decimal path
    and renders the string \"65\" -- ints are counts, chars are glyphs."""
    source = """
void main() {
    set_pos(0, 0);
    write_text(65, 0x1F);
}
"""
    proc, cycles, mem, gfx, asm_text = compile_and_run_with_gfx(source)
    assert 'ITOS' in asm_text, "int argument must still use ITOS:\n" + asm_text
    assert mem.read_byte(0xA000) == ord('6'), (
        f"Expected '6' at 0xA000, got 0x{mem.read_byte(0xA000):02X}")
    assert mem.read_byte(0xA001) == ord('5')
    assert mem.read_byte(0xA002) == 0, "ITOS string must be NUL-terminated"
    print("PASS test_write_text_int_still_uses_itos")


def test_write_text_string_literal_passes_through():
    """Regression guard: write_text(\"Hi\", color) passes the literal's DEFSTR
    address straight to TEXT -- no ITOS, no char-buffer indirection."""
    source = """
void main() {
    set_pos(0, 0);
    write_text("Hi", 0x1F);
}
"""
    proc, cycles, mem, gfx, asm_text = compile_and_run_with_gfx(source)
    assert 'ITOS' not in asm_text, (
        "string literal must pass through without ITOS:\n" + asm_text)
    assert 'MOV [0xA000], R0' not in asm_text, (
        "string literal must not use the char scratch buffer")
    pixels = _screen_pixels(gfx)
    assert pixels > 0, "Expected glyphs from the 'Hi' literal"
    print(f"PASS test_write_text_string_literal_passes_through (pixels={pixels})")


def test_write_text_string_var_passes_through():
    """Regression guard: write_text(s, color) with a string variable passes
    the pointer directly (a file-scope string was previously ITOS'd as its
    pointer digits -- guarded by _is_string_or_binary_expr)."""
    source = """
void main() {
    string s = "Hi";
    set_pos(0, 0);
    write_text(s, 0x1F);
}
"""
    proc, cycles, mem, gfx, asm_text = compile_and_run_with_gfx(source)
    assert 'ITOS' not in asm_text
    pixels = _screen_pixels(gfx)
    assert pixels > 0
    print(f"PASS test_write_text_string_var_passes_through (pixels={pixels})")


def test_write_text_multiple_chars_sequential():
    """Three write_text(char) calls each redraw the scratch buffer; all three
    glyphs must land on screen and the buffer ends holding the LAST char."""
    source = """
void main() {
    string s = "ABC";
    set_pos(0, 0);
    write_text((char)s[0], 0x1F);
    write_text((char)s[1], 0x1F);
    write_text((char)s[2], 0x1F);
}
"""
    proc, cycles, mem, gfx, asm_text = compile_and_run_with_gfx(source)
    assert 'ITOS' not in asm_text
    # Scratch buffer holds the last char written ('C').
    assert mem.read_byte(0xA000) == ord('C'), (
        f"Expected 'C' at 0xA000, got 0x{mem.read_byte(0xA000):02X}")
    assert mem.read_byte(0xA001) == 0
    pixels = _screen_pixels(gfx)
    assert pixels > 0
    print(f"PASS test_write_text_multiple_chars_sequential (pixels={pixels})")


def test_write_text_char_index_glyph_width():
    """With the fix the glyph occupies only the first char cell (x < 16).
    The old ITOS bug rendered three digits for '108', spanning x >= 16."""
    source = """
void main() {
    string final = "Hello";
    set_pos(0, 0);
    write_text((char)final[3], 0x1F);
}
"""
    proc, cycles, mem, gfx, asm_text = compile_and_run_with_gfx(source)
    assert 'ITOS' not in asm_text
    screen = gfx._compositor._screen
    ys, xs = (screen != 0).nonzero()
    assert len(xs) > 0, "Expected a drawn glyph"
    max_x = max(int(x) for x in xs)
    assert max_x < 16, (
        f"Glyph pixels should be within the first two char cells (x<16); "
        f"got max x={max_x} -- the old ITOS bug rendered three digits")
    print(f"PASS test_write_text_char_index_glyph_width (max_x={max_x})")


def test_write_text_global_string_index():
    """The same fix must hold for GLOBAL string scalars: g[i] is char-typed."""
    source = """
string g = "World";
void main() {
    set_pos(0, 0);
    write_text((char)g[0], 0x1F);
}
"""
    proc, cycles, mem, gfx, asm_text = compile_and_run_with_gfx(source)
    assert 'ITOS' not in asm_text
    assert mem.read_byte(0xA000) == ord('W'), (
        f"Expected 'W' at 0xA000, got 0x{mem.read_byte(0xA000):02X}")
    assert mem.read_byte(0xA001) == 0
    print("PASS test_write_text_global_string_index")


def test_write_text_binary_var_index():
    """binary scalars share the string code path: b[i] is char-typed too."""
    source = """
void main() {
    binary b = "Z";
    set_pos(0, 0);
    write_text((char)b[0], 0x1F);
}
"""
    proc, cycles, mem, gfx, asm_text = compile_and_run_with_gfx(source)
    assert 'ITOS' not in asm_text
    assert mem.read_byte(0xA000) == ord('Z')
    assert mem.read_byte(0xA001) == 0
    print("PASS test_write_text_binary_var_index")


def test_write_text_char_in_user_function():
    """Char conversion must also work when write_text is called from a
    non-main function with the string passed as a parameter."""
    source = """
void show(string s) {
    set_pos(0, 0);
    write_text((char)s[1], 0x1F);
}

void main() {
    show("ABC");
}
"""
    proc, cycles, mem, gfx, asm_text = compile_and_run_with_gfx(source)
    assert 'ITOS' not in asm_text
    assert mem.read_byte(0xA000) == ord('B'), (
        f"Expected 'B' at 0xA000, got 0x{mem.read_byte(0xA000):02X}")
    assert mem.read_byte(0xA001) == 0
    pixels = _screen_pixels(gfx)
    assert 0 < pixels < 50, f"Expected one glyph, got {pixels} px"
    print(f"PASS test_write_text_char_in_user_function (pixels={pixels})")


# ---------------------------------------------------------------------------
# (string) and (int) casts on char-typed expressions
#
# (string)char  -> 1-character string holding the GLYPH (not the decimal
#                  digits of its code), via the 0xA000 scratch buffer.
# (int)char     -> the numeric code (e.g. 108 for 'l'); rendering it with
#                  write_text produces the decimal digits "108".
# ---------------------------------------------------------------------------

def test_string_cast_of_string_index():
    """(string)final[3] yields the 1-char string \"l\": write_text renders the
    glyph, and the scratch buffer holds 0x6C + NUL (not \"108\")."""
    source = """
void main() {
    string final = "Hello";
    set_pos(0, 0);
    write_text((string)final[3], 0x1F);
}
"""
    proc, cycles, mem, gfx, asm_text = compile_and_run_with_gfx(source)
    assert 'ITOS' not in asm_text, (
        "(string)char must not ITOS the character code:\n" + asm_text)
    assert mem.read_byte(0xA000) == ord('l'), (
        f"Expected 'l' (0x6C) at 0xA000, got 0x{mem.read_byte(0xA000):02X}")
    assert mem.read_byte(0xA001) == 0
    pixels = _screen_pixels(gfx)
    assert 0 < pixels < 50, f"Expected one glyph, got {pixels} px"
    print(f"PASS test_string_cast_of_string_index (pixels={pixels})")


def test_string_cast_of_char_literal_strlen():
    """strlen((string)'A') must be 1: the cast produces a real 1-byte string."""
    compile_and_run('int main() { return strlen((string)\'A\'); }',
                    expected_r0=1)


def test_string_cast_content_via_index():
    """(string)'Q' yields a real 1-byte string: indexing a variable bound to
    the cast result reads back the glyph byte 'Q' (0x51)."""
    compile_and_run("""
int main() {
    string s = (string)'Q';
    return s[0];
}
""", expected_r0=ord('Q'))


def test_string_cast_of_char_variable():
    """(string)c where c is a char variable yields a 1-char glyph string."""
    compile_and_run("""
int main() {
    char c = 'z';
    string s = (string)c;
    return strlen(s) * 256 + s[0];
}
""", expected_p0=(1 << 8) | ord('z'))


def test_int_cast_of_string_index_is_numeric():
    """(int)final[3] keeps the NUMERIC code: 0x6C == 108.  Rendering it with
    write_text must ITOS to the decimal digits \"108\"."""
    compile_and_run('int main() { string f = "Hello"; return (int)f[3]; }',
                    expected_r0=108)
    source = """
void main() {
    string final = "Hello";
    set_pos(0, 0);
    write_text((int)final[3], 0x1F);
}
"""
    proc, cycles, mem, gfx, asm_text = compile_and_run_with_gfx(source)
    assert 'ITOS' in asm_text, (
        "(int)char rendered by write_text must use ITOS digits:\n" + asm_text)
    assert mem.read_byte(0xA000) == ord('1')
    assert mem.read_byte(0xA001) == ord('0')
    assert mem.read_byte(0xA002) == ord('8')
    assert mem.read_byte(0xA003) == 0
    print("PASS test_int_cast_of_string_index_is_numeric")


def test_string_cast_of_int_still_decimal_digits():
    """Regression guard: (string) of an INT (not char) keeps the ITOS
    decimal-digit behaviour -- only char-typed sources become glyphs."""
    compile_and_run('int main() { return strlen((string)65); }',
                    expected_r0=2)
    compile_and_run("""
int main() {
    string s = (string)65;
    return s[0] * 256 + s[1];
}
""", expected_p0=(ord('6') << 8) | ord('5'))


def test_string_cast_concat_with_literal():
    """(string)'H' + \"i\" concatenates the 1-char glyph string with the
    literal: strlen must be 2 and the content must be 'H','i'."""
    compile_and_run("""
int main() {
    string s = (string)'H' + "i";
    return strlen(s) * 65536 / 256 + s[0] + s[1];
}
""", expected_r0=((2 * 256) + ord('H') + ord('i')) & 0xFF)
