"""Tier 3 item 8: function-like macros in the preprocessor.

Covers:
- Basic single/multi-parameter invocation and substitution
- Whitespace between the macro name and '(' (still an invocation)
- Bare macro name with no '(' stays an ordinary identifier
- Nested invocations, arguments pre-expanded like C (f(f(4)) -> 4)
- String arguments containing commas and parenthesized arguments
- Object-like #define regression (unchanged behavior)
- #if conditions that invoke macros
- Diagnostics: wrong arity, unterminated invocation, redefinition,
  invalid/variadic parameters, #undef
- End-to-end compile: a program whose arithmetic uses a macro
"""
import os
import sys

import pytest

from nova_main import initialize_system
from astrid.errors import CompileError
from astrid.preprocessor import Preprocessor


def preprocess(source):
    """Run the preprocessor over source and return the expanded text."""
    return Preprocessor(source).process()


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


def compile_and_run(source, expected_r0=None, max_cycles=2000000):
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
        Assembler().assemble(asm_path)
        proc, cycles, mem = run_binary(bin_path, max_cycles=max_cycles)
        assert proc.halted, "Program did not halt"
        if expected_r0 is not None:
            assert proc.r0 == expected_r0, (
                f"Expected R0={expected_r0}, got {proc.r0}")
        return proc, cycles, mem
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


# ---------------------------------------------------------------------------
# Expansion behavior
# ---------------------------------------------------------------------------

def test_single_parameter_invocation():
    out = preprocess('#define SQ(x) ((x)*(x))\nint a = SQ(3);\n')
    assert '((3)*(3))' in out
    assert 'SQ' not in out.splitlines()[1]
    print("PASS test_single_parameter_invocation")


def test_multiple_parameters():
    out = preprocess('#define ADD(a, b) ((a)+(b))\nint c = ADD(1, 2);\n')
    assert '((1)+(2))' in out
    print("PASS test_multiple_parameters")


def test_whitespace_before_paren_invokes():
    """C allows `SQ (3)`: whitespace between name and '(' still invokes."""
    out = preprocess('#define SQ(x) ((x)*(x))\nint a = SQ (3);\n')
    assert '((3)*(3))' in out
    print("PASS test_whitespace_before_paren_invokes")


def test_bare_name_stays_identifier():
    """Without '(' the function-like macro name is an ordinary identifier."""
    out = preprocess('#define SQ(x) ((x)*(x))\nint SQ = 9;\n')
    assert 'int SQ = 9;' in out
    print("PASS test_bare_name_stays_identifier")


def test_nested_invocation_in_argument():
    out = preprocess('#define ADD(a, b) ((a)+(b))\nint c = ADD(ADD(1, 2), 3);\n')
    assert '((1)+(2))' in out
    assert '(3)' in out
    print("PASS test_nested_invocation_in_argument")


def test_argument_pre_expansion_like_c():
    """f(f(4)) with #define f(x) x must fold to 4, not leave a painted f."""
    out = preprocess('#define f(x) x\nint b = f(f(4));\n')
    assert '4' in out
    assert 'f(' not in out
    print("PASS test_argument_pre_expansion_like_c")


def test_string_argument_with_comma():
    """A comma inside a string literal is not an argument separator."""
    out = preprocess('#define STR(x) x\nchar *s = STR("a,b");\n')
    assert '"a,b"' in out
    assert 'STR' not in out.splitlines()[1]
    print("PASS test_string_argument_with_comma")


def test_parenthesized_argument():
    """A comma inside nested parentheses belongs to the inner expression."""
    out = preprocess('#define ID(x) x\nint v = ID((1, 2));\n')
    # The inner comma survives as a comma operator inside the parens.
    assert '(1, 2)' in out
    print("PASS test_parenthesized_argument")


def test_zero_parameter_macro():
    out = preprocess('#define FIVE() 5\nint n = FIVE();\n')
    assert '5' in out
    assert 'FIVE' not in out.splitlines()[1]
    print("PASS test_zero_parameter_macro")



def test_empty_body_macro_expands_to_nothing():
    out = preprocess('#define NOTHING()\nint n = NOTHING();\n')
    second = out.splitlines()[1]
    assert 'NOTHING' not in second
    print("PASS test_empty_body_macro_expands_to_nothing")


def test_object_like_regression():
    """Object-like #define keeps its original behavior."""
    out = preprocess('#define WIDTH 64\nint w = WIDTH + 1;\n')
    assert '64' in out
    assert 'WIDTH' not in out.splitlines()[1]
    print("PASS test_object_like_regression")


def test_object_like_paren_body_is_not_function_like():
    """`#define F (x)` (space before paren) stays object-like in C."""
    out = preprocess('#define P (7)\nint v = P;\n')
    assert '(7)' in out
    print("PASS test_object_like_paren_body_is_not_function_like")


def test_macro_in_if_condition():
    out = preprocess('#define SQ(x) ((x)*(x))\n#if SQ(2) == 4\nyes\n#endif\n')
    assert 'yes' in out
    print("PASS test_macro_in_if_condition")


def test_macro_in_if_condition_false():
    out = preprocess('#define SQ(x) ((x)*(x))\n#if SQ(2) == 5\nyes\n#endif\n')
    assert 'yes' not in out
    print("PASS test_macro_in_if_condition_false")


def test_token_boundary_no_fusion():
    """Expansion padding must not fuse `+ +` into `++`."""
    out = preprocess('#define PLUS +\nint v = 1 PLUS + 2;\n')
    assert '++' not in out
    print("PASS test_token_boundary_no_fusion")


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def test_wrong_arity_fails():
    with pytest.raises(CompileError) as exc:
        preprocess('#define SQ(x) ((x)*(x))\nint a = SQ(1, 2);\n')
    assert 'argument' in str(exc.value)
    print("PASS test_wrong_arity_fails")


def test_unterminated_invocation_fails():
    with pytest.raises(CompileError) as exc:
        preprocess('#define SQ(x) x\nint a = SQ(1;\n')
    assert 'unterminated' in str(exc.value)
    print("PASS test_unterminated_invocation_fails")


def test_redefinition_fails():
    with pytest.raises(CompileError) as exc:
        preprocess('#define SQ(x) x\n#define SQ(y) y\n')
    assert 'redefined' in str(exc.value)
    print("PASS test_redefinition_fails")


def test_identical_redefinition_allowed():
    out = preprocess('#define SQ(x) x\n#define SQ(x) x\nint a = SQ(2);\n')
    assert '2' in out
    print("PASS test_identical_redefinition_allowed")


def test_invalid_parameter_fails():
    with pytest.raises(CompileError) as exc:
        preprocess('#define M(a, 1) a\n')
    assert 'parameter' in str(exc.value)
    print("PASS test_invalid_parameter_fails")


def test_variadic_parameter_fails():
    with pytest.raises(CompileError) as exc:
        preprocess('#define M(a, ...) a\n')
    assert 'variadic' in str(exc.value)
    print("PASS test_variadic_parameter_fails")


def test_undef_removes_function_macro():
    out = preprocess('#define SQ(x) x\n#undef SQ\nint a = SQ(3);\n')
    # After #undef the name is a plain (undefined) identifier again.
    assert 'SQ(3)' in out
    print("PASS test_undef_removes_function_macro")


def test_ifdef_recognizes_function_macro():
    out = preprocess('#define SQ(x) x\n#ifdef SQ\nyes\n#endif\n')
    assert 'yes' in out
    print("PASS test_ifdef_recognizes_function_macro")


def test_defined_recognizes_function_macro():
    out = preprocess('#define SQ(x) x\n#if defined(SQ)\nyes\n#endif\n')
    assert 'yes' in out
    print("PASS test_defined_recognizes_function_macro")


# ---------------------------------------------------------------------------
# End-to-end: compile and run a program that uses a macro
# ---------------------------------------------------------------------------

def test_runtime_program_uses_macro():
    source = """
#define SQUARE(x) ((x)*(x))
int main() {
    return SQUARE(7) + SQUARE(2);
}
"""
    # 49 + 4 = 53 (low byte in R0)
    proc, cycles, mem = compile_and_run(source, expected_r0=53)
    print(f"PASS test_runtime_program_uses_macro (cycles={cycles})")


def test_runtime_multi_arg_macro_in_condition():
    source = """
#define MAX(a, b) (((a) > (b)) ? (a) : (b))
int main() {
    int x = 12;
    int y = 30;
    if (MAX(x, y) == y) {
        return 1;
    }
    return 0;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=1)
    print(f"PASS test_runtime_multi_arg_macro_in_condition (cycles={cycles})")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
