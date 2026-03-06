"""Tests for NoBASIC compiler entrypoint and CLI argument parsing."""

from pathlib import Path
from types import SimpleNamespace
import subprocess

import pytest

import nobasic_compiler
from compiler.utils.error import CompilerError


def _install_pipeline_stubs(monkeypatch):
    """Install minimal lexer/parser/analyzer/generator stubs for compile tests."""
    captured = {
        "generator_kwargs": None,
        "generator_instance": None,
        "tokenize_args": None,
        "parse_args": None,
        "analyze_args": None,
    }

    class StubLexer:
        def tokenize(self, source, source_file):
            captured["tokenize_args"] = (source, source_file)
            return ["TOKENS"]

    class StubParser:
        def parse(self, tokens, source_file):
            captured["parse_args"] = (tokens, source_file)
            return "AST"

    class StubAnalyzer:
        def analyze(self, ast, source_file):
            captured["analyze_args"] = (ast, source_file)

    class StubGenerator:
        def __init__(self, **kwargs):
            captured["generator_kwargs"] = kwargs
            captured["generator_instance"] = self
            self.opt_config = {}

        def generate(self, ast):
            assert ast == "AST"
            return "HLT\n"

    monkeypatch.setattr(nobasic_compiler, "Lexer", StubLexer)
    monkeypatch.setattr(nobasic_compiler, "Parser", StubParser)
    monkeypatch.setattr(nobasic_compiler, "SemanticAnalyzer", StubAnalyzer)
    monkeypatch.setattr(nobasic_compiler, "CodeGenerator", StubGenerator)
    return captured


def test_compile_nobasic_uses_default_output_and_writes_bin(tmp_path, monkeypatch, capsys):
    captured = _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "program.nobasic"
    source_file.write_text("Pause\n")

    def fake_run(command, capture_output, text):
        output_asm = Path(command[2])
        output_asm.with_suffix(".bin").write_bytes(b"\x00")
        return SimpleNamespace(stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    nobasic_compiler.compile_nobasic(str(source_file))

    asm_file = source_file.with_suffix(".asm")
    bin_file = source_file.with_suffix(".bin")
    assert asm_file.exists()
    assert bin_file.exists()
    assert asm_file.read_text() == "HLT\n"
    assert captured["tokenize_args"][0] == "Pause\n"
    assert captured["parse_args"] == (["TOKENS"], str(source_file))
    assert captured["analyze_args"] == ("AST", str(source_file))
    assert "Compilation successful" in capsys.readouterr().out


def test_compile_nobasic_passes_optimization_flags(tmp_path, monkeypatch):
    captured = _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "opts.nobasic"
    source_file.write_text("Pause\n")
    output_file = tmp_path / "custom_output.asm"

    def fake_run(command, capture_output, text):
        Path(command[2]).with_suffix(".bin").write_bytes(b"\x00")
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    nobasic_compiler.compile_nobasic(
        str(source_file),
        output_file=str(output_file),
        enable_optimizations=True,
        debug_optimizations=True,
        enable_peephole=True,
        enable_live_range_scheduling=True,
    )

    assert captured["generator_kwargs"] == {
        "debug_allocation": True,
        "enable_optimizations": True,
        "enable_peephole": True,
        "enable_live_range_scheduling": True,
    }
    assert output_file.exists()
    assert output_file.with_suffix(".bin").exists()


def test_compile_nobasic_exits_if_assembler_does_not_produce_binary(tmp_path, monkeypatch, capsys):
    _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "fail_bin.nobasic"
    source_file.write_text("Pause\n")

    def fake_run(command, capture_output, text):
        return SimpleNamespace(stdout="assembler output", stderr="assembler error")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic(str(source_file))
    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert "Assembly failed" in output
    assert "Assembler output" in output


def test_compile_nobasic_verbose_mode_prints_optimization_details(tmp_path, monkeypatch, capsys):
    captured = _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "verbose.nobasic"
    source_file.write_text("Pause\n")

    def fake_run(command, capture_output, text):
        output_asm = Path(command[2])
        output_asm.with_suffix(".bin").write_bytes(b"\x00")
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    nobasic_compiler.compile_nobasic(
        str(source_file),
        verbose=True,
        enable_optimizations=True,
        debug_optimizations=True,
        enable_peephole=True,
        enable_live_range_scheduling=True,
    )

    assert captured["generator_instance"].opt_config["debug_optimizations"] is True
    output = capsys.readouterr().out
    assert "Compiling" in output
    assert "Optimizations: ENABLED" in output
    assert "Peephole optimization: ENABLED" in output
    assert "Live range scheduling: ENABLED" in output
    assert "Code generation complete" in output
    assert "Binary written to" in output


def test_compile_nobasic_verbose_mode_reports_optimizations_disabled(tmp_path, monkeypatch, capsys):
    _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "verbose_disabled.nobasic"
    source_file.write_text("Pause\n")

    def fake_run(command, capture_output, text):
        output_asm = Path(command[2])
        output_asm.with_suffix(".bin").write_bytes(b"\x00")
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    nobasic_compiler.compile_nobasic(
        str(source_file),
        verbose=True,
        enable_optimizations=False,
        enable_peephole=True,
        enable_live_range_scheduling=True,
    )

    output = capsys.readouterr().out
    assert "Optimizations: DISABLED" in output


def test_compile_nobasic_handles_unexpected_exception(tmp_path, monkeypatch, capsys):
    source_file = tmp_path / "unexpected.nobasic"
    source_file.write_text("Pause\n")

    class StubLexer:
        def tokenize(self, source, source_file):
            return ["TOKENS"]

    class FailingParser:
        def parse(self, tokens, source_file):
            raise RuntimeError("boom")

    monkeypatch.setattr(nobasic_compiler, "Lexer", StubLexer)
    monkeypatch.setattr(nobasic_compiler, "Parser", FailingParser)

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic(str(source_file))
    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert "Unexpected error: boom" in output
    assert "Traceback" in output


def test_compile_nobasic_handles_compiler_error(tmp_path, monkeypatch):
    source_file = tmp_path / "bad.nobasic"
    source_file.write_text("bad\n")

    class FailingLexer:
        def tokenize(self, source, source_file):
            raise CompilerError("broken syntax")

    monkeypatch.setattr(nobasic_compiler, "Lexer", FailingLexer)

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic(str(source_file))
    assert exc.value.code == 1


def test_main_shows_usage_when_no_arguments(monkeypatch, capsys):
    monkeypatch.setattr(nobasic_compiler.sys, "argv", ["nobasic_compiler.py"])

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.main()
    assert exc.value.code == 1
    assert "Usage:" in capsys.readouterr().out


def test_main_parses_flags_and_calls_compile(monkeypatch, tmp_path):
    source_file = tmp_path / "sample.nobasic"
    source_file.write_text("Pause\n")
    output_file = tmp_path / "sample.asm"
    called = {}

    def fake_compile(*args):
        called["args"] = args

    monkeypatch.setattr(nobasic_compiler, "compile_nobasic", fake_compile)
    monkeypatch.setattr(
        nobasic_compiler.sys,
        "argv",
        [
            "nobasic_compiler.py",
            str(source_file),
            "--verbose",
            "--disable-optimizations",
            "--enable-peephole",
            "--enable-live-range",
            "--debug-optimizations",
            "--output",
            str(output_file),
        ],
    )

    nobasic_compiler.main()

    assert called["args"] == (
        str(source_file),
        str(output_file),
        True,
        True,
        True,
        True,
        True,
    )


def test_main_parses_disable_flags_and_calls_compile(monkeypatch, tmp_path):
    source_file = tmp_path / "sample_disable.nobasic"
    source_file.write_text("Pause\n")
    called = {}

    def fake_compile(*args):
        called["args"] = args

    monkeypatch.setattr(nobasic_compiler, "compile_nobasic", fake_compile)
    monkeypatch.setattr(
        nobasic_compiler.sys,
        "argv",
        [
            "nobasic_compiler.py",
            str(source_file),
            "--disable-optimizations",
            "--disable-peephole",
            "--disable-live-range",
        ],
    )

    nobasic_compiler.main()

    assert called["args"] == (
        str(source_file),
        None,
        False,
        False,
        False,
        False,
        False,
    )


def test_main_supports_legacy_positional_output(monkeypatch, tmp_path):
    source_file = tmp_path / "sample.nobasic"
    source_file.write_text("Pause\n")
    output_file = tmp_path / "legacy.asm"
    called = {}

    def fake_compile(*args):
        called["args"] = args

    monkeypatch.setattr(nobasic_compiler, "compile_nobasic", fake_compile)
    monkeypatch.setattr(
        nobasic_compiler.sys,
        "argv",
        ["nobasic_compiler.py", str(source_file), str(output_file)],
    )

    nobasic_compiler.main()
    assert called["args"][1] == str(output_file)


def test_main_fails_for_unknown_option(monkeypatch, tmp_path, capsys):
    source_file = tmp_path / "sample.nobasic"
    source_file.write_text("Pause\n")
    monkeypatch.setattr(
        nobasic_compiler.sys,
        "argv",
        ["nobasic_compiler.py", str(source_file), "--not-a-real-option"],
    )

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.main()
    assert exc.value.code == 1
    assert "Unknown option" in capsys.readouterr().out


def test_main_fails_when_output_flag_missing_argument(monkeypatch, tmp_path, capsys):
    source_file = tmp_path / "sample.nobasic"
    source_file.write_text("Pause\n")
    monkeypatch.setattr(
        nobasic_compiler.sys,
        "argv",
        ["nobasic_compiler.py", str(source_file), "--output"],
    )

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.main()
    assert exc.value.code == 1
    assert "--output requires an argument" in capsys.readouterr().out