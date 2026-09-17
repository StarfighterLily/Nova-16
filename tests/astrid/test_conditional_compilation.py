"""Conditional compilation across the lexer, file units, CLI and emulator."""
import subprocess
import sys
from pathlib import Path

import pytest

from astrid import Lexer, Parser
from astrid.compiler_api import compile_astrid
from astrid.errors import LexerError
from astrid.preprocessor import Preprocessor, PreprocessorError

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.unit


def values(source, defines=None):
    return [t.value for t in Lexer(source, defines=defines).tokenize() if t.type != 'EOF']


@pytest.mark.parametrize('expression,expected', [
    ('1', True), ('0', False), ('UNKNOWN', False),
    ('defined FLAG && !defined(MISSING)', True),
    ('defined(EMPTY)', True), ('defined(ZERO)', True),
    ('ZERO', False), ('1 + 2 * 3 == 7', True),
    ('(1 + 2) * 3 == 9', True), ('1 << 3 + 1 == 16', True),
    ('0x10 + 0b10 + 0o10 == 26', True), ('012 == 12', True),
    ('3 > 2 && 2 >= 2 && 1 < 2 && 1 <= 1', True),
    ('1 != 2 && (7 & 3) == 3 && (1 | 2) == 3 && (3 ^ 1) == 2', True),
    ('~0 == -1 && +4 >> 1 == 2', True), ('-7 / 3 == -2 && -7 % 3 == -1', True),
    ('0 && 1 / 0', False), ('1 || 1 / 0', True),
    ('0 && (1 << -1)', False), ('1 || 0 && 0', True),
    ('definedFLAG', False), ('2 < 1 < 1', True), ('ALIAS == 3', True),
])
def test_conditions(expression, expected):
    source = f'#if {expression}\nyes\n#else\nno\n#endif\n'
    assert values(source, {'FLAG': None, 'EMPTY': '', 'ZERO': 0,
                           'ALIAS': 'NEXT', 'NEXT': 3}) == ['yes' if expected else 'no']


def test_nested_selection_and_inactive_effects():
    source = '''#define ON
#ifdef ON
#ifndef MISSING
selected
#else
#error wrong
#endif
#elif 1 / 0
#error wrong
#else
#error wrong
#endif
#if 0
#define LEAK
#undef ON
include "missing.ast";
$ invalid code
#if 1 / 0
wrong
#else
wrong
#endif
#endif
#ifdef LEAK
wrong
#endif
#ifdef ON
still_on
#endif
'''
    assert values(source) == ['selected', 'still_on']


def test_elif_first_match():
    assert values('#if 0\na\n#elif 0\nb\n#elif 1\nc\n#elif 1 / 0\nd\n#else\ne\n#endif') == ['c']


def test_macro_tokens_strings_comments_and_recursion():
    source = '''#define A B
#define B 42
#define EMPTY
#define SELF SELF
#define PLUS +
A AB EMPTY SELF PLUS+ "A // #if" 'A' 0xAB
/* A
#error ignored
*/
#undef B
#define B 7
A
'''
    assert values(source) == ['42', 'AB', 'SELF', '+', '+', '"A // #if"', "'A'", '0xAB', '7']
    assert values('#define A B\n#define B A\nA') == ['A']


def test_comments_directives_multiline_literals_and_locations():
    source = '/* comment\n*/ #define LONG 123456\nLONG x; // ignored\n"start\n#define NOT_A_DIRECTIVE\nend"\n'
    tokens = Lexer(source).tokenize()
    assert [(t.value, t.line, t.column) for t in tokens[:3]] == [
        ('123456', 3, 1), ('x', 3, 6), (';', 3, 7)]
    assert tokens[3].type == 'STRING'
    assert '#define NOT_A_DIRECTIVE' in tokens[3].value
    with pytest.raises(LexerError) as err:
        Lexer('#define A 123456\nA $', source_path='example.ast').tokenize()
    assert (err.value.line, err.value.column, err.value.filename) == (2, 3, 'example.ast')


@pytest.mark.parametrize('source,message', [
    ('#else', 'without matching'), ('#endif', 'without matching'),
    ('#elif 1', 'without matching'), ('#if 1', 'unterminated'),
    ('#if 1\n#else\n#else\n#endif', 'after #else'),
    ('#if 0\n#else\n#elif 1\n#endif', 'after #else'),
    ('#if\n#endif', 'requires a condition'), ('#ifdef A B\n#endif', 'one macro'),
    ('#if 1\n#endif extra', 'does not accept'),
    ('#if 1\n#else extra\n#endif', 'does not accept'),
    ('#if 0\n#elif\n#endif', 'requires a condition'),
    ('#define 123', 'requires a macro'), ('#undef A B', 'one macro'),
    ('#define F(x) x', 'function-like'), ('#define A 1\\', 'multiline'),
    ('#define A 1\n#define A 2', 'redefined'), ('#include "a"', 'unknown directive'),
    ('#error intentional', 'intentional'), ('#if 1 / 0\n#endif', 'invalid #if'),
    ('#if 1 << -1\n#endif', 'shift count'), ('#if defined()\n#endif', 'defined requires'),
    ('#if (1\n#endif', 'incomplete'), ('#if 1 2\n#endif', 'unexpected token'),
    ('#if "x"\n#endif', 'invalid token'), ('#if 1.5\n#endif', 'unexpected token'),
])
def test_diagnostics(source, message):
    with pytest.raises(PreprocessorError, match=message) as err:
        Lexer(source, source_path='bad.ast').tokenize()
    assert err.value.filename == 'bad.ast'
    assert err.value.line >= 1
    assert err.value.source_text == source


def test_empty_same_redefinition_and_repeated_lexing():
    lexer = Lexer('#\n#define FLAG\n#define FLAG\n#undef MISSING\n#ifdef FLAG\nok\n#endif')
    assert [t.value for t in lexer.tokenize()] == ['ok', '']
    assert [t.value for t in lexer.tokenize()] == ['ok', '']
    assert values('#ifdef FLAG\nwrong\n#endif') == []


@pytest.mark.parametrize('defines', [{'bad-name': 1}, {'A': '1\n2'}, {123: 1}])
def test_invalid_initial_defines(defines):
    with pytest.raises(PreprocessorError):
        values('', defines)


@pytest.mark.parametrize('mode', ['include', 'inherits'])
def test_file_units_inherit_include_site_snapshot(tmp_path, mode):
    child = tmp_path / 'child.ast'
    child.write_text('''#if CONFIG != 7
#error incorrect include-site snapshot
#endif
#define CHILD_ONLY
int helper() { return CONFIG; }
''', encoding='utf-8')
    source = f'''#define CONFIG 7
{mode} "child.ast";
#undef CONFIG
#define CONFIG 9
#ifdef CHILD_ONLY
#error child definitions leaked
#endif
#if 0
include "missing.ast";
#endif
int main() {{ return helper() + CONFIG; }}
'''
    program = Parser(Lexer(source).tokenize(), source_path=str(tmp_path / 'main.ast')).parse()
    assert {f.name for f in program.functions} == {'main', 'helper'}
    child.write_text('#error child diagnostic', encoding='utf-8')
    with pytest.raises(PreprocessorError) as err:
        Parser(Lexer(source).tokenize(), source_path=str(tmp_path / 'main.ast')).parse()
    assert err.value.filename == str(child)
    assert err.value.line == 1


@pytest.mark.parametrize('enabled', [False, True])
@pytest.mark.integration
@pytest.mark.cpu
@pytest.mark.graphics
def test_cli_api_and_headless_execution(tmp_path, enabled):
    from nova_assembler import Assembler
    from nova_main import initialize_system

    source = tmp_path / 'conditional.ast'
    source.write_text('''#ifndef VALUE
#define VALUE 7
#endif
#ifdef DRAW
int main() {
    asm("MOV VM, 0; MOV VL, 0; MOV VX, 12; MOV VY, 34; SWRITE 31");
    return VALUE;
}
#elif !defined(DRAW)
int main() { return VALUE; }
#else
$ invalid excluded source
#endif
''', encoding='utf-8')
    cli_asm = tmp_path / 'cli.asm'
    api_asm = tmp_path / 'api.asm'
    defines = {'DRAW': None, 'VALUE': 42} if enabled else {}
    options = ['-DDRAW', '-DVALUE=42'] if enabled else []
    result = subprocess.run([sys.executable, str(ROOT / 'astrid' / 'astrid_compiler.py'),
                             str(source), '-o', str(cli_asm), *options],
                            capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert compile_astrid(str(source), str(api_asm), defines=defines, log=None)
    assert cli_asm.read_text() == api_asm.read_text()
    assert Assembler().assemble(str(cli_asm))
    binary = cli_asm.with_suffix('.bin')
    report = subprocess.run([sys.executable, str(ROOT / 'nova_main.py'), '--headless',
                             str(binary), '--cycles', '10000'], capture_output=True,
                            text=True, encoding='utf-8', timeout=30)
    assert report.returncode == 0, report.stdout + report.stderr
    expected = 42 if enabled else 7
    assert 'CPU Halted: True' in report.stdout
    assert f"R0-R9: ['0x{expected:02X}'" in report.stdout
    assert f'Graphics: {int(enabled)} non-black pixels on screen' in report.stdout
    proc, mem, gfx, _, _ = initialize_system(enable_sound=False)
    proc.pc = mem.load(str(binary))
    for _ in range(10000):
        if proc.halted:
            break
        proc.step()
    assert proc.halted
    assert proc.r0 == expected
    assert int(gfx.get_screen()[34, 12]) == (31 if enabled else 0)


def test_cli_diagnostic(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / 'astrid' / 'astrid_compiler.py'),
                             '-o', str(tmp_path / 'bad.asm')], input='#else\n',
                            capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert result.returncode == 1
    assert 'preprocessor error' in result.stderr
    assert 'Traceback' not in result.stderr
    assert not (tmp_path / 'bad.asm').exists()


def test_expansion_limits():
    defines = {f'A{i}': f'A{i + 1}' for i in range(67)}
    with pytest.raises(PreprocessorError, match='64 levels'):
        values('A0', defines)
    with pytest.raises(PreprocessorError, match='1 MiB'):
        Preprocessor('', {'BIG': 'x' * 1048577}).expand('BIG')
