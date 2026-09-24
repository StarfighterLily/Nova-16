"""Tests for Tier 5: absolute placement, address casts, and volatile.

Covers the three C-parity features from features.md:

* Placement   `int scb[16] @ 0xF000;`  -- pin a global at a fixed address,
  emitted as its own ORG segment (sprite SCBs, MMIO windows).
* Casting     `(int *)0xF000` / `*(int *)addr` -- address casts desugar to
  the same thing peek2/poke2 do: the value is the full 16-bit address.
* `volatile`  -- finally *means* something: excluded from register
  allocation and spill windows, and every access compiles to a fresh
  memory load (never folded or CSE'd).
"""
import os
import re
import sys
import tempfile

import pytest

from nova_main import initialize_system


def _compile_to_asm(source):
    """Compile Astrid source text; return (asm_path, tmp_source)."""
    fd = tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8')
    fd.write(source)
    fd.close()
    from astrid_compiler import main as compiler_main
    old_argv = sys.argv
    sys.argv = [old_argv[0], fd.name, '-o', fd.name.replace('.ast', '.asm')]
    try:
        compiler_main()
    finally:
        sys.argv = old_argv
    return fd.name.replace('.ast', '.asm'), fd.name


def _cleanup(asm_path, tmp_source=None):
    paths = [asm_path.replace('.asm', ext)
             for ext in ('.asm', '.bin', '.org', '.sym', '.nex')]
    if tmp_source:
        paths.append(tmp_source)
    for p in paths:
        if os.path.exists(p):
            os.unlink(p)


def _assemble(asm_path):
    from nova_assembler import Assembler
    assert Assembler().assemble(asm_path), "assembler failed"


def _compile_expect_failure(source):
    """Compile `source`; return True if it failed, False if it succeeded."""
    asm_path, tmp_src = _compile_to_asm(source)
    try:
        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            from astrid_compiler import main as compiler_main
            old_argv = sys.argv
            sys.argv = [old_argv[0], tmp_src, '-o', asm_path]
            try:
                return compiler_main() != 0
            finally:
                sys.argv = old_argv
    finally:
        _cleanup(asm_path, tmp_src)


def _run_to_halt(asm_path, max_cycles=5000):
    """Assemble + load + run to halt; return (proc, mem)."""
    _assemble(asm_path)
    bin_path = asm_path.replace('.asm', '.bin')
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    proc.pc = mem.load(bin_path)
    for _ in range(max_cycles):
        if proc.halted:
            break
        proc.step()
    assert proc.halted, "program did not halt"
    return proc, mem


def _sym_addr(sym_path, name):
    """Look up a symbol's address from an assembler .sym file.

    The .sym writer uppercases all symbol names, so the lookup is
    case-insensitive."""
    want = name.upper()
    with open(sym_path, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2 and parts[0].upper() == want:
                return int(parts[1], 16)
    return None


# ---------------------------------------------------------------------------
# Absolute placement (@ addr)
# ---------------------------------------------------------------------------

SCB_SOURCE = """
int scb[16] @ 0xF000;
int ordinary;

int main() {
    scb[0] = 0x1234;
    scb[2] = 0xBEEF;
    ordinary = 7;
    return 0;
}
"""


class TestPlacement:

    def test_placed_global_gets_own_org_segment(self):
        """@ 0xF000 emits its own ORG segment with the gvar label."""
        asm_path, tmp_src = _compile_to_asm(SCB_SOURCE)
        try:
            with open(asm_path, encoding='utf-8') as f:
                text = f.read()
            assert 'ORG 0xF000' in text, "missing ORG 0xF000"
            assert "; Placed global 'scb'" in text
            assert 'gvar_scb:' in text
        finally:
            _cleanup(asm_path, tmp_src)

    def test_placed_global_does_not_consume_0x8000_slot(self):
        """A placed global must not shift the unplaced globals' addresses."""
        asm_path, tmp_src = _compile_to_asm(SCB_SOURCE)
        try:
            _assemble(asm_path)
            sym = asm_path.replace('.asm', '.sym')
            assert _sym_addr(sym, 'gvar_scb') == 0xF000, (
                "scb should be pinned at 0xF000")
            # `ordinary` is the first unplaced global: still 0x8000.
            assert _sym_addr(sym, 'gvar_ordinary') == 0x8000, (
                "unplaced globals must stay contiguous at 0x8000")
        finally:
            _cleanup(asm_path, tmp_src)

    def test_placed_global_accessible_at_runtime(self):
        """scb[0]/scb[2] read/write the exact placed addresses."""
        asm_path, tmp_src = _compile_to_asm(SCB_SOURCE)
        try:
            proc, mem = _run_to_halt(asm_path)
            assert mem.read_word(0xF000) == 0x1234, "scb[0] wrong"
            assert mem.read_word(0xF004) == 0xBEEF, "scb[2] wrong"
            assert mem.read_word(0x8000) == 7, "ordinary wrong"
        finally:
            _cleanup(asm_path, tmp_src)

    def test_initialized_placed_global_keeps_data_at_exact_address(self):
        """A scalar initializer belongs at the explicit address, not 0x8000."""
        source = """
int placed @ 0xE000 = 0x1234;
int ordinary;

int main() {
    ordinary = 7;
    return 0;
}
"""
        asm_path, tmp_src = _compile_to_asm(source)
        try:
            _assemble(asm_path)
            sym = asm_path.replace('.asm', '.sym')
            assert _sym_addr(sym, 'gvar_placed') == 0xE000
            assert _sym_addr(sym, 'gvar_ordinary') == 0x8000
            proc, mem = _run_to_halt(asm_path)
            assert mem.read_word(0xE000) == 0x1234
            assert mem.read_word(0x8000) == 7
        finally:
            _cleanup(asm_path, tmp_src)

    def test_placement_on_local_is_rejected(self):
        """@ addr on a local is a compile error (globals only)."""
        assert _compile_expect_failure(
            "int main() { int x @ 0xF000; return 0; }\n"), (
            "local @ placement should fail to compile")

    def test_placed_global_with_included_control_flow_assembles_and_runs(
            self, tmp_path):
        """Regression: an included @ global must survive the full pipeline.

        Astrid include expansion can bring high-level `if` statements into a
        compilation unit. Code generation must lower those statements rather
        than emitting IF/ENDIF text that the assembly preprocessor mistakes
        for unclosed assembly conditionals.
        """
        include_path = tmp_path / "placed_include.ast"
        include_path.write_text(
            "int counter @ 0xE010;\n"
            "void bump() { counter = counter + 1; }\n",
            encoding="utf-8")
        source_path = tmp_path / "placed_main.ast"
        source_path.write_text(
            'include "placed_include.ast"\n'
            "int main() { bump(); if (counter) { counter = 2; } return 0; }\n",
            encoding="utf-8")
        asm_path = tmp_path / "placed_main.asm"

        import sys
        from astrid_compiler import main as compiler_main
        old_argv = sys.argv
        sys.argv = [old_argv[0], str(source_path), "-o", str(asm_path)]
        try:
            assert compiler_main() == 0
        finally:
            sys.argv = old_argv

        text = asm_path.read_text(encoding="utf-8")
        assert "ORG 0xE010" in text
        assert not any(line.strip().upper().startswith(("IF ", "ENDIF"))
                       for line in text.splitlines())

        proc, mem = _run_to_halt(str(asm_path))
        assert mem.read_word(0xE010) == 2

    def test_placed_global_survives_assembler_segment_loading(self):
        """The assembler's .org metadata must load the pinned segment."""
        asm_path, tmp_src = _compile_to_asm(SCB_SOURCE)
        try:
            proc, mem = _run_to_halt(asm_path)
            assert proc.halted
            assert mem.read_word(0xF000) == 0x1234
            assert mem.read_word(0xF004) == 0xBEEF
            assert mem.read_word(0x8000) == 7
        finally:
            _cleanup(asm_path, tmp_src)

    def test_placement_non_constant_is_rejected(self):
        """@ addr with a non-constant expression is a compile error.

        (0xF000 + 1) IS constant (folds to 0xF001); a variable reference is
        not (only enum constants are compile-time integers)."""
        assert _compile_expect_failure(
            "int base = 0xF000;\n"
            "int scb[16] @ base;\n"
            "int main() { return 0; }\n"), (
            "non-constant placement should fail to compile")


# ---------------------------------------------------------------------------
# Address casts ((T *)addr) and *(T *)addr derefs
# ---------------------------------------------------------------------------

class TestAddressCasts:

    def test_pointer_cast_global_init(self):
        """int *scbp = (int *)0xF000; stores the full address."""
        asm_path, tmp_src = _compile_to_asm(
            "int *scbp = (int *)0xF000;\nint main() { return 0; }\n")
        try:
            proc, mem = _run_to_halt(asm_path)
            assert mem.read_word(0x8000) == 0xF000, (
                "pointer initializer must hold the full address")
        finally:
            _cleanup(asm_path, tmp_src)

    def test_char_pointer_cast_keeps_full_address(self):
        """Regression: (char *)addr must NOT be folded to the low byte."""
        asm_path, tmp_src = _compile_to_asm(
            "int main() { char *p = (char *)0xF000; return 0; }\n")
        try:
            with open(asm_path, encoding='utf-8') as f:
                text = f.read()
            assert '61440' in text or '0xF000' in text, (
                f"(char *)0xF000 lost its full address; asm:\n{text[:2000]}")
        finally:
            _cleanup(asm_path, tmp_src)

    def test_deref_of_cast_reads_and_writes_mmio(self):
        """*(int *)addr behaves like peek2/poke2 at runtime."""
        asm_path, tmp_src = _compile_to_asm("""
int main() {
    *(int *)0xF000 = 0x1234;
    *(int *)0xF004 = 0xBEEF;
    int x = *(int *)0xF000;
    int z = *(int *)0xF004;
    return (x == 0x1234 && z == 0xBEEF) ? 42 : 1;
}
""")
        try:
            proc, mem = _run_to_halt(asm_path)
            assert proc.p0 == 42, f"deref-of-cast round trip failed: R0={proc.r0:#x}"
            assert mem.read_word(0xF000) == 0x1234
            assert mem.read_word(0xF004) == 0xBEEF
        finally:
            _cleanup(asm_path, tmp_src)

    def test_cast_pointer_plus_offset_addresses_array(self):
        """(int *)base + n walks the placed array with word stride."""
        asm_path, tmp_src = _compile_to_asm("""
int scb[16] @ 0xF000;

int main() {
    int *p = (int *)0xF000;
    p[3] = 77;
    int v = *(p + 3);
    return (v == 77) ? 42 : 1;
}
""")
        try:
            proc, mem = _run_to_halt(asm_path)
            assert proc.p0 == 42, "pointer arithmetic through cast failed"
            assert mem.read_word(0xF006) == 77, "scb[3] wrong"
        finally:
            _cleanup(asm_path, tmp_src)


# ---------------------------------------------------------------------------
# volatile
# ---------------------------------------------------------------------------

class TestVolatile:

    def test_volatile_global_reads_are_not_cse_folded(self):
        """`v + v` on a volatile global must emit TWO memory loads."""
        asm_path, tmp_src = _compile_to_asm(
            "volatile int v;\nint main() { return v + v; }\n")
        try:
            with open(asm_path, encoding='utf-8') as f:
                text = f.read()
            start = text.find('func_main:')
            body = text[start:text.find('ORG 0x8000')]
            loads = len(re.findall(r'MOV P\d, \[0x8000\]', body))
            assert loads == 2, (
                f"expected two volatile loads, found {loads}:\n{body[:1500]}")
        finally:
            _cleanup(asm_path, tmp_src)

    def test_volatile_local_is_not_spill_allocated(self):
        """A volatile local must stay FP-relative, never get a spill slot."""
        asm_path, tmp_src = _compile_to_asm("""
int main() {
    volatile int lv = 5;
    int plain = 6;
    return lv + plain;
}
""")
        try:
            with open(asm_path, encoding='utf-8') as f:
                text = f.read()
            start = text.find('func_main:')
            body = text[start:]
            # No spill-window address (0xC000+) may hold the volatile local.
            assert 'MOV P0, [0xC0' not in body, (
                "volatile local got a spill slot; must stay FP-relative")
            assert '[FP-' in body, "expected FP-relative volatile local access"
        finally:
            _cleanup(asm_path, tmp_src)

    def test_volatile_runtime_round_trip(self):
        """A volatile global is readable and writable at runtime."""
        asm_path, tmp_src = _compile_to_asm("""
volatile int v;

int main() {
    v = 0x5A5A;
    int a = v;
    int b = v;
    return (a == 0x5A5A && b == 0x5A5A) ? 42 : 1;
}
""")
        try:
            proc, mem = _run_to_halt(asm_path)
            assert proc.p0 == 42, f"volatile round trip failed: R0={proc.r0:#x}"
            assert mem.read_word(0x8000) == 0x5A5A
        finally:
            _cleanup(asm_path, tmp_src)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

