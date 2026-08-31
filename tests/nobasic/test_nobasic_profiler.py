"""Tests for NoBASIC profiler reporting, traversal, and CLI behavior."""

from pathlib import Path

import nobasic_profiler


def _make_node(class_name, **attrs):
    node_type = type(class_name, (), {})
    node = node_type()
    for key, value in attrs.items():
        setattr(node, key, value)
    return node


def test_generate_report_formats_metrics_and_recommendations(tmp_path):
    source_file = tmp_path / "profile_target.nobasic"
    source_file.write_text("Pause\n")

    profiler = nobasic_profiler.NoBASICProfiler(str(source_file))
    profiler.parsing_time = 0.125
    profiler.semantic_time = 0.25
    profiler.codegen_time = 1.5
    profiler.total_time = 1.875
    profiler.symbols = {f"v{i}": "NUMBER" for i in range(600)}
    profiler.assembly_code = "ORG 0x0000\nMOV R0, 1\nHLT\n"
    profiler.ast = object()
    profiler.analyze_code_complexity = lambda: {
        "cyclomatic_complexity": 12,
        "statement_count": 20,
        "function_count": 2,
        "loop_count": 3,
        "conditional_count": 4,
        "max_nesting_depth": 6,
    }

    report = profiler.generate_report()

    assert "Parsing Time: 0.1250s" in report
    assert "Semantic Analysis Time: 0.2500s" in report
    assert "Code Generation Time: 1.5000s" in report
    assert "Total Time: 1.8750s" in report
    assert "Assembly Lines: 4" in report
    assert "Instructions: 3" in report
    assert "Consider breaking down complex functions" in report
    assert "Reduce nesting depth for better readability" in report
    assert "Code generation is slow - consider optimizing the compiler" in report
    assert "High memory usage - consider optimizing variable usage" in report


def test_analyze_code_complexity_visits_all_expression_branches(tmp_path):
    source_file = tmp_path / "complexity_target.nobasic"
    source_file.write_text("Pause\n")

    profiler = nobasic_profiler.NoBASICProfiler(str(source_file))
    profiler.ast = _make_node(
        "Program",
        statements=[
            _make_node(
                "BinaryExpr",
                left=_make_node("LiteralExpr"),
                right=_make_node(
                    "FunctionCallExpr",
                    arguments=[_make_node("LiteralExpr"), _make_node("LiteralExpr")],
                ),
            ),
            _make_node(
                "IfStmt",
                condition=_make_node("LiteralExpr"),
                then_branch=[
                    _make_node(
                        "WhileStmt",
                        body=[_make_node("LiteralExpr")],
                    )
                ],
                else_branch=[_make_node("LiteralExpr")],
            ),
        ],
    )

    complexity = profiler.analyze_code_complexity()

    assert complexity == {
        "cyclomatic_complexity": 3,
        "statement_count": 11,
        "function_count": 1,
        "loop_count": 1,
        "conditional_count": 1,
        "max_nesting_depth": 3,
    }


def test_main_accepts_detailed_flag_and_uses_resolved_source(monkeypatch, tmp_path, capsys):
    source_file = tmp_path / "demo.nobasic"
    source_file.write_text("Pause\n")
    calls = []

    class StubProfiler:
        def __init__(self, source_path):
            calls.append(("init", source_path))

        def profile_compilation(self):
            calls.append(("profile",))

        def generate_report(self):
            calls.append(("report",))
            return "PROFILE REPORT"

        def profile_with_cprofile(self):
            calls.append(("detailed",))

    monkeypatch.setattr(nobasic_profiler, "NoBASICProfiler", StubProfiler)
    monkeypatch.setattr(nobasic_profiler, "resolve_source_file_path", lambda value: source_file.resolve())
    monkeypatch.setattr(
        nobasic_profiler.sys,
        "argv",
        ["nobasic_profiler.py", "demo.nobasic", "--detailed"],
    )

    assert nobasic_profiler.main() == 0

    assert calls == [
        ("init", str(source_file.resolve())),
        ("profile",),
        ("report",),
        ("detailed",),
    ]
    assert "PROFILE REPORT" in capsys.readouterr().out


def test_main_rejects_unknown_option(monkeypatch, tmp_path, capsys):
    source_file = tmp_path / "demo.nobasic"
    source_file.write_text("Pause\n")
    monkeypatch.setattr(
        nobasic_profiler.sys,
        "argv",
        ["nobasic_profiler.py", str(source_file), "--nope"],
    )

    assert nobasic_profiler.main() == 1
    assert "Unknown option: --nope" in capsys.readouterr().out


def test_main_reports_missing_file_after_resolve_failure(monkeypatch, capsys):
    monkeypatch.setattr(
        nobasic_profiler.sys,
        "argv",
        ["nobasic_profiler.py", "missing.nobasic"],
    )

    def fail_resolve(_value):
        raise nobasic_profiler.CompilerError("missing")

    monkeypatch.setattr(nobasic_profiler, "resolve_source_file_path", fail_resolve)

    assert nobasic_profiler.main() == 1
    assert "File not found: missing.nobasic" in capsys.readouterr().out