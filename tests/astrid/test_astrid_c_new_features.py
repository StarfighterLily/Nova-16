"""Tests for newly added C-language features in the Astrid compiler.

Covers:
1. Comma operator: (a, b) evaluates a, then b, yielding b.
2. Struct assignment: s1 = s2 copies all fields.
3. typedef: type aliases (typedef int myint;).
4. goto/labels: unconditional jumps to labeled statements.
5. union: overlapping storage (all members share byte offset 0).
"""
import os
import sys

# Path setup handled by tests/astrid/conftest.py

from nova_main import initialize_system
from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser, CommaOp, Goto, Label


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
        Assembler().assemble(asm_path)
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

def test_parser_comma_operator():
    """Comma operator produces a CommaOp AST node."""
    lexer = Lexer("int main() { return (1, 2); }")
    parser = Parser(lexer.tokenize())
    ast = parser.parse()
    ret = ast.functions[0].body[0]
    assert isinstance(ret.value, CommaOp), f"Expected CommaOp, got {type(ret.value).__name__}"
    print("PASS test_parser_comma_operator")


def test_parser_typedef_basic():
    """typedef int myint; records the alias."""
    lexer = Lexer("typedef int myint;\nint main() { return 0; }")
    parser = Parser(lexer.tokenize())
    ast = parser.parse()
    assert 'myint' in ast.type_aliases
    assert ast.type_aliases['myint'] == 'int'
    print("PASS test_parser_typedef_basic")


def test_parser_goto_statement():
    """goto label; produces a Goto AST node."""
    lexer = Lexer("int main() { goto end; return 0; end: return 1; }")
    parser = Parser(lexer.tokenize())
    ast = parser.parse()
    goto_found = any(isinstance(s, Goto) and s.label == 'end' for s in ast.functions[0].body)
    assert goto_found, "Goto node not found"
    print("PASS test_parser_goto_statement")


def test_parser_label_definition():
    """label: stmt produces a Label AST node."""
    lexer = Lexer("int main() { goto end; return 0; end: return 1; }")
    parser = Parser(lexer.tokenize())
    ast = parser.parse()
    label_found = any(isinstance(s, Label) and s.name == 'end' for s in ast.functions[0].body)
    assert label_found, "Label node not found"
    print("PASS test_parser_label_definition")


def test_parser_union_definition():
    """union Tag { int i; char c; }; records the union."""
    lexer = Lexer("union Data { int i; char c; };\nint main() { return 0; }")
    parser = Parser(lexer.tokenize())
    ast = parser.parse()
    assert 'Data' in ast.union_defs
    fields = ast.union_defs['Data']
    field_names = [f[0] if isinstance(f, tuple) else f for f in fields]
    assert 'i' in field_names and 'c' in field_names
    print("PASS test_parser_union_definition")


# ---------------------------------------------------------------------------
# Runtime tests: comma operator
# ---------------------------------------------------------------------------

def test_comma_operator_basic():
    """(a, b) evaluates a, then b, yielding b."""
    source = """
int main() {
    int x = (1, 2);
    return x;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=2)
    print(f"PASS test_comma_operator_basic (cycles={cycles}, R0={proc.r0})")


def test_comma_operator_yields_last():
    """(1, 2, 3) yields 3."""
    source = """
int main() {
    return (1, 2, 3);
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=3)
    print(f"PASS test_comma_operator_yields_last (cycles={cycles}, R0={proc.r0})")


def test_comma_operator_side_effects():
    """Comma operator evaluates left side (with side effects) before right."""
    source = """
int main() {
    int a = 0;
    int b = (a = 5, a + 3);
    return b;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=8)
    print(f"PASS test_comma_operator_side_effects (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Runtime tests: typedef
# ---------------------------------------------------------------------------

def test_typedef_int_variable():
    """typedef int myint; myint x = 5; return x;"""
    source = """
typedef int myint;

int main() {
    myint x = 5;
    return x;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=5)
    print(f"PASS test_typedef_int_variable (cycles={cycles}, R0={proc.r0})")


def test_typedef_in_expression():
    """typedef int myint; myint a = 3; myint b = 4; return a + b;"""
    source = """
typedef int myint;

int main() {
    myint a = 3;
    myint b = 4;
    return a + b;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=7)
    print(f"PASS test_typedef_in_expression (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Runtime tests: goto/labels
# ---------------------------------------------------------------------------

def test_goto_skips_statement():
    """goto skips the intermediate statement."""
    source = """
int main() {
    int x = 1;
    goto skip;
    x = 99;
skip:
    return x;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=1)
    print(f"PASS test_goto_skips_statement (cycles={cycles}, R0={proc.r0})")


def test_goto_jumps_forward():
    """goto jumps forward to a label."""
    source = """
int main() {
    goto end;
    return 0;
end:
    return 42;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f"PASS test_goto_jumps_forward (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Runtime tests: union
# ---------------------------------------------------------------------------

def test_union_int_member():
    """Writing to int member and reading it back."""
    source = """
union Data {
    int i;
    char c;
};

int main() {
    union Data d;
    d.i = 42;
    return d.i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f"PASS test_union_int_member (cycles={cycles}, R0={proc.r0})")


def test_union_overlapping_storage():
    """Writing to one member affects the other (overlapping storage)."""
    source = """
union Data {
    int i;
    char c;
};

int main() {
    union Data d;
    d.i = 0x1234;
    return d.c;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=0x34)
    print(f"PASS test_union_overlapping_storage (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Runtime tests: struct assignment
# ---------------------------------------------------------------------------

def test_struct_assignment_copies_fields():
    """s1 = s2 copies all fields from s2 to s1."""
    source = """
struct Point {
    int x;
    int y;
};

int main() {
    struct Point a;
    struct Point b;
    a.x = 10;
    a.y = 20;
    b.x = 50;
    b.y = 60;
    a = b;
    return a.x + a.y;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=110)
    print(f"PASS test_struct_assignment_copies_fields (cycles={cycles}, R0={proc.r0})")


def test_struct_assignment_isolation():
    """After s1 = s2, modifying s2 does not affect s1."""
    source = """
struct Point {
    int x;
    int y;
};

int main() {
    struct Point a;
    struct Point b;
    a.x = 10;
    a.y = 20;
    b.x = 50;
    b.y = 60;
    a = b;
    b.x = 99;
    return a.x;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=50)
    print(f"PASS test_struct_assignment_isolation (cycles={cycles}, R0={proc.r0})")


if __name__ == '__main__':
    # Parser-level tests
    test_parser_comma_operator()
    test_parser_typedef_basic()
    test_parser_goto_statement()
    test_parser_label_definition()
    test_parser_union_definition()
    # Runtime tests
    test_comma_operator_basic()
    test_comma_operator_yields_last()
    test_comma_operator_side_effects()
    test_typedef_int_variable()
    test_typedef_in_expression()
    test_goto_skips_statement()
    test_goto_jumps_forward()
    test_union_int_member()
    test_union_overlapping_storage()
    test_struct_assignment_copies_fields()
    test_struct_assignment_isolation()
    print("All Astrid new C-feature tests passed!")