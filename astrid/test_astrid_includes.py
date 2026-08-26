"""Tests for Astrid multi-file compilation units: include / inherits.

Semantics:
- ``include "file.ast";`` splices another file's functions, globals, and
  enums into the program. Duplicate definitions are errors.
- ``inherits "file.ast";`` pulls in a base unit whose definitions are used
  ONLY where the inheriting program does not define its own version
  (override semantics). An inherited definition also shadows a same-named
  definition that arrived via plain ``include``; definitions written
  directly in the inheriting file always win over both.

Robustness:
- Relative include paths resolve against the directory of the file that
  contains the directive (recursively).
- Include cycles raise SyntaxError with the full chain.
- Diamond includes (same file reached twice) merge exactly once.
"""
import os
import shutil
import sys
import tempfile

import pytest

# Add project root to path so we can import nova_main and astrid modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add astrid directory to path so we can import astrid_compiler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nova_main import initialize_system
from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _Unit:
    """A temporary directory holding .ast files for one test."""

    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix='astrid_inc_')

    def write(self, name, source):
        path = os.path.join(self.dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(source)
        return path

    def parse(self, name):
        path = os.path.join(self.dir, name)
        with open(path, encoding='utf-8') as f:
            src = f.read()
        return Parser(Lexer(src).tokenize(), source_path=path).parse()

    def compile_and_run(self, name, max_cycles=500000):
        """Full pipeline: compile -> assemble -> run headless."""
        from astrid_compiler import main as compiler_main
        path = os.path.join(self.dir, name)
        old_argv = sys.argv
        sys.argv = [old_argv[0], path]
        try:
            compiler_main()
        finally:
            sys.argv = old_argv
        asm_path = path.replace('.ast', '.asm')
        bin_path = path.replace('.ast', '.bin')
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(bin_path)
        cycles = 0
        while cycles < max_cycles and not proc.halted:
            cycles += 1
            proc.step()
        assert proc.halted, f"{name}: program did not halt"
        return proc, cycles, mem

    def cleanup(self):
        shutil.rmtree(self.dir, ignore_errors=True)


@pytest.fixture
def unit():
    u = _Unit()
    yield u
    u.cleanup()


# ---------------------------------------------------------------------------
# Parser-level: include
# ---------------------------------------------------------------------------

def test_include_merges_functions_globals_enums(unit):
    unit.write('lib.ast',
               'int base_val = 10;\n'
               'enum Color { RED, GREEN };\n'
               'int helper(int v) { return v * 2; }\n')
    unit.write('main.ast',
               'include "lib.ast";\n'
               'int main() { return helper(21) + base_val + GREEN; }\n')
    ast = unit.parse('main.ast')
    names = [f.name for f in ast.functions]
    assert names == ['helper', 'main']
    assert [g.name for g in ast.globals] == ['base_val']
    assert ast.enum_constants == {'RED': 0, 'GREEN': 1}


def test_include_duplicate_definition_is_error(unit):
    unit.write('lib.ast', 'int helper(int v) { return v * 2; }\n')
    # In-file redefinition of an included function is an error.
    unit.write('main.ast',
               'include "lib.ast";\n'
               'int helper(int v) { return v; }\n'
               'int main() { return 0; }\n')
    with pytest.raises(SyntaxError, match="Duplicate definition"):
        unit.parse('main.ast')


def test_include_duplicate_between_files_is_error(unit):
    unit.write('a.ast', 'int dup() { return 1; }\n')
    unit.write('b.ast', 'include "a.ast";\nint dup() { return 2; }\n')
    unit.write('main.ast',
               'include "b.ast";\nint main() { return 0; }\n')
    with pytest.raises(SyntaxError, match="Duplicate definition"):
        unit.parse('main.ast')


def test_include_cycle_detected(unit):
    unit.write('cyc_a.ast', 'include "cyc_b.ast";\nint fa() { return 1; }\n')
    unit.write('cyc_b.ast', 'include "cyc_a.ast";\nint fb() { return 2; }\n')
    unit.write('main.ast',
               'include "cyc_a.ast";\nint main() { return 0; }\n')
    with pytest.raises(SyntaxError, match="[Cc]ircular"):
        unit.parse('main.ast')


def test_diamond_include_merges_once(unit):
    unit.write('base.ast', 'int shared() { return 7; }\n')
    unit.write('left.ast',
               'include "base.ast";\nint l() { return shared(); }\n')
    unit.write('right.ast',
               'include "base.ast";\nint r() { return shared(); }\n')
    unit.write('main.ast',
               'include "left.ast";\ninclude "right.ast";\n'
               'int main() { return l() + r(); }\n')
    ast = unit.parse('main.ast')
    names = [f.name for f in ast.functions]
    assert names.count('shared') == 1, (
        f"diamond include merged 'shared' {names.count('shared')} times")
    assert names == ['shared', 'l', 'r', 'main']


def test_include_missing_file_is_error(unit):
    unit.write('main.ast', 'include "does_not_exist.ast";\nvoid main() { }\n')
    with pytest.raises(SyntaxError, match="not found"):
        unit.parse('main.ast')


def test_nested_include_uses_child_directory(unit):
    """An include inside a subdirectory resolves relative to THAT file,
    not the root source."""
    unit.write(os.path.join('sub', 'deep.ast'),
               'int deep() { return 3; }\n')
    unit.write('mid.ast', 'include "sub/deep.ast";\n'
                          'int mid() { return deep(); }\n')
    unit.write('main.ast',
               'include "mid.ast";\n'
               'int main() { return mid(); }\n')
    ast = unit.parse('main.ast')
    assert [f.name for f in ast.functions] == ['deep', 'mid', 'main']


# ---------------------------------------------------------------------------
# Parser-level: inherits
# ---------------------------------------------------------------------------

def test_inherits_override_wins(unit):
    """The inheriting file's own definition replaces the base's."""
    unit.write('base.ast', 'int greet() { return 1; }\n')
    unit.write('main.ast',
               'inherits "base.ast";\n'
               'int greet() { return 99; }\n'
               'int main() { return greet(); }\n')
    ast = unit.parse('main.ast')
    greet = next(f for f in ast.functions if f.name == 'greet')
    ret = greet.body[0]
    assert ret.value.value == '99', "override must replace the base version"
    # Only ONE greet may exist (duplicate labels would break assembly).
    assert [f.name for f in ast.functions].count('greet') == 1


def test_inherits_keeps_non_overridden_base_functions(unit):
    unit.write('base.ast',
               'int kept() { return 5; }\nint dropped() { return 6; }\n')
    unit.write('main.ast',
               'inherits "base.ast";\n'
               'int dropped() { return 60; }\n'
               'int main() { return kept() + dropped(); }\n')
    ast = unit.parse('main.ast')
    kept = next(f for f in ast.functions if f.name == 'kept')
    dropped = next(f for f in ast.functions if f.name == 'dropped')
    assert kept.body[0].value.value == '5'
    assert dropped.body[0].value.value == '60'


def test_inherits_global_initializer_from_base(unit):
    unit.write('base.ast', 'int cfg = 42;\nint scratch;\n')
    unit.write('main.ast',
               'inherits "base.ast";\n'
               'int main() { return cfg; }\n')
    ast = unit.parse('main.ast')
    assert [g.name for g in ast.globals] == ['cfg', 'scratch']
    assert ast.globals[0].value.value == '42'


def test_inherits_shadowed_global_not_pulled_in(unit):
    unit.write('base.ast', 'int mode = 1;\nint extra = 2;\n')
    unit.write('main.ast',
               'inherits "base.ast";\n'
               'int mode = 100;\n'
               'int main() { return mode + extra; }\n')
    ast = unit.parse('main.ast')
    gnames = [g.name for g in ast.globals]
    assert gnames.count('mode') == 1
    mode = next(g for g in ast.globals if g.name == 'mode')
    assert mode.value.value == '100', "child's global initializer must win"


def test_inherited_shadows_included_definition(unit):
    """include lib (defines greet) + inherits derived (overrides greet)
    -> the derived version wins; only definitions written directly in the
    top-level file outrank inherited ones."""
    unit.write('lib.ast', 'int greet() { return 1; }\n')
    unit.write('derived.ast',
               'inherits "lib.ast";\nint greet() { return 99; }\n')
    unit.write('main.ast',
               'include "lib.ast";\n'
               'inherits "derived.ast";\n'
               'int main() { return greet(); }\n')
    ast = unit.parse('main.ast')
    greet = next(f for f in ast.functions if f.name == 'greet')
    assert greet.body[0].value.value == '99'
    assert [f.name for f in ast.functions].count('greet') == 1


def test_transitive_inherits_chain(unit):
    """A inherits B inherits C: all transitively reachable defs merge."""
    unit.write('c.ast', 'int cfn() { return 1; }\n')
    unit.write('b.ast', 'inherits "c.ast";\nint bfn() { return 2; }\n')
    unit.write('a.ast', 'inherits "b.ast";\n'
                        'int main() { return cfn() + bfn(); }\n')
    ast = unit.parse('a.ast')
    names = sorted(f.name for f in ast.functions)
    assert names == ['bfn', 'cfn', 'main']


def test_enum_gap_fill_via_inherits(unit):
    """Inherited enum constants fill gaps; the child's own declarations
    keep their values even when declared after the directive."""
    unit.write('base.ast', 'enum Color { RED, GREEN = 5, BLUE };\n')
    unit.write('main.ast',
               'inherits "base.ast";\n'
               'enum Color { GREEN = 9 };\n'   # child re-declaration wins
               'int main() { return RED + GREEN + BLUE; }\n')
    ast = unit.parse('main.ast')
    assert ast.enum_constants['RED'] == 0
    assert ast.enum_constants['GREEN'] == 9   # child's own value kept
    assert ast.enum_constants['BLUE'] == 6    # gap-filled from the base


# ---------------------------------------------------------------------------
# Runtime: full compile -> assemble -> headless execute
# ---------------------------------------------------------------------------

def test_include_runtime(unit):
    """helper(21)=42 + base_val=10 + GREEN=1 -> R0=53."""
    unit.write('lib.ast',
               'int base_val = 10;\n'
               'enum Color { RED, GREEN };\n'
               'int helper(int v) { return v * 2; }\n')
    unit.write('main.ast',
               'include "lib.ast";\n'
               'int main() { return helper(21) + base_val + GREEN; }\n')
    proc, cycles, mem = unit.compile_and_run('main.ast')
    assert proc.r0 == 53, f"Expected R0=53, got {proc.r0}"
    print(f"PASS test_include_runtime (cycles={cycles}, R0={proc.r0})")


def test_inherits_override_runtime(unit):
    """Every call site resolves to the override: greet() returns 99,
    including calls made from inside the base file itself."""
    unit.write('base.ast',
               'int greet() { return 1; }\n'
               'int wrap() { return greet(); }\n')
    unit.write('main.ast',
               'inherits "base.ast";\n'
               'int greet() { return 99; }\n'
               'int main() { return greet() + wrap(); }\n')
    proc, cycles, mem = unit.compile_and_run('main.ast')
    assert proc.r0 == 198, (
        f"Expected R0=198 (both call sites hit override), got {proc.r0}")
    print(f"PASS test_inherits_override_runtime (cycles={cycles}, R0={proc.r0})")


def test_include_runtime_shared_globals(unit):
    """Functions from an included file read/write the same globals."""
    unit.write('counter.ast',
               'int total;\n'
               'void bump(int n) { total += n; }\n'
               'int get_total() { return total; }\n')
    unit.write('main.ast',
               'include "counter.ast";\n'
               'int main() {\n'
               '    bump(10);\n'
               '    bump(32);\n'
               '    return get_total();\n'
               '}\n')
    proc, cycles, mem = unit.compile_and_run('main.ast')
    assert proc.r0 == 42, f"Expected R0=42, got {proc.r0}"
    print(f"PASS test_include_runtime_shared_globals "
          f"(cycles={cycles}, R0={proc.r0})")


def test_include_runtime_char_arrays_and_strings(unit):
    """Included string helpers operate on the including file's buffers."""
    unit.write('strutil.ast',
               'int first_char(char s[]) { return s[0]; }\n')
    unit.write('main.ast',
               'include "strutil.ast";\n'
               'int main() {\n'
               '    char buf[] = "Nova";\n'
               '    return strlen(buf) * 100 + first_char(buf);\n'
               '}\n')
    proc, cycles, mem = unit.compile_and_run('main.ast')
    # strlen("Nova")=4, 'N'=78 -> 4*100+78 = 478
    assert proc.p0 == 478, f"Expected P0=478, got {proc.p0}"
    print(f"PASS test_include_runtime_char_arrays_and_strings "
          f"(cycles={cycles}, P0={proc.p0})")


if __name__ == '__main__':
    class _U:
        def __enter__(self):
            self.u = _Unit()
            return self.u

        def __exit__(self, *a):
            self.u.cleanup()

    with _U() as u: test_include_merges_functions_globals_enums(u)
    with _U() as u: test_include_duplicate_definition_is_error(u)
    with _U() as u: test_include_duplicate_between_files_is_error(u)
    with _U() as u: test_include_cycle_detected(u)
    with _U() as u: test_diamond_include_merges_once(u)
    with _U() as u: test_include_missing_file_is_error(u)
    with _U() as u: test_nested_include_uses_child_directory(u)
    with _U() as u: test_inherits_override_wins(u)
    with _U() as u: test_inherits_keeps_non_overridden_base_functions(u)
    with _U() as u: test_inherits_global_initializer_from_base(u)
    with _U() as u: test_inherits_shadowed_global_not_pulled_in(u)
    with _U() as u: test_inherited_shadows_included_definition(u)
    with _U() as u: test_transitive_inherits_chain(u)
    with _U() as u: test_enum_gap_fill_via_inherits(u)
    with _U() as u: test_include_runtime(u)
    with _U() as u: test_inherits_override_runtime(u)
    with _U() as u: test_include_runtime_shared_globals(u)
    with _U() as u: test_include_runtime_char_arrays_and_strings(u)
    print("All Astrid include/inherits tests passed!")
