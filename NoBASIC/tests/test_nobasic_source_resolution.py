"""Regression tests for shared NoBASIC source path resolution across tools."""

from pathlib import Path
from types import SimpleNamespace

import nobasic_compiler
import nobasic_debugger
import nobasic_inspect


class _DummyNode:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _StubLexer:
    def tokenize(self, source, source_file):
        return [f"FILE({Path(source_file).name})", f"LEN({len(source)})"]


class _StubParser:
    def parse(self, tokens, source_file):
        return _DummyNode(statements=[_DummyNode(kind="Pause")])


class _StubAnalyzer:
    def __init__(self):
        self.symbol_table = SimpleNamespace(variables={"value": "NUMBER"})

    def analyze(self, ast, source_file):
        return None


class _StubGenerator:
    def generate(self, ast):
        return "ORG 0x0000\nHLT\n"


def _make_fake_nobasic_tree(tmp_path):
    fake_nobasic_dir = tmp_path / "NoBASIC"
    progs_dir = fake_nobasic_dir / "progs"
    progs_dir.mkdir(parents=True)
    source_file = progs_dir / "demo.nobasic"
    source_file.write_text("Pause\n")
    return fake_nobasic_dir, source_file


def test_inspector_accepts_source_paths_relative_to_nobasic_dir(tmp_path, monkeypatch, capsys):
    fake_nobasic_dir, source_file = _make_fake_nobasic_tree(tmp_path)

    monkeypatch.setattr(nobasic_compiler, "__file__", str(fake_nobasic_dir / "nobasic_compiler.py"))
    monkeypatch.setattr(nobasic_inspect, "Lexer", _StubLexer)
    monkeypatch.setattr(nobasic_inspect, "Parser", _StubParser)
    monkeypatch.setattr(nobasic_inspect, "SemanticAnalyzer", _StubAnalyzer)
    monkeypatch.setattr(nobasic_inspect, "CodeGenerator", _StubGenerator)

    inspector = nobasic_inspect.NoBASICInspector("progs/demo.nobasic")

    assert inspector.source_file == str(source_file.resolve())
    assert inspector.inspect_all() is True
    output = capsys.readouterr().out
    assert f"Source file: {source_file.resolve()}" in output
    assert "FILE(demo.nobasic)" in output


def test_inspector_main_accepts_source_paths_relative_to_nobasic_dir(tmp_path, monkeypatch):
    fake_nobasic_dir, source_file = _make_fake_nobasic_tree(tmp_path)
    calls = []

    class _InspectorStub:
        def __init__(self, source_path):
            calls.append(("init", source_path))

        def inspect_all(self, output_dir):
            calls.append(("inspect_all", output_dir))
            return True

    monkeypatch.setattr(nobasic_compiler, "__file__", str(fake_nobasic_dir / "nobasic_compiler.py"))
    monkeypatch.setattr(nobasic_inspect, "NoBASICInspector", _InspectorStub)
    monkeypatch.setattr(
        nobasic_inspect.sys,
        "argv",
        ["nobasic_inspect.py", "progs/demo.nobasic"],
    )

    assert nobasic_inspect.main() == 0
    assert calls == [
        ("init", str(source_file.resolve())),
        ("inspect_all", None),
    ]


def test_debugger_accepts_source_paths_relative_to_nobasic_dir(tmp_path, monkeypatch, capsys):
    fake_nobasic_dir, source_file = _make_fake_nobasic_tree(tmp_path)
    calls = []
    analyzer = _StubAnalyzer()
    ast = _DummyNode(kind="Program")

    def fake_run_frontend_pipeline(source_path, lexer_factory, parser_factory, analyzer_factory):
        calls.append((source_path, lexer_factory, parser_factory, analyzer_factory))
        return SimpleNamespace(
            resolved_source_file=source_file.resolve(),
            source="Pause\n",
            line_map=[(str(source_file.resolve()), 1)],
            tokens=["TOKENS"],
            ast=ast,
            analyzer=analyzer,
        )

    monkeypatch.setattr(nobasic_compiler, "__file__", str(fake_nobasic_dir / "nobasic_compiler.py"))
    monkeypatch.setattr(nobasic_debugger, "run_frontend_pipeline", fake_run_frontend_pipeline)
    monkeypatch.setattr(nobasic_debugger, "Lexer", _StubLexer)
    monkeypatch.setattr(nobasic_debugger, "Parser", _StubParser)
    monkeypatch.setattr(nobasic_debugger, "SemanticAnalyzer", _StubAnalyzer)

    debugger = nobasic_debugger.NoBASICDebugger("progs/demo.nobasic")

    assert debugger.source_file == str(source_file.resolve())
    assert debugger.source_lines == ["Pause\n"]
    assert debugger.parse_program() is True
    assert calls == [
        (str(source_file.resolve()), _StubLexer, _StubParser, _StubAnalyzer),
    ]
    output = capsys.readouterr().out
    assert f"Parsing {source_file.resolve()}..." in output