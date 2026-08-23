"""Tests for newly added C-language features in the Astrid compiler.

Covers:
1. Arrays: declaration, indexing (read/write), initializer lists,
   compound assignment on elements, element postfix ++/--, array decay
   to base address for string builtins.
2. Global variables: scalars and arrays, with/without initializers.
3. Ternary conditional operator (?:), including nesting.
4. Prefix increment/decrement (++i / --i) with C semantics.
5. Compound assignment %= (previously raised SyntaxError).
6. Compound shift assignments <<= and >>=.
"""
import os
import sys

import pytest

# Add project root and astrid dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nova_main import initialize_system
from astrid.lexer.lexer import Lexer
from astrid.parser.parser import (
    Parser, ArrayAccess, ArrayAssignment, TernaryOp, PrefixOp, VarDecl,
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

def test_parser_array_declaration():
    """int arr[10]; should produce a VarDecl with array_size."""
    lexer = Lexer("int main() { int arr[10]; return 0; }")
    parser = Parser(lexer.tokenize())
    ast = parser.parse()
    decl = ast.functions[0].body[0]
    assert isinstance(decl, VarDecl)
    assert decl.is_array
    assert int(decl.array_size.value, 0) == 10


def test_parser_array_initializer_list():
    """int arr[3] = {1, 2, 3}; should capture the init list."""
    lexer = Lexer("int main() { int arr[3] = {1, 2, 3}; return 0; }")
    parser = Parser(lexer.tokenize())
    ast = parser.parse()
    decl = ast.functions[0].body[0]
    assert decl.is_array
    assert len(decl.init_list) == 3


def test_parser_array_access_expression():
    """arr[i] should parse as an ArrayAccess node."""
    lexer = Lexer("int main() { return arr[i]; }")
    parser = Parser(lexer.tokenize())
    ast = parser.parse()
    ret = ast.functions[0].body[0]
    assert isinstance(ret.value, ArrayAccess)
    assert ret.value.name == 'arr'


def test_parser_array_assignment():
    """arr[i] = v should parse as an ArrayAssignment statement."""
    lexer = Lexer("int main() { arr[2] = 5; }")
    parser = Parser(lexer.tokenize())
    ast = parser.parse()
    stmt = ast.functions[0].body[0]
    assert isinstance(stmt, ArrayAssignment)
    assert stmt.target.name == 'arr'


def test_parser_ternary_node():
    """a ? b : c should parse as a TernaryOp."""
    lexer = Lexer("int main() { int x = a ? b : c; return x; }")
    parser = Parser(lexer.tokenize())
    ast = parser.parse()
    decl = ast.functions[0].body[0]
    assert isinstance(decl.value, TernaryOp)


def test_parser_prefix_increment_node():
    """++i should parse as a PrefixOp."""
    lexer = Lexer("int main() { int x = ++i; return x; }")
    parser = Parser(lexer.tokenize())
    ast = parser.parse()
    decl = ast.functions[0].body[0]
    assert isinstance(decl.value, PrefixOp)
    assert decl.value.op == '++'


def test_parser_global_variable():
    """Top-level `int g = 5;` should land in Program.globals."""
    lexer = Lexer("int g = 5;\nvoid main() { }")
    parser = Parser(lexer.tokenize())
    ast = parser.parse()
    assert len(ast.globals) == 1
    assert ast.globals[0].name == 'g'
    assert len(ast.functions) == 1


# ---------------------------------------------------------------------------
# Runtime tests: arrays
# ---------------------------------------------------------------------------

def test_local_array_read_write():
    """Local array store/load round-trip through indexed access."""
    source = """
int main() {
    int arr[4];
    arr[0] = 11;
    arr[1] = 22;
    arr[2] = 33;
    arr[3] = 44;
    return arr[0] + arr[1] + arr[2] + arr[3];
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=110)
    print(f"PASS test_local_array_read_write (cycles={cycles}, R0={proc.r0})")


def test_local_array_with_loop_index():
    """Array accessed with a variable index inside a loop."""
    source = """
int main() {
    int arr[8];
    int i;
    for (i = 0; i < 8; i++) {
        arr[i] = i * 2;
    }
    int sum = 0;
    for (i = 0; i < 8; i++) {
        sum += arr[i];
    }
    return sum;
}
"""
    # sum of 0,2,4,...,14 = 56
    proc, cycles, mem = compile_and_run(source, expected_r0=56)
    print(f"PASS test_local_array_with_loop_index (cycles={cycles}, R0={proc.r0})")


def test_local_array_initializer_list():
    """Initializer list fills local array elements at runtime."""
    source = """
int main() {
    int arr[4] = {10, 20, 30, 40};
    return arr[1] + arr[3];
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=60)
    print(f"PASS test_local_array_initializer_list (cycles={cycles}, R0={proc.r0})")


def test_char_array_as_string_buffer():
    """char arrays decay to their base address for string builtins."""
    source = """
int main() {
    char buf[16];
    strcpy(buf, "Hello");
    strcat(buf, "!");
    return strlen(buf);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=6)
    print(f"PASS test_char_array_as_string_buffer (cycles={cycles}, R0={proc.r0})")


def test_array_element_compound_assignment():
    """arr[i] += n and friends operate in place."""
    source = """
int main() {
    int arr[3];
    arr[0] = 100;
    arr[1] = 7;
    arr[2] = 9;
    arr[0] -= 58;      // 42
    arr[1] *= 6;       // 42
    arr[2] <<= 2;      // 36 ... then fix below
    arr[2] >>= 1;      // 18
    arr[2] += 24;      // 42
    return arr[0] + arr[1] + arr[2];
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=126)
    print(f"PASS test_array_element_compound_assignment (cycles={cycles}, R0={proc.r0})")


def test_array_element_postfix_increment():
    """arr[i]++ returns the old value and updates the element."""
    source = """
int main() {
    int arr[2];
    arr[0] = 5;
    arr[1] = 0;
    int old = arr[0]++;
    arr[1] = old;
    return arr[0] * 10 + arr[1];
}
"""
    # arr[0]=6, arr[1]=5 -> 65
    proc, cycles, mem = compile_and_run(source, expected_r0=65)
    print(f"PASS test_array_element_postfix_increment (cycles={cycles}, R0={proc.r0})")


def test_array_in_function_params_scope_isolation():
    """Arrays in different functions do not interfere."""
    source = """
void fill(int arr_idx_unused) {
}

int make_sum() {
    int a[3];
    a[0] = 1;
    a[1] = 2;
    a[2] = 3;
    return a[0] + a[1] + a[2];
}

int main() {
    int b[3];
    b[0] = 10;
    b[1] = 20;
    b[2] = 30;
    int s1 = make_sum();
    return s1 + b[0] + b[1] + b[2];
}
"""
    # 6 + 60 = 66
    proc, cycles, mem = compile_and_run(source, expected_r0=66)
    print(f"PASS test_array_in_function_params_scope_isolation (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Runtime tests: globals
# ---------------------------------------------------------------------------

def test_global_scalar_default_and_init():
    """Globals live at fixed addresses; initializers apply at load time."""
    source = """
int counter;
int start_value = 77;

int main() {
    counter = start_value + 5;
    return counter;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=82)
    print(f"PASS test_global_scalar_default_and_init (cycles={cycles}, R0={proc.r0})")


def test_global_shared_across_functions():
    """Functions read/write the same global storage."""
    source = """
int total;

void add_to_total(int amount) {
    total += amount;
}

int main() {
    add_to_total(10);
    add_to_total(20);
    add_to_total(12);
    return total;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f"PASS test_global_shared_across_functions (cycles={cycles}, R0={proc.r0})")


def test_global_array_with_initializer():
    """Global arrays initialize via DW data at load time."""
    source = """
int table[5] = {2, 4, 6, 8, 10};

int main() {
    int sum = 0;
    int i;
    for (i = 0; i < 5; i++) {
        sum += table[i];
    }
    return sum;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=30)
    print(f"PASS test_global_array_with_initializer (cycles={cycles}, R0={proc.r0})")


def test_global_array_mutation_persists():
    """Writes to global arrays persist across function calls."""
    source = """
int slots[4];

void bump(int idx) {
    slots[idx] += 1;
}

int main() {
    bump(0);
    bump(0);
    bump(3);
    return slots[0] * 10 + slots[3];
}
"""
    # slots[0]=2, slots[3]=1 -> 21
    proc, cycles, mem = compile_and_run(source, expected_r0=21)
    print(f"PASS test_global_array_mutation_persists (cycles={cycles}, R0={proc.r0})")


def test_global_char_array_string_ops():
    """Global char buffers work with string builtins by name."""
    source = """
char msg[32];

int main() {
    strcpy(msg, "Nova");
    return strlen(msg);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=4)
    print(f"PASS test_global_char_array_string_ops (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Runtime tests: ternary operator
# ---------------------------------------------------------------------------

def test_ternary_true_branch():
    source = """
int main() {
    int x = 1 ? 42 : 99;
    return x;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f"PASS test_ternary_true_branch (cycles={cycles}, R0={proc.r0})")


def test_ternary_false_branch():
    source = """
int main() {
    int x = 0 ? 42 : 99;
    return x;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=99)
    print(f"PASS test_ternary_false_branch (cycles={cycles}, R0={proc.r0})")


def test_ternary_with_condition_expression():
    source = """
int main() {
    int a = 7;
    int b = 3;
    int m = a > b ? a : b;
    return m;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=7)
    print(f"PASS test_ternary_with_condition_expression (cycles={cycles}, R0={proc.r0})")


def test_ternary_nested_right_associative():
    """a ? b : c ? d : e parses as a ? b : (c ? d : e)."""
    source = """
int main() {
    int x = 0 ? 1 : 0 ? 22 : 33;
    return x;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=33)
    print(f"PASS test_ternary_nested_right_associative (cycles={cycles}, R0={proc.r0})")


def test_ternary_short_circuit_branches():
    """Only the selected branch executes (side-effect check)."""
    source = """
int calls;

int side(int v) {
    calls += 1;
    return v;
}

int main() {
    int r = 1 ? side(5) : side(50);
    return r * 10 + calls;
}
"""
    # side(5) only -> r=5, calls=1 -> 51
    proc, cycles, mem = compile_and_run(source, expected_r0=51)
    print(f"PASS test_ternary_short_circuit_branches (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Runtime tests: prefix ++/--
# ---------------------------------------------------------------------------

def test_prefix_increment_returns_new_value():
    source = """
int main() {
    int i = 5;
    int x = ++i;
    return x * 10 + i;
}
"""
    # both 6 -> 66
    proc, cycles, mem = compile_and_run(source, expected_r0=66)
    print(f"PASS test_prefix_increment_returns_new_value (cycles={cycles}, R0={proc.r0})")


def test_prefix_decrement_returns_new_value():
    source = """
int main() {
    int i = 5;
    int x = --i;
    return x * 10 + i;
}
"""
    # both 4 -> 44
    proc, cycles, mem = compile_and_run(source, expected_r0=44)
    print(f"PASS test_prefix_decrement_returns_new_value (cycles={cycles}, R0={proc.r0})")


def test_prefix_vs_postfix_difference():
    source = """
int main() {
    int i = 5;
    int pre = ++i;    // i=6, pre=6
    int post = i++;   // post=6, i=7
    return i * 100 + pre * 10 + post;
}
"""
    # 7*100 + 6*10 + 6 = 766
    proc, cycles, mem = compile_and_run(source, expected_r0=254)  # 766 & 0xFF
    assert proc.p0 == 766, f"Expected P0=766, got {proc.p0}"
    print(f"PASS test_prefix_vs_postfix_difference (cycles={cycles}, P0={proc.p0})")


def test_prefix_in_for_update():
    source = """
int main() {
    int sum = 0;
    int i;
    for (i = 0; i < 5; ++i) {
        sum += i;
    }
    return sum;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=10)
    print(f"PASS test_prefix_in_for_update (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Runtime tests: compound assignment fixes
# ---------------------------------------------------------------------------

def test_modulo_compound_assignment():
    """x %= n previously raised SyntaxError; must now work."""
    source = """
int main() {
    int x = 17;
    x %= 5;
    return x;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=2)
    print(f"PASS test_modulo_compound_assignment (cycles={cycles}, R0={proc.r0})")


def test_shift_compound_assignments():
    """x <<= n and x >>= n work."""
    source = """
int main() {
    int x = 3;
    x <<= 4;    // 48
    x >>= 2;    // 12
    return x;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=12)
    print(f"PASS test_shift_compound_assignments (cycles={cycles}, R0={proc.r0})")


def test_bitwise_compound_assignments_on_globals():
    source = """
int flags = 0xF0;

int main() {
    flags |= 0x0F;
    flags &= 0x3C;
    flags ^= 0xFF;
    return flags;
}
"""
    # 0xF0|0x0F=0xFF; 0xFF&0x3C=0x3C; 0x3C^0xFF=0xC3=195
    proc, cycles, mem = compile_and_run(source, expected_r0=0xC3)
    print(f"PASS test_bitwise_compound_assignments_on_globals (cycles={cycles}, R0={proc.r0})")


if __name__ == '__main__':
    test_parser_array_declaration()
    test_parser_array_initializer_list()
    test_parser_array_access_expression()
    test_parser_array_assignment()
    test_parser_ternary_node()
    test_parser_prefix_increment_node()
    test_parser_global_variable()
    test_local_array_read_write()
    test_local_array_with_loop_index()
    test_local_array_initializer_list()
    test_char_array_as_string_buffer()
    test_array_element_compound_assignment()
    test_array_element_postfix_increment()
    test_array_in_function_params_scope_isolation()
    test_global_scalar_default_and_init()
    test_global_shared_across_functions()
    test_global_array_with_initializer()
    test_global_array_mutation_persists()
    test_global_char_array_string_ops()
    test_ternary_true_branch()
    test_ternary_false_branch()
    test_ternary_with_condition_expression()
    test_ternary_nested_right_associative()
    test_ternary_short_circuit_branches()
    test_prefix_increment_returns_new_value()
    test_prefix_decrement_returns_new_value()
    test_prefix_vs_postfix_difference()
    test_prefix_in_for_update()
    test_modulo_compound_assignment()
    test_shift_compound_assignments()
    test_bitwise_compound_assignments_on_globals()
    print("All Astrid C-feature tests passed!")