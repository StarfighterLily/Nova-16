"""Tests for Astrid builtin constant-folding optimizations.

Verifies that the ExpressionSimplifier folds math builtins with constant
arguments to the exact same values the Nova-16 runtime opcode handlers
(core/exec_handlers.py) would produce at runtime.

Also verifies that side-effecting builtins are NEVER folded, even with
constant arguments.
"""
import math
import os
import sys

import pytest

# Add project root to path so we can import nova_main and astrid modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add astrid directory to path so we can import astrid_compiler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nova_main import initialize_system
from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser, Number, FuncCall
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


def _simplify_expr(source_expr):
    """Parse a single expression and run it through ExpressionSimplifier."""
    lexer = Lexer(f"int main() {{ int x = {source_expr}; return x; }}")
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    main_func = ast.functions[0]
    var_decl = main_func.body[0]
    simplifier = ExpressionSimplifier()
    return simplifier.simplify(var_decl.value)


# Each case: (expression_source, expected_int_value)
# The expected values match core/exec_handlers.py EXACTLY.
FOLDABLE_BUILTINS = [
    # sin/cos/tan (fixed-point x256; tan is x1000)
    ("sin(0)", int(math.sin(0) * 256)),
    ("sin(256)", int(math.sin(1.0) * 256)),
    ("cos(0)", int(math.cos(0) * 256)),
    ("cos(256)", int(math.cos(1.0) * 256)),
    ("tan(0)", int(math.tan(0) * 1000)),
    # sqrt
    ("sqrt(0)", 0),
    ("sqrt(1)", 1),
    ("sqrt(64)", 8),
    # abs
    ("abs(-42)", 42),
    ("abs(42)", 42),
    # atan/asin/acos (fixed-point x256)
    ("atan(0)", int(math.atan(0) * 256)),
    ("atan(256)", int(math.atan(1.0) * 256)),
    ("asin(0)", int(math.asin(0) * 256)),
    ("acos(0)", int(math.acos(0) * 256)),
    # deg/rad
    ("deg(0)", int((0 * math.pi / 180.0) * 256)),
    ("deg(90)", int((90 * math.pi / 180.0) * 256)),
    ("deg(180)", int((180 * math.pi / 180.0) * 256)),
    ("rad(0)", int((0 / 256.0) * 180.0 / math.pi)),
    ("rad(256)", int((256 / 256.0) * 180.0 / math.pi)),
    # floor/ceil/round/trunc/frac/intgr/int
    ("floor(0)", int(math.floor(0 / 256.0))),
    ("floor(256)", int(math.floor(256 / 256.0))),
    ("ceil(0)", int(math.ceil(0 / 256.0))),
    ("ceil(256)", int(math.ceil(256 / 256.0))),
    ("round(0)", int(round(0 / 256.0))),
    ("round(256)", int(round(256 / 256.0))),
    ("trunc(0)", int(0 / 256.0)),
    ("trunc(256)", int(256 / 256.0)),
    ("frac(0)", int(math.fmod(0, 256))),
    ("frac(256)", int(math.fmod(256, 256))),
    ("intgr(0)", int(0 / 256.0)),
    ("intgr(256)", int(256 / 256.0)),
    # log/exp (fixed-point x256)
    ("log(256)", int(math.log(256 / 256.0) * 256)),
    ("exp(0)", int(math.exp(0) * 256)),
    ("exp(256)", int(math.exp(1.0) * 256)),
    # min/max (binary)
    ("min(10, 20)", 10),
    ("min(20, 10)", 10),
    ("min(5, 5)", 5),
    ("max(10, 20)", 20),
    ("max(20, 10)", 20),
    ("max(5, 5)", 5),
    # powr
    ("powr(2, 0)", 1),
    ("powr(2, 1)", 2),
    ("powr(2, 3)", 8),
    ("powr(10, 2)", 100),
    # clz
    ("clz(0x0001)", 15),
    ("clz(0x8000)", 0),
    ("clz(0xFFFF)", 0),
    ("clz(0x00FF)", 8),
    # ctz
    ("ctz(0x0001)", 0),
    ("ctz(0x0002)", 1),
    ("ctz(0x8000)", 15),
    ("ctz(0xFFFF)", 0),
    # popcnt
    ("popcnt(0)", 0),
    ("popcnt(0x0001)", 1),
    ("popcnt(0x0F0F)", 8),
    ("popcnt(0xFFFF)", 16),
    # swap
    ("swap(0x0000)", 0x0000),
    ("swap(0x1234)", 0x3412),
    ("swap(0xFFFF)", 0xFFFF),
]


@pytest.mark.parametrize("expr_src,expected", FOLDABLE_BUILTINS,
                         ids=[f"{expr}={val}" for expr, val in FOLDABLE_BUILTINS])
def test_builtin_constant_folding(expr_src, expected):
    """Math builtins with constant args must fold to Number(expected)."""
    result = _simplify_expr(expr_src)
    assert isinstance(result, Number), (
        f"{expr_src}: Expected folded Number, got {type(result).__name__}"
    )
    assert int(result.value, 0) == expected, (
        f"{expr_src}: Expected {expected}, got {int(result.value, 0)}"
    )


# Math builtins with out-of-domain constant args must NOT fold.
# The runtime opcode handlers fall back to a default value (0) when the
# domain is violated, and the fold must produce the identical result --
# which it can't at compile time, so it falls through to the real call.
DOMAIN_ERROR_BUILTINS = [
    "asin(512)",    # 512/256 = 2.0 outside [-1, 1]
    "asin(-512)",   # -2.0 outside [-1, 1]
    "acos(512)",    # 2.0 outside [-1, 1]
    "acos(-512)",   # -2.0 outside [-1, 1]
    "sqrt(-1)",     # negative square root
    "log(0)",       # log of zero
    "log(-256)",    # log of negative
    "powr(2, -1)",  # negative exponent
]


@pytest.mark.parametrize("expr_src", DOMAIN_ERROR_BUILTINS,
                         ids=[expr for expr in DOMAIN_ERROR_BUILTINS])
def test_domain_error_builtins_not_folded(expr_src):
    """Out-of-domain builtin calls must NOT be folded at compile time."""
    result = _simplify_expr(expr_src)
    assert isinstance(result, FuncCall), (
        f"{expr_src}: Expected FuncCall (not folded), got {type(result).__name__}"
    )
    print(f"PASS domain-error not-folded: {expr_src}")


# Side-effecting builtins that must NEVER be folded even with constant args.
NON_FOLDABLE_BUILTINS = [
    # Graphics
    "set_mode(1)", "set_vmode(0)", "set_layer(0)", "set_pos(1, 2)",
    "write_screen(1)", "screen_fill(0x0F)",
    "scroll_x(1)", "scroll_y(1)", "screen_rotate(0, 1)",
    "screen_shift(0, 1)", "screen_flip(0)", "draw_line(0, 0)",
    "draw_circle(0, 0)", "screen_invert()", "screen_blit()",
    "set_blend_mode(0)", "draw_char('A')", "set_pointers(1, 2)",
    "write_text(1, 2)", "set_font(0)", "layer_swap(1)", "layer_move(2)",
    "layer_copy(3)",
    # Sound
    "sound_play(1, 2, 3)", "sound_stop()", "sound_trigger(0)",
    "set_timer(0, 255, 80, 3)",
    # Interrupts
    "sti()", "cli()", "iret()", "software_int(0)",
    "enable_interrupts()", "disable_interrupts()",
    # Keyboard
    "key_available()", "key_read()", "key_clear()", "key_count()",
    "key_ctrl(0)",
    # Random (non-deterministic)
    "random()", "random_range(1, 10)",
    # Serial
    "ser_out(65)", "ser_in()", "ser_stat()", "ser_ctrl(0)",
    # Memory
    "memcpy(1, 2, 3)", "memset(1, 2, 3)", "memmove(1, 2, 3)",
    "memcmp(1, 2, 3, 4)", "memtest(1, 2, 3)", "memswap(1, 2, 3)",
    # Bit manipulation (flags/state changing at CPU level)
    "btst(1, 2)", "bset(1, 2)", "bclr(1, 2)", "bflip(1, 2)",
    "xchng(1, 2)",
    # Misc
    "nop()", "pushf()", "popf()", "pusha()", "popa()", "halt()",
    # BCD
    "sed()", "cld()", "cla()",
    "bcd2bin(0x42)", "bin2bcd(42)", "bcdadd(1, 2)", "bcdsub(1, 2)",
    "bcda(1, 2)", "bcds(1, 2)", "bcdcmp(1, 2)",
    # Mouse
    "mouse_ctrl(0)",
]


@pytest.mark.parametrize("expr_src", NON_FOLDABLE_BUILTINS,
                         ids=[expr for expr in NON_FOLDABLE_BUILTINS])
def test_side_effect_builtins_not_folded(expr_src):
    """Side-effecting builtins must NOT be folded, even with constant args."""
    result = _simplify_expr(expr_src)
    assert isinstance(result, FuncCall), (
        f"{expr_src}: Expected FuncCall (not folded), got {type(result).__name__}"
    )


@pytest.mark.parametrize("expr_src", NON_FOLDABLE_BUILTINS,
                         ids=[f"runtime_{expr}" for expr in NON_FOLDABLE_BUILTINS])
def test_side_effect_builtins_compile_and_run(expr_src):
    """Side-effecting builtins compile, assemble, and run successfully."""
    source = f"void main() {{ {expr_src}; }}"
    proc, cycles, mem = compile_and_run(source)
    assert proc.halted, f"{expr_src}: Program did not halt"
    print(f"PASS runtime: {expr_src} (cycles={cycles})")


def test_builtin_folding_compiler_pipeline():
    """A program using folded math builtins should compile, assemble, and run."""
    source = """
int main() {
    int a = abs(-100);
    int b = min(10, 20);
    int c = max(10, 20);
    int d = clz(0x8000);
    int e = ctz(0x0001);
    int f = popcnt(0x0F0F);
    int g = swap(0x1234);
    int h = sqrt(81);
    return a + b + c + d + e + f + h;
}
"""
    # abs(100) + min(10) + max(20) + clz(0) + ctz(0) + popcnt(8) + sqrt(9)
    # = 100 + 10 + 20 + 0 + 0 + 8 + 9 = 147
    proc, cycles, mem = compile_and_run(source, expected_r0=147)
    print(f"PASS test_builtin_folding_compiler_pipeline (cycles={cycles}, R0={proc.r0})")


if __name__ == '__main__':
    # Run all parametrized test cases manually for non-pytest invocation
    failed = 0
    for expr_src, expected in FOLDABLE_BUILTINS:
        try:
            test_builtin_constant_folding(expr_src, expected)
            print(f"PASS fold: {expr_src} -> {expected}")
        except AssertionError as e:
            print(f"FAIL fold: {expr_src}: {e}")
            failed += 1
    for expr_src in NON_FOLDABLE_BUILTINS:
        try:
            test_side_effect_builtins_not_folded(expr_src)
            print(f"PASS not-fold: {expr_src}")
        except AssertionError as e:
            print(f"FAIL not-fold: {expr_src}: {e}")
            failed += 1
    for expr_src in DOMAIN_ERROR_BUILTINS:
        try:
            test_domain_error_builtins_not_folded(expr_src)
            print(f"PASS domain-error not-fold: {expr_src}")
        except AssertionError as e:
            print(f"FAIL domain-error not-fold: {expr_src}: {e}")
            failed += 1
    try:
        test_builtin_folding_compiler_pipeline()
    except AssertionError as e:
        print(f"FAIL pipeline: {e}")
        failed += 1
    if failed:
        print(f"{failed} test(s) failed!")
        sys.exit(1)
    print("All Astrid builtin folding tests passed!")