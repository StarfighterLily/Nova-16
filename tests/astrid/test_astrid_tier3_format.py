# Part 1 of 2: imports and helpers.
"""Tier 3 item 9: format(fmt, ...) / writef(fmt, ...).

Covers:
- format content for every conversion: %d %x %s %c %%
- Negative/char %d values; zero-padded %x
- format results feeding strlen/indexing/concatenation
- Nested format calls (separate scratch buffers)
- writef and write_text(format(...)) drawing to the screen
- Two %x conversions in one program (unique hex labels)
- Diagnostics: unsupported conversion, arity mismatch, non-literal fmt,
  trailing %
"""
import os
import sys

import pytest

from nova_main import initialize_system
from astrid.errors import CodeGenError
from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser
from astrid.codegen.codegen import CodeGenerator


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def parse_and_generate(source):
    return CodeGenerator().generate(parse(source))


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
    return proc, cycle, mem, gfx


def compile_and_run(source, expected_r0=None, expected_p0=None,
                    max_cycles=2000000):
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
        proc, cycles, mem, gfx = run_binary(bin_path, max_cycles=max_cycles)
        assert proc.halted, "Program did not halt"
        if expected_r0 is not None:
            assert proc.r0 == expected_r0, (
                f"Expected R0={expected_r0}, got {proc.r0}")
        if expected_p0 is not None:
            assert proc.p0 == expected_p0, (
                f"Expected P0={expected_p0}, got {proc.p0}")
        return proc, cycles, mem, gfx
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)

# ---------------------------------------------------------------------------
# format content: every conversion
# ---------------------------------------------------------------------------

def test_format_percent_d_content():
    """format("n=%d", 42) -> "n=42": length 4 and last char '2'."""
    proc, cycles, mem, gfx = compile_and_run("""
int main() {
    string s = format("n=%d", 42);
    return strlen(s) * 256 + s[3];
}
""", expected_p0=(4 << 8) | ord('2'))
    print(f"PASS test_format_percent_d_content (cycles={cycles})")


def test_format_percent_d_negative():
    proc, cycles, mem, gfx = compile_and_run("""
int main() {
    string s = format("%d", -7);
    return strlen(s) * 256 + s[0];
}
""", expected_p0=(2 << 8) | ord('-'))
    print(f"PASS test_format_percent_d_negative (cycles={cycles})")


def test_format_percent_d_char_promotes_to_decimal():
    """%d on a char renders its decimal code ('A' -> "65"), like C."""
    proc, cycles, mem, gfx = compile_and_run("""
int main() {
    char c = 'A';
    string s = format("%d", c);
    return strlen(s) * 256 + s[1];
}
""", expected_p0=(2 << 8) | ord('5'))
    print("PASS test_format_percent_d_char_promotes_to_decimal")


def test_format_percent_x_content():
    """%x renders 4 zero-padded uppercase hex digits (0xBE -> "00BE")."""
    proc, cycles, mem, gfx = compile_and_run("""
int main() {
    string s = format("%x", 0xBE);
    return strlen(s) * 256 + s[3];
}
""", expected_p0=(4 << 8) | ord('E'))
    print(f"PASS test_format_percent_x_content (cycles={cycles})")


def test_format_percent_s_content():
    proc, cycles, mem, gfx = compile_and_run("""
int main() {
    string s = format("[%s]", "ab");
    return strlen(s) * 256 + s[2];
}
""", expected_p0=(4 << 8) | ord('b'))
    print(f"PASS test_format_percent_s_content (cycles={cycles})")


def test_format_percent_c_content():
    """%c emits one glyph byte, not a decimal code."""
    proc, cycles, mem, gfx = compile_and_run("""
int main() {
    string s = format("%c%c", 'H', 'i');
    return strlen(s) * 256 + s[1];
}
""", expected_p0=(2 << 8) | ord('i'))
    print(f"PASS test_format_percent_c_content (cycles={cycles})")


def test_format_percent_percent_is_literal():
    """%% folds to a single percent in buffered and literal-only forms."""
    proc, cycles, mem, gfx = compile_and_run("""
int main() {
    string s = format("100%% %d%%", 5);
    return strlen(s) * 256 + s[6];
}
""", expected_p0=(7 << 8) | ord('%'))
    print(f"PASS test_format_percent_percent_is_literal (cycles={cycles})")

# ---------------------------------------------------------------------------
# Composition: concat, nesting, strlen, two %x sites
# ---------------------------------------------------------------------------

def test_format_result_feeds_strlen():
    proc, cycles, mem, gfx = compile_and_run("""
int main() {
    return strlen(format("%d+%d", 12, 30));
}
""", expected_r0=5)
    print(f"PASS test_format_result_feeds_strlen (cycles={cycles})")


def test_format_result_concats_with_literal():
    """format() is a string value: `format(...) + "!"` concatenates."""
    proc, cycles, mem, gfx = compile_and_run("""
int main() {
    string s = format("%d", 7) + "!";
    return strlen(s) * 256 + s[1];
}
""", expected_p0=(2 << 8) | ord('!'))
    print(f"PASS test_format_result_concats_with_literal (cycles={cycles})")


def test_nested_format_uses_separate_buffers():
    proc, cycles, mem, gfx = compile_and_run("""
int main() {
    string s = format("%s%d", format("%d", 1), 2);
    return strlen(s) * 256 + s[1];
}
""", expected_p0=(2 << 8) | ord('2'))
    print(f"PASS test_nested_format_uses_separate_buffers (cycles={cycles})")


def test_two_hex_conversions_unique_labels():
    """Two %x sites in one program must not share hex jump labels."""
    proc, cycles, mem, gfx = compile_and_run("""
int main() {
    string a = format("%x", 0xBEEF);
    int first = a[3];
    string b = format("%x", 0xCAFE);
    int second = b[3];
    return first * 256 + second;
}
""", expected_p0=(ord('F') << 8) | ord('E'))
    print(f"PASS test_two_hex_conversions_unique_labels (cycles={cycles})")


def test_stringh_cast_twice_unique_labels():
    """Regression for emit_hex_string: two (stringh) casts in one program."""
    proc, cycles, mem, gfx = compile_and_run("""
int main() {
    string a = (stringh)0xDEAD;
    int first = a[3];
    string b = (stringh)0xBEEF;
    int second = b[3];
    return first * 256 + second;
}
""", expected_p0=(ord('D') << 8) | ord('F'))
    print(f"PASS test_stringh_cast_twice_unique_labels (cycles={cycles})")


# ---------------------------------------------------------------------------
# writef / write_text(format(...)) drawing
# ---------------------------------------------------------------------------

def test_writef_literal_only_draws():
    """writef with no conversions draws the literal (no scratch buffer)."""
    proc, cycles, mem, gfx = compile_and_run("""
void main() {
    set_pos(0, 0);
    writef("OK");
}
""")
    pixels = _screen_pixels(gfx)
    assert pixels > 0, "writef drew nothing"
    print(f"PASS test_writef_literal_only_draws (pixels={pixels})")


def test_writef_with_conversion_draws():
    proc, cycles, mem, gfx = compile_and_run("""
void main() {
    set_pos(0, 0);
    writef("HP:%d", 99);
}
""")
    pixels = _screen_pixels(gfx)
    assert pixels > 0, "writef drew nothing"
    print(f"PASS test_writef_with_conversion_draws (pixels={pixels})")


def test_write_text_of_format_draws():
    """write_text(format(...), color) skips the ITOS pass (string arg)."""
    source = """
void main() {
    set_pos(0, 0);
    write_text(format("SC:%d", 7), 0x1F);
}
"""
    asm_text = compile_source(source)
    proc, cycles, mem, gfx = compile_and_run(source)
    pixels = _screen_pixels(gfx)
    assert pixels > 0, "write_text(format(...)) drew nothing"
    assert 'builtin_write_text' in asm_text
    print(f"PASS test_write_text_of_format_draws (pixels={pixels})")


def test_writef_two_sites_one_program():
    proc, cycles, mem, gfx = compile_and_run("""
void main() {
    set_pos(0, 0);
    writef("A%d", 1);
    set_pos(0, 10);
    writef("B%d", 2);
}
""")
    pixels = _screen_pixels(gfx)
    assert pixels > 0, "two writef sites drew nothing"
    print(f"PASS test_writef_two_sites_one_program (pixels={pixels})")


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def test_unsupported_conversion_rejected():
    with pytest.raises(CodeGenError) as exc:
        parse_and_generate('int main() {\n return format("%q", 1);\n}\n')
    assert '%q' in str(exc.value)
    print("PASS test_unsupported_conversion_rejected")


def test_conversion_arity_mismatch_rejected():
    with pytest.raises(CodeGenError) as exc:
        parse_and_generate('int main() {\n return format("%d", 1, 2);\n}\n')
    assert 'conversion' in str(exc.value)
    print("PASS test_conversion_arity_mismatch_rejected")


def test_missing_argument_rejected():
    with pytest.raises(CodeGenError) as exc:
        parse_and_generate('int main() {\n return format("%d");\n}\n')
    assert 'conversion' in str(exc.value)
    print("PASS test_missing_argument_rejected")


def test_non_literal_format_rejected():
    with pytest.raises(CodeGenError) as exc:
        parse_and_generate(
            'int main() {\n int n = 3;\n return format(n);\n}\n')
    assert 'string literal' in str(exc.value)
    print("PASS test_non_literal_format_rejected")


def test_trailing_percent_rejected():
    with pytest.raises(CodeGenError) as exc:
        parse_and_generate('int main() {\n return format("bad %");\n}\n')
    assert 'incomplete' in str(exc.value)
    print("PASS test_trailing_percent_rejected")


def test_format_emits_no_builtin_call():
    """format expands inline: the emitted assembly never CALLs a
    nonexistent builtin_format label."""
    asm_text = compile_source(
        'int main() {\n return strlen(format("%d", 5));\n}\n')
    assert 'CALL builtin_format' not in asm_text
    assert 'ITOS' in asm_text
    print("PASS test_format_emits_no_builtin_call")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

def _screen_pixels(gfx):
    screen = getattr(gfx._compositor, '_screen', None)
    if screen is None:
        screen = gfx.screen
    return int((screen != 0).sum())
