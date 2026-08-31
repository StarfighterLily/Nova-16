"""Tests for shared NoBASIC frontend pipeline consumers."""

from pathlib import Path

import pytest

import nobasic_compiler
import nobasic_inspect
import nobasic_profiler
from compiler.parser.ast import DataType
from compiler.utils.error import CompilerError


class _DummyNode:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_run_frontend_pipeline_expands_includes_before_lexing(tmp_path):
    source_file = tmp_path / "main.nobasic"
    include_file = tmp_path / "lib.nobasic"
    include_file.write_text("x = 1\n")
    source_file.write_text('Include "lib.nobasic"\nPause\n')

    captured = {}

    class StubLexer:
        def tokenize(self, source, source_file_arg):
            captured["tokenize"] = (source, source_file_arg)
            return ["TOKENS"]

    class StubParser:
        def parse(self, tokens, source_file_arg):
            captured["parse"] = (tokens, source_file_arg)
            return _DummyNode(kind="Program")

    class StubAnalyzer:
        def __init__(self):
            self.symbol_table = _DummyNode(variables={})

        def analyze(self, ast, source_file_arg):
            captured["analyze"] = (ast.kind, source_file_arg)

    pipeline = nobasic_compiler.run_frontend_pipeline(
        str(source_file),
        lexer_factory=StubLexer,
        parser_factory=StubParser,
        analyzer_factory=StubAnalyzer,
    )

    assert pipeline.source == "x = 1\nPause\n"
    assert pipeline.line_map[0] == (str(include_file.resolve()), 1)
    assert pipeline.line_map[1] == (str(source_file.resolve()), 2)
    assert captured["tokenize"] == ("x = 1\nPause\n", str(source_file.resolve()))
    assert captured["parse"] == (["TOKENS"], str(source_file.resolve()))
    assert captured["analyze"] == ("Program", str(source_file.resolve()))


def test_run_frontend_pipeline_remaps_include_errors(tmp_path):
    source_file = tmp_path / "main.nobasic"
    include_file = tmp_path / "lib.nobasic"
    include_file.write_text("x = 1\ny = #\n")
    source_file.write_text('Include "lib.nobasic"\nPause\n')

    class FailingLexer:
        def tokenize(self, source, source_file_arg):
            raise CompilerError("Unexpected character: #", source_file_arg, 2, 5)

    with pytest.raises(CompilerError) as exc:
        nobasic_compiler.run_frontend_pipeline(
            str(source_file),
            lexer_factory=FailingLexer,
        )

    assert exc.value.filename == str(include_file.resolve())
    assert exc.value.line == 2
    assert exc.value.column == 5


def test_inspector_uses_shared_frontend_pipeline_for_includes(tmp_path, monkeypatch, capsys):
    source_file = tmp_path / "main.nobasic"
    include_file = tmp_path / "lib.nobasic"
    include_file.write_text("A = 1\n")
    source_file.write_text('Include "lib.nobasic"\nPause\n')

    class StubLexer:
        def tokenize(self, source, source_file_arg):
            return [f"LEN({len(source)})", f"FILE({Path(source_file_arg).name})"]

    class StubParser:
        def parse(self, tokens, source_file_arg):
            return _DummyNode(statements=[_DummyNode(kind="Assign", target="A", value=1)])

    class StubAnalyzer:
        def __init__(self):
            self.symbol_table = _DummyNode(variables={"A": DataType.NUMBER})

        def analyze(self, ast, source_file_arg):
            return None

    class StubGenerator:
        def generate(self, ast):
            return "ORG 0x0000\nHLT\n"

    monkeypatch.setattr(nobasic_inspect, "Lexer", StubLexer)
    monkeypatch.setattr(nobasic_inspect, "Parser", StubParser)
    monkeypatch.setattr(nobasic_inspect, "SemanticAnalyzer", StubAnalyzer)
    monkeypatch.setattr(nobasic_inspect, "CodeGenerator", StubGenerator)

    inspector = nobasic_inspect.NoBASICInspector(str(source_file))

    assert inspector.inspect_all() is True

    output = capsys.readouterr().out
    assert "LEN(12)" in output
    assert "A: DataType.NUMBER" in output


def test_profiler_preprocesses_includes_and_counts_symbol_types(tmp_path, monkeypatch, capsys):
    source_file = tmp_path / "main.nobasic"
    include_file = tmp_path / "lib.nobasic"
    include_file.write_text('name = "ok"\n')
    source_file.write_text('Include "lib.nobasic"\nvalue = 7\n')

    captured = {}

    class StubLexer:
        def tokenize(self, source, source_file_arg):
            captured["tokenize"] = (source, source_file_arg)
            return ["TOKENS"]

    class StubParser:
        def parse(self, tokens, source_file_arg):
            return _DummyNode(kind="Program")

    class StubAnalyzer:
        def __init__(self):
            self.symbol_table = _DummyNode(
                variables={
                    "name": DataType.STRING,
                    "value": DataType.NUMBER,
                    "legacy": {"type": "STRING"},
                }
            )

        def analyze(self, ast, source_file_arg):
            return None

    class StubGenerator:
        def generate(self, ast):
            return "ORG 0x0000\nHLT\n"

    monkeypatch.setattr(nobasic_profiler, "Lexer", StubLexer)
    monkeypatch.setattr(nobasic_profiler, "Parser", StubParser)
    monkeypatch.setattr(nobasic_profiler, "SemanticAnalyzer", StubAnalyzer)
    monkeypatch.setattr(nobasic_profiler, "CodeGenerator", StubGenerator)

    profiler = nobasic_profiler.NoBASICProfiler(str(source_file))
    summary = profiler.profile_compilation()
    memory_usage = profiler.analyze_memory_usage()

    assert captured["tokenize"] == ('name = "ok"\nvalue = 7\n', str(source_file.resolve()))
    assert summary["token_count"] == 1
    assert summary["symbol_count"] == 3
    assert memory_usage == {
        "total_variables": 3,
        "number_variables": 1,
        "string_variables": 2,
        "estimated_memory_bytes": 6,
    }
    assert "Profiling compilation of" in capsys.readouterr().out