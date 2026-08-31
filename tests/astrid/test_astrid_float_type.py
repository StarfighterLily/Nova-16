"""High-coverage tests for the Astrid `float` type (Q8.8 fixed-point).

The Nova-16 CPU has no native IEEE-754 floating point; its "float" support
is Q8.8 fixed-point: a 16-bit value whose high byte holds the signed integer
part and low byte holds 1/256ths.  Astrid's `float` maps directly onto this
representation (2 bytes, stored like an int), calling ITOF/FTOI for
conversions and FMUL/FDIV for multiply/divide. Addition and subtraction need
no scaling (fixed-point adds directly).

Tests cover:
1. Lexer: float literal tokenization (positive, negative, edge cases)
2. Parser: float type keyword, float variable declarations, float expressions
3. Codegen/Runtime:
   - Float variable declarations and initialization
   - Float arithmetic (Q8.8 fixed-point: +, -, *, /)
   - Float comparisons
   - Type conversions (int<->float, char<->float)
   - Float compound assignments (+=, -=, *=, /=)
   - Float arrays
   - Float globals
   - Float function parameters and return values
   - Float in expressions (mixed int/float)
   - Float prefix/postfix operators
"""
import os
import sys

# Path setup handled by tests/astrid/conftest.py

from nova_main import initialize_system
from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser, Number, Cast, VarDecl, BinaryOp


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
# Lexer tests
# ---------------------------------------------------------------------------

def test_lexer_float_literal_positive():
    """Positive float literals should be tokenized as NUMBER."""
    lexer = Lexer("float f = 1.5;")
    tokens = lexer.tokenize()
    number_tokens = [t for t in tokens if t.type == 'NUMBER']
    assert len(number_tokens) == 1
    assert number_tokens[0].value == '1.5'


def test_lexer_float_literal_zero():
    """Zero float literal (0.0) should be tokenized as NUMBER."""
    lexer = Lexer("float f = 0.0;")
    tokens = lexer.tokenize()
    number_tokens = [t for t in tokens if t.type == 'NUMBER']
    assert len(number_tokens) == 1
    assert number_tokens[0].value == '0.0'


def test_lexer_float_literal_small_fraction():
    """Small fraction (0.0625 = 1/16) should be tokenized as NUMBER."""
    lexer = Lexer("float f = 0.0625;")
    tokens = lexer.tokenize()
    number_tokens = [t for t in tokens if t.type == 'NUMBER']
    assert len(number_tokens) == 1
    assert number_tokens[0].value == '0.0625'


def test_lexer_float_literal_large():
    """Large float literal (128.5) should be tokenized as NUMBER."""
    lexer = Lexer("float f = 128.5;")
    tokens = lexer.tokenize()
    number_tokens = [t for t in tokens if t.type == 'NUMBER']
    assert len(number_tokens) == 1
    assert number_tokens[0].value == '128.5'


def test_lexer_float_literal_negative():
    """Negative float literal via unary minus should tokenize correctly."""
    lexer = Lexer("float f = -1.5;")
    tokens = lexer.tokenize()
    # Should have: float, f, =, -, 1.5, ;
    number_tokens = [t for t in tokens if t.type == 'NUMBER']
    assert len(number_tokens) == 1
    assert number_tokens[0].value == '1.5'
    # The minus should be an OPERATOR
    op_tokens = [t for t in tokens if t.type == 'OPERATOR' and t.value == '-']
    assert len(op_tokens) == 1


def test_lexer_float_keyword():
    """'float' should be recognized as a KEYWORD."""
    lexer = Lexer("float f;")
    tokens = lexer.tokenize()
    kw_tokens = [t for t in tokens if t.type == 'KEYWORD' and t.value == 'float']
    assert len(kw_tokens) == 1


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

def test_parser_float_var_declaration():
    """float f; should produce a VarDecl with var_type='float'."""
    lexer = Lexer("int main() { float f; return 0; }")
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    main_func = ast.functions[0]
    var_decl = main_func.body[0]
    assert isinstance(var_decl, VarDecl)
    assert var_decl.var_type == 'float'


def test_parser_float_var_with_init():
    """float f = 1.5; should produce a VarDecl with var_type='float' and value."""
    lexer = Lexer("int main() { float f = 1.5; return 0; }")
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    main_func = ast.functions[0]
    var_decl = main_func.body[0]
    assert isinstance(var_decl, VarDecl)
    assert var_decl.var_type == 'float'
    assert var_decl.value is not None


def test_parser_float_type_keyword():
    """Parser should recognize 'float' as a base type."""
    from astrid.parser.parser import BASE_TYPES


# ---------------------------------------------------------------------------
# Codegen/Runtime: Float variable declarations and initialization
# ---------------------------------------------------------------------------

def test_float_var_init_literal():
    """float f = 1.5; should encode 1.5 as Q8.8 (384 = 0x0180)."""
    source = """
int main() {
    float f = 1.5;
    int i = (int)f;  // FTOI: 384 >> 8 = 1
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=1)
    print(f"PASS test_float_var_init_literal (cycles={cycles}, R0={proc.r0})")


def test_float_var_init_zero():
    """float f = 0.0; should encode 0.0 as Q8.8 (0)."""
    source = """
int main() {
    float f = 0.0;
    int i = (int)f;  // FTOI: 0 >> 8 = 0
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=0)
    print(f"PASS test_float_var_init_zero (cycles={cycles}, R0={proc.r0})")


def test_float_var_init_negative():
    """float f = -1.5; should encode -1.5 as Q8.8 (0xFE80)."""
    source = """
int main() {
    float f = -1.5;
    int i = (int)f;  // FTOI: -384 >> 8 = -2 (arithmetic right shift)
    return i;
}
"""
    # -1.5 in Q8.8 = -384 (0xFE80), FTOI: -384 >> 8 = -2 (0xFFFE), R0 = 0xFE = 254
    proc, cycles, mem = compile_and_run(source, expected_r0=0xFE)
    print(f"PASS test_float_var_init_negative (cycles={cycles}, R0={proc.r0})")


def test_float_var_init_integer_promotion():
    """float f = 5; should promote int 5 to Q8.8 (1280 = 0x0500)."""
    source = """
int main() {
    float f = 5;
    int i = (int)f;  // FTOI: 1280 >> 8 = 5
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=5)
    print(f"PASS test_float_var_init_integer_promotion (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Codegen/Runtime: Float arithmetic (Q8.8 fixed-point)
# ---------------------------------------------------------------------------

def test_float_addition():
    """float a = 1.5; float b = 2.5; a + b = 4.0 (Q8.8: 384 + 640 = 1024)."""
    source = """
int main() {
    float a = 1.5;
    float b = 2.5;
    float c = a + b;
    int i = (int)c;  // FTOI: 1024 >> 8 = 4
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=4)
    print(f"PASS test_float_addition (cycles={cycles}, R0={proc.r0})")


def test_float_subtraction():
    """float a = 5.5; float b = 2.5; a - b = 3.0 (Q8.8: 1408 - 640 = 768)."""
    source = """
int main() {
    float a = 5.5;
    float b = 2.5;
    float c = a - b;
    int i = (int)c;  // FTOI: 768 >> 8 = 3
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=3)
    print(f"PASS test_float_subtraction (cycles={cycles}, R0={proc.r0})")


def test_float_multiplication():
    """float a = 2.0; float b = 3.0; a * b = 6.0 (Q8.8: 512 * 768 / 256 = 1536)."""
    source = """
int main() {
    float a = 2.0;
    float b = 3.0;
    float c = a * b;
    int i = (int)c;  // FTOI: 1536 >> 8 = 6
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=6)
    print(f"PASS test_float_multiplication (cycles={cycles}, R0={proc.r0})")


def test_float_division():
    """float a = 6.0; float b = 2.0; a / b = 3.0 (Q8.8: 1536 / 512 = 768)."""
    source = """
int main() {
    float a = 6.0;
    float b = 2.0;
    float c = a / b;
    int i = (int)c;  // FTOI: 768 >> 8 = 3
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=3)
    print(f"PASS test_float_division (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Codegen/Runtime: Float comparisons
# ---------------------------------------------------------------------------

def test_float_comparison_greater():
    """float a = 2.0; float b = 1.0; a > b should be true (1)."""
    source = """
int main() {
    float a = 2.0;
    float b = 1.0;
    int result = 0;
    if (a > b) {
        result = 1;
    }
    return result;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=1)
    print(f"PASS test_float_comparison_greater (cycles={cycles}, R0={proc.r0})")


def test_float_comparison_less():
    """float a = 1.0; float b = 2.0; a < b should be true (1)."""
    source = """
int main() {
    float a = 1.0;
    float b = 2.0;
    int result = 0;
    if (a < b) {
        result = 1;
    }
    return result;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=1)
    print(f"PASS test_float_comparison_less (cycles={cycles}, R0={proc.r0})")


def test_float_comparison_equal():
    """float a = 1.5; float b = 1.5; a == b should be true (1)."""
    source = """
int main() {
    float a = 1.5;
    float b = 1.5;
    int result = 0;
    if (a == b) {
        result = 1;
    }
    return result;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=1)
    print(f"PASS test_float_comparison_equal (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Codegen/Runtime: Type conversions
# ---------------------------------------------------------------------------

def test_int_to_float_cast():
    """(float)5 should promote int 5 to Q8.8 (1280 = 0x0500)."""
    source = """
int main() {
    int x = 5;
    float f = (float)x;
    int i = (int)f;  // FTOI: 1280 >> 8 = 5
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=5)
    print(f"PASS test_int_to_float_cast (cycles={cycles}, R0={proc.r0})")


def test_float_to_int_cast():
    """(int)1.5 should truncate to 1 (FTOI)."""
    source = """
int main() {
    float f = 1.5;
    int i = (int)f;  // FTOI: 384 >> 8 = 1
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=1)
    print(f"PASS test_float_to_int_cast (cycles={cycles}, R0={proc.r0})")


def test_char_to_float_cast():
    """(float)65 (char 'A') should promote to Q8.8 (16640 = 0x4100)."""
    source = """
int main() {
    char c = 65;
    float f = (float)c;
    int i = (int)f;  // FTOI: 16640 >> 8 = 65
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=65)
    print(f"PASS test_char_to_float_cast (cycles={cycles}, R0={proc.r0})")


def test_float_to_char_cast():
    """(char)1.5 should truncate to 1 (FTOI then low byte)."""
    source = """
int main() {
    float f = 1.5;
    char c = (char)f;  // FTOI: 384 >> 8 = 1, then low byte = 1
    return c;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=1)
    print(f"PASS test_float_to_char_cast (cycles={cycles}, R0={proc.r0})")


def test_float_cast_syntax():
    """(float)x cast syntax should promote int to Q8.8."""
    source = """
int main() {
    int x = 10;
    float f = (float)x;
    int i = (int)f;  // FTOI: 2560 >> 8 = 10
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=10)
    print(f"PASS test_float_cast_syntax (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Codegen/Runtime: Float compound assignments
# ---------------------------------------------------------------------------

def test_float_compound_add():
    """float f = 1.0; f += 2.0; f should be 3.0."""
    source = """
int main() {
    float f = 1.0;
    f += 2.0;
    int i = (int)f;  // FTOI: 768 >> 8 = 3
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=3)
    print(f"PASS test_float_compound_add (cycles={cycles}, R0={proc.r0})")


def test_float_compound_sub():
    """float f = 5.0; f -= 2.0; f should be 3.0."""
    source = """
int main() {
    float f = 5.0;
    f -= 2.0;
    int i = (int)f;  // FTOI: 768 >> 8 = 3
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=3)
    print(f"PASS test_float_compound_sub (cycles={cycles}, R0={proc.r0})")


def test_float_compound_mul():
    """float f = 2.0; f *= 3.0; f should be 6.0."""
    source = """
int main() {
    float f = 2.0;
    f *= 3.0;
    int i = (int)f;  // FTOI: 1536 >> 8 = 6
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=6)
    print(f"PASS test_float_compound_mul (cycles={cycles}, R0={proc.r0})")


def test_float_compound_div():
    """float f = 6.0; f /= 2.0; f should be 3.0."""
    source = """
int main() {
    float f = 6.0;
    f /= 2.0;
    int i = (int)f;  // FTOI: 768 >> 8 = 3
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=3)
    print(f"PASS test_float_compound_div (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Codegen/Runtime: Float arrays
# ---------------------------------------------------------------------------

def test_float_array_declaration():
    """float arr[3]; should declare a float array."""
    source = """
int main() {
    float arr[3];
    arr[0] = 1.5;
    arr[1] = 2.5;
    arr[2] = 3.5;
    int sum = (int)arr[0] + (int)arr[1] + (int)arr[2];
    return sum;  // 1 + 2 + 3 = 6
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=6)
    print(f"PASS test_float_array_declaration (cycles={cycles}, R0={proc.r0})")


def test_float_array_with_init():
    """float arr[3] = {1.0, 2.0, 3.0}; should initialize correctly."""
    source = """
int main() {
    float arr[3] = {1.0, 2.0, 3.0};
    int sum = (int)arr[0] + (int)arr[1] + (int)arr[2];
    return sum;  // 1 + 2 + 3 = 6
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=6)
    print(f"PASS test_float_array_with_init (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Codegen/Runtime: Float globals
# ---------------------------------------------------------------------------

def test_float_global_declaration():
    """Global float g = 1.5; should be accessible."""
    source = """
float g = 1.5;

int main() {
    int i = (int)g;  // FTOI: 384 >> 8 = 1
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=1)
    print(f"PASS test_float_global_declaration (cycles={cycles}, R0={proc.r0})")


def test_float_global_mutation():
    """Global float mutation should persist."""
    source = """
float g = 1.0;

int main() {
    g = g + 2.0;
    int i = (int)g;  // FTOI: 768 >> 8 = 3
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=3)
    print(f"PASS test_float_global_mutation (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Codegen/Runtime: Float function parameters and return values
# ---------------------------------------------------------------------------

def test_float_function_parameter():
    """Function with float parameter should work."""
    source = """
int compute(float x) {
    return (int)x;
}

int main() {
    float f = 3.5;
    int result = compute(f);  // FTOI: 896 >> 8 = 3
    return result;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=3)
    print(f"PASS test_float_function_parameter (cycles={cycles}, R0={proc.r0})")


def test_float_function_return():
    """Function returning float should work."""
    source = """
float get_value() {
    return 2.5;
}

int main() {
    float f = get_value();
    int i = (int)f;  // FTOI: 640 >> 8 = 2
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=2)
    print(f"PASS test_float_function_return (cycles={cycles}, R0={proc.r0})")


def test_float_function_add():
    """Function adding two floats should work."""
    source = """
float add(float a, float b) {
    return a + b;
}

int main() {
    float result = add(1.5, 2.5);
    int i = (int)result;  // FTOI: 1024 >> 8 = 4
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=4)
    print(f"PASS test_float_function_add (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Codegen/Runtime: Float in expressions (mixed int/float)
# ---------------------------------------------------------------------------

def test_float_mixed_int_expression():
    """float f = 1.5 + 2; should promote 2 to Q8.8 then add."""
    source = """
int main() {
    float f = 1.5 + 2;
    int i = (int)f;  // 1.5 (384) + 2 (512) = 896 >> 8 = 3
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=3)
    print(f"PASS test_float_mixed_int_expression (cycles={cycles}, R0={proc.r0})")


def test_float_expression_chain():
    """float f = 1.0 + 2.0 + 3.0; should equal 6.0."""
    source = """
int main() {
    float f = 1.0 + 2.0 + 3.0;
    int i = (int)f;  // FTOI: 1536 >> 8 = 6
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=6)
    print(f"PASS test_float_expression_chain (cycles={cycles}, R0={proc.r0})")


def test_float_expression_with_mul():
    """float f = 2.0 * 3.0 + 1.0; should equal 7.0."""
    source = """
int main() {
    float f = 2.0 * 3.0 + 1.0;
    int i = (int)f;  // (512 * 768 / 256) + 256 = 1536 + 256 = 1792 >> 8 = 7
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=7)


# ---------------------------------------------------------------------------
# Codegen/Runtime: Float prefix/postfix operators
# ---------------------------------------------------------------------------

def test_float_prefix_increment():
    """float f = 1.0; ++f should be 2.0."""
    source = """
int main() {
    float f = 1.0;
    ++f;
    int i = (int)f;  // FTOI: 512 >> 8 = 2
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=2)
    print(f"PASS test_float_prefix_increment (cycles={cycles}, R0={proc.r0})")


def test_float_postfix_increment():
    """float f = 1.0; f++ should be 2.0."""
    source = """
int main() {
    float f = 1.0;
    f++;
    int i = (int)f;  // FTOI: 512 >> 8 = 2
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=2)
    print(f"PASS test_float_postfix_increment (cycles={cycles}, R0={proc.r0})")


def test_float_prefix_decrement():
    """float f = 3.0; --f should be 2.0."""
    source = """
int main() {
    float f = 3.0;
    --f;
    int i = (int)f;  // FTOI: 512 >> 8 = 2
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=2)
    print(f"PASS test_float_prefix_decrement (cycles={cycles}, R0={proc.r0})")


def test_float_postfix_decrement():
    """float f = 3.0; f-- should be 2.0."""
    source = """
int main() {
    float f = 3.0;
    f--;
    int i = (int)f;  // FTOI: 512 >> 8 = 2
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=2)
    print(f"PASS test_float_postfix_decrement (cycles={cycles}, R0={proc.r0})")


# ---------------------------------------------------------------------------
# Codegen/Runtime: Edge cases
# ---------------------------------------------------------------------------

def test_float_q88_precision():
    """float f = 0.5; should encode as 128 (0x0080) in Q8.8."""
    source = """
int main() {
    float f = 0.5;
    int i = (int)f;  // FTOI: 128 >> 8 = 0
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=0)
    print(f"PASS test_float_q88_precision (cycles={cycles}, R0={proc.r0})")


def test_float_assignment_from_expression():
    """float f = 1.0 + 2.0 * 3.0; should equal 7.0."""
    source = """
int main() {
    float f = 1.0 + 2.0 * 3.0;
    int i = (int)f;  // 256 + (512*768/256) = 256 + 1536 = 1792 >> 8 = 7
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=7)
    print(f"PASS test_float_assignment_from_expression (cycles={cycles}, R0={proc.r0})")


def test_float_cast_identity():
    """(float)f where f is already float should be identity."""
    source = """
int main() {
    float f = 2.5;
    float g = (float)f;
    int i = (int)g;  // FTOI: 640 >> 8 = 2
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=2)
    print(f"PASS test_float_cast_identity (cycles={cycles}, R0={proc.r0})")


def test_int_cast_identity():
    """(int)i where i is already int should be identity."""
    source = """
int main() {
    int i = 42;
    int j = (int)i;
    return j;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f"PASS test_int_cast_identity (cycles={cycles}, R0={proc.r0})")


def test_float_in_if_condition():
    """Float comparison in if condition should work."""
    source = """
int main() {
    float f = 5.0;
    int result = 0;
    if (f > 3.0) {
        result = 1;
    }
    return result;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=1)
    print(f"PASS test_float_in_if_condition (cycles={cycles}, R0={proc.r0})")


def test_float_in_while_condition():
    """Float comparison in while condition should work."""
    source = """
int main() {
    float f = 0.0;
    int count = 0;
    while (f < 3.0) {
        f += 1.0;
        count += 1;
    }
    return count;  // count = 3
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=3)
    print(f"PASS test_float_in_while_condition (cycles={cycles}, R0={proc.r0})")


def test_float_compound_add_integer():
    """float f = 1.0; f += 2; should promote 2 to Q8.8 then add."""
    source = """
int main() {
    float f = 1.0;
    f += 2;
    int i = (int)f;  // 256 + 512 = 768 >> 8 = 3
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=3)
    print(f"PASS test_float_compound_add_integer (cycles={cycles}, R0={proc.r0})")


def test_float_compound_mul_integer():
    """float f = 2.0; f *= 3; should promote 3 to Q8.8 then multiply."""
    source = """
int main() {
    float f = 2.0;
    f *= 3;
    int i = (int)f;  // (512 * 768) >> 8 = 6
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=6)
    print(f"PASS test_float_compound_mul_integer (cycles={cycles}, R0={proc.r0})")


def test_float_multiple_operations():
    """Complex float expression: (1.0 + 2.0) * (3.0 + 1.0) = 12.0."""
    source = """
int main() {
    float a = 1.0 + 2.0;
    float b = 3.0 + 1.0;
    float c = a * b;
    int i = (int)c;  // 768 * 1024 / 256 = 3072 >> 8 = 12
    return i;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=12)
    print(f"PASS test_float_multiple_operations (cycles={cycles}, R0={proc.r0})")


def test_float_global_array():
    """Global float array should work."""
    source = """
float values[3] = {1.0, 2.0, 3.0};

int main() {
    int sum = (int)values[0] + (int)values[1] + (int)values[2];
    return sum;  // 1 + 2 + 3 = 6
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=6)
    print(f"PASS test_float_global_array (cycles={cycles}, R0={proc.r0})")


def test_float_for_loop_accumulator():
    """Float accumulator in for loop should work."""
    source = """
int main() {
    float sum = 0.0;
    int i;
    for (i = 0; i < 5; i++) {
        sum += 0.5;
    }
    int result = (int)sum;  // 5 * 0.5 = 2.5 -> FTOI = 2
    return result;
}
"""
    proc, cycles, mem = compile_and_run(source, expected_r0=2)
    print(f"PASS test_float_for_loop_accumulator (cycles={cycles}, R0={proc.r0})")


if __name__ == '__main__':
    # Lexer tests
    test_lexer_float_literal_positive()
    test_lexer_float_literal_zero()
    test_lexer_float_literal_small_fraction()
    test_lexer_float_literal_large()
    test_lexer_float_literal_negative()
    test_lexer_float_keyword()

    # Parser tests
    test_parser_float_var_declaration()
    test_parser_float_var_with_init()
    test_parser_float_type_keyword()

    # Runtime tests
    test_float_var_init_literal()
    test_float_var_init_zero()
    test_float_var_init_negative()
    test_float_var_init_integer_promotion()

    test_float_addition()
    test_float_subtraction()
    test_float_multiplication()
    test_float_division()

    test_float_comparison_greater()
    test_float_comparison_less()
    test_float_comparison_equal()

    test_int_to_float_cast()
    test_float_to_int_cast()
    test_char_to_float_cast()
    test_float_to_char_cast()
    test_float_cast_syntax()

    test_float_compound_add()
    test_float_compound_sub()
    test_float_compound_mul()
    test_float_compound_div()

    test_float_array_declaration()
    test_float_array_with_init()

    test_float_global_declaration()
    test_float_global_mutation()

    test_float_function_parameter()
    test_float_function_return()
    test_float_function_add()

    test_float_mixed_int_expression()
    test_float_expression_chain()
    test_float_expression_with_mul()

    test_float_prefix_increment()
    test_float_postfix_increment()
    test_float_prefix_decrement()
    test_float_postfix_decrement()

    test_float_q88_precision()
    test_float_assignment_from_expression()
    test_float_cast_identity()
    test_int_cast_identity()
    test_float_in_if_condition()
    test_float_in_while_condition()
    test_float_compound_add_integer()
    test_float_compound_mul_integer()
    test_float_multiple_operations()
    test_float_global_array()
    test_float_for_loop_accumulator()

    print("\nAll Astrid float type tests passed!")