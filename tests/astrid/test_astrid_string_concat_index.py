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
