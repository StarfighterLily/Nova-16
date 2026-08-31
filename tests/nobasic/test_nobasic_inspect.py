"""Tests for NoBASIC inspection helpers and CLI entry behavior."""

from pathlib import Path

import pytest

import nobasic_inspect
from compiler.utils.error import CompilerError


class _DummyNode:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _StubLexer:
    def tokenize(self, source, source_file):
        return [f"TOK({len(source)})", f"FILE({Path(source_file).name})"]


class _StubParser:
    def parse(self, tokens, source_file):
        return _DummyNode(
            statements=[
                _DummyNode(kind="Assign", target="A", value=1),
                _DummyNode(kind="Disp", value="Hello"),
            ],
            meta="root",
        )


class _StubSymbolTable:
    variables = {"A": "NUMBER", "Name": "STRING"}


class _StubAnalyzer:
    def __init__(self):
        self.symbol_table = _StubSymbolTable()

    def analyze(self, ast, source_file):
        return None


class _StubGenerator:
    def generate(self, ast):
        return "ORG 0x0000\nHLT\n"


class _FailingLexer:
    def tokenize(self, source, source_file):
        raise CompilerError("lexer failed")


def _install_success_stubs(monkeypatch):
    monkeypatch.setattr(nobasic_inspect, "Lexer", _StubLexer)
    monkeypatch.setattr(nobasic_inspect, "Parser", _StubParser)
    monkeypatch.setattr(nobasic_inspect, "SemanticAnalyzer", _StubAnalyzer)
    monkeypatch.setattr(nobasic_inspect, "CodeGenerator", _StubGenerator)


def test_inspect_all_prints_results_without_output_dir(tmp_path, monkeypatch, capsys):
    _install_success_stubs(monkeypatch)
    source_file = tmp_path / "program.nobasic"
    source_file.write_text('Disp "Hello"\n')

    inspector = nobasic_inspect.NoBASICInspector(str(source_file))

    assert inspector.inspect_all() is True

    out = capsys.readouterr().out
    assert "NoBASIC Inspection Results" in out
    assert "TOKENS:" in out
    assert "SYMBOLS:" in out
    assert "ASSEMBLY (first 20 lines):" in out


def test_inspect_all_saves_all_artifacts_when_output_dir_provided(tmp_path, monkeypatch, capsys):
    _install_success_stubs(monkeypatch)
    source_file = tmp_path / "save_me.nobasic"
    source_file.write_text("A = 1\n")
    output_dir = tmp_path / "inspect_output"

    inspector = nobasic_inspect.NoBASICInspector(str(source_file))

    assert inspector.inspect_all(str(output_dir)) is True

    ast_file = output_dir / "save_me_ast.json"
    symbols_file = output_dir / "save_me_symbols.json"
    tokens_file = output_dir / "save_me_tokens.txt"
    asm_file = output_dir / "save_me_assembly.asm"

    assert ast_file.exists()
    assert symbols_file.exists()
    assert tokens_file.exists()
    assert asm_file.exists()
    assert "A" in symbols_file.read_text()
    assert "TOK(" in tokens_file.read_text()
    assert "HLT" in asm_file.read_text()
    assert "Inspection results saved to" in capsys.readouterr().out


def test_inspect_all_returns_false_on_compiler_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(nobasic_inspect, "Lexer", _FailingLexer)
    monkeypatch.setattr(nobasic_inspect, "Parser", _StubParser)
    monkeypatch.setattr(nobasic_inspect, "SemanticAnalyzer", _StubAnalyzer)
    monkeypatch.setattr(nobasic_inspect, "CodeGenerator", _StubGenerator)

    source_file = tmp_path / "broken.nobasic"
    source_file.write_text("bad\n")

    inspector = nobasic_inspect.NoBASICInspector(str(source_file))

    assert inspector.inspect_all() is False
    assert "Inspection error: Error: lexer failed" in capsys.readouterr().out


def test_ast_to_dict_truncates_deep_nodes_and_ignores_private_fields(tmp_path, monkeypatch):
    _install_success_stubs(monkeypatch)
    source_file = tmp_path / "ast.nobasic"
    source_file.write_text("A=1\n")

    inspector = nobasic_inspect.NoBASICInspector(str(source_file))

    deep = _DummyNode(child=_DummyNode(child=_DummyNode(child=_DummyNode(value=99))), _secret="x")
    result = inspector._ast_to_dict(deep, max_depth=1)

    assert result["type"] == "_DummyNode"
    assert "_secret" not in result
    assert result["child"]["type"] == "_DummyNode"
    assert result["child"]["child"]["truncated"] is True


def test_symbols_to_dict_uses_analyzer_symbol_table(tmp_path, monkeypatch):
    _install_success_stubs(monkeypatch)
    source_file = tmp_path / "symbols.nobasic"
    source_file.write_text("A=1\n")

    inspector = nobasic_inspect.NoBASICInspector(str(source_file))
    symbols = inspector._symbols_to_dict()

    assert symbols == {
        "A": {"type": "NUMBER"},
        "Name": {"type": "STRING"},
    }


def test_print_ast_level_handles_statement_lists_and_attribute_nodes(tmp_path, monkeypatch, capsys):
    _install_success_stubs(monkeypatch)
    source_file = tmp_path / "ast_print.nobasic"
    source_file.write_text("A=1\n")

    inspector = nobasic_inspect.NoBASICInspector(str(source_file))

    ast_with_statements = {
        "type": "ProgramNode",
        "statements": [
            {"type": "Stmt", "value": "one"},
            {"type": "Stmt", "value": "two"},
            {"type": "Stmt", "value": "three"},
            {"type": "Stmt", "value": "four"},
        ],
    }

    inspector._print_ast_level(ast_with_statements, depth=0, max_depth=2)
    inspector._print_ast_level({"type": "Literal", "value": "42"}, depth=0, max_depth=2)
    inspector._print_ast_level({"type": "Skipped"}, depth=5, max_depth=2)

    out = capsys.readouterr().out
    assert "ProgramNode: 4 statements" in out
    assert "... and 1 more" in out
    assert "Literal: value=42" in out
    assert "Skipped" not in out


def test_main_returns_usage_error_when_no_args(monkeypatch, capsys):
    monkeypatch.setattr(nobasic_inspect.sys, "argv", ["nobasic_inspect.py"])

    assert nobasic_inspect.main() == 1

    out = capsys.readouterr().out
    assert "Usage: python nobasic_inspect.py" in out


def test_main_returns_error_for_missing_file(monkeypatch, tmp_path, capsys):
    missing = tmp_path / "does_not_exist.nobasic"
    monkeypatch.setattr(nobasic_inspect.sys, "argv", ["nobasic_inspect.py", str(missing)])

    assert nobasic_inspect.main() == 1
    assert f"File not found: {missing}" in capsys.readouterr().out


def test_main_returns_zero_when_inspection_succeeds(monkeypatch, tmp_path):
    source_file = tmp_path / "ok.nobasic"
    output_dir = tmp_path / "out"
    source_file.write_text("A=1\n")

    class _InspectorSuccess:
        def __init__(self, source_path):
            self.source_path = source_path

        def inspect_all(self, output):
            assert output == str(output_dir)
            return True

    monkeypatch.setattr(nobasic_inspect, "NoBASICInspector", _InspectorSuccess)
    monkeypatch.setattr(
        nobasic_inspect.sys,
        "argv",
        ["nobasic_inspect.py", str(source_file), str(output_dir)],
    )

    assert nobasic_inspect.main() == 0


def test_main_returns_one_when_inspection_fails(monkeypatch, tmp_path):
    source_file = tmp_path / "fail.nobasic"
    source_file.write_text("A=1\n")

    class _InspectorFailure:
        def __init__(self, source_path):
            self.source_path = source_path

        def inspect_all(self, output):
            assert output is None
            return False

    monkeypatch.setattr(nobasic_inspect, "NoBASICInspector", _InspectorFailure)
    monkeypatch.setattr(nobasic_inspect.sys, "argv", ["nobasic_inspect.py", str(source_file)])

    assert nobasic_inspect.main() == 1
