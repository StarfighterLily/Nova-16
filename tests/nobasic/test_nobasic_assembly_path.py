"""Regression tests for NoBASIC assembler path selection and diagnostics."""

from pathlib import Path
from types import SimpleNamespace
import subprocess

import pytest

import nobasic_compiler


def _install_pipeline_stubs(monkeypatch):
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


def test_compile_nobasic_prefers_in_process_assembler_by_default(tmp_path, monkeypatch):
    _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "program.nobasic"
    source_file.write_text("Pause\n", encoding="ascii")
    calls = {}

    class StubAssembler:
        def __init__(self, log=print, trace=False):
            calls["log"] = log
            calls["trace"] = trace

        def assemble(self, filename):
            calls["filename"] = filename
            Path(filename).with_suffix(".bin").write_bytes(b"\x00")
            return True

    monkeypatch.setattr(
        nobasic_compiler,
        "_get_nova_assembler_module",
        lambda: SimpleNamespace(Assembler=StubAssembler),
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("subprocess assembler should not be used")),
    )

    nobasic_compiler.compile_nobasic(str(source_file), log=lambda _message: None)

    assert calls["trace"] is False
    assert Path(calls["filename"]).resolve() == source_file.with_suffix(".asm").resolve()
    assert source_file.with_suffix(".bin").exists()


def test_compile_nobasic_buffers_in_process_assembler_logs_until_failure(tmp_path, monkeypatch, capsys):
    _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "broken.nobasic"
    source_file.write_text("Pause\n", encoding="ascii")

    class StubAssembler:
        def __init__(self, log=print, trace=False):
            self.log = log
            self.trace = trace

        def assemble(self, filename):
            assert self.trace is False
            self.log("first pass")
            self.log("bad opcode")
            return False

    monkeypatch.setattr(
        nobasic_compiler,
        "_get_nova_assembler_module",
        lambda: SimpleNamespace(Assembler=StubAssembler),
    )

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic(str(source_file))

    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert "first pass" in output
    assert "bad opcode" in output
    assert f"Assembly failed for {source_file.with_suffix('.asm')}" in output


def test_compile_nobasic_falls_back_to_subprocess_when_module_load_fails(tmp_path, monkeypatch):
    _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "fallback.nobasic"
    source_file.write_text("Pause\n", encoding="ascii")
    commands = []

    monkeypatch.setattr(
        nobasic_compiler,
        "_get_nova_assembler_module",
        lambda: (_ for _ in ()).throw(ImportError("no in-process assembler")),
    )

    def fake_run(command, capture_output, text):
        commands.append(command)
        Path(command[2]).with_suffix(".bin").write_bytes(b"\x00")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    nobasic_compiler.compile_nobasic(str(source_file), log=lambda _message: None)

    assert len(commands) == 1
    command = commands[0]
    assert Path(command[0]).resolve() == Path(nobasic_compiler.sys.executable).resolve()
    assert Path(command[1]).resolve() == Path(nobasic_compiler.__file__).resolve().parent.parent / "nova_assembler.py"
    assert Path(command[2]).resolve() == source_file.with_suffix(".asm").resolve()


@pytest.mark.parametrize(
    ("crash_phase", "expected_message", "log_messages"),
    [
        ("init", "Assembly failed for {output}: init exploded", []),
        ("assemble", "Assembly failed for {output}: assemble exploded", ["phase 1", "phase 2"]),
    ],
)
def test_compile_nobasic_does_not_mask_in_process_assembler_crashes(
    tmp_path,
    monkeypatch,
    capsys,
    crash_phase,
    expected_message,
    log_messages,
):
    _install_pipeline_stubs(monkeypatch)
    source_file = tmp_path / "crash.nobasic"
    source_file.write_text("Pause\n", encoding="ascii")
    subprocess_calls = []

    class StubAssembler:
        def __init__(self, log=print, trace=False):
            self.log = log
            self.trace = trace
            if crash_phase == "init":
                raise RuntimeError("init exploded")

        def assemble(self, filename):
            assert self.trace is False
            for message in log_messages:
                self.log(message)
            raise RuntimeError("assemble exploded")

    monkeypatch.setattr(
        nobasic_compiler,
        "_get_nova_assembler_module",
        lambda: SimpleNamespace(Assembler=StubAssembler),
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess_calls.append((args, kwargs)),
    )

    with pytest.raises(SystemExit) as exc:
        nobasic_compiler.compile_nobasic(str(source_file))

    assert exc.value.code == 1
    assert subprocess_calls == []
    output = capsys.readouterr().out
    expected_output = source_file.with_suffix(".asm")
    assert expected_message.format(output=expected_output) in output
    for message in log_messages:
        assert message in output
