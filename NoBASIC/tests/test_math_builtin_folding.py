"""
Regression tests: compile-time constant folding of math builtins must agree
with the real Nova-16 opcodes it's pre-computing.

optimizations.py::ExpressionSimplifier._fold_builtin_call previously used
different unit conventions and fixed-point scaling than the runtime opcode
handlers in core/exec_handlers.py -- e.g. the SIN/COS/TAN/ATAN/ASIN/ACOS fold
wrapped the input/output in math.radians()/math.degrees() that the real SIN
opcode (core/exec_handlers.py::_sin) never applies, and DEG/RAD's fold had
the conversion running in the opposite direction from the DEG/RAD opcodes.
This meant `a = 45: x = SIN(a)` (folded away to a literal by the optimizer,
since `a` is a compile-time constant) and the same program with a
non-foldable `a` (falls through to the real SIN opcode at runtime) silently
produced *different* results for the same logical input -- purely
depending on whether the optimizer happened to be able to fold it.

These tests compile identical NoBASIC source twice -- once with
optimizations on (folds the call to a literal MOV) and once off (emits the
real opcode) -- run both through the actual Nova-16 CPU (core/exec.py via
nova_cpu.py), and assert they compute the same result. See
feedback_nova_flag_scheduler / feedback_nova_signed_offset_addressing
memory for the project's history of exactly this class of bug: independent
implementations (here, an AST-level optimization vs. the CPU opcode it
mirrors) silently disagreeing.
"""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))  # NoBASIC package root

from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.analyzer import SemanticAnalyzer
from compiler.codegen.generator import CodeGenerator
from compiler.codegen.optimizations import ExpressionSimplifier
from compiler.parser.ast import LiteralExpr, DataType

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from nova_assembler import Assembler
from nova_cpu import CPU
from nova.memory import Memory
from nova_gfx import GFX
from nova_keyboard import NovaKeyboard
from nova_sound import NovaSound


def _make_cpu():
    memory = Memory()
    gfx = GFX()
    keyboard = NovaKeyboard()
    sound = NovaSound()
    cpu = CPU(memory, gfx, keyboard, sound)
    keyboard.cpu = cpu
    memory.gfx_system = gfx
    return cpu


def _compile(source: str, optimize: bool):
    """Compile NoBASIC source; return (asm_text, generator)."""
    tokens = Lexer().tokenize(source)
    program = Parser().parse(tokens)
    SemanticAnalyzer().analyze(program)
    generator = CodeGenerator(enable_optimizations=optimize)
    asm_text = generator.generate(program)
    return asm_text, generator


def _read_variable(cpu, generator, varname: str) -> int:
    """Read a NoBASIC variable's final value from wherever the register
    allocator put it (register or spilled memory slot)."""
    if varname in generator.var_reg:
        reg = generator.var_reg[varname]
        if reg.startswith('R'):
            return cpu.Rregisters[int(reg[1:])]
        if reg.startswith('P'):
            return cpu.Pregisters[int(reg[1:])]
        raise AssertionError(f"Unrecognized register name: {reg}")
    if varname in generator.spill_slots:
        addr = generator.spill_slots[varname]
        return cpu.memory.read_word(addr)
    raise AssertionError(
        f"Variable {varname!r} not found in var_reg or spill_slots "
        f"(var_reg={generator.var_reg}, spill_slots={generator.spill_slots})"
    )


def _run_and_get_variable(source: str, varname: str, optimize: bool) -> int:
    """Compile `source`, run it to completion on the real Nova-16 CPU, and
    return the final value of NoBASIC variable `varname`."""
    asm_text, generator = _compile(source, optimize)

    with tempfile.TemporaryDirectory() as tmpdir:
        asm_path = Path(tmpdir) / "prog.asm"
        asm_path.write_text(asm_text, encoding="utf-8")

        assembler = Assembler()
        assert assembler.assemble(str(asm_path)), (
            f"Assembly failed (optimize={optimize}) for:\n{asm_text}"
        )

        bin_path = asm_path.with_suffix(".bin")
        cpu = _make_cpu()
        entry_point = cpu.memory.load(str(bin_path))
        cpu.pc = entry_point

        cycles = 0
        while not cpu.halted and cycles < 20000:
            cpu.step()
            cycles += 1
        assert cpu.halted, f"Program did not halt (optimize={optimize}): {asm_text}"

        return _read_variable(cpu, generator, varname)


# (function, argument) pairs chosen to stay within each builtin's valid
# domain post-fix (e.g. ASIN/ACOS need |arg/256| <= 1).
MATH_BUILTIN_CASES = [
    ("SIN", 45), ("SIN", 402),
    ("COS", 45), ("COS", 0),
    ("TAN", 30),
    ("ATAN", 100), ("ATAN", -100),
    ("ASIN", 100), ("ACOS", 100),
    ("DEG", 90), ("DEG", 180), ("DEG", -90),
    ("RAD", 402), ("RAD", 128), ("RAD", -402),
    ("FLOOR", 314), ("CEIL", 314), ("ROUND", 314), ("TRUNC", 314),
    ("FRAC", 314), ("INTGR", 314),
    ("FLOOR", -100), ("CEIL", -100), ("ROUND", -100), ("TRUNC", -100),
    ("FRAC", -100), ("INTGR", -100),
    ("LOG", 512), ("LOG", -512),
    ("SIN", -45), ("COS", -45), ("TAN", -30),
]


class TestMathBuiltinFoldingMatchesRuntime:
    @pytest.mark.parametrize("func,value", MATH_BUILTIN_CASES)
    def test_folded_and_runtime_results_agree(self, func, value):
        source = f"a = {value}\nx = {func.lower()}(a)"

        folded_result = _run_and_get_variable(source, "x", optimize=True)
        runtime_result = _run_and_get_variable(source, "x", optimize=False)

        assert folded_result == runtime_result, (
            f"{func}({value}): constant-folded result {folded_result} != "
            f"runtime-opcode result {runtime_result}"
        )


class TestFoldBuiltinCallGroundTruth:
    """Direct unit tests pinning `_fold_builtin_call`'s output to values
    computed independently (not copy-pasted from optimizations.py), so a
    regression that breaks both the fold *and* the formula used here in the
    same way would still be caught by TestMathBuiltinFoldingMatchesRuntime
    above, while a typo unique to the fold is caught here.
    """

    def setup_method(self):
        self.simplifier = ExpressionSimplifier()

    def _fold(self, name: str, *values: int):
        args = [LiteralExpr(v, DataType.NUMBER) for v in values]
        result = self.simplifier._fold_builtin_call(name, args)
        assert result is not None, f"{name}({values}) unexpectedly failed to fold"
        return result.value

    def test_sin_cos_use_fixed_point_radians_not_degrees(self):
        import math
        # sin(45/256 rad) * 256, NOT sin(radians(45)) * 256
        assert self._fold("SIN", 45) == int(math.sin(45 / 256.0) * 256)
        assert self._fold("COS", 45) == int(math.cos(45 / 256.0) * 256)

    def test_tan_uses_raw_radians_and_scale_1000_not_256(self):
        import math
        assert self._fold("TAN", 30) == int(math.tan(30) * 1000)

    def test_atan_asin_acos_stay_in_fixed_point_radians(self):
        import math
        # No math.degrees() conversion: output is fixed-point (x256) radians,
        # matching _atan/_asin/_acos in core/exec_handlers.py.
        assert self._fold("ATAN", 100) == int(math.atan(100 / 256.0) * 256)
        assert self._fold("ASIN", 100) == int(math.asin(100 / 256.0) * 256)
        assert self._fold("ACOS", 100) == int(math.acos(100 / 256.0) * 256)

    def test_deg_converts_plain_degrees_to_fixed_point_radians(self):
        import math
        assert self._fold("DEG", 90) == int((90 * math.pi / 180.0) * 256)

    def test_rad_converts_fixed_point_radians_to_plain_degrees(self):
        import math
        assert self._fold("RAD", 402) == int((402 / 256.0) * 180.0 / math.pi)

    def test_floor_ceil_round_trunc_frac_intgr_treat_input_as_fixed_point(self):
        import math
        v = 314  # NOT floor/ceil/etc of the raw literal -- of v/256.0
        assert self._fold("FLOOR", v) == int(math.floor(v / 256.0))
        assert self._fold("CEIL", v) == int(math.ceil(v / 256.0))
        assert self._fold("ROUND", v) == int(round(v / 256.0))
        assert self._fold("TRUNC", v) == int(v / 256.0)
        assert self._fold("FRAC", v) == int(math.fmod(v, 256))
        assert self._fold("INTGR", v) == int(v / 256.0)

    def test_trunc_frac_truncate_toward_zero_not_floor(self):
        """-100/256 == -0.39: TRUNC must give 0 (toward zero), not -1
        (floor). Distinguishes int(v/256.0) from the old v // 256, which
        are identical for positive v and only diverge on negatives."""
        import math
        v = -100
        assert self._fold("TRUNC", v) == 0
        assert self._fold("INTGR", v) == 0
        assert self._fold("FRAC", v) == -100
        # v == TRUNC(v) * 256 + FRAC(v)
        assert self._fold("TRUNC", v) * 256 + self._fold("FRAC", v) == v

    def test_log_divides_by_256_before_taking_log(self):
        import math
        assert self._fold("LOG", 512) == int(math.log(512 / 256.0) * 256)

    def test_asin_acos_out_of_domain_skip_folding_rather_than_clamp(self):
        # Previously these clamped the ratio to [-1, 1] and folded anyway,
        # silently diverging from the runtime opcode (which falls back to 0
        # via its own try/except on out-of-domain input). Skipping the fold
        # lets the real opcode compute the same fallback at runtime.
        assert self.simplifier._fold_builtin_call(
            "ASIN", [LiteralExpr(1000, DataType.NUMBER)]
        ) is None
        assert self.simplifier._fold_builtin_call(
            "ACOS", [LiteralExpr(1000, DataType.NUMBER)]
        ) is None
