"""
Regression tests: NoBASIC's register allocator must treat every NUMBER as a
full 16-bit signed value, whether an expression gets constant-folded at
compile time or evaluated at runtime.

Before this fix, `core/exec_handlers.py`'s DIV/MOD/NOT/shift opcodes (which
mask and interpret values purely by the destination register's width, with
no separate sign-awareness) silently disagreed with the constant folder
whenever the generic register allocator's default (`generate_assignment`'s
hardcoded "R1 for numeric temps", and `self.allocation_order`'s R-registers-
first default) handed out an 8-bit R register for a value that needed to
stay a full 16-bit two's-complement pattern. E.g. `x = -7 / 2` folded to -3
at compile time, but the same computation forced through a runtime DIV on an
8-bit-allocated loop variable computed 249 // 2 = 124 -- the register width
the allocator happened to choose silently changed the answer for identical
source-level values.

Fixing register width alone also exposed a second, distinct gap: Nova-16's
DIV/MOD opcodes are unsigned at the hardware level (core/exec_handlers.py's
_div/_mod do a raw `//`/`%` on the register's bit pattern), so even with
both operands correctly held in full-width P registers, `-7 / 2` divided the
*unsigned* pattern 65529 by 2 and got 32764. Closing that required emitting
actual sign-correcting codegen (_emit_signed_div/_emit_signed_mod in
generator.py) around the unsigned DIV/MOD opcodes.

See feedback_nova_independent_implementations_drift memory for the full
history of this bug class.
"""

import math
import sys
import tempfile
from pathlib import Path

import pytest


from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.analyzer import SemanticAnalyzer
from compiler.codegen.generator import CodeGenerator

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
    tokens = Lexer().tokenize(source)
    program = Parser().parse(tokens)
    SemanticAnalyzer().analyze(program)
    generator = CodeGenerator(enable_optimizations=optimize)
    asm_text = generator.generate(program)
    return asm_text, generator


def _read_variable(cpu, generator, varname: str) -> int:
    if varname in generator.var_reg:
        reg = generator.var_reg[varname]
        if reg.startswith('R'):
            return cpu.Rregisters[int(reg[1:])]
        if reg.startswith('P'):
            return cpu.Pregisters[int(reg[1:])]
        raise AssertionError(f"Unrecognized register name: {reg}")
    if varname in generator.spill_slots:
        return cpu.memory.read_word(generator.spill_slots[varname])
    raise AssertionError(
        f"Variable {varname!r} not found in var_reg or spill_slots "
        f"(var_reg={generator.var_reg}, spill_slots={generator.spill_slots})"
    )


def _run_and_get_variable(source: str, varname: str, optimize: bool) -> int:
    asm_text, generator = _compile(source, optimize)

    with tempfile.TemporaryDirectory() as tmpdir:
        asm_path = Path(tmpdir) / "prog.asm"
        asm_path.write_text(asm_text, encoding="utf-8")

        assembler = Assembler(log=None)
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


def _to_signed_16(value: int) -> int:
    return value - 0x10000 if value >= 0x8000 else value


class TestFoldVsRuntimeWidthAgreement:
    """A value forced through a runtime op on a narrow-allocated variable
    (a FOR loop counter with a tiny declared range) must match the same
    computation constant-folded at compile time."""

    @pytest.mark.parametrize("fold_expr,runtime_body,varname", [
        ("-7 / 2", "FOR i = -7 TO -7\nx = i / 2\nNEXT", "x"),
        ("NOT 5", "FOR i = 5 TO 5\nx = NOT i\nNEXT", "x"),
        ("1 << 10", "FOR i = 1 TO 1\nx = i << 10\nNEXT", "x"),
        ("-1 << 3", "FOR i = -1 TO -1\nx = i << 3\nNEXT", "x"),
        ("NOT -1", "FOR i = -1 TO -1\nx = NOT i\nNEXT", "x"),
    ])
    def test_folded_and_runtime_results_agree(self, fold_expr, runtime_body, varname):
        fold_source = f"x = {fold_expr}"
        folded = _run_and_get_variable(fold_source, varname, optimize=True)
        runtime = _run_and_get_variable(runtime_body, varname, optimize=True)
        assert folded == runtime, (
            f"{fold_expr}: constant-folded {folded} != runtime {runtime}"
        )


class TestSignedDivision:
    """Nova-16's DIV opcode is unsigned hardware; NoBASIC's '/' must still
    truncate toward zero like a signed division, matching Python's
    int(a / b) for same-magnitude cases."""

    @pytest.mark.parametrize("a,b", [
        (-7, 2), (7, -2), (-7, -2), (7, 2),
        (-8, 4), (8, -4), (-9, 3), (0, 5), (-1, 3), (1, -1),
    ])
    def test_div_truncates_toward_zero_for_all_sign_combinations(self, a, b):
        expected = int(a / b)  # Python's int() truncates toward zero
        source = f"x = {a} / {b}"
        result = _to_signed_16(_run_and_get_variable(source, "x", optimize=True))
        assert result == expected, f"{a}/{b}: got {result}, expected {expected}"

    @pytest.mark.parametrize("a,b", [
        (-7, 2), (7, -2), (-7, -2), (7, 2), (-9, 4), (9, -4),
    ])
    def test_div_matches_between_folded_and_runtime_paths(self, a, b):
        fold_source = f"x = {a} / {b}"
        runtime_source = f"FOR i = {a} TO {a}\nx = i / {b}\nNEXT"
        folded = _run_and_get_variable(fold_source, "x", optimize=True)
        runtime = _run_and_get_variable(runtime_source, "x", optimize=True)
        assert folded == runtime


class TestSignedModuloCodegenHelper:
    """MOD/'%' has no lexer token in NoBASIC (confirmed: neither appears
    anywhere in compiler/lexer/tokens.py or the parser), so
    generator.py::_emit_signed_mod is unreachable from real NoBASIC source
    today. Exercise it directly against the real CPU so it's still verified
    -- and so it's ready the moment '%'/MOD becomes a real operator."""

    def _run_mod(self, a: int, b: int) -> int:
        generator = CodeGenerator()
        generator.current_output = generator.output
        generator.output.append(f"MOV P0, {a & 0xFFFF}")
        generator.output.append(f"MOV P1, {b & 0xFFFF}")
        generator._emit_signed_mod("P0", "P1")
        generator.output.append("HLT")
        asm_text = "\n".join(generator.output)

        with tempfile.TemporaryDirectory() as tmpdir:
            asm_path = Path(tmpdir) / "prog.asm"
            asm_path.write_text(asm_text, encoding="utf-8")
            assembler = Assembler(log=None)
            assert assembler.assemble(str(asm_path)), asm_text
            cpu = _make_cpu()
            entry_point = cpu.memory.load(str(asm_path.with_suffix(".bin")))
            cpu.pc = entry_point
            cycles = 0
            while not cpu.halted and cycles < 2000:
                cpu.step()
                cycles += 1
            return _to_signed_16(cpu.Pregisters[0])

    @pytest.mark.parametrize("a,b", [
        (-7, 2), (7, -2), (-7, -2), (7, 2), (0, 5), (-9, 4), (9, -4),
    ])
    def test_mod_matches_c_style_truncating_semantics(self, a, b):
        expected = int(math.fmod(a, b))  # C-style: result takes dividend's sign
        result = self._run_mod(a, b)
        assert result == expected, f"{a} MOD {b}: got {result}, expected {expected}"


class TestDynamicPRegisterSpillCorrectness:
    """Forcing every NUMBER through P registers (only ~7 available, P0-P6)
    means expressions with many simultaneously-live variables can exhaust
    the pool where the old R+P combined pool had slack.
    _evict_dead_variable_for_p_register() dynamically spills a register-
    resident variable that's provably dead from that point forward (reusing
    the same live_at_point/program_counter interference data
    allocate_register() already trusts) rather than hard-failing. This
    doesn't just check that compilation succeeds -- it runs the result on
    the real CPU and checks the arithmetic is still correct, since a wrong
    eviction choice would silently corrupt a still-needed variable instead
    of raising an error."""

    def test_complex_expression_with_many_variables_computes_correct_result(self):
        source = (
            "a = 3\nb = 5\nc = 7\nd = 11\ne = 13\nf = 17\n"
            "result = a + b * c - d / e + f\n"
        )
        # a + (b*c) - (d/e) + f = 3 + 35 - 0 + 17 = 55  (11/13 truncates to 0)
        expected = 3 + (5 * 7) - int(11 / 13) + 17
        result = _to_signed_16(_run_and_get_variable(source, "result", optimize=True))
        assert result == expected

    def test_many_negative_variables_stay_correctly_signed_under_pressure(self):
        source = (
            "a = -3\nb = -5\nc = -7\nd = -11\ne = -13\nf = -17\n"
            "result = a + b + c + d + e + f\n"
        )
        expected = -3 + -5 + -7 + -11 + -13 + -17
        result = _to_signed_16(_run_and_get_variable(source, "result", optimize=True))
        assert result == expected
