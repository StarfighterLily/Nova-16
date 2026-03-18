"""Robustness tests for reusable NoBASIC codegen pipeline state and memory guards."""

import re

import pytest

import nobasic_compiler
from compiler.codegen.generator import CodeGenerator
from compiler.codegen.live_range_scheduler import LiveRangeScheduler
from compiler.lexer.lexer import Lexer
from compiler.parser.ast import StructType
from compiler.parser.parser import Parser
from compiler.semantic.analyzer import SemanticAnalyzer
from compiler.utils.error import CodeGenError


def _analyze_program(source: str):
    lexer = Lexer()
    parser = Parser()
    analyzer = SemanticAnalyzer()
    tokens = lexer.tokenize(source)
    program = parser.parse(tokens)
    analyzer.analyze(program)
    return program


def test_generate_resets_struct_state_between_calls():
    generator = CodeGenerator()

    first_program = _analyze_program("""
    struct Point x y end
    p.x = 1
    """)
    generator.generate(first_program)

    assert generator.struct_types
    assert generator.struct_bases
    assert generator.struct_instances

    second_program = _analyze_program("value = 2")
    second_output = generator.generate(second_program)

    assert generator.struct_types == {}
    assert generator.struct_bases == {}
    assert generator.struct_instances == {}
    assert "; Struct Point declared" not in second_output
    assert "; Allocate struct p (Point)" not in second_output


def test_generate_resets_spill_and_liveness_state_between_calls():
    generator = CodeGenerator()
    generator.spill_slots = {"stale": 0x7000}
    generator.next_spill_address = 0x7002
    generator.live_ranges = {"stale": (1, 3)}
    generator.live_at_point = {1: {"stale"}}
    generator.auto_free_registers = {"R0"}
    generator.register_usage["R0"] = True

    program = _analyze_program("value = 3")
    generator.generate(program)

    assert generator.spill_slots == {}
    assert generator.next_spill_address == generator.spill_base_address
    assert "stale" not in generator.live_ranges
    assert "value" in generator.live_ranges
    assert 1 not in generator.live_at_point or "stale" not in generator.live_at_point[1]
    assert "R0" not in generator.auto_free_registers
    assert generator.register_usage["R0"] is False


def test_generate_with_error_remapping_wraps_runtime_codegen_failures(tmp_path):
    source_file = tmp_path / "program.nobasic"
    source_file.write_text("Pause\n")

    class FailingGenerator:
        def generate(self, ast):
            raise RuntimeError("Register exhaustion")

    with pytest.raises(CodeGenError) as exc:
        nobasic_compiler.generate_with_error_remapping(
            FailingGenerator(),
            object(),
            str(source_file),
            [(str(source_file.resolve()), 1)],
        )

    assert exc.value.filename == str(source_file)
    assert exc.value.line == 1
    assert exc.value.column == 1
    assert exc.value.message == "Register exhaustion"


@pytest.mark.parametrize(
    ("exception_type", "message"),
    [
        (TypeError, "unsupported operand type"),
        (ValueError, "invalid constant fold"),
    ],
)
def test_generate_with_error_remapping_wraps_non_compiler_codegen_failures(tmp_path, exception_type, message):
    source_file = tmp_path / "program.nobasic"
    source_file.write_text("Pause\n")

    class FailingGenerator:
        def generate(self, ast):
            raise exception_type(message)

    with pytest.raises(CodeGenError) as exc:
        nobasic_compiler.generate_with_error_remapping(
            FailingGenerator(),
            object(),
            str(source_file),
            [(str(source_file.resolve()), 1)],
        )

    assert exc.value.filename == str(source_file)
    assert exc.value.line == 1
    assert exc.value.column == 1
    assert exc.value.message == message


def test_variable_and_list_descriptor_allocations_respect_spill_boundary():
    generator = CodeGenerator()
    generator.next_address = generator.spill_base_address - 2

    assert generator.get_variable_address("x") == generator.spill_base_address - 2

    with pytest.raises(CodeGenError, match="variable 'y'"):
        generator.get_variable_address("y")

    generator.list_descriptors = {}
    generator.next_address = generator.spill_base_address - 2
    with pytest.raises(CodeGenError, match="list descriptor 'L1'"):
        generator._get_or_create_list_descriptor("L1")


def test_struct_and_buffer_allocations_respect_spill_boundary():
    generator = CodeGenerator()
    generator.struct_types["point"] = StructType("Point", ["x", "y"])
    generator.next_address = generator.spill_base_address - 2

    with pytest.raises(CodeGenError, match=r"struct 'p' \(Point\)"):
        generator.allocate_struct_instance("p", "point")

    generator.next_address = generator.spill_base_address - 128
    with pytest.raises(CodeGenError, match="string concatenation buffer"):
        generator._reserve_data_memory(256, "string concatenation buffer")


def test_default_codegen_enables_post_generation_optimizations_for_real_program():
    source = """
    a = 1
    b = 2
    c = a + b
    d = c + 4
    if d > 3 then
        disp("ok")
    end
    while a < d
        a = a + 1
    end
    """
    program = _analyze_program(source)

    default_output = CodeGenerator().generate(program)
    explicit_output = CodeGenerator(
        enable_optimizations=True,
        enable_peephole=True,
        enable_live_range_scheduling=True,
    ).generate(program)
    disabled_output = CodeGenerator(
        enable_optimizations=True,
        enable_peephole=False,
        enable_live_range_scheduling=False,
    ).generate(program)

    assert default_output == explicit_output
    assert "DEFSTR \"ok\"" in default_output
    assert "WHILE" not in default_output
    assert re.search(r"\bJ(?:LT|LE|GT|GE|Z|NZ)\b", default_output)
    assert "MOV R0, R0" not in default_output
    assert len(default_output.splitlines()) <= len(disabled_output.splitlines())


def test_large_program_skips_live_range_scheduler_cutoff(monkeypatch):
    source = "\n".join(["pause"] * 200)
    program = _analyze_program(source)

    def fail_schedule(self, assembly_lines, variable_lifetimes=None):
        raise AssertionError("live range scheduler should have been skipped for oversized assembly")

    monkeypatch.setattr(LiveRangeScheduler, "schedule", fail_schedule)

    output = CodeGenerator(enable_peephole=False, enable_live_range_scheduling=True).generate(program)

    assert output.count("KEYSTAT R0") == 200
    assert output.strip().endswith("HLT")