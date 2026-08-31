"""Tests for advanced C-language features in the Astrid compiler.

Covers:
1. Function prototypes / forward declarations: calling functions before definition.
2. Comma operator: (a, b) evaluates a, then b, yielding b.
3. Struct assignment: s1 = s2 copies all fields.
4. Nested switch statements.
5. Complex for loops with break/continue.
6. Edge cases: empty switch, deeply nested ternary.
7. Pointer equivalence and struct member addresses.
8. Array decay in function calls.
9. Global struct variables.
10. Volatile/const qualifiers.
"""
import os
import sys
import tempfile

import pytest

# Path setup handled by tests/astrid/conftest.py

from nova_main import initialize_system
from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser


def run_binary(bin_path, max_cycles=3000000):
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
# Function prototypes / forward declarations
# ---------------------------------------------------------------------------

def test_forward_function_declaration():
    """A function can be called before it is defined (natural in Astrid)."""
    source = """
int add(int a, int b);

int main() {
    return add(3, 4);
}

int add(int a, int b) {
    return a + b;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=7)
    print(f"PASS test_forward_function_declaration (cycles={cycles}, R0={proc.r0})")


def test_mutual_recursion():
    """Two functions calling each other (mutual recursion)."""
    source = """
int is_even(int n);
int is_odd(int n);

int is_even(int n) {
    if (n == 0) return 1;
    return is_odd(n - 1);
}

int is_odd(int n) {
    if (n == 0) return 0;
    return is_even(n - 1);
}

int main() {
    return is_even(4);  // 1 (true)
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=1)
    print(f"PASS test_mutual_recursion (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Comma operator
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Comma operator not yet implemented in parser")
def test_comma_operator_basic():
    """The comma operator evaluates left-to-right, yields the right value."""
    source = """
int main() {
    int x = (5, 10);
    return x;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=10)
    print(f"PASS test_comma_operator_basic (cycles={cycles}, R0={proc.r0})")


@pytest.mark.skip(reason="Comma operator not yet implemented in parser")
def test_comma_operator_with_side_effects():
    """Comma operator with side effects in the left operand."""
    source = """
int main() {
    int a = 0;
    int b = (a = 5, a + 3);
    return b;  // 8
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=8)
    print(f"PASS test_comma_operator_with_side_effects (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Struct assignment
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Struct assignment (b = a) not yet implemented in codegen")
def test_struct_assignment_copies_fields():
    """Assigning one struct variable to another copies all fields."""
    source = """
struct Point { int x; int y; };

int main() {
    struct Point a;
    struct Point b;
    a.x = 10;
    a.y = 20;
    b = a;
    return b.x + b.y;  // 30
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=30)
    print(f"PASS test_struct_assignment_copies_fields (cycles={cycles}, R0={proc.r0})")


@pytest.mark.skip(reason="Struct assignment (b = a) not yet implemented in codegen")
def test_struct_assignment_does_not_alias():
    """After struct assignment, modifying the source does not affect the copy."""
    source = """
struct Point { int x; int y; };

int main() {
    struct Point a;
    struct Point b;
    a.x = 10;
    a.y = 20;
    b = a;
    a.x = 99;
    return b.x;  // still 10
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=10)
    print(f"PASS test_struct_assignment_does_not_alias (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Nested switch statements
# ---------------------------------------------------------------------------

def test_nested_switch():
    """A switch inside a case of another switch."""
    source = """
int main() {
    int x = 1;
    int y = 2;
    int result = 0;
    switch (x) {
        case 1:
            switch (y) {
                case 2:
                    result = 10;
                    break;
                case 3:
                    result = 20;
                    break;
            }
            break;
        case 2:
            result = 30;
            break;
    }
    return result;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=10)
    print(f"PASS test_nested_switch (cycles={cycles}, R0={proc.r0})")


def test_switch_with_variable_case_expression():
    """Switch where the case values use enum constants."""
    source = """
enum Op { OP_ADD = 1, OP_SUB = 2 };

int main() {
    int op = OP_ADD;
    int a = 5;
    int b = 3;
    int result = 0;
    switch (op) {
        case OP_ADD:
            result = a + b;
            break;
        case OP_SUB:
            result = a - b;
            break;
    }
    return result;  // 8
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=8)
    print(f"PASS test_switch_with_variable_case_expression (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Complex for loops with break/continue
# ---------------------------------------------------------------------------

def test_nested_for_loops():
    """Nested for loops compute a sum."""
    source = """
int main() {
    int sum = 0;
    int i;
    int j;
    for (i = 0; i < 3; i++) {
        for (j = 0; j < 4; j++) {
            sum++;
        }
    }
    return sum;  // 12
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=12)
    print(f"PASS test_nested_for_loops (cycles={cycles}, R0={proc.r0})")


def test_break_in_nested_loop():
    """Break only exits the innermost loop."""
    source = """
int main() {
    int count = 0;
    int i;
    int j;
    for (i = 0; i < 5; i++) {
        for (j = 0; j < 5; j++) {
            count++;
            if (j == 2) break;  // breaks inner loop
        }
    }
    // Outer runs 5 times, inner runs 3 times each => 15
    return count;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=15)
    print(f"PASS test_break_in_nested_loop (cycles={cycles}, R0={proc.r0})")


def test_continue_in_nested_loop():
    """Continue skips to the next iteration of the innermost loop."""
    source = """
int main() {
    int sum = 0;
    int i;
    int j;
    for (i = 0; i < 3; i++) {
        for (j = 0; j < 5; j++) {
            if (j == 2) continue;
            sum += j;
        }
    }
    // Each inner loop: 0+1+3+4 = 8, 3 times => 24
    return sum;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=24)
    print(f"PASS test_continue_in_nested_loop (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_switch():
    """An empty switch statement compiles and runs without error."""
    source = """
int main() {
    int x = 5;
    switch (x) {
    }
    return 42;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f"PASS test_empty_switch (cycles={cycles}, R0={proc.r0})")


def test_switch_single_case():
    """A switch with only a single case and no default."""
    source = """
int main() {
    int x = 1;
    int result = 0;
    switch (x) {
        case 1:
            result = 100;
            break;
    }
    return result;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=100)
    print(f"PASS test_switch_single_case (cycles={cycles}, R0={proc.r0})")


def test_deeply_nested_ternary():
    """Ternary operator nested three levels deep."""
    source = """
int main() {
    int a = 1;
    int b = 2;
    int c = 3;
    int result = (a > b) ? 10 : (b > c) ? 20 : (c > a) ? 30 : 40;
    return result;  // 30
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=30)
    print(f"PASS test_deeply_nested_ternary (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Pointer equivalence: *(p + i) == p[i]
# ---------------------------------------------------------------------------

def test_pointer_subscript_equivalence():
    """*(p + i) and p[i] produce the same result."""
    source = """
int main() {
    int arr[4] = {10, 20, 30, 40};
    int *p = arr;
    int a = *(p + 2);  // 30
    int b = p[2];      // 30
    return a + b;       // 60
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=60)
    print(f"PASS test_pointer_subscript_equivalence (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Struct member address
# ---------------------------------------------------------------------------

def test_address_of_struct_member():
    """&s.field yields the address of a struct field."""
    source = """
struct Point { int x; int y; };

int main() {
    struct Point s;
    int *px = &s.x;
    *px = 42;
    return s.x;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f"PASS test_address_of_struct_member (cycles={cycles}, R0={proc.r0})")


def test_address_of_arrow_member():
    """&s->field yields the address of a field via pointer."""
    source = """
struct Point { int x; int y; };

int main() {
    struct Point s;
    struct Point *ps = &s;
    int *py = &ps->y;
    *py = 99;
    return s.y;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=99)
    print(f"PASS test_address_of_arrow_member (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Array decay in function calls
# ---------------------------------------------------------------------------

def test_array_decay_to_pointer():
    """When passing an array to a function, it decays to a pointer."""
    source = """
int sum_array(int *arr, int n) {
    int sum = 0;
    int i;
    for (i = 0; i < n; i++) {
        sum += arr[i];
    }
    return sum;
}

int main() {
    int data[5] = {1, 2, 3, 4, 5};
    return sum_array(data, 5);  // 15
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=15)
    print(f"PASS test_array_decay_to_pointer (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Global struct variables
# ---------------------------------------------------------------------------

def test_global_struct_variable():
    """A global struct variable is accessible from functions."""
    source = """
struct Config { int width; int height; };
struct Config settings;

void init_settings() {
    settings.width = 640;
    settings.height = 480;
}

int main() {
    init_settings();
    return settings.width / 10 + settings.height / 10;  // 64 + 48 = 112
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=112)
    print(f"PASS test_global_struct_variable (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Volatile / const qualifiers (accepted, normalized)
# ---------------------------------------------------------------------------

def test_volatile_qualifier_accepted():
    """The volatile qualifier is accepted and treated like the base type."""
    source = """
volatile int counter = 0;

int main() {
    counter = 42;
    return counter;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f"PASS test_volatile_qualifier_accepted (cycles={cycles}, R0={proc.r0})")


def test_const_qualifier_on_pointer():
    """const int *p is accepted (const is normalized away)."""
    source = """
int main() {
    int x = 10;
    const int *p = &x;
    return *p;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=10)
    print(f"PASS test_const_qualifier_on_pointer (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Complex expressions
# ---------------------------------------------------------------------------

def test_chained_assignment():
    """Chained assignment: a = b = c = 5."""
    source = """
int main() {
    int a;
    int b;
    int c;
    a = b = c = 5;
    return a + b + c;  // 15
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=15)
    print(f"PASS test_chained_assignment (cycles={cycles}, R0={proc.r0})")


def test_complex_condition_with_bitwise():
    """Complex condition combining bitwise and logical operators."""
    source = """
int main() {
    int flags = 0x0F;
    int mask = 0x03;
    if ((flags & mask) == mask || (flags & 0xF0) != 0) {
        return 1;
    }
    return 0;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=1)
    print(f"PASS test_complex_condition_with_bitwise (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Struct with array member
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Struct array field not yet supported by parser")
def test_struct_with_array_member():
    """A struct containing an array member."""
    source = """
struct Buffer { int data[4]; int count; };

int main() {
    struct Buffer buf;
    buf.data[0] = 1;
    buf.data[1] = 2;
    buf.data[2] = 3;
    buf.data[3] = 4;
    buf.count = 4;
    return buf.data[2] + buf.count;  // 3 + 4 = 7
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=7)
    print(f"PASS test_struct_with_array_member (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Enum in struct field
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Enum as struct field not yet supported by parser")
def test_enum_as_struct_field():
    """An enum type used as a struct field."""
    source = """
enum Color { RED = 0, GREEN = 1, BLUE = 2 };

struct Pixel {
    int x;
    int y;
    enum Color c;
};

int main() {
    struct Pixel p;
    p.x = 10;
    p.y = 20;
    p.c = GREEN;
    return p.x + p.y + p.c;  // 10 + 20 + 1 = 31
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=31)
    print(f"PASS test_enum_as_struct_field (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Global array of structs
# ---------------------------------------------------------------------------

def test_global_array_of_structs():
    """A global array of struct values."""
    source = """
struct Item { int id; int value; };

struct Item items[3];

int main() {
    items[0].id = 1;
    items[0].value = 100;
    items[1].id = 2;
    items[1].value = 200;
    items[2].id = 3;
    items[2].value = 300;
    return items[1].value;  // 200
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=200)
    print(f"PASS test_global_array_of_structs (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Do-while with complex condition
# ---------------------------------------------------------------------------

def test_do_while_complex_condition():
    """Do-while loop with a compound condition."""
    source = """
int main() {
    int i = 0;
    int sum = 0;
    do {
        sum += i;
        i++;
    } while (i < 10 && sum < 100);
    return sum;  // 0+1+2+...+9 = 45
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=45)
    print(f"PASS test_do_while_complex_condition (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Function with no parameters (void)
# ---------------------------------------------------------------------------

def test_function_with_void_parameter():
    """A function explicitly declared with void parameters."""
    source = """
int get_answer(void) {
    return 42;
}

int main() {
    return get_answer();
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f"PASS test_function_with_void_parameter (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Long if-else chain (else if ladder)
# ---------------------------------------------------------------------------

def test_else_if_ladder():
    """A long else-if ladder selects the correct branch."""
    source = """
int main() {
    int x = 3;
    int result = 0;
    if (x == 1) {
        result = 10;
    } else if (x == 2) {
        result = 20;
    } else if (x == 3) {
        result = 30;
    } else if (x == 4) {
        result = 40;
    } else {
        result = 50;
    }
    return result;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=30)
    print(f"PASS test_else_if_ladder (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Switch with fallthrough and break
# ---------------------------------------------------------------------------

def test_switch_fallthrough_cases():
    """Multiple cases sharing the same code block via fallthrough."""
    source = """
int main() {
    int x = 2;
    int result = 0;
    switch (x) {
        case 1:
        case 2:
        case 3:
            result = 100;
            break;
        case 4:
            result = 200;
            break;
        default:
            result = 300;
    }
    return result;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=100)
    print(f"PASS test_switch_fallthrough_cases (cycles={cycles}, R0={proc.r0})")


if __name__ == '__main__':
    test_forward_function_declaration()
    test_mutual_recursion()
    # Comma operator tests skipped - not yet implemented
    # Struct assignment tests skipped - not yet implemented
    # Struct array field and enum-as-struct-field tests skipped - not yet supported
    test_nested_switch()
    test_switch_with_variable_case_expression()
    test_nested_for_loops()
    test_break_in_nested_loop()
    test_continue_in_nested_loop()
    test_empty_switch()
    test_switch_single_case()
    test_deeply_nested_ternary()
    test_pointer_subscript_equivalence()
    test_address_of_struct_member()
    test_address_of_arrow_member()
    test_array_decay_to_pointer()
    test_global_struct_variable()
    test_volatile_qualifier_accepted()
    test_const_qualifier_on_pointer()
    test_chained_assignment()
    test_complex_condition_with_bitwise()
    test_global_array_of_structs()
    test_do_while_complex_condition()
    test_function_with_void_parameter()
    test_else_if_ladder()
    test_switch_fallthrough_cases()
    print("All Astrid advanced C-feature tests passed!")