"""Tests for lazy (usage-driven) builtin emission in the Astrid compiler.

Verifies that:
1. Only builtins actually called by the program are emitted into the
   generated assembly (lazy linking), shrinking binaries dramatically.
2. Programs that call no builtins emit no builtin section at all.
3. Aliases (set_mode -> builtin_set_vmode) resolve to one shared stub.
4. Constant-folded builtin calls do not force their stub to be emitted.
5. --emit-all-builtins / emit_all_builtins=True restores legacy behavior.
6. Programs compiled with lazy emission still run correctly on the emulator.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nova_main import initialize_system
from astrid.codegen.codegen import CodeGenerator


def _compile_to_asm(source, extra_args=None):
    """Compile Astrid source text; return (asm_text, source_path).

    The caller is responsible for removing all generated files via
    _cleanup(source_path)."""
    import tempfile
    fd = tempfile.NamedTemporaryFile(mode="w", suffix=".ast", delete=False,
                                     encoding="utf-8")
    fd.write(source)
    fd.close()
    source_path = fd.name
    from astrid_compiler import main as compiler_main
    old_argv = sys.argv
    argv = [old_argv[0], source_path, "-o", source_path.replace(".ast", ".asm")]
    if extra_args:
        argv.extend(extra_args)
    sys.argv = argv
    try:
        compiler_main()
    finally:
        sys.argv = old_argv
    asm_path = source_path.replace(".ast", ".asm")
    with open(asm_path, encoding="utf-8") as f:
        asm_text = f.read()
    return asm_text, source_path


def _cleanup(source_path):
    for ext in [".ast", ".asm", ".bin", ".org", ".sym"]:
        p = source_path.replace(".ast", ext)
        if os.path.exists(p):
            os.unlink(p)


def run_binary(bin_path, max_cycles=2000000):
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry_point = mem.load(bin_path)
    proc.pc = entry_point
    cycle = 0
    while cycle < max_cycles and not proc.halted:
        cycle += 1
        proc.step()
    return proc, cycle, mem


def compile_and_run(source, expected_r0=None, expected_p0=None):
    _, source_path = _compile_to_asm(source)
    try:
        from nova_assembler import Assembler
        Assembler().assemble(source_path.replace(".ast", ".asm"))
        proc, cycles, mem = run_binary(source_path.replace(".ast", ".bin"))
        assert proc.halted, "Program did not halt"
        if expected_r0 is not None:
            assert proc.r0 == expected_r0, f"Expected R0={expected_r0}, got {proc.r0}"
        if expected_p0 is not None:
            assert proc.p0 == expected_p0, f"Expected P0={expected_p0}, got {proc.p0}"
        return proc, cycles, mem
    finally:
        _cleanup(source_path)


# ---------------------------------------------------------------------------
# Lazy emission behavior
# ---------------------------------------------------------------------------

def test_used_builtin_present_unused_absent():
    """Only called builtins appear in the output assembly."""
    source = """
void main() {
    set_layer(0);
    screen_fill(0x0F);
}
"""
    asm_text, source_path = _compile_to_asm(source)
    try:
        assert "builtin_screen_fill:" in asm_text
        assert "SFILL" in asm_text
        # Never called -> must not be emitted anywhere in the file.
        assert "builtin_set_vmode" not in asm_text
        assert "builtin_random" not in asm_text
        assert "builtin_write_text" not in asm_text
        print("PASS test_used_builtin_present_unused_absent")
    finally:
        _cleanup(source_path)


def test_no_builtin_section_without_calls():
    """A program with zero builtin calls emits no builtin section."""
    source = """
int main() {
    int x = 10;
    int y = x * 2;
    return y;
}
"""
    asm_text, source_path = _compile_to_asm(source)
    try:
        assert "; Built-in Function Implementations" not in asm_text
        print("PASS test_no_builtin_section_without_calls")
    finally:
        _cleanup(source_path)


def test_alias_shares_single_stub():
    """Aliases (set_mode/set_vmode, sti/enable_interrupts) share one stub."""
    source = """
void main() {
    set_mode(1);
    enable_interrupts();
}
"""
    asm_text, source_path = _compile_to_asm(source)
    try:
        assert asm_text.count("builtin_set_vmode:") == 1
        assert asm_text.count("builtin_sti:") == 1
        # Aliases must not synthesize separate stubs.
        assert "builtin_set_mode" not in asm_text
        assert "builtin_enable_interrupts" not in asm_text
        print("PASS test_alias_shares_single_stub")
    finally:
        _cleanup(source_path)


def test_folded_builtin_not_emitted():
    """Constant-folded builtin calls leave no stub behind."""
    source = """
int main() {
    int a = abs(-42);
    int b = min(10, 20);
    return a + b;
}
"""
    asm_text, source_path = _compile_to_asm(source)
    try:
        assert "builtin_abs" not in asm_text
        assert "builtin_min" not in asm_text
        print("PASS test_folded_builtin_not_emitted")
    finally:
        _cleanup(source_path)


def test_table_covers_every_mapped_builtin():
    """Every name->label mapping must have a table implementation (and vice versa)."""
    gen = CodeGenerator()
    impls = CodeGenerator.BUILTIN_IMPLEMENTATIONS
    for name, label in gen.builtin_functions.items():
        assert label in impls, (
            f"builtin '{name}' maps to '{label}' which has no implementation"
        )
    assert set(impls) == set(gen.builtin_functions.values()), (
        "BUILTIN_IMPLEMENTATIONS and builtin_functions label sets diverge"
    )
    print("PASS test_table_covers_every_mapped_builtin")


# ---------------------------------------------------------------------------
# Legacy escape hatch
# ---------------------------------------------------------------------------

def test_emit_all_flag_restores_legacy():
    """emit_all_builtins=True emits every implementation in the table."""
    assert CodeGenerator().emit_all_builtins is False
    assert CodeGenerator(emit_all_builtins=True).emit_all_builtins is True

    source = "int main() { return 7; }"
    asm_text, source_path = _compile_to_asm(source, extra_args=["--emit-all-builtins"])
    try:
        for label in CodeGenerator.BUILTIN_IMPLEMENTATIONS:
            assert label + ":" in asm_text, f"{label} missing with --emit-all-builtins"
        print("PASS test_emit_all_flag_restores_legacy")
    finally:
        _cleanup(source_path)


# ---------------------------------------------------------------------------
# Binary size regression guard
# ---------------------------------------------------------------------------

def test_screenflash_style_binary_shrinks():
    """A tiny graphics loop must no longer carry ~1.5KB of unused stubs."""
    source = """
void main() {
    while (1) {
        screen_fill(0x00);
        screen_fill(0x0F);
    }
}
"""
    asm_text, source_path = _compile_to_asm(source)
    try:
        from nova_assembler import Assembler
        Assembler().assemble(source_path.replace(".ast", ".asm"))
        size = os.path.getsize(source_path.replace(".ast", ".bin"))
        # Legacy emission produced ~1.6KB for this program; lazy emission
        # links only builtin_screen_fill, so the binary must stay small.
        assert size < 256, f"Binary too large: {size} bytes (legacy was ~1612)"
        assert "builtin_screen_fill:" in asm_text
        print(f"PASS test_screenflash_style_binary_shrinks (binary={size} bytes)")
    finally:
        _cleanup(source_path)


# ---------------------------------------------------------------------------
# Runtime correctness with lazy emission
# ---------------------------------------------------------------------------

def test_lazy_builtins_run_correctly():
    """Programs using lazily-linked builtins still execute correctly."""
    source = """
int main() {
    int x = 20;
    int a = max(10, x);
    int b = strlen("Nova");
    return a + b;
}
"""
    # max(10, 20) = 20, strlen("Nova") = 4 -> 24
    proc, cycles, mem = compile_and_run(source, expected_r0=24)
    print(f"PASS test_lazy_builtins_run_correctly (cycles={cycles}, R0={proc.r0})")


def test_lazy_graphics_builtins_render():
    """Lazily-linked graphics builtins produce visible pixels headlessly."""
    source = """
void main() {
    set_layer(0);
    screen_fill(0x0F);
}
"""
    _, source_path = _compile_to_asm(source)
    try:
        from nova_assembler import Assembler
        Assembler().assemble(source_path.replace(".ast", ".asm"))
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        entry_point = mem.load(source_path.replace(".ast", ".bin"))
        proc.pc = entry_point
        cycles = 0
        while cycles < 2000000 and not proc.halted:
            cycles += 1
            proc.step()
        assert proc.halted, "Program did not halt"
        screen = gfx.screen
        assert (screen != 0).sum() > 0, "Screen should have non-zero pixels after fill"
        assert screen[128, 128] == 0x0F
        print(f"PASS test_lazy_graphics_builtins_render (cycles={cycles})")
    finally:
        _cleanup(source_path)


if __name__ == "__main__":
    test_used_builtin_present_unused_absent()
    test_no_builtin_section_without_calls()
    test_alias_shares_single_stub()
    test_folded_builtin_not_emitted()
    test_table_covers_every_mapped_builtin()
    test_emit_all_flag_restores_legacy()
    test_screenflash_style_binary_shrinks()
    test_lazy_builtins_run_correctly()
    test_lazy_graphics_builtins_render()
    print("All Astrid lazy-builtin tests passed!")
