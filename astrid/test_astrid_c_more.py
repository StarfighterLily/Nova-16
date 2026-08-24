"""Tests for additional C-language features added to the Astrid compiler.

Covers:
1. Pointer indexing: p[i] read/write on int* and char* (subscript
   semantics with pointee-size scaling).
2. Pointer arithmetic scaling: p + n / p - n (constant AND variable
   offsets), p += n, ++p/--p, p++/p--.
3. Deref increment/decrement: (*p)++ and ++(*p).
4. enum declarations: auto-increment values, explicit values, negative
   values, use in expressions, case labels, array sizes, and global
   initializers.
5. Adjacent string literal concatenation ("abc" "def").
6. Extended escape sequences (\a \b \f \v).
7. sizeof(arrayVariable) returning total byte count (local and global).
8. C type qualifiers/modifiers: signed, unsigned, long, short, register,
   volatile, extern, static, inline (accepted; normalized to base types).
9. Global pointer variables.
"""
import os
import sys

import pytest

# Add project root and astrid dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nova_main import initialize_system
from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser


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


def compile_and_run(source, expected_r0=None, expected_p0=None):
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
        if expected_p0 is not None:
            assert proc.p0 == expected_p0, f"Expected P0={expected_p0}, got {proc.p0}"
        return proc, cycles, mem
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


# ---------------------------------------------------------------------------
# Parser-level tests
# ---------------------------------------------------------------------------

def test_parser_enum_constants():
    """enum declarations record name -> value mappings."""
    lexer = Lexer("enum Color { RED, GREEN = 5, BLUE }; void main() { }")
    ast = Parser(lexer.tokenize()).parse()
    assert ast.enum_constants == {'RED': 0, 'GREEN': 5, 'BLUE': 6}


def test_parser_enum_negative_and_char_values():
    """Enum explicit values may be negative numbers or char literals."""
    lexer = "enum T { A = -3, B, C = 'Z' }; void main() { }"
    ast = Parser(Lexer(lexer).tokenize()).parse()
    assert ast.enum_constants == {'A': -3, 'B': -2, 'C': 90}


def test_parser_string_concatenation():
    """Adjacent string literals merge into one literal."""
    lexer = 'int main() { return strlen("Hello" " World"); }'
    ast = Parser(lexer and Lexer(lexer).tokenize()).parse()
    ret = ast.functions[0].body[0]
    from astrid.parser.parser import FuncCall
    call = ret.value
    assert isinstance(call, FuncCall)
    assert call.args[0].value == "Hello World"


def test_parser_qualifier_normalization():
    """signed/unsigned/long/short normalize to their base type keyword."""
    src = ("unsigned int x;" + chr(10) +
           "static long helper(void) { return 1; }" + chr(10) +
           "void main() { }")
    ast = Parser(Lexer(src).tokenize()).parse()
    names = [f.name for f in ast.functions]
    assert 'helper' in names and 'main' in names
    # The global declaration survived normalization.
    assert len(ast.globals) == 1
    assert ast.globals[0].name == 'x'


# ---------------------------------------------------------------------------
# Runtime tests: pointer indexing
# ---------------------------------------------------------------------------

def test_pointer_indexing_read():
    """p[i] reads element i through an int pointer."""
    source = """
int main() {
    int arr[4] = {11, 22, 33, 44};
    int *p = arr;
    return p[2];
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=33)
    print(f"PASS test_pointer_indexing_read (cycles={cycles}, R0={proc.r0})")


def test_pointer_indexing_write():
    """p[i] = v writes through the pointer into the underlying array."""
    source = """
int main() {
    int arr[3];
    int *p = arr;
    p[0] = 7;
    p[1] = 8;
    p[2] = 9;
    return arr[0] + arr[1] + arr[2];
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=24)
    print(f"PASS test_pointer_indexing_write (cycles={cycles}, R0={proc.r0})")


def test_char_pointer_indexing():
    """char* subscripting addresses single bytes."""
    source = """
int main() {
    char buf[] = "abc";
    char *cp = buf;
    return cp[0] * 100 + cp[2];   // 97*100 + 99 = 9799
}
"""
    proc, cycles, mem = compile_and_run(source, expected_p0=9799)
    print(f"PASS test_char_pointer_indexing (cycles={cycles}, P0={proc.p0})")


def test_pointer_indexing_in_loop():
    """Classic pointer-walk loop over an array."""
    source = """
int main() {
    int arr[5] = {1, 2, 3, 4, 5};
    int *p = arr;
    int sum = 0;
    int i;
    for (i = 0; i < 5; i++) {
        sum += p[i];
    }
    return sum;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=15)
    print(f"PASS test_pointer_indexing_in_loop (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Runtime tests: pointer arithmetic scaling
# ---------------------------------------------------------------------------

def test_pointer_plus_constant_offset():
    """*(p + n) scales the constant offset by the pointee size."""
    source = """
int main() {
    int arr[4] = {10, 20, 30, 40};
    int *p = arr;
    return *(p + 2);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=30)
    print(f"PASS test_pointer_plus_constant_offset (cycles={cycles}, R0={proc.r0})")


def test_pointer_plus_variable_offset():
    """*(p + i) scales a VARIABLE offset by the pointee size."""
    source = """
int main() {
    int arr[4] = {10, 20, 30, 40};
    int *p = arr;
    int i = 3;
    return *(p + i);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=40)
    print(f"PASS test_pointer_plus_variable_offset (cycles={cycles}, R0={proc.r0})")


def test_pointer_compound_add():
    """p += n advances by n elements."""
    source = """
int main() {
    int arr[4] = {10, 20, 30, 40};
    int *p = arr;
    p += 2;
    return *p;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=30)
    print(f"PASS test_pointer_compound_add (cycles={cycles}, R0={proc.r0})")


def test_pointer_prefix_increment():
    """++p advances one ELEMENT (2 bytes for int*)."""
    source = """
int main() {
    int arr[3] = {5, 6, 7};
    int *p = arr;
    ++p;
    return *p;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=6)
    print(f"PASS test_pointer_prefix_increment (cycles={cycles}, R0={proc.r0})")


def test_pointer_postfix_increment():
    """p++ returns the old address but advances one element."""
    source = """
int main() {
    int arr[3] = {5, 6, 7};
    int *p = arr;
    int *q = p++;
    return *q * 10 + *p;   // 5*10 + 6 = 56
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=56)
    print(f"PASS test_pointer_postfix_increment (cycles={cycles}, R0={proc.r0})")


def test_pointer_plus_mirrored_constant():
    """(n + p) — the constant-first form the ExpressionSimplifier
    canonicalizes to — scales identically to (p + n)."""
    source = """
int main() {
    int arr[4] = {10, 20, 30, 40};
    int *p = arr;
    return *(2 + p);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=30)
    print(f"PASS test_pointer_plus_mirrored_constant (cycles={cycles}, R0={proc.r0})")


def test_array_decay_arithmetic():
    """arr + i decays the array to a pointer and scales by elem size."""
    source = """
int main() {
    int arr[3] = {9, 8, 7};
    return *(arr + 1);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=8)
    print(f"PASS test_array_decay_arithmetic (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Runtime tests: deref increment/decrement
# ---------------------------------------------------------------------------

def test_deref_postfix_increment():
    """(*p)++ returns the OLD pointee value and increments in place."""
    source = """
int main() {
    int x = 41;
    int *p = &x;
    int old = (*p)++;
    return old * 10 + x;   // 41*10 + 42 = 452
}
"""
    proc, cycles, mem = compile_and_run(source, expected_p0=452)
    print(f"PASS test_deref_postfix_increment (cycles={cycles}, P0={proc.p0})")


def test_deref_prefix_increment():
    """++(*p) increments the pointee and yields the NEW value."""
    source = """
int main() {
    int x = 41;
    int *p = &x;
    int new_val = ++(*p);
    return new_val * 10 + x;   // 42*10 + 42 = 462
}
"""
    proc, cycles, mem = compile_and_run(source, expected_p0=462)
    print(f"PASS test_deref_prefix_increment (cycles={cycles}, P0={proc.p0})")


# ---------------------------------------------------------------------------
# Runtime tests: enums
# ---------------------------------------------------------------------------

def test_enum_auto_values():
    """Enum constants evaluate to their auto-assigned values."""
    source = """
enum State { OFF, ON, BLINK };

int main() {
    return OFF * 100 + ON * 10 + BLINK;   // 0 + 10 + 2 = 12
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=12)
    print(f"PASS test_enum_auto_values (cycles={cycles}, R0={proc.r0})")


def test_enum_explicit_values():
    """Explicit enum values reset the auto counter (C semantics)."""
    source = """
enum Level { LOW = 10, MID, HIGH = 100 };

int main() {
    return LOW + MID + HIGH;   // 10 + 11 + 100 = 121
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=121)
    print(f"PASS test_enum_explicit_values (cycles={cycles}, R0={proc.r0})")


def test_enum_in_switch():
    """Enum constants work as switch case labels."""
    source = """
enum Cmd { START = 1, STOP, PAUSE };

int main() {
    int action = PAUSE;
    int result = 0;
    switch (action) {
        case START:
            result = 1;
            break;
        case STOP:
            result = 2;
            break;
        case PAUSE:
            result = 3;
            break;
    }
    return result;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=3)
    print(f"PASS test_enum_in_switch (cycles={cycles}, R0={proc.r0})")


def test_enum_as_array_size():
    """Enum constants are valid array sizes."""
    source = """
enum { SIZE = 4 };

int main() {
    int data[SIZE] = {2, 4, 6, 8};
    int sum = 0;
    int i;
    for (i = 0; i < SIZE; i++) {
        sum += data[i];
    }
    return sum;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=20)
    print(f"PASS test_enum_as_array_size (cycles={cycles}, R0={proc.r0})")


def test_enum_in_global_initializer():
    """Global variables can be initialized with enum constants."""
    source = """
enum Config { WIDTH = 64, HEIGHT = 32 };
int screen_w = WIDTH;

int main() {
    return screen_w + HEIGHT;   // 64 + 32 = 96
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=96)
    print(f"PASS test_enum_in_global_initializer (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Runtime tests: string concatenation & escapes
# ---------------------------------------------------------------------------

def test_adjacent_string_concat_runtime():
    """Concatenated literals behave as one string at runtime."""
    source = """
int main() {
    char buf[16];
    strcpy(buf, "Nova" "-" "16");
    return strlen(buf);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=7)
    print(f"PASS test_adjacent_string_concat_runtime (cycles={cycles}, R0={proc.r0})")


def test_extended_escapes():
    """\\a \\b \\f \\v resolve to their ASCII control codes."""
    bs = chr(92)  # backslash, kept out of literals for file encoding safety
    source = (
        "int main() {" + chr(10) +
        "    int a = '" + bs + "a';" + chr(10) +
        "    int b = '" + bs + "b';" + chr(10) +
        "    int f = '" + bs + "f';" + chr(10) +
        "    int v = '" + bs + "v';" + chr(10) +
        "    return a + b + f + v;" + chr(10) +   # 7+8+12+11 = 38
        "}"
    )
    proc, cycles, mem = compile_and_run(source, expected_r0=38)
    print(f"PASS test_extended_escapes (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Runtime tests: sizeof(array)
# ---------------------------------------------------------------------------

def test_sizeof_local_array():
    """sizeof(localArray) is count * elem_size bytes."""
    source = """
int main() {
    int nums[5];
    char text[7];
    return sizeof(nums) * 10 + sizeof(text);   // (5*2)*10 + 7 = 107
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=107)
    print(f"PASS test_sizeof_local_array (cycles={cycles}, R0={proc.r0})")


def test_sizeof_global_array():
    """sizeof(globalArray) is count * elem_size bytes."""
    source = """
int table[6];

int main() {
    return sizeof(table);   // 6 * 2 = 12
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=12)
    print(f"PASS test_sizeof_global_array (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Runtime tests: qualifiers / modifiers
# ---------------------------------------------------------------------------

def test_type_qualifiers_compile_and_run():
    """signed/unsigned/long/short/register/volatile/const/static all parse
    and behave like their base types."""
    source = """
static unsigned int limit = 200;

long compute(register volatile const int base) {
    short int offset = 5;
    unsigned long total = base + offset;
    return total;
}

int main(void) {
    signed int x = -3;
    return limit + compute(x);   // 200 + (-3 + 5) = 202
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=202)
    print(f"PASS test_type_qualifiers_compile_and_run (cycles={cycles}, R0={proc.r0})")


def test_extern_inline_qualifiers():
    """extern/inline qualifiers are accepted on declarations."""
    source = """
extern int shared_counter;

inline int bump(int v) {
    return v + 1;
}

int main() {
    shared_counter = 40;
    return bump(shared_counter);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=41)
    print(f"PASS test_extern_inline_qualifiers (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Runtime tests: global pointers
# ---------------------------------------------------------------------------

def test_global_pointer_variable():
    """Global pointers hold addresses and support deref/indexing."""
    source = """
int gval = 77;
int *gptr;

int main() {
    gptr = &gval;
    *gptr += 3;
    return gval;   // 80
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=80)
    print(f"PASS test_global_pointer_variable (cycles={cycles}, R0={proc.r0})")


def test_global_pointer_indexing():
    """A global pointer can index into a global array."""
    source = """
int data[4] = {5, 10, 15, 20};
int *cursor;

int main() {
    cursor = data;
    cursor[2] = 99;
    return data[0] + data[2];   // 5 + 99 = 104
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=104)
    print(f"PASS test_global_pointer_indexing (cycles={cycles}, R0={proc.r0})")


if __name__ == '__main__':
    test_parser_enum_constants()
    test_parser_enum_negative_and_char_values()
    test_parser_string_concatenation()
    test_parser_qualifier_normalization()
    test_pointer_indexing_read()
    test_pointer_indexing_write()
    test_char_pointer_indexing()
    test_pointer_indexing_in_loop()
    test_pointer_plus_constant_offset()
    test_pointer_plus_variable_offset()
    test_pointer_compound_add()
    test_pointer_plus_mirrored_constant()
    test_pointer_prefix_increment()
    test_pointer_postfix_increment()
    test_array_decay_arithmetic()
    test_deref_postfix_increment()
    test_deref_prefix_increment()
    test_enum_auto_values()
    test_enum_explicit_values()
    test_enum_in_switch()
    test_enum_as_array_size()
    test_enum_in_global_initializer()
    test_adjacent_string_concat_runtime()
    test_extended_escapes()
    test_sizeof_local_array()
    test_sizeof_global_array()
    test_type_qualifiers_compile_and_run()
    test_extern_inline_qualifiers()
    test_global_pointer_variable()
    test_global_pointer_indexing()
    print("All Astrid additional C-feature tests passed!")