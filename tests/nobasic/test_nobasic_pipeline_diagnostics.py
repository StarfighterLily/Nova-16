"""Tests for include-aware diagnostics across NoBASIC pipeline tools."""

from pathlib import Path
from types import SimpleNamespace

import nobasic_debugger
import nobasic_inspect
import nobasic_profiler
import pytest

from compiler.utils.error import CompilerError


class _DummyNode:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _StubLexer:
    def tokenize(self, source, source_file):
        return ["TOKENS"]


class _StubParser:
    def parse(self, tokens, source_file):
        return _DummyNode(kind="Program", statements=[])


class _StubAnalyzer:
    def __init__(self):
        self.symbol_table = SimpleNamespace(variables={"value": "NUMBER"})

    def analyze(self, ast, source_file):
        return None


def test_inspector_remaps_codegen_errors_from_included_files(tmp_path, monkeypatch, capsys):
    source_file = tmp_path / "main.nobasic"
    include_file = tmp_path / "lib.nobasic"
    include_file.write_text("value = 1\n")
    source_file.write_text('Include "lib.nobasic"\nPause\n')

    class FailingGenerator:
        def generate(self, ast):
            raise CompilerError("bad codegen", str(source_file.resolve()), 1, 4)

    monkeypatch.setattr(nobasic_inspect, "Lexer", _StubLexer)
    monkeypatch.setattr(nobasic_inspect, "Parser", _StubParser)
    monkeypatch.setattr(nobasic_inspect, "SemanticAnalyzer", _StubAnalyzer)
    monkeypatch.setattr(nobasic_inspect, "CodeGenerator", FailingGenerator)

    inspector = nobasic_inspect.NoBASICInspector(str(source_file))

    assert inspector.inspect_all() is False
    output = capsys.readouterr().out
    assert f"Inspection error: Error in {include_file.resolve()} at line 1, column 4: bad codegen" in output


def test_profiler_uses_shared_pipeline_and_remaps_codegen_errors(tmp_path, monkeypatch):
    source_file = tmp_path / "main.nobasic"
    include_file = tmp_path / "lib.nobasic"
    source_file.write_text('Include "lib.nobasic"\n')
    include_file.write_text("value = 1\n")
    calls = []

    monkeypatch.setattr(nobasic_profiler, "Lexer", _StubLexer)
    monkeypatch.setattr(nobasic_profiler, "Parser", _StubParser)
    monkeypatch.setattr(nobasic_profiler, "SemanticAnalyzer", _StubAnalyzer)

    class FailingGenerator:
        def generate(self, ast):
            raise CompilerError("profiler codegen failed", str(source_file.resolve()), 1, 2)

    def fake_run_frontend_pipeline(source_path, lexer_factory, parser_factory, analyzer_factory):
        calls.append((source_path, lexer_factory, parser_factory, analyzer_factory))
        analyzer = _StubAnalyzer()
        return SimpleNamespace(
            resolved_source_file=source_file.resolve(),
            source="value = 1\n",
            line_map=[(str(include_file.resolve()), 1)],
            tokens=["TOKENS"],
            ast=_DummyNode(kind="Program"),
            analyzer=analyzer,
        )

    monkeypatch.setattr(nobasic_profiler, "run_frontend_pipeline", fake_run_frontend_pipeline)
    monkeypatch.setattr(nobasic_profiler, "CodeGenerator", FailingGenerator)

    profiler = nobasic_profiler.NoBASICProfiler(str(source_file))

    with pytest.raises(CompilerError) as exc:
        profiler.profile_compilation()

    assert calls == [(str(source_file), _StubLexer, _StubParser, _StubAnalyzer)]
    assert exc.value.filename == str(include_file.resolve())
    assert exc.value.line == 1
    assert exc.value.column == 2
    assert exc.value.message == "profiler codegen failed"


def test_debugger_parse_program_uses_shared_pipeline(tmp_path, monkeypatch, capsys):
    source_file = tmp_path / "program.nobasic"
    source_file.write_text("Pause\n")
    calls = []
    analyzer = _StubAnalyzer()
    ast = _DummyNode(kind="Program")

    def fake_run_frontend_pipeline(source_path, lexer_factory, parser_factory, analyzer_factory):
        calls.append((source_path, lexer_factory, parser_factory, analyzer_factory))
        return SimpleNamespace(
            resolved_source_file=source_file.resolve(),
            source="Pause\n",
            line_map=[(str(source_file.resolve()), 1)],
            tokens=["TOKENS", "MORE"],
            ast=ast,
            analyzer=analyzer,
        )

    monkeypatch.setattr(nobasic_debugger, "run_frontend_pipeline", fake_run_frontend_pipeline)
    monkeypatch.setattr(nobasic_debugger, "Lexer", _StubLexer)
    monkeypatch.setattr(nobasic_debugger, "Parser", _StubParser)
    monkeypatch.setattr(nobasic_debugger, "SemanticAnalyzer", _StubAnalyzer)

    debugger = nobasic_debugger.NoBASICDebugger(str(source_file))

    assert debugger.parse_program() is True
    assert calls == [(str(source_file), _StubLexer, _StubParser, _StubAnalyzer)]
    assert debugger.tokens == ["TOKENS", "MORE"]
    assert debugger.ast is ast
    assert debugger.analyzer is analyzer
    assert debugger.symbols == {"value": "NUMBER"}
    assert debugger.line_map == [(str(source_file.resolve()), 1)]
    assert debugger.resolved_source_file == source_file.resolve()
    output = capsys.readouterr().out
    assert "Lexical analysis complete: 2 tokens" in output
    assert "Semantic analysis complete" in output


def test_debugger_parse_program_reports_pipeline_errors(tmp_path, monkeypatch, capsys):
    source_file = tmp_path / "program.nobasic"
    source_file.write_text('Include "lib.nobasic"\n')
    include_file = tmp_path / "lib.nobasic"
    include_file.write_text("bad\n")

    def fake_run_frontend_pipeline(source_path, lexer_factory, parser_factory, analyzer_factory):
        raise CompilerError("unexpected token", str(include_file.resolve()), 1, 1)

    monkeypatch.setattr(nobasic_debugger, "run_frontend_pipeline", fake_run_frontend_pipeline)
    monkeypatch.setattr(nobasic_debugger, "Lexer", _StubLexer)
    monkeypatch.setattr(nobasic_debugger, "Parser", _StubParser)
    monkeypatch.setattr(nobasic_debugger, "SemanticAnalyzer", _StubAnalyzer)

    debugger = nobasic_debugger.NoBASICDebugger(str(source_file))

    assert debugger.parse_program() is False
    assert f"Error: Error in {include_file.resolve()} at line 1, column 1: unexpected token" in capsys.readouterr().out


def test_debugger_generate_code_uses_shared_codegen_wrapper(tmp_path, monkeypatch):
    source_file = tmp_path / "program.nobasic"
    source_file.write_text("Pause\n")
    debugger = nobasic_debugger.NoBASICDebugger(str(source_file))
    debugger.ast = _DummyNode(kind="Program")
    debugger.line_map = [(str(source_file.resolve()), 1)]
    debugger.resolved_source_file = source_file.resolve()

    captured = {}

    def fake_generate_with_error_remapping(generator, ast, source_path, line_map):
        captured["args"] = (generator, ast, source_path, line_map)
        return "ORG 0x0000\nHLT\n"

    monkeypatch.setattr(nobasic_debugger, "generate_with_error_remapping", fake_generate_with_error_remapping)

    assembly = debugger.generate_code()

    assert assembly == "ORG 0x0000\nHLT\n"
    assert captured["args"] == (
        debugger.generator,
        debugger.ast,
        str(source_file.resolve()),
        [(str(source_file.resolve()), 1)],
    )


def test_debugger_compile_and_load_program_reports_codegen_errors(tmp_path, monkeypatch, capsys):
    source_file = tmp_path / "program.nobasic"
    include_file = tmp_path / "lib.nobasic"
    source_file.write_text('Include "lib.nobasic"\n')
    include_file.write_text("Pause\n")

    debugger = nobasic_debugger.NoBASICDebugger(str(source_file))
    debugger.ast = _DummyNode(kind="Program")
    debugger.line_map = [(str(include_file.resolve()), 1)]
    debugger.resolved_source_file = source_file.resolve()

    monkeypatch.setattr(debugger, "initialize_emulator", lambda: True)

    def fake_generate_with_error_remapping(generator, ast, source_path, line_map):
        raise CompilerError("debugger codegen failed", str(include_file.resolve()), 1, 7)

    monkeypatch.setattr(nobasic_debugger, "generate_with_error_remapping", fake_generate_with_error_remapping)

    assert debugger.compile_and_load_program() is False
    assert (
        f"Failed to compile and load program: Error in {include_file.resolve()} at line 1, column 7: debugger codegen failed"
        in capsys.readouterr().out
    )