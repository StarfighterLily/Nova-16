"""Regression tests for Astrid compiler fixes.

Covers:
1. Logical NOT (!) produces 0/1 semantics, NOT bitwise complement.
2. Bitwise NOT (~) produces 16-bit complement.
3. do-while `continue` jumps to condition check (C semantics).
4. int() builtin works with non-constant arguments.
5. Nested switch/case fall-through with break.
6. Nested loops with break/continue in switch.
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
from astrid.codegen.optimizations import ExpressionSimplifier


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
    # (e.g. Unicode arrows in comments) that cp1252 cannot encode.
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


def test_logical_not_nonzero():
    """!5 should be 0, not 0xFFFA (bitwise complement)."""
    source = """
int main() {
    int a = 5;
    int b = !a;
    return b;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=0)
    print(f"PASS test_logical_not_nonzero (cycles={cycles}, R0={proc.r0})")


def test_logical_not_zero():
    """!0 should be 1."""
    source = """
int main() {
    int b = !0;
    return b;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=1)
    print(f"PASS test_logical_not_zero (cycles={cycles}, R0={proc.r0})")


def test_logical_not_in_expr():
    """! result should flow into arithmetic correctly."""
    source = """
int main() {
    int a = 5;
    int b = !a;
    int c = !0;
    return b * 10 + c;
}
"""
    # !5 = 0, !0 = 1 → 0*10 + 1 = 1
    proc, cycles, mem = compile_and_run(source, expected_r0=1)
    print(f"PASS test_logical_not_in_expr (cycles={cycles}, R0={proc.r0})")


def test_bitwise_not():
    """~0x00FF should be 0xFF00 (16-bit complement)."""
    source = """
int main() {
    int x = ~0x00FF;
    return x;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_p0=0xFF00)
    print(f"PASS test_bitwise_not (cycles={cycles}, P0=0x{proc.p0:04X})")


def test_logical_not_of_zero_variable():
    """!0 variable should be 1."""
    source = """
int main() {
    int a = 0;
    int b = !a;
    return b;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=1)
    print(f"PASS test_logical_not_of_zero_variable (cycles={cycles}, R0={proc.r0})")


def test_do_while_continue():
    """continue in a do-while should jump to condition check.

    Without the fix, `continue` jumps to the *start* of the loop body,
    skipping the condition and causing an infinite loop. With correct
    C semantics, it jumps to the condition; when i >= 5 the loop exits.
    """
    source = """
int main() {
    int i = 0;
    int sum = 0;
    do {
        i = i + 1;
        if (i % 2 == 0) {
            continue;
        }
        sum = sum + i;
    } while (i < 5);
    return sum;  // 1 + 3 + 5 = 9
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=9)
    print(f"PASS test_do_while_continue (cycles={cycles}, R0={proc.r0})")


def test_do_while_continue_condition_false():
    """continue in do-while when condition is initially false should still exit."""
    source = """
int main() {
    int i = 0;
    int count = 0;
    do {
        i = i + 1;
        if (i == 1) {
            continue;
        }
        count = count + 1;
    } while (i < 3);
    return count;  // i=2 and i=3 counted → 2
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=2)
    print(f"PASS test_do_while_continue_condition_false (cycles={cycles}, R0={proc.r0})")


def test_int_builtin_non_constant():
    """int() builtin with non-constant argument should compile and run."""
    source = """
int main() {
    int a = 300;
    int b = int(a);
    return b;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=0x2C)  # 300 & 0xFF = 44
    print(f"PASS test_int_builtin_non_constant (cycles={cycles}, R0={proc.r0})")


def test_int_builtin_returns_low_byte():
    """int() of a value >255 should still produce full P0 but R0 holds low byte."""
    source = """
int main() {
    int a = 1234;
    int b = int(a);
    return b;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_p0=1234)
    print(f"PASS test_int_builtin_returns_low_byte (cycles={cycles}, P0={proc.p0})")


def test_switch_fallthrough_break():
    """switch with fall-through then break at the right place."""
    source = """
int main() {
    int x = 1;
    int result = 0;
    switch (x) {
        case 1:
            result = result + 10;
        case 2:
            result = result + 20;
            break;
        case 3:
            result = 99;
        default:
            result = 100;
    }
    return result;  // 10 + 20 = 30 (stops at break)
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=30)
    print(f"PASS test_switch_fallthrough_nested (cycles={cycles}, R0={proc.r0})")


def test_switch_default_no_match():
    """Switch default executes when no case matches and no break in default."""
    source = """
int main() {
    int x = 9;
    int result = 0;
    switch (x) {
        case 1:
            result = 10;
            break;
        case 2:
            result = 20;
            break;
        default:
            result = 42;
    }
    return result;  // 42
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f"PASS test_switch_default_no_match (cycles={cycles}, R0={proc.r0})")


def test_nested_switch_break_outer_loop():
    """break inside a switch nested in a loop should exit the switch, not the loop."""
    source = """
int main() {
    int i = 0;
    int total = 0;
    while (i < 3) {
        i = i + 1;
        int x = i;
        switch (x) {
            case 1:
                total = total + 10;
                break;
            case 2:
                total = total + 20;
                break;
            default:
                total = total + 30;
        }
        total = total * 2;
    }
    return total;
}
"""
    # i=1: x=1 → total=10 → *2=20
    # i=2: x=2 → total=20+20=40 → *2=80
    # i=3: x=3 → default → total=80+30=110 → *2=220
    # R0 truncates to 220&0xFF = 220 (0xDC = 220)
    proc, cycles, mem = compile_and_run(source)
    assert proc.p0 == 220, f"Expected P0=220, got {proc.p0}"
    print(f"PASS test_nested_switch_break_outer_loop (cycles={cycles}, P0={proc.p0})")


def test_break_in_while_and_switch():
    """break should target the innermost loop/switch appropriately."""
    source = """
int main() {
    int i = 0;
    int sum = 0;
    while (i < 5) {
        i = i + 1;
        switch (i) {
            case 2:
                sum = sum + 100;
                break;  // exits switch only
            case 4:
                sum = sum + 400;
                break;
            default:
                sum = sum + i;
        }
    }
    return sum;  // 1 + 100 + 3 + 400 + 5 = 509
}
"""
    proc, cycles, mem = compile_and_run(source, expected_p0=509)
    print(f"PASS test_break_in_while_loop (cycles={cycles}, P0={proc.p0})")


def test_expr_simplifier_logical_not():
    """ExpressionSimplifier must fold ! to 0/1 correctly.
    !5 is logical-false (0), NOT bitwise ~5 (0xFFFA).
    """
    lexer = Lexer("int main() { int x = !5; return x; }")
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    var_decl = ast.functions[0].body[0]
    simpl = ExpressionSimplifier()
    result = simpl.simplify(var_decl.value)
    from astrid.parser.parser import Number
    assert isinstance(result, Number), f"Expected Number, got {type(result).__name__}"
    assert int(result.value, 0) == 0, f"!5 should fold to 0, got {result.value}"
    print(f"PASS test_exprsimplifier_logical_not (!5 -> {result.value})")


def test_exprsimplifier_bitwise_not():
    """ExpressionSimplifier must fold ~constant to 16-bit complement."""
    lexer = Lexer("int main() { int x = ~0x00FF; return x; }")
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    var_decl = ast.functions[0].body[0]
    simpl = ExpressionSimplifier()
    result = simpl.simplify(var_decl.value)
    from astrid.parser.parser import Number
    assert isinstance(result, Number), f"Expected Number, got {type(result).__name__}"
    assert int(result.value, 0) == 0xFF00, f"~0x00FF should fold to 0xFF00, got {result.value}"
    print(f"PASS test_exprsimplifier_bitwise_not (~0x00FF -> {result.value})")


def test_int_builtin_in_expression_contexts():
    """int() must parse in ALL expression contexts, not just statement start.

    The lexer classifies `int` as a KEYWORD, so the parser's primary-expression
    handler must recognize `int(...)` as a builtin call. Covers:
    - var declaration initializer:  int b = int(a);
    - return expression:            return int(a);
    - nested inside arithmetic:     int c = int(a) + 1;
    """
    source = """
int main() {
    int a = 300;
    int b = int(a);
    int c = int(a) + 1;
    return int(b) + c;
}
"""
    # b = 300, c = 301, return 300 + 301 = 601
    proc, cycles, mem = compile_and_run(source, expected_p0=601)
    print(f"PASS test_int_builtin_in_expression_contexts (cycles={cycles}, P0={proc.p0})")


def test_int_builtin_constant_folding_matches_runtime():
    """int(CONSTANT) folds to the same value the runtime identity builtin gives."""
    from astrid.parser.parser import Number
    lexer = Lexer("int main() { int x = int(300); return x; }")
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    var_decl = ast.functions[0].body[0]
    simpl = ExpressionSimplifier()
    result = simpl.simplify(var_decl.value)
    assert isinstance(result, Number), f"Expected folded Number, got {type(result).__name__}"
    assert int(result.value, 0) == 300, f"int(300) should fold to 300 (identity), got {result.value}"
    print(f"PASS test_int_builtin_constant_folding_matches_runtime (int(300) -> {result.value})")


def test_unicode_arrow_in_comment_compiles():
    """Source containing non-ASCII characters (Unicode arrows) in comments
    must compile. Test harnesses write sources as UTF-8; the compiler reads
    them back with encoding='utf-8' so no cp1252 encode/decode errors occur.
    """
    source = """int main() {
    // i=2 and i=3 counted → 2
    /* arrows: → ⇒ → */
    int count = 0;
    int i = 0;
    do {
        i = i + 1;
        if (i == 1) { continue; }
        count = count + 1;
    } while (i < 3);
    return count;  // i=2 and i=3 counted → 2
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=2)
    print(f"PASS test_unicode_arrow_in_comment_compiles (cycles={cycles}, R0={proc.r0})")


def test_software_int_still_raises_interrupt():
    """software_int() must keep its software-interrupt semantics after the
    int()/software_int() builtin split (builtin_int vs builtin_software_int)."""
    source = """
void main() {
    software_int(0);
}
"""
    proc, cycles, mem = compile_and_run(source)
    assert proc.halted, "Program did not halt"
    print(f"PASS test_software_int_still_raises_interrupt (cycles={cycles})")


def test_double_negative():
    """Double negation: -(-a) must evaluate back to a itself.

    With a = -5: -a = 5, then -(-a) = -(5) = -5. The compiler correctly
    produces -5 (16-bit two's complement 0xFFFB); R0 holds the low byte
    0xFB = 251.
    """
    source = """
int main() {
    int a = -5;
    int b = -(-a);
    return b;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=0xFB)
    assert proc.p0 == 0xFFFB, f"Expected P0=0xFFFB (-5), got {proc.p0}"
    print(f"PASS test_double_negative (cycles={cycles}, P0=0x{proc.p0:04X}, R0=0x{proc.r0:02X})")


if __name__ == '__main__':
    test_logical_not_nonzero()
    test_logical_not_zero()
    test_logical_not_in_expr()
    test_bitwise_not()
    test_logical_not_of_zero_variable()
    test_do_while_continue()
    test_do_while_continue_condition_false()
    test_int_builtin_non_constant()
    test_int_builtin_returns_low_byte()
    test_switch_fallthrough_break()
    test_switch_default_no_match()
    test_nested_switch_break_outer_loop()
    test_break_in_while_and_switch()
    test_expr_simplifier_logical_not()
    test_exprsimplifier_bitwise_not()
    test_double_negative()
    test_int_builtin_in_expression_contexts()
    test_int_builtin_constant_folding_matches_runtime()
    test_unicode_arrow_in_comment_compiles()
    test_software_int_still_raises_interrupt()
    print("All Astrid regression tests passed!")
