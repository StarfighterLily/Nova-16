"""Resilience tests for NoBASIC pipeline entrypoints and CLI wrappers."""

from pathlib import Path

import pytest

import nobasic_compiler
import nobasic_profiler
from compiler.utils.error import CompilerError


def _install_compile_stubs(monkeypatch):
    class StubLexer:
        def tokenize(self, source, source_file):
            return ["TOKENS"]

    class StubParser:
        def parse(self, tokens, source_file):
            return "AST"

    class StubAnalyzer:
        def analyze(self, ast, source_file):
            return None

    class StubGenerator:
        def __init__(self, **_kwargs):
            self.opt_config = {}

        def generate(self, ast):
            assert ast == "AST"
            return "HLT\n"

    monkeypatch.setattr(nobasic_compiler, "Lexer", StubLexer)
    monkeypatch.setattr(nobasic_compiler, "Parser", StubParser)
    monkeypatch.setattr(nobasic_compiler, "SemanticAnalyzer", StubAnalyzer)
    monkeypatch.setattr(nobasic_compiler, "CodeGenerator", StubGenerator)


def test_compile_nobasic_reports_custom_assembler_callback_exceptions(tmp_path, monkeypatch, capsys):
    _install_compile_stubs(monkeypatch)
    source_file = tmp_path / "callback_fail.nobasic"
    source_file.write_text("Pause\n")
    output_file = tmp_path / "callback_fail.asm"

    def failing_assemble(_assembly_file, _verbose, _emit):
        raise OSError("assembler callback exploded")

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic(
            str(source_file),
            output_file=str(output_file),
            assemble_callback=failing_assemble,
        )

    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert f"Assembly failed for {output_file}: assembler callback exploded" in output
    assert "Unexpected error" not in output
    assert output_file.exists()
    assert not output_file.with_suffix(".bin").exists()


def test_profiler_main_reports_pipeline_compiler_errors(monkeypatch, tmp_path, capsys):
    source_file = tmp_path / "profile_error.nobasic"
    source_file.write_text("Pause\n")
    calls = []

    class StubProfiler:
        def __init__(self, source_path):
            calls.append(("init", source_path))

        def profile_compilation(self):
            calls.append(("profile",))
            raise CompilerError("register exhaustion", str(source_file.resolve()), 3, 7)

        def generate_report(self):
            calls.append(("report",))
            return "SHOULD NOT PRINT"

        def profile_with_cprofile(self):
            calls.append(("detailed",))

    monkeypatch.setattr(nobasic_profiler, "NoBASICProfiler", StubProfiler)
    monkeypatch.setattr(nobasic_profiler, "resolve_source_file_path", lambda value: source_file.resolve())
    monkeypatch.setattr(
        nobasic_profiler.sys,
        "argv",
        ["nobasic_profiler.py", str(source_file), "--detailed"],
    )

    assert nobasic_profiler.main() == 1

    assert calls == [
        ("init", str(source_file.resolve())),
        ("profile",),
    ]
    output = capsys.readouterr().out
    assert "Profiling error: Error in" in output
    assert "register exhaustion" in output
    assert "SHOULD NOT PRINT" not in output
