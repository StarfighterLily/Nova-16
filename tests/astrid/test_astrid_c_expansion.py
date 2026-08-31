"""Tests for newly expanded C-language features in the Astrid compiler.

Covers:
1. Forward references: main() calling functions defined later in the source.
2. C-style prototypes: `int add(int a, int b);` declarations.
3. Empty parameter lists: `int main(void)` and `int main()`.
4. Assignment expressions: chained assignment (`a = b = c`) and assignments
   inside conditions/arguments.
5. C-style string initialization of char arrays: `char buf[] = "Hi";`
   (local and global), including NUL termination and strlen compatibility.
6. sizeof operator: sizeof(int) == 2, sizeof(char) == 1.
7. const qualifier: accepted on globals and locals.
8. Binary (0b) and octal (0o) integer literals.
9. Array parameters: `void f(int arr[], int n)` with decay semantics.
10. Unary plus operator.
11. Basic pointers: declaration (`int *p`), address-of (&x), dereference
    (*p read and *p = v write), pointer arithmetic.
12. Empty statements (`;`).
13. Escape sequences in char/string literals (backslash-n, backslash-0,
    and hex escapes like backslash-x41).
"""
import os
import sys

import pytest

# Path setup handled by tests/astrid/conftest.py

from nova_main import initialize_system
from astrid.lexer.lexer import Lexer
from astrid.parser.parser import (
    Parser, Number, VarDecl, AddressOf, Deref, SizeofExpr,
)


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

def test_parser_address_of_node():
    """&x should parse as an AddressOf node."""
    lexer = Lexer("int main() { int *p = &x; return 0; }")
    ast = Parser(lexer.tokenize()).parse()
    decl = ast.functions[0].body[0]
    assert isinstance(decl.value, AddressOf)


def test_parser_deref_node():
    """*p should parse as a Deref node."""
    lexer = Lexer("int main() { return *p; }")
    ast = Parser(lexer.tokenize()).parse()
    ret = ast.functions[0].body[0]
    assert isinstance(ret.value, Deref)


def test_parser_sizeof_node():
    """sizeof(int) should parse as a SizeofExpr node."""
    lexer = Lexer("int main() { int x = sizeof(int); return x; }")
    ast = Parser(lexer.tokenize()).parse()
    decl = ast.functions[0].body[0]
    assert isinstance(decl.value, SizeofExpr)
    assert decl.value.target == 'int'


def test_parser_pointer_decl_records_depth():
    """`int *p;` should record pointer_depth == 1."""
    lexer = Lexer("int main() { int *p; return 0; }")
    ast = Parser(lexer.tokenize()).parse()
    decl = ast.functions[0].body[0]
    assert isinstance(decl, VarDecl)
    assert decl.pointer_depth == 1
    assert decl.is_pointer


def test_parser_void_param_list():
    """`int main(void)` should produce zero params."""
    lexer = Lexer("int main(void) { return 0; }")
    ast = Parser(lexer.tokenize()).parse()
    assert len(ast.functions) == 1
    assert len(ast.functions[0].params) == 0


def test_parser_array_param():
    """`void f(int arr[], int n)` should mark arr as an array parameter."""
    lexer = Lexer("void f(int arr[], int n) { }")
    ast = Parser(lexer.tokenize()).parse()
    params = ast.functions[0].params
    assert len(params) == 2
    assert params[0].is_array_param
    assert not params[1].is_array_param


def test_parser_prototype_is_skipped():
    """A prototype-only declaration should not appear as a function."""
    # Build source with an explicit newline to keep this file ASCII-safe.
    src = "int add(int a, int b);" + chr(10) + "void main() { }"
    lexer = Lexer(src)
    ast = Parser(lexer.tokenize()).parse()
    names = [f.name for f in ast.functions]
    assert 'add' not in names
    assert 'main' in names


def test_parser_char_string_init_expands_to_chars():
    """char buf[] = "Hi" should expand to CharLiterals + NUL terminator."""
    lexer = Lexer('int main() { char buf[] = "Hi"; return buf[0]; }')
    ast = Parser(lexer.tokenize()).parse()
    decl = ast.functions[0].body[0]
    assert decl.is_array
    assert decl.init_list is not None
    # "Hi" -> 'H', 'i', '\0'
    assert [c.char_value for c in decl.init_list] == [ord('H'), ord('i'), 0]


def test_parser_escape_sequences():
    """Char literal escapes (backslash-n, backslash-0, backslash-xNN)
    should resolve correctly."""
    bs = chr(92)  # backslash character, kept out of literals for safety
    src = ("int main() { char a = '" + bs + "n'; char b = '" + bs + "0'; "
           "char c = '" + bs + "x41'; return 0; }")
    lexer = Lexer(src)
    ast = Parser(lexer.tokenize()).parse()
    body = ast.functions[0].body
    assert body[0].value.char_value == 10   # backslash-n -> newline (10)
    assert body[1].value.char_value == 0    # backslash-0 -> NUL
    assert body[2].value.char_value == 65   # backslash-x41 -> 'A'


# ---------------------------------------------------------------------------
# Runtime tests: forward references & prototypes
# ---------------------------------------------------------------------------

def test_forward_reference_call():
    """main() can call a function defined later in the source."""
    source = """
int main() {
    return helper() + helper2();
}

int helper() {
    return 20;
}

int helper2() {
    return 22;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f"PASS test_forward_reference_call (cycles={cycles}, R0={proc.r0})")


def test_c_style_prototype():
    """C-style prototypes compile and forward calls resolve."""
    source = """
int add(int a, int b);

int main(void) {
    return add(40, 2);
}

int add(int a, int b) {
    return a + b;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f"PASS test_c_style_prototype (cycles={cycles}, R0={proc.r0})")


def test_void_param_list_runs():
    """`int main(void)` compiles and runs."""
    source = """
int main(void) {
    return 77;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=77)
    print(f"PASS test_void_param_list_runs (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Runtime tests: assignment expressions
# ---------------------------------------------------------------------------

def test_chained_assignment():
    """a = b = c assigns right-to-left; both targets get the value."""
    source = """
int main() {
    int a;
    int b;
    a = b = 5;
    return a * 10 + b;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=55)
    print(f"PASS test_chained_assignment (cycles={cycles}, R0={proc.r0})")


def test_assignment_in_condition():
    """if ((x = f()) == val) evaluates the assignment then compares."""
    source = """
int give() {
    return 9;
}

int main() {
    int x;
    if ((x = give()) == 9) {
        return 1;
    }
    return 0;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=1)
    print(f"PASS test_assignment_in_condition (cycles={cycles}, R0={proc.r0})")


def test_compound_assignment_expression_value():
    """Compound assignment used as an expression yields the new value."""
    source = """
int main() {
    int x = 10;
    int y;
    y = (x += 5);
    return y * 100 + x;
}
"""
    # x becomes 15, y = 15 -> 15*100 + 15 = 1515; R0 low byte = 1515 & 0xFF
    proc, cycles, mem = compile_and_run(source, expected_p0=1515)
    print(f"PASS test_compound_assignment_expression_value (cycles={cycles}, P0={proc.p0})")


# ---------------------------------------------------------------------------
# Runtime tests: char array string initialization
# ---------------------------------------------------------------------------

def test_local_char_array_string_init():
    """char buf[] = "Hello" initializes bytes + NUL locally."""
    source = """
int main() {
    char buf[] = "Hello";
    return strlen(buf);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=5)
    print(f"PASS test_local_char_array_string_init (cycles={cycles}, R0={proc.r0})")


def test_global_char_array_string_init():
    """Global char buffers initialize via DB data at load time."""
    source = """
char msg[] = "Nova";

int main() {
    return strlen(msg);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=4)
    print(f"PASS test_global_char_array_string_init (cycles={cycles}, R0={proc.r0})")


def test_sized_char_array_string_init():
    """char buf[16] = "Hi" fills prefix and leaves the rest untouched."""
    source = """
int main() {
    char buf[16] = "Hi";
    strcpy(buf, "Hello");
    return strlen(buf);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=5)
    print(f"PASS test_sized_char_array_string_init (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Runtime tests: sizeof / const / numeric literals
# ---------------------------------------------------------------------------

def test_sizeof_types():
    """sizeof(int)==2, sizeof(char)==1."""
    source = """
int main() {
    int i = sizeof(int);
    char c = sizeof(char);
    return i * 10 + c;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=21)
    print(f"PASS test_sizeof_types (cycles={cycles}, R0={proc.r0})")


def test_sizeof_expression():
    """sizeof(expr) infers the type of the expression."""
    source = """
int main() {
    int x = 5;
    char ch = 7;
    return sizeof(x) * 10 + sizeof(ch);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=21)
    print(f"PASS test_sizeof_expression (cycles={cycles}, R0={proc.r0})")


def test_const_qualifier_globals_and_locals():
    """const variables behave like normal variables."""
    source = """
const int LIMIT = 40;

int main() {
    const int base = 2;
    return LIMIT + base;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f"PASS test_const_qualifier_globals_and_locals (cycles={cycles}, R0={proc.r0})")


def test_binary_literal():
    """0b1010 == 10."""
    source = """
int main() {
    int x = 0b1010;
    return x;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=10)
    print(f"PASS test_binary_literal (cycles={cycles}, R0={proc.r0})")


def test_octal_literal():
    """0o17 == 15."""
    source = """
int main() {
    int x = 0o17;
    return x;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=15)
    print(f"PASS test_octal_literal (cycles={cycles}, R0={proc.r0})")


def test_unary_plus():
    """+x is a no-op."""
    source = """
int main() {
    int x = -5;
    int y = +x;
    return -y;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_p0=5)
    print(f"PASS test_unary_plus (cycles={cycles}, P0={proc.p0})")


def test_empty_statement():
    """Lone ';' compiles to nothing."""
    source = """
int main() {
    ;
    ;
    return 6;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=6)
    print(f"PASS test_empty_statement (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Runtime tests: array parameters
# ---------------------------------------------------------------------------

def test_array_param_sum():
    """Arrays passed by name decay to addresses inside callees."""
    source = """
int sum(int arr[], int n) {
    int total = 0;
    int i;
    for (i = 0; i < n; i++) {
        total += arr[i];
    }
    return total;
}

int main() {
    int data[4] = {10, 20, 30, 40};
    return sum(data, 4);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=100)
    print(f"PASS test_array_param_sum (cycles={cycles}, R0={proc.r0})")


def test_array_param_mutation_visible_to_caller():
    """Writes through an array parameter modify the caller's array."""
    source = """
void fill(int arr[], int n, int v) {
    int i;
    for (i = 0; i < n; i++) {
        arr[i] = v;
    }
}

int main() {
    int data[3];
    fill(data, 3, 7);
    return data[0] + data[1] + data[2];
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=21)
    print(f"PASS test_array_param_mutation_visible_to_caller (cycles={cycles}, R0={proc.r0})")


def test_char_array_param_strlen():
    """char array parameters work with string builtins."""
    source = """
int length(char s[]) {
    return strlen(s);
}

int main() {
    char text[] = "Astrid";
    return length(text);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=6)
    print(f"PASS test_char_array_param_strlen (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Runtime tests: pointers
# ---------------------------------------------------------------------------

def test_pointer_decl_and_read():
    """int *p = &x; *p reads through the pointer."""
    source = """
int main() {
    int x = 42;
    int *p = &x;
    return *p;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f"PASS test_pointer_decl_and_read (cycles={cycles}, R0={proc.r0})")


def test_pointer_write():
    """*p = v writes through the pointer to the pointee."""
    source = """
int main() {
    int x = 0;
    int *p = &x;
    *p = 42;
    return x;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f"PASS test_pointer_write (cycles={cycles}, R0={proc.r0})")


def test_pointer_compound_write():
    """*p += n operates in place through the pointer."""
    source = """
int main() {
    int x = 40;
    int *p = &x;
    *p += 2;
    return x;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f"PASS test_pointer_compound_write (cycles={cycles}, R0={proc.r0})")


def test_pointer_swap_via_function():
    """Classic swap(&a, &b) using pointers as parameters."""
    source = """
void swap(int *pa, int *pb) {
    int tmp = *pa;
    *pa = *pb;
    *pb = tmp;
}

int main() {
    int a = 3;
    int b = 8;
    swap(&a, &b);
    return a * 10 + b;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=83)
    print(f"PASS test_pointer_swap_via_function (cycles={cycles}, R0={proc.r0})")


def test_pointer_arithmetic_walks_array():
    """*(arr + i) addresses element i (pointer arithmetic)."""
    source = """
int main() {
    int arr[3] = {11, 22, 33};
    int *p = arr;
    return *(p + 1);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=22)
    print(f"PASS test_pointer_arithmetic_walks_array (cycles={cycles}, R0={proc.r0})")


def test_pointer_to_global():
    """Pointers can reference global storage."""
    source = """
int counter;

int main() {
    int *p = &counter;
    *p = 55;
    return counter;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=55)
    print(f"PASS test_pointer_to_global (cycles={cycles}, R0={proc.r0})")


def test_address_of_array_element():
    """&arr[i] yields the address of one element."""
    source = """
int main() {
    int arr[3] = {5, 6, 7};
    int *p = &arr[2];
    *p = 99;
    return arr[2];
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=99)
    print(f"PASS test_address_of_array_element (cycles={cycles}, R0={proc.r0})")


def test_returning_pointer_value():
    """Functions can return addresses (16-bit values fit in P0)."""
    source = """
int gval = 123;

int *get_ptr() {
    return &gval;
}

int main() {
    int *p = get_ptr();
    return *p;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=123)
    print(f"PASS test_returning_pointer_value (cycles={cycles}, R0={proc.r0})")


if __name__ == '__main__':
    test_parser_address_of_node()
    test_parser_deref_node()
    test_parser_sizeof_node()
    test_parser_pointer_decl_records_depth()
    test_parser_void_param_list()
    test_parser_array_param()
    test_parser_prototype_is_skipped()
    test_parser_char_string_init_expands_to_chars()
    test_parser_escape_sequences()
    test_forward_reference_call()
    test_c_style_prototype()
    test_void_param_list_runs()
    test_chained_assignment()
    test_assignment_in_condition()
    test_compound_assignment_expression_value()
    test_local_char_array_string_init()
    test_global_char_array_string_init()
    test_sized_char_array_string_init()
    test_sizeof_types()
    test_sizeof_expression()
    test_const_qualifier_globals_and_locals()
    test_binary_literal()
    test_octal_literal()
    test_unary_plus()
    test_empty_statement()
    test_array_param_sum()
    test_array_param_mutation_visible_to_caller()
    test_char_array_param_strlen()
    test_pointer_decl_and_read()
    test_pointer_write()
    test_pointer_compound_write()
    test_pointer_swap_via_function()
    test_pointer_arithmetic_walks_array()
    test_pointer_to_global()
    test_address_of_array_element()
    test_returning_pointer_value()
    print("All Astrid C-expansion tests passed!")