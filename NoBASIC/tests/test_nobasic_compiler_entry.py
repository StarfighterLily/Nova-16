"""Tests for NoBASIC compiler entrypoint and CLI argument parsing."""

from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
from typing import Any, Dict

import pytest

import nobasic_compiler
from compiler.utils.error import CompilerError

REPO_ROOT = Path(nobasic_compiler.__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from nova_assembler import Assembler
from tests.conftest import opcode_value


def _install_pipeline_stubs(monkeypatch):
    """Install minimal lexer/parser/analyzer/generator stubs for compile tests."""
    captured: Dict[str, Any] = {
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


def _install_in_process_assembler_stub(monkeypatch, *, success=True, messages=None):
    """Install a stub in-process assembler module for compile path tests."""
    calls: Dict[str, Any] = {}
    buffered_messages = list(messages or [])

    class StubAssembler:
        def __init__(self, log=print, trace=False):
            calls["log"] = log
            calls["trace"] = trace

        def assemble(self, filename):
            output_asm = Path(filename)
            calls["filename"] = output_asm
            for message in buffered_messages:
                if calls["log"] is not None:
                    calls["log"](message)
            if success:
                output_asm.with_suffix(".bin").write_bytes(b"\x00")
            return success

    monkeypatch.setattr(
        nobasic_compiler,
        "_get_nova_assembler_module",
        lambda: SimpleNamespace(Assembler=StubAssembler),
    )
    return calls


def test_compile_nobasic_uses_default_output_and_writes_bin(tmp_path, monkeypatch, capsys):
    captured = _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "program.nobasic"
    source_file.write_text("Pause\n")
    _install_in_process_assembler_stub(monkeypatch)

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


def test_compile_nobasic_supports_custom_logger_without_stdout(tmp_path, monkeypatch, capsys):
    _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "logged.nobasic"
    source_file.write_text("Pause\n")
    messages = []
    _install_in_process_assembler_stub(monkeypatch)

    nobasic_compiler.compile_nobasic(str(source_file), verbose=True, log=messages.append)

    assert capsys.readouterr().out == ""
    assert any(message.startswith("Compiling ") for message in messages)
    assert any("Compilation successful" in message for message in messages)


def test_compile_nobasic_can_use_custom_assembler_callback(tmp_path, monkeypatch):
    _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "custom_asm.nobasic"
    source_file.write_text("Pause\n")
    output_file = tmp_path / "custom_asm_output.asm"
    callback_calls = []

    def fake_assemble(assembly_file, verbose, emit):
        callback_calls.append((assembly_file, verbose))
        assembly_file.with_suffix(".bin").write_bytes(b"\x00")
        emit("assembled in process")
        return True

    nobasic_compiler.compile_nobasic(
        str(source_file),
        output_file=str(output_file),
        assemble_callback=fake_assemble,
        log=lambda _message: None,
    )

    assert callback_calls == [(output_file, False)]
    assert output_file.exists()
    assert output_file.with_suffix(".bin").exists()


def test_compile_nobasic_passes_optimization_flags(tmp_path, monkeypatch):
    captured = _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "opts.nobasic"
    source_file.write_text("Pause\n")
    output_file = tmp_path / "custom_output.asm"
    _install_in_process_assembler_stub(monkeypatch)

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


def test_compile_nobasic_defaults_to_enabled_optimizations_and_creates_output_dirs(tmp_path, monkeypatch):
    captured = _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "nested_output.nobasic"
    source_file.write_text("Pause\n")
    output_file = tmp_path / "build" / "artifacts" / "program.asm"
    calls = _install_in_process_assembler_stub(monkeypatch)

    nobasic_compiler.compile_nobasic(str(source_file), output_file=str(output_file))

    assert captured["generator_kwargs"] == {
        "debug_allocation": False,
        "enable_optimizations": True,
        "enable_peephole": True,
        "enable_live_range_scheduling": True,
    }
    assert output_file.parent.is_dir()
    assert output_file.exists()
    assert output_file.with_suffix(".bin").exists()
    assert calls["trace"] is False
    assert Path(calls["filename"]).resolve() == output_file.resolve()


def test_compile_nobasic_rejects_non_asm_output_path_before_assembly(tmp_path, monkeypatch, capsys):
    _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "bad_output.nobasic"
    source_file.write_text("Pause\n")
    output_file = tmp_path / "bad_output.bin"
    assembler_called = False

    def fake_run(command, capture_output, text):
        nonlocal assembler_called
        assembler_called = True
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic(str(source_file), output_file=str(output_file))

    assert exc.value.code == 1
    assert assembler_called is False
    output = capsys.readouterr().out
    assert f"Output file must have .asm extension for target 'nova': {output_file}" in output
    assert output_file.exists() is False


def test_compile_nobasic_exits_if_assembler_does_not_produce_binary(tmp_path, monkeypatch, capsys):
    _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "fail_bin.nobasic"
    source_file.write_text("Pause\n")
    _install_in_process_assembler_stub(monkeypatch, success=False, messages=["assembler error", "assembler output"])

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic(str(source_file))
    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert f"Assembly failed for {source_file.with_suffix('.asm')}" in output
    assert "assembler error" in output
    assert "assembler output" in output


def test_compile_nobasic_exits_if_assembler_returns_nonzero_even_with_binary(tmp_path, monkeypatch, capsys):
    _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "assembler_exit.nobasic"
    source_file.write_text("Pause\n")

    monkeypatch.setattr(nobasic_compiler, "_get_nova_assembler_module", lambda: (_ for _ in ()).throw(ImportError("no module")))

    def fake_run(command, capture_output, text):
        output_asm = Path(command[2])
        output_asm.with_suffix(".bin").write_bytes(b"\x00")
        return SimpleNamespace(returncode=7, stdout="assembler stdout", stderr="assembler stderr")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic(str(source_file))

    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert "Assembly failed with exit code 7" in output
    assert "Assembler stderr: assembler stderr" in output
    assert "Assembler output: assembler stdout" in output


def test_compile_nobasic_reports_assembler_launch_failure(tmp_path, monkeypatch, capsys):
    _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "missing_assembler.nobasic"
    source_file.write_text("Pause\n")

    monkeypatch.setattr(nobasic_compiler, "_get_nova_assembler_module", lambda: (_ for _ in ()).throw(ImportError("no module")))

    def fake_run(command, capture_output, text):
        raise FileNotFoundError("assembler missing")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic(str(source_file))

    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert "Assembly failed: could not execute assembler" in output
    assert "assembler missing" in output


def test_compile_nobasic_removes_stale_binary_before_assembly(tmp_path, monkeypatch, capsys):
    _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "stale_bin.nobasic"
    source_file.write_text("Pause\n")
    stale_bin = source_file.with_suffix(".bin")
    stale_bin.write_bytes(b"stale")

    monkeypatch.setattr(nobasic_compiler, "_get_nova_assembler_module", lambda: (_ for _ in ()).throw(ImportError("no module")))

    def fake_run(command, capture_output, text):
        return SimpleNamespace(stdout="assembler output", stderr="assembler error")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic(str(source_file))

    assert exc.value.code == 1
    assert not stale_bin.exists()
    output = capsys.readouterr().out
    assert "Assembly failed" in output
    assert "Assembler output" in output


def test_compile_nobasic_verbose_mode_prints_optimization_details(tmp_path, monkeypatch, capsys):
    captured = _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "verbose.nobasic"
    source_file.write_text("Pause\n")
    calls = _install_in_process_assembler_stub(monkeypatch, messages=["assembler ok"])

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
    assert "assembler ok" in output
    assert "Binary written to" in output
    assert calls["trace"] is True


def test_compile_nobasic_verbose_mode_reports_optimizations_disabled(tmp_path, monkeypatch, capsys):
    _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "verbose_disabled.nobasic"
    source_file.write_text("Pause\n")
    _install_in_process_assembler_stub(monkeypatch)

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


def test_compile_nobasic_remaps_non_compiler_codegen_failures_from_includes(tmp_path, monkeypatch, capsys):
    source_file = tmp_path / "main.nobasic"
    include_file = tmp_path / "lib.nobasic"
    include_file.write_text("value = 1\n")
    source_file.write_text('Include "lib.nobasic"\nPause\n')

    class StubLexer:
        def tokenize(self, source, source_file):
            return ["TOKENS"]

    class StubParser:
        def parse(self, tokens, source_file):
            return "AST"

    class StubAnalyzer:
        def analyze(self, ast, source_file):
            return None

    class FailingGenerator:
        def __init__(self, **_kwargs):
            self.opt_config = {}

        def generate(self, ast):
            raise TypeError("unsupported assignment target")

    monkeypatch.setattr(nobasic_compiler, "Lexer", StubLexer)
    monkeypatch.setattr(nobasic_compiler, "Parser", StubParser)
    monkeypatch.setattr(nobasic_compiler, "SemanticAnalyzer", StubAnalyzer)
    monkeypatch.setattr(nobasic_compiler, "CodeGenerator", FailingGenerator)

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic(str(source_file))

    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert (
        f"Compilation error: Error in {include_file.resolve()} at line 1, column 1: unsupported assignment target"
        in output
    )
    assert "Unexpected error" not in output
    assert "Traceback" not in output


def test_compile_nobasic_expands_include_directive(tmp_path, monkeypatch):
    captured = _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "main.nobasic"
    include_file = tmp_path / "lib.nobasic"

    include_file.write_text("x = 1\n")
    source_file.write_text('Include "lib.nobasic"\nPause\n')

    def fake_run(command, capture_output, text):
        Path(command[2]).with_suffix(".bin").write_bytes(b"\x00")
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    nobasic_compiler.compile_nobasic(str(source_file))

    assert captured["tokenize_args"][0] == "x = 1\nPause\n"
    assert captured["tokenize_args"][1] == str(source_file)


def test_compile_nobasic_reports_include_cycle(tmp_path, monkeypatch, capsys):
    source_file = tmp_path / "main.nobasic"
    other_file = tmp_path / "other.nobasic"

    source_file.write_text('Include "other.nobasic"\nPause\n')
    other_file.write_text('Include "main.nobasic"\n')

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic(str(source_file))

    assert exc.value.code == 1
    assert "Include cycle detected" in capsys.readouterr().out


def test_compile_nobasic_reports_include_cycle_at_recursive_include_site(tmp_path, capsys):
    source_file = tmp_path / "main.nobasic"
    other_file = tmp_path / "other.nobasic"

    source_file.write_text('Pause\nInclude "other.nobasic"\n')
    other_file.write_text('Pause\nInclude "main.nobasic"\n')

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic(str(source_file))

    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert f"Error in {other_file.resolve()} at line 2" in output
    assert "Include cycle detected: main.nobasic -> other.nobasic -> main.nobasic" in output


def test_compile_nobasic_does_not_expand_include_inside_asm_block(tmp_path, monkeypatch):
    captured = _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "main.nobasic"
    source_file.write_text('Asm\nInclude "missing.nobasic"\nEnd\nPause\n')

    def fake_run(command, capture_output, text):
        Path(command[2]).with_suffix(".bin").write_bytes(b"\x00")
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    nobasic_compiler.compile_nobasic(str(source_file))

    assert 'Include "missing.nobasic"' in captured["tokenize_args"][0]


def test_compile_nobasic_does_not_expand_include_inside_commented_asm_block(tmp_path, monkeypatch):
    captured = _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "main.nobasic"
    source_file.write_text('Asm // raw assembly follows\nInclude "missing.nobasic"\nEnd // back to NoBASIC\nPause\n')

    def fake_run(command, capture_output, text):
        Path(command[2]).with_suffix(".bin").write_bytes(b"\x00")
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    nobasic_compiler.compile_nobasic(str(source_file))

    assert 'Include "missing.nobasic"' in captured["tokenize_args"][0]


def test_compile_nobasic_inline_asm_rtc_registers_round_trip_to_binary(tmp_path):
    source_file = tmp_path / "rtc_inline.nobasic"
    output_file = tmp_path / "rtc_inline.asm"
    source_file.write_text("Asm\nMOV P0, C0\nMOV P1, C1\nHLT\nEnd\n")

    def assemble_callback(assembly_file, verbose, emit):
        assembler = Assembler()
        success = assembler.assemble(str(assembly_file))
        emit(f"assembled={success}")
        return success

    nobasic_compiler.compile_nobasic(
        str(source_file),
        output_file=str(output_file),
        assemble_callback=assemble_callback,
        log=lambda _message: None,
    )

    asm_text = output_file.read_text(encoding='ascii')
    assert "MOV P0, C0" in asm_text
    assert "MOV P1, C1" in asm_text

    binary = output_file.with_suffix('.bin').read_bytes()
    assert opcode_value('C0') in binary
    assert opcode_value('C1') in binary


def test_preprocess_source_returns_line_map_for_included_lines(tmp_path):
    source_file = tmp_path / "main.nobasic"
    include_file = tmp_path / "lib.nobasic"

    include_file.write_text("a = 1\nb = 2\n")
    source_file.write_text('Include "lib.nobasic"\nPause\n')

    source, line_map = nobasic_compiler.preprocess_source(str(source_file))

    assert source == "a = 1\nb = 2\nPause\n"
    assert line_map[0] == (str(include_file.resolve()), 1)
    assert line_map[1] == (str(include_file.resolve()), 2)
    assert line_map[2] == (str(source_file.resolve()), 2)


def test_preprocess_source_expands_include_with_trailing_comment(tmp_path):
    source_file = tmp_path / "main.nobasic"
    include_file = tmp_path / "lib.nobasic"

    include_file.write_text("a = 1\n")
    source_file.write_text('Include "lib.nobasic" // shared helpers\nPause\n')

    source, line_map = nobasic_compiler.preprocess_source(str(source_file))

    assert source == "a = 1\nPause\n"
    assert line_map == [
        (str(include_file.resolve()), 1),
        (str(source_file.resolve()), 2),
    ]


def test_preprocess_source_caches_repeated_nested_includes_per_run(tmp_path, monkeypatch):
    source_file = tmp_path / "main.nobasic"
    first_include = tmp_path / "first.nobasic"
    second_include = tmp_path / "second.nobasic"
    shared_include = tmp_path / "shared.nobasic"

    source_file.write_text('Include "first.nobasic"\nInclude "second.nobasic"\n')
    first_include.write_text('Include "shared.nobasic"\na = 1\n')
    second_include.write_text('Include "shared.nobasic"\nb = 2\n')
    shared_include.write_text('shared = 42\n')

    original_open = open
    open_counts = {}

    def counting_open(path, *args, **kwargs):
        resolved_path = Path(path).resolve()
        open_counts[resolved_path] = open_counts.get(resolved_path, 0) + 1
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", counting_open)

    source, line_map = nobasic_compiler.preprocess_source(str(source_file))

    assert source == "shared = 42\na = 1\nshared = 42\nb = 2\n"
    assert line_map == [
        (str(shared_include.resolve()), 1),
        (str(first_include.resolve()), 2),
        (str(shared_include.resolve()), 1),
        (str(second_include.resolve()), 2),
    ]
    assert open_counts[source_file.resolve()] == 1
    assert open_counts[first_include.resolve()] == 1
    assert open_counts[second_include.resolve()] == 1
    assert open_counts[shared_include.resolve()] == 1


def test_strip_line_comment_preserves_double_slash_inside_string_literal():
    line = 'Include "dir//lib.nobasic" // trailing comment\n'

    assert nobasic_compiler._strip_line_comment(line) == 'Include "dir//lib.nobasic" '


def test_compile_nobasic_remaps_lexer_error_to_included_file(tmp_path, monkeypatch, capsys):
    source_file = tmp_path / "main.nobasic"
    include_file = tmp_path / "lib.nobasic"

    include_file.write_text("x = 10\ny = #\n")
    source_file.write_text('Include "lib.nobasic"\nPause\n')

    class FailingLexer:
        def tokenize(self, source, source_file_arg):
            raise CompilerError("Unexpected character: #", source_file_arg, 2, 5)

    monkeypatch.setattr(nobasic_compiler, "Lexer", FailingLexer)

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic(str(source_file))

    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert f"Error in {include_file.resolve()} at line 2" in output


@pytest.mark.parametrize(
    ("included_source", "expected_line", "expected_message"),
    [
        ("x = sin()\n", 1, "Wrong number of arguments for function 'sin': expected 1, got 0"),
        ("x = unknown_func(1)\n", 1, "Undefined function 'unknown_func'"),
        ("struct Point x y end\nq = p.z\n", 2, "Struct 'Point' has no field 'z'"),
    ],
)
def test_compile_nobasic_remaps_semantic_error_to_included_file(
    tmp_path,
    capsys,
    included_source,
    expected_line,
    expected_message,
):
    source_file = tmp_path / "main.nobasic"
    include_file = tmp_path / "lib.nobasic"

    include_file.write_text(included_source)
    source_file.write_text('Include "lib.nobasic"\nPause\n')

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic(str(source_file))

    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert f"Error in {include_file.resolve()} at line {expected_line}" in output
    assert expected_message in output


def test_preprocess_source_resolves_relative_to_compiler_dir(tmp_path, monkeypatch):
    fake_nobasic_dir = tmp_path / "NoBASIC"
    progs_dir = fake_nobasic_dir / "progs"
    progs_dir.mkdir(parents=True)

    source_file = progs_dir / "starfield.nobasic"
    source_file.write_text("Pause\n")

    monkeypatch.setattr(nobasic_compiler, "__file__", str(fake_nobasic_dir / "nobasic_compiler.py"))

    source, line_map = nobasic_compiler.preprocess_source("progs/starfield.nobasic")

    assert source == "Pause\n"
    assert line_map == [(str(source_file.resolve()), 1)]


def test_compile_nobasic_reports_missing_top_level_source_file(capsys):
    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic("does_not_exist.nobasic")

    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert "Source file not found" in output


def test_compile_nobasic_rejects_directory_source_path(tmp_path, capsys):
    source_dir = tmp_path / "program.nobasic"
    source_dir.mkdir()

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic(str(source_dir))

    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert f"Source path is not a file: {source_dir.resolve()}" in output


def test_compile_nobasic_reports_directory_include_target(tmp_path, capsys):
    source_file = tmp_path / "main.nobasic"
    include_dir = tmp_path / "lib.nobasic"
    include_dir.mkdir()
    source_file.write_text('Include "lib.nobasic"\nPause\n')

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic(str(source_file))

    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert f"Error in {source_file.resolve()} at line 1, column 1" in output
    assert f"Included path is not a file: {include_dir.resolve()}" in output


def test_compile_nobasic_rejects_output_directory_with_asm_suffix(tmp_path, monkeypatch, capsys):
    _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "program.nobasic"
    source_file.write_text("Pause\n")
    output_dir = tmp_path / "artifacts.asm"
    output_dir.mkdir()
    assembler_called = False

    def fake_run(command, capture_output, text):
        nonlocal assembler_called
        assembler_called = True
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic(str(source_file), output_file=str(output_dir))

    assert exc.value.code == 1
    assert assembler_called is False
    output = capsys.readouterr().out
    assert f"Output path is a directory, expected .asm file: {output_dir}" in output


def test_compile_nobasic_rejects_output_path_when_parent_is_file(tmp_path, monkeypatch, capsys):
    _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "program.nobasic"
    source_file.write_text("Pause\n")
    parent_file = tmp_path / "artifacts"
    parent_file.write_text("not a directory\n")
    output_file = parent_file / "program.asm"
    assembler_called = False

    def fake_run(command, capture_output, text):
        nonlocal assembler_called
        assembler_called = True
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic(str(source_file), output_file=str(output_file))

    assert exc.value.code == 1
    assert assembler_called is False
    output = capsys.readouterr().out
    assert f"Output directory is not a directory: {parent_file}" in output
    assert "Unexpected error" not in output


def test_compile_nobasic_include_without_trailing_newline_preserves_boundary(tmp_path, monkeypatch):
    captured = _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "main.nobasic"
    include_file = tmp_path / "math.nobasic"

    include_file.write_text("Function Add(a, b)\n    Return a + b\nEnd")
    source_file.write_text('Include "math.nobasic"\nDisp Add(2,3)\n')

    def fake_run(command, capture_output, text):
        Path(command[2]).with_suffix(".bin").write_bytes(b"\x00")
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    nobasic_compiler.compile_nobasic(str(source_file))

    flattened = captured["tokenize_args"][0]
    assert "End\nDisp Add(2,3)" in flattened


def test_resolve_includes_reports_recursive_failures_at_include_site(tmp_path, monkeypatch):
    source_file = tmp_path / "main.nobasic"
    first_include = tmp_path / "first.nobasic"
    second_include = tmp_path / "second.nobasic"

    source_file.write_text('Pause\nInclude "first.nobasic"\n')
    first_include.write_text('Pause\nInclude "second.nobasic"\n')
    second_include.write_text('Pause\n')

    with pytest.raises(CompilerError) as depth_error:
        nobasic_compiler._resolve_includes_from_file(source_file, max_depth=2)

    assert depth_error.value.filename == str(first_include.resolve())
    assert depth_error.value.line == 2
    assert "Maximum include depth (2) exceeded" in depth_error.value.message

    original_open = open

    def failing_open(path, *args, **kwargs):
        if Path(path).resolve() == second_include.resolve():
            raise OSError("permission denied")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", failing_open)

    with pytest.raises(CompilerError) as read_error:
        nobasic_compiler._resolve_includes_from_file(source_file)

    assert read_error.value.filename == str(first_include.resolve())
    assert read_error.value.line == 2
    assert "Failed to read include file: permission denied" in read_error.value.message


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

    def fake_compile(*args, **kwargs):
        called["args"] = args
        called["kwargs"] = kwargs

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

    assert called["args"][0] == str(source_file)
    assert called["args"][1] == str(output_file)
    assert called["args"][2] is True  # verbose
    assert called["kwargs"].get("target") == "nova"
    assert called["kwargs"].get("enable_linking") is True


def test_main_parses_disable_flags_and_calls_compile(monkeypatch, tmp_path):
    source_file = tmp_path / "sample_disable.nobasic"
    source_file.write_text("Pause\n")
    called = {}

    def fake_compile(*args, **kwargs):
        called["args"] = args
        called["kwargs"] = kwargs

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
    assert called["kwargs"].get("target") == "nova"
    assert called["kwargs"].get("enable_linking") is True


@pytest.mark.parametrize(
    ("extra_args", "expected_enable_optimizations", "expected_debug_optimizations"),
    [
        (["--debug-optimizations", "--disable-optimizations"], True, True),
        (["--disable-optimizations", "--debug-optimizations"], True, True),
        (["--disable-optimizations", "--enable-optimizations"], True, False),
        (["--enable-optimizations", "--disable-optimizations"], False, False),
    ],
)
def test_main_honors_flag_ordering_and_debug_invariant(
    monkeypatch,
    tmp_path,
    extra_args,
    expected_enable_optimizations,
    expected_debug_optimizations,
):
    source_file = tmp_path / "sample_flags.nobasic"
    source_file.write_text("Pause\n")
    called = {}

    def fake_compile(*args, **kwargs):
        called["args"] = args
        called["kwargs"] = kwargs

    monkeypatch.setattr(nobasic_compiler, "compile_nobasic", fake_compile)
    monkeypatch.setattr(
        nobasic_compiler.sys,
        "argv",
        ["nobasic_compiler.py", str(source_file), *extra_args],
    )

    nobasic_compiler.main()

    assert called["args"][0] == str(source_file)
    assert called["args"][3] == expected_enable_optimizations
    assert called["args"][4] == expected_debug_optimizations
    assert called["kwargs"].get("target") == "nova"
    assert called["kwargs"].get("enable_linking") is True


def test_compile_nobasic_defaults_match_explicitly_enabled_post_generation_optimizations(tmp_path, monkeypatch):
    source_file = tmp_path / "default_opts.nobasic"
    source_file.write_text("Pause\n")
    captured_calls = []

    class StubGenerator:
        def __init__(self, **kwargs):
            captured_calls.append(kwargs)
            self.opt_config = {}

        def generate(self, ast):
            assert ast == "AST"
            return "HLT\n"

    class StubLexer:
        def tokenize(self, source, source_file):
            return ["TOKENS"]

    class StubParser:
        def parse(self, tokens, source_file):
            return "AST"

    class StubAnalyzer:
        def analyze(self, ast, source_file):
            return None

    def fake_run(command, capture_output, text):
        Path(command[2]).with_suffix(".bin").write_bytes(b"\x00")
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(nobasic_compiler, "Lexer", StubLexer)
    monkeypatch.setattr(nobasic_compiler, "Parser", StubParser)
    monkeypatch.setattr(nobasic_compiler, "SemanticAnalyzer", StubAnalyzer)
    monkeypatch.setattr(nobasic_compiler, "CodeGenerator", StubGenerator)
    monkeypatch.setattr(subprocess, "run", fake_run)

    nobasic_compiler.compile_nobasic(str(source_file), log=lambda _message: None)
    nobasic_compiler.compile_nobasic(
        str(source_file),
        output_file=str(tmp_path / "explicit.asm"),
        enable_optimizations=True,
        enable_peephole=True,
        enable_live_range_scheduling=True,
        log=lambda _message: None,
    )

    assert captured_calls == [
        {
            "debug_allocation": False,
            "enable_optimizations": True,
            "enable_peephole": True,
            "enable_live_range_scheduling": True,
        },
        {
            "debug_allocation": False,
            "enable_optimizations": True,
            "enable_peephole": True,
            "enable_live_range_scheduling": True,
        },
    ]


def test_main_supports_legacy_positional_output(monkeypatch, tmp_path):
    source_file = tmp_path / "sample.nobasic"
    source_file.write_text("Pause\n")
    output_file = tmp_path / "legacy.asm"
    called = {}

    def fake_compile(*args, **kwargs):
        called["args"] = args

    monkeypatch.setattr(nobasic_compiler, "compile_nobasic", fake_compile)
    monkeypatch.setattr(
        nobasic_compiler.sys,
        "argv",
        ["nobasic_compiler.py", str(source_file), str(output_file)],
    )

    nobasic_compiler.main()
    assert called["args"][1] == str(output_file)


def test_main_supports_case_insensitive_legacy_positional_output(monkeypatch, tmp_path):
    source_file = tmp_path / "sample.NoBasic"
    source_file.write_text("Pause\n")
    output_file = tmp_path / "LEGACY_OUTPUT.ASM"
    called = {}

    def fake_compile(*args, **kwargs):
        called["args"] = args

    monkeypatch.setattr(nobasic_compiler, "compile_nobasic", fake_compile)
    monkeypatch.setattr(
        nobasic_compiler.sys,
        "argv",
        ["nobasic_compiler.py", str(source_file), str(output_file)],
    )

    nobasic_compiler.main()

    assert called["args"][0] == str(source_file)
    assert called["args"][1] == str(output_file)


def test_main_rejects_non_asm_positional_output(monkeypatch, tmp_path, capsys):
    source_file = tmp_path / "sample.nobasic"
    source_file.write_text("Pause\n")
    bogus_output = tmp_path / "legacy.asm.bak"

    monkeypatch.setattr(
        nobasic_compiler.sys,
        "argv",
        ["nobasic_compiler.py", str(source_file), str(bogus_output)],
    )

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.main()

    assert exc.value.code == 1
    assert f"Unknown option: {bogus_output}" in capsys.readouterr().out


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


def test_main_accepts_case_insensitive_asm_output_flag(monkeypatch, tmp_path):
    source_file = tmp_path / "sample.nobasic"
    source_file.write_text("Pause\n")
    output_file = tmp_path / "CUSTOM_OUTPUT.ASM"
    called = {}

    def fake_compile(*args, **kwargs):
        called["args"] = args

    monkeypatch.setattr(nobasic_compiler, "compile_nobasic", fake_compile)
    monkeypatch.setattr(
        nobasic_compiler.sys,
        "argv",
        ["nobasic_compiler.py", str(source_file), "--output", str(output_file)],
    )

    nobasic_compiler.main()

    assert called["args"][0] == str(source_file)
    assert called["args"][1] == str(output_file)


def test_main_rejects_non_asm_output_flag(monkeypatch, tmp_path, capsys):
    source_file = tmp_path / "sample.nobasic"
    source_file.write_text("Pause\n")
    output_file = tmp_path / "sample.bin"

    monkeypatch.setattr(
        nobasic_compiler.sys,
        "argv",
        ["nobasic_compiler.py", str(source_file), "--output", str(output_file)],
    )

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.main()

    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert f"Output file must have .asm extension for target 'nova': {output_file}" in output
