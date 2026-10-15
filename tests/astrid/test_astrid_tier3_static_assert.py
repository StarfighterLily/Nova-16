# Part 1 of 2: imports, helpers, parser tests, passing-guard runtime tests.
"""Tier 3 item 12: static_assert(cond, msg) compile-time guards.

Covers:
- Parser: file-scope and statement-level forms, message unescaping
- Guards that pass (arithmetic, enums, sizeof on types/structs/arrays)
- Guards that fail (zero conditions) with the message in the diagnostic
- Non-constant conditions rejected with a hint toward runtime `if`
- Missing/non-string message rejected by the parser
- Layout-guard use case: struct size vs. a budget (the SCB-page pattern)
- No code emitted for a guard (assembly is untouched)
"""
import os
import sys

import pytest

from nova_main import initialize_system
from astrid.errors import CompileError, CodeGenError
from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser, StaticAssert
from astrid.codegen.codegen import CodeGenerator


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def compile_source(source):
    """Compile Astrid source to assembly text (no assemble/run)."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8') as f:
        f.write(source)
        source_path = f.name
    try:
        from astrid_compiler import main as compiler_main
        old_argv = sys.argv
        sys.argv = [old_argv[0], source_path,
                    '-o', source_path.replace('.ast', '.asm')]
        try:
            compiler_main()
        finally:
            sys.argv = old_argv
        asm_path = source_path.replace('.ast', '.asm')
        with open(asm_path, encoding='utf-8') as f:
            return f.read()
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


def run_binary(bin_path, max_cycles=2000000):
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry_point = mem.load(bin_path)
    proc.pc = entry_point
    cycle = 0
    while cycle < max_cycles and not proc.halted:
        cycle += 1
        proc.step()
    return proc, cycle, mem


def compile_and_run(source, expected_r0=None, max_cycles=2000000):
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8') as f:
        f.write(source)
        source_path = f.name
    try:
        from astrid_compiler import main as compiler_main
        old_argv = sys.argv
        sys.argv = [old_argv[0], source_path,
                    '-o', source_path.replace('.ast', '.asm')]
        try:
            compiler_main()
        finally:
            sys.argv = old_argv
        asm_path = source_path.replace('.ast', '.asm')
        bin_path = source_path.replace('.ast', '.bin')
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)
        proc, cycles, mem = run_binary(bin_path, max_cycles=max_cycles)
        assert proc.halted, "Program did not halt"
        if expected_r0 is not None:
            assert proc.r0 == expected_r0, (
                f"Expected R0={expected_r0}, got {proc.r0}")
        return proc, cycles, mem
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


# ---------------------------------------------------------------------------
# Parser-level
# ---------------------------------------------------------------------------

def test_file_scope_parses_to_node():
    ast = parse('static_assert(3 > 2, "guard holds");\nint main() {\nreturn 1;\n}\n')
    assert len(ast.static_asserts) == 1
    node = ast.static_asserts[0]
    assert isinstance(node, StaticAssert)
    assert node.message == 'guard holds'
    print("PASS test_file_scope_parses_to_node")


def test_statement_level_parses_to_node():
    ast = parse('int main() {\nstatic_assert(1 + 1 == 2, "m");\nreturn 0;\n}\n')
    stmt = ast.functions[0].body[0]
    assert isinstance(stmt, StaticAssert)
    assert stmt.message == 'm'
    print("PASS test_statement_level_parses_to_node")


def test_message_unescaped():
    ast = parse('static_assert(1, "a\\tb");\nint main() {\nreturn 0;\n}\n')
    assert ast.static_asserts[0].message == 'a\tb'
    print("PASS test_message_unescaped")


def test_missing_message_fails():
    with pytest.raises(CompileError) as exc:
        parse('static_assert(1);\nint main() {\nreturn 0;\n}\n')
    assert 'message' in str(exc.value).lower() or ',' in str(exc.value)
    print("PASS test_missing_message_fails")


def test_non_string_message_fails():
    with pytest.raises(CompileError) as exc:
        parse('static_assert(1, x);\nint main() {\nreturn 0;\n}\n')
    assert 'string' in str(exc.value).lower()
    print("PASS test_non_string_message_fails")


# ---------------------------------------------------------------------------
# Guards that pass (compile and run)
# ---------------------------------------------------------------------------

def test_passing_guard_compiles_and_runs():
    source = 'static_assert(6 * 7 == 42, "sanity");\nint main() {\nreturn 42;\n}\n'
    proc, cycles, mem = compile_and_run(source, expected_r0=42)
    print(f"PASS test_passing_guard_compiles_and_runs (cycles={cycles})")


def test_enum_condition_passes():
    source = ('enum Color { RED = 1, GREEN = 2 };\n'
              'static_assert(GREEN == RED + 1, "enum order");\n'
              'int main() {\nreturn 0;\n}\n')
    proc, cycles, mem = compile_and_run(source, expected_r0=0)
    print(f"PASS test_enum_condition_passes (cycles={cycles})")


def test_sizeof_type_guard_passes():
    source = ('static_assert(sizeof(int) == 2, "int is 16-bit");\n'
              'static_assert(sizeof(char) == 1, "char is a byte");\n'
              'int main() {\nreturn 2;\n}\n')
    proc, cycles, mem = compile_and_run(source, expected_r0=2)
    print(f"PASS test_sizeof_type_guard_passes (cycles={cycles})")


def test_sizeof_struct_guard_passes():
    source = ('struct Point { int x; int y; };\n'
              'static_assert(sizeof(struct Point) == 4, "two words");\n'
              'int main() {\nreturn 4;\n}\n')
    proc, cycles, mem = compile_and_run(source, expected_r0=4)
    print(f"PASS test_sizeof_struct_guard_passes (cycles={cycles})")


def test_sizeof_global_array_guard_passes():
    source = ('int scores[16];\n'
              'static_assert(sizeof(scores) == 32, "table budget");\n'
              'int main() {\nscores[3] = 7;\nreturn scores[3];\n}\n')
    proc, cycles, mem = compile_and_run(source, expected_r0=7)
    print(f"PASS test_sizeof_global_array_guard_passes (cycles={cycles})")


def test_statement_guard_passes():
    source = ('int main() {\nstatic_assert(1 + 1 == 2, "inside body");\n'
              'return 11;\n}\n')
    proc, cycles, mem = compile_and_run(source, expected_r0=11)
    print(f"PASS test_statement_guard_passes (cycles={cycles})")


def test_logical_operators_in_guard():
    source = ('static_assert(1 == 1 && 2 != 3 || !(4), "logic folds");\n'
              'static_assert(~0 == 0xFFFF, "bitwise not folds");\n'
              'int main() {\nreturn 1;\n}\n')
    proc, cycles, mem = compile_and_run(source, expected_r0=1)
    print(f"PASS test_logical_operators_in_guard (cycles={cycles})")


# ---------------------------------------------------------------------------
# Guards that fail (compile-time diagnostics)
# ---------------------------------------------------------------------------

def test_failing_guard_reports_message():
    source = 'static_assert(2 + 2 == 5, "math is broken");\nint main() {\nreturn 0;\n}\n'
    with pytest.raises(CodeGenError) as exc:
        parse_and_generate(source)
    assert 'math is broken' in str(exc.value)
    print("PASS test_failing_guard_reports_message")


def test_failing_sizeof_guard_reports_message():
    source = ('struct Small { int a; };\n'
              'static_assert(sizeof(struct Small) == 99, "wrong footprint");\n'
              'int main() {\nreturn 0;\n}\n')
    with pytest.raises(CodeGenError) as exc:
        parse_and_generate(source)
    assert 'wrong footprint' in str(exc.value)
    print("PASS test_failing_sizeof_guard_reports_message")


def test_statement_guard_failure_fails_compile():
    source = ('int main() {\nstatic_assert(0, "body guard tripped");\n'
              'return 0;\n}\n')
    with pytest.raises(CodeGenError) as exc:
        parse_and_generate(source)
    assert 'body guard tripped' in str(exc.value)
    print("PASS test_statement_guard_failure_fails_compile")


def test_non_constant_condition_rejected_with_hint():
    source = ('int main() {\nint x = 3;\nstatic_assert(x > 0, "needs folding");\n'
              'return 0;\n}\n')
    with pytest.raises(CodeGenError) as exc:
        parse_and_generate(source)
    message = str(exc.value).lower()
    assert 'compile-time' in message and 'runtime' in message
    print("PASS test_non_constant_condition_rejected_with_hint")


def test_function_call_condition_rejected():
    source = ('int main() {\nstatic_assert(strlen("ab") == 2, "runtime call");\n'
              'return 0;\n}\n')
    with pytest.raises(CodeGenError):
        parse_and_generate(source)
    print("PASS test_function_call_condition_rejected")


def test_guard_emits_no_code():
    """A passing guard leaves no trace in the emitted assembly."""
    with_guards = compile_source(
        'static_assert(1 + 1 == 2, "first");\n'
        'static_assert(sizeof(int) == 2, "second");\n'
        'int main() {\nstatic_assert(1, "third");\nreturn 5;\n}\n')
    without = compile_source('int main() {\nreturn 5;\n}\n')
    assert 'static_assert' not in with_guards
    assert [l for l in with_guards.splitlines()
            if not l.startswith('; Generated')] == [
        l for l in without.splitlines() if not l.startswith('; Generated')]
    print("PASS test_guard_emits_no_code")


def parse_and_generate(source):
    """Helper: parse and run the full code generator (returns assembly)."""
    from astrid.lexer.lexer import Lexer as _Lexer
    from astrid.parser.parser import Parser as _Parser
    from astrid.codegen.codegen import CodeGenerator as _Gen
    ast = _Parser(_Lexer(source).tokenize()).parse()
    return _Gen().generate(ast)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
