"""Regression tests for the Astrid sprite builtins (sprite_blit / sprite_blitall).

Both builtins drive the hardware SPBLIT / SPBLITALL opcodes, which render
from the memory-mapped sprite control blocks (SCB) at 0xF000-0xF0FF
(16 sprites x 16 bytes).

The whole pipeline is exercised headlessly against the real emulator:
  1. `sprite_blitall()` renders every active sprite from its SCB.
  2. `sprite_blit(id)` renders a single sprite by id.
  3. The sprite data address is a 16-bit big-endian SCB word.  Because the
     MEMSET instruction fills COUNT bytes with the LOW byte of its value,
     the address word must be written one byte at a time (poke) -- a single
     `memset(0xF000, 0x8000, 2)` used to write 0x0000 and left the engine
     reading sprite pixels out of the zero page (regression guard).
  4. Sprites can live in a banked window (0x8000-0xBFFF) -- the engine
     reads the bitmap through the same BANK-aware window that wrote it.
  5. Transparency: interior pixels equal to the transparency color leave
     the destination untouched.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nova_main import initialize_system
from astrid.codegen.codegen import CodeGenerator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compile_to_asm(source):
    """Compile Astrid source text; return (asm_path, tmp_source_path)."""
    fd = tempfile.NamedTemporaryFile(mode="w", suffix=".ast", delete=False,
                                     encoding="utf-8")
    fd.write(source)
    fd.close()
    tmp_src = fd.name
    from astrid_compiler import main as compiler_main
    out = tmp_src.replace(".ast", ".asm")
    old_argv = sys.argv
    sys.argv = [old_argv[0], tmp_src, "-o", out]
    try:
        compiler_main()
    finally:
        sys.argv = old_argv
    return out, tmp_src


def _cleanup(asm_path, tmp_source=None):
    paths = [asm_path.replace(".asm", ext)
             for ext in (".asm", ".bin", ".org", ".sym")]
    if tmp_source:
        paths.append(tmp_source)
    for p in paths:
        if os.path.exists(p):
            os.unlink(p)


def _assemble_and_run(source):
    """Compile, assemble, run to halt against a fresh emulator instance.

    Returns (proc, mem, gfx) with all temp artifacts already removed.
    """
    asm_path, tmp_src = _compile_to_asm(source)
    try:
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)
        bin_path = asm_path.replace(".asm", ".bin")
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(bin_path)
        cycles = 0
        while cycles < 500000 and not proc.halted:
            cycles += 1
            proc.step()
        assert proc.halted, f"program did not halt (cycles={cycles})"
        return proc, mem, gfx
    finally:
        _cleanup(asm_path, tmp_src)


# Program shared by the sprite_blitall() and sprite_blit() tests:
# an 8x8 magenta (0x5F) outline box, transparent interior, at (128,120),
# staged in bank page 1 so the BANK-aware sprite read is also exercised.
# `BLIT;` is replaced with the call under test.
SPRITE_PROGRAM = """
void main() {
    set_bank(1);
    memset(0x8000, 0x5F, 8);
    for (int r = 1; r < 7; r++) {
        memset(0x8000 + r * 8,     0x5F, 1);
        memset(0x8000 + r * 8 + 1, 0x00, 6);
        memset(0x8000 + r * 8 + 7, 0x5F, 1);
    }
    memset(0x8000 + 56, 0x5F, 8);

    poke(0xF000, 0x80);          // data address high byte -> 0x8000
    poke(0xF001, 0x00);          // data address low byte
    poke(0xF002, 128);           // x
    poke(0xF003, 120);           // y
    poke(0xF004, 8);             // width
    poke(0xF005, 8);             // height
    poke(0xF006, 0b00000011);    // active + transparency, sprite layer 5
    poke(0xF007, 0x00);          // transparency color = black
    BLIT;
}
"""


def _assert_outline_box(mem, gfx, label):
    """Shared pixel/SCB assertions for the 8x8 outline box."""
    scb = mem.read_bytes_direct(0xF000, 8)
    data_addr = (scb[0] << 8) | scb[1]
    assert data_addr == 0x8000, (
        f"{label}: SCB data address = {data_addr:#06x}, expected 0x8000 "
        "(memset low-byte regression)")
    assert scb[2] == 128 and scb[3] == 120 and scb[4] == 8 and scb[5] == 8
    assert scb[6] == 0b00000011 and scb[7] == 0x00

    # Bitmap landed in bank page 1 exactly as drawn (row-major box).
    page = mem._bank_pages[1]
    assert page[0] == 0x5F and page[7] == 0x5F
    for r in range(1, 7):
        assert page[r * 8] == 0x5F and page[r * 8 + 7] == 0x5F, (
            f"{label}: interior row {r} borders missing")
        assert all(page[r * 8 + i] == 0x00 for i in range(1, 7))

    # Sprite layer 5 (index 0 of sprite_layers) holds the border.
    layer5 = gfx.sprite_layers[0]
    block = layer5[120:128, 128:136]
    assert int((block == 0x5F).sum()) == 28, (
        f"{label}: expected 28 border pixels on layer 5, "
        f"got {int((block == 0x5F).sum())}")
    # Interior is transparent: destination untouched (zeros here).
    assert int((block[1:7, 1:7] != 0).sum()) == 0, (
        f"{label}: transparent interior must be untouched")

    # Composited screen shows the border too (screen property is lazy).
    cell = gfx.screen[120:128, 128:136]
    assert int((cell == 0x5F).sum()) == 28, (
        f"{label}: composited screen missing sprite border "
        f"(got {int((cell == 0x5F).sum())} px)")
    print(f"PASS {label} (layer5 border=28, screen border=28, "
          f"transparent center preserved)")


# ---------------------------------------------------------------------------
# sprite_blitall()
# ---------------------------------------------------------------------------


def test_sprite_blitall_renders_from_scb():
    proc, mem, gfx = _assemble_and_run(
        SPRITE_PROGRAM.replace("BLIT;", "sprite_blitall();"))
    assert mem.current_bank == 1
    _assert_outline_box(mem, gfx, "sprite_blitall")


def test_sprite_blitall_clears_then_redraws_sprite_layers():
    """SPBLITALL clears sprite layers 5-8 before redrawing (no ghosting)."""
    source = SPRITE_PROGRAM.replace(
        "BLIT;",
        "sprite_blitall();\n"
        "    for (int i = 0; i < 4; i++) {\n"
        "        set_layer(i + 5);\n"
        "        screen_fill(0x5F);\n"
        "    }\n"
        "    sprite_blitall();")
    proc, mem, gfx = _assemble_and_run(source)
    # After the second SPBLITALL: layer 5 must hold ONLY the redrawn box
    # (no leftover fill from the manual screen_fill() step), and layers
    # 6-8 must be completely cleared by SPBLITALL's reset.
    assert int((gfx.sprite_layers[0] != 0).sum()) == 28, (
        f"sprite layer 5 should hold the 28-px box, "
        f"got {int((gfx.sprite_layers[0] != 0).sum())} px")
    for i in range(1, 4):
        assert int((gfx.sprite_layers[i] != 0).sum()) == 0, (
            f"sprite layer {i+5} still has ink after SPBLITALL re-blit")
    _assert_outline_box(mem, gfx, "sprite_blitall-redraw")
    print("PASS sprite layers cleared before re-blit")


# ---------------------------------------------------------------------------
# sprite_blit(id)
# ---------------------------------------------------------------------------


def test_sprite_blit_single_sprite():
    proc, mem, gfx = _assemble_and_run(
        SPRITE_PROGRAM.replace("BLIT;", "sprite_blit(0);"))
    _assert_outline_box(mem, gfx, "sprite_blit(0)")


def test_sprite_blit_extra_sprites_ignored():
    """sprite_blit(3) with only sprite 0 configured renders nothing."""
    proc, mem, gfx = _assemble_and_run(
        SPRITE_PROGRAM.replace("BLIT;", "sprite_blit(3);"))
    total = sum(int((gfx.sprite_layers[i] != 0).sum()) for i in range(4))
    assert total == 0, (
        f"sprite_blit(3) must not blit sprite 0 (got {total} px)")
    print("PASS sprite_blit(3) renders 0 px (sprite 0 untouched)")


# ---------------------------------------------------------------------------
# Codegen wiring
# ---------------------------------------------------------------------------


def test_sprite_builtins_mapped_and_implemented():
    gen = CodeGenerator()
    for name, label in (("sprite_blit", "builtin_sprite_blit"),
                        ("sprite_blitall", "builtin_sprite_blitall")):
        assert gen.builtin_functions[name] == label
        assert label in CodeGenerator.BUILTIN_IMPLEMENTATIONS
    impl_blit = CodeGenerator.BUILTIN_IMPLEMENTATIONS["builtin_sprite_blit"]
    impl_all = CodeGenerator.BUILTIN_IMPLEMENTATIONS["builtin_sprite_blitall"]
    assert any(line.startswith("SPBLIT ") for line in impl_blit)
    assert any(line == "SPBLITALL" for line in impl_all)
    print("PASS sprite builtin mapping / stub codegen")


def test_unused_sprite_builtins_not_emitted():
    """Lazy emission: a program that never touches sprites links no stub."""
    asm_path, tmp_src = _compile_to_asm("int main() { return 7; }\n")
    try:
        with open(asm_path, encoding="utf-8") as f:
            text = f.read()
        assert "builtin_sprite_blit" not in text
        assert "builtin_sprite_blitall" not in text
        print("PASS unused sprite builtins are not linked")
    finally:
        _cleanup(asm_path, tmp_src)


if __name__ == "__main__":
    test_sprite_builtins_mapped_and_implemented()
    test_unused_sprite_builtins_not_emitted()
    test_sprite_blitall_renders_from_scb()
    test_sprite_blitall_clears_then_redraws_sprite_layers()
    test_sprite_blit_single_sprite()
    test_sprite_blit_extra_sprites_ignored()
    print("All Astrid sprite-builtin tests passed!")