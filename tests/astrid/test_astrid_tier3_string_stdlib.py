# Part 1 of 2: imports, helpers, mapping checks, strchr/strrchr/strstr.
"""Tier 3 item 11: the missing string stdlib (strchr/strrchr/strstr and
strncpy/strncat/atoi), implemented as lazily-linked asm builtins with the
same cdecl calling convention as the existing string builtins.

Covers:
- builtin table mappings (name -> label, return type, implementation)
- strchr/strrchr/strstr: first hit, last hit, empty needle, absent
- strncpy exact-n semantics (including zero-padding) and strncat
  at-most-n plus NUL termination
- atoi: plain, signed, leading spaces, stops at non-digits
"""
import os
import sys

import pytest

from nova_main import initialize_system
from astrid.codegen.codegen import CodeGenerator


def run_binary(bin_path, max_cycles=2000000):
    """Run a binary headlessly and return (proc, cycles, mem)."""
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry_point = mem.load(bin_path)
    proc.pc = entry_point
    cycle = 0
    while cycle < max_cycles and not proc.halted:
        cycle += 1
        proc.step()
    return proc, cycle, mem


def compile_and_run(source, expected_r0=None, expected_p0=None,
                    max_cycles=2000000):
    """Compile Astrid source, assemble, and run. Returns (proc, cycles, mem)."""
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
        if expected_p0 is not None:
            assert proc.p0 == expected_p0, (
                f"Expected P0={expected_p0}, got {proc.p0}")
        return proc, cycles, mem
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


def read_cstring(mem, addr):
    """Read a null-terminated byte string from emulator memory."""
    chars = []
    i = 0
    while True:
        b = mem.read_byte(addr + i)
        if b == 0:
            break
        chars.append(chr(b))
        i += 1
        assert i < 4096, "Unterminated string in emulator memory"
    return ''.join(chars)


# ---------------------------------------------------------------------------
# Table mappings
# ---------------------------------------------------------------------------

def test_builtin_table_mappings():
    gen = CodeGenerator()
    expected = {
        'strchr': 'builtin_strchr',
        'strrchr': 'builtin_strrchr',
        'strstr': 'builtin_strstr',
        'strncpy': 'builtin_strncpy',
        'strncat': 'builtin_strncat',
        'atoi': 'builtin_atoi',
    }
    for name, label in expected.items():
        assert gen.builtin_functions[name] == label, name
        assert label in CodeGenerator.BUILTIN_IMPLEMENTATIONS, name
        assert CodeGenerator.BUILTIN_RETURN_TYPES[name] == 'int', name

# ---------------------------------------------------------------------------
# strchr / strrchr / strstr
# ---------------------------------------------------------------------------

def test_strchr_first_hit_offset():
    """strchr finds the first 'o' in "Hello" at offset 4."""
    compile_and_run("""
int main() {
    string s = "Hello";
    int hit = strchr(s, 'o');
    return hit - s;
}
""", expected_r0=4)
    print("PASS test_strchr_first_hit_offset")


def test_strchr_miss_is_zero():
    """strchr returns 0 when the character is absent."""
    compile_and_run("""
int main() {
    string s = "Hello";
    return strchr(s, 'z');
}
""", expected_r0=0)
    print("PASS test_strchr_miss_is_zero")


def test_strchr_first_of_repeated():
    """strchr returns the FIRST of several matches (offset of 'l' is 2)."""
    compile_and_run("""
int main() {
    string s = "Hello";
    return strchr(s, 'l') - s;
}
""", expected_r0=2)
    print("PASS test_strchr_first_of_repeated")


def test_strchr_result_is_usable_pointer():
    """The strchr result points at live string content (reads 'ello')."""
    compile_and_run("""
int main() {
    string s = "Hello";
    string tail = strchr(s, 'e');
    return tail[0] * 256 + tail[1];
}
""", expected_p0=(ord('e') << 8) | ord('l'))
    print("PASS test_strchr_result_is_usable_pointer")


def test_strrchr_last_of_repeated():
    """strrchr returns the LAST 'l' in "Hello" at offset 3."""
    compile_and_run("""
int main() {
    string s = "Hello";
    return strrchr(s, 'l') - s;
}
""", expected_r0=3)
    print("PASS test_strrchr_last_of_repeated")


def test_strrchr_miss_is_zero():
    compile_and_run("""
int main() {
    string s = "Hello";
    return strrchr(s, 'z');
}
""", expected_r0=0)
    print("PASS test_strrchr_miss_is_zero")


def test_strrchr_single_char():
    """A single-char string scans its only character (offset 0)."""
    compile_and_run("""
int main() {
    string s = "Q";
    return strrchr(s, 'Q') - s;
}
""", expected_r0=0)
    print("PASS test_strrchr_single_char")


def test_strstr_first_occurrence():
    """strstr finds "World" in "Hello World" at offset 6."""
    compile_and_run("""
int main() {
    string s = "Hello World";
    return strstr(s, "World") - s;
}
""", expected_r0=6)
    print("PASS test_strstr_first_occurrence")


def test_strstr_miss_is_zero():
    compile_and_run("""
int main() {
    string s = "Hello";
    return strstr(s, "xyz");
}
""", expected_r0=0)
    print("PASS test_strstr_miss_is_zero")


def test_strstr_empty_needle_is_haystack():
    """C: an empty needle matches at the start (offset 0)."""
    compile_and_run("""
int main() {
    string s = "Hello";
    return strstr(s, "") - s;
}
""", expected_r0=0)
    print("PASS test_strstr_empty_needle_is_haystack")


def test_strstr_needle_longer_than_haystack():
    compile_and_run("""
int main() {
    string s = "Hi";
    return strstr(s, "Hello World");
}
""", expected_r0=0)

# ---------------------------------------------------------------------------
# strncpy / strncat
# ---------------------------------------------------------------------------

def test_strncpy_exact_copy():
    compile_and_run("""
int main() {
    char buf[8];
    string d = strncpy(buf, "abc", 8);
    return strlen(d);
}
""", expected_r0=3)
    print("PASS test_strncpy_exact_copy")


def test_strncpy_truncates_checked():
    """strncpy(dst, "abcdef", 3) writes 'a','b','c' (sum in full P0)."""
    source = """
int main() {
    char buf[8];
    char *d = strncpy(buf, "abcdef", 3);
    return d[0] + d[1] + d[2];
}
"""
    proc, cycles, mem = compile_and_run(source)
    assert proc.p0 == ord('a') + ord('b') + ord('c'), (
        f"Expected P0=294, got {proc.p0}")
    print("PASS test_strncpy_truncates_checked")


def test_strncpy_zero_pads_tail():
    """With a short src, the tail up to n is zero-filled (C semantics)."""
    compile_and_run("""
int main() {
    char buf[8];
    buf[0] = 'Z'; buf[1] = 'Z'; buf[2] = 'Z'; buf[3] = 'Z'; buf[4] = 'Z';
    strncpy(buf, "ab", 5);
    return buf[2] + buf[3] + buf[4];
}
""", expected_r0=0)
    print("PASS test_strncpy_zero_pads_tail")


def test_strncpy_short_copy_content():
    """The copied prefix reads back intact alongside the padding."""
    compile_and_run("""
int main() {
    char buf[8];
    char *d = strncpy(buf, "Hi", 4);
    return d[0] * 256 + d[1];
}
""", expected_p0=(ord('H') << 8) | ord('i'))
    print("PASS test_strncpy_short_copy_content")


def test_strncat_appends():
    compile_and_run("""
int main() {
    char buf[16];
    strcpy(buf, "foo");
    strcat(buf, "bar");
    string d = strncat(buf, "!!", 16);
    return strlen(d);
}
""", expected_r0=8)
    print("PASS test_strncat_appends")


def test_strncat_respects_limit():
    """strncat(dst, "abcdef", 2) appends only 2 chars then NUL."""
    compile_and_run("""
int main() {
    char buf[16];
    strcpy(buf, "x");
    strncat(buf, "abcdef", 2);
    return strlen(buf);
}
""", expected_r0=3)
    print("PASS test_strncat_respects_limit")


def test_strncat_zero_limit_keeps_string():
    """strncat with n=0 appends nothing but still terminates."""
    compile_and_run("""
int main() {
    char buf[16];
    strcpy(buf, "keep");
    strncat(buf, "XYZ", 0);
    return strlen(buf) * 256 + buf[3];
}
""", expected_p0=(4 << 8) | ord('p'))
    print("PASS test_strncat_zero_limit_keeps_string")


def test_strncat_content():
    compile_and_run("""
int main() {
    char buf[16];
    strcpy(buf, "ab");
    strncat(buf, "cd", 16);
    return buf[2] * 256 + buf[3];
}
""", expected_p0=(ord('c') << 8) | ord('d'))
    print("PASS test_strncat_content")


# ---------------------------------------------------------------------------
# atoi
# ---------------------------------------------------------------------------

def test_atoi_plain():
    """1234 full 16-bit value (in P0); R0 only sees the low byte."""
    proc, cycles, mem = compile_and_run(
        'int main() {\nreturn atoi("1234");\n}\n')
    assert proc.p0 == 1234, f"Expected P0=1234, got {proc.p0}"
    assert proc.r0 == (1234 & 0xFF)
    print("PASS test_atoi_plain")


def test_atoi_negative():
    """atoi("-42") negates to 0xFFD6 in P0 (R0 sees 0xD6 = 214)."""
    proc, cycles, mem = compile_and_run(
        'int main() {\nreturn atoi("-42");\n}\n')
    assert proc.p0 == (-42) & 0xFFFF, f"Expected P0=0xFFD6, got {proc.p0}"
    assert proc.r0 == (-42) & 0xFF
    print("PASS test_atoi_negative")


def test_atoi_leading_spaces_and_plus():
    compile_and_run('int main() {\nreturn atoi("   +56");\n}\n',
                    expected_r0=56)
    print("PASS test_atoi_leading_spaces_and_plus")


def test_atoi_stops_at_nondigit():
    compile_and_run('int main() {\nreturn atoi("78x9");\n}\n',
                    expected_r0=78)
    print("PASS test_atoi_stops_at_nondigit")


def test_atoi_empty_is_zero():
    compile_and_run('int main() {\nreturn atoi("");\n}\n',
                    expected_r0=0)
    print("PASS test_atoi_empty_is_zero")


def test_atoi_nondigit_start_is_zero():
    compile_and_run('int main() {\nreturn atoi("abc");\n}\n',
                    expected_r0=0)
    print("PASS test_atoi_nondigit_start_is_zero")


def test_atoi_multidigit_place_value():
    """Place values accumulate: "907" = 9*100 + 7 (in P0)."""
    proc, cycles, mem = compile_and_run(
        'int main() {\nreturn atoi("907");\n}\n')
    assert proc.p0 == 907, f"Expected P0=907, got {proc.p0}"
    print("PASS test_atoi_multidigit_place_value")


def test_atoi_feeds_arithmetic():
    """atoi feeds arithmetic like a parsed config value would."""
    compile_and_run('int main() {\nint v = atoi("40");\nreturn v + 2;\n}\n',
                    expected_r0=42)
    print("PASS test_atoi_feeds_arithmetic")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

    print("PASS test_strstr_needle_longer_than_haystack")


def test_strstr_result_content():
    """strstr result points at the matched run ("World"[0] is 'W')."""
    compile_and_run("""
int main() {
    string s = "Hello World";
    string hit = strstr(s, "World");
    return hit[0];
}
""", expected_r0=ord('W'))
    print("PASS test_strstr_result_content")

    print("PASS test_builtin_table_mappings")
