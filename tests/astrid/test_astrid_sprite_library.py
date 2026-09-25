"""Headless integration tests for astrid/progs/includes/sprite.ast."""
from pathlib import Path
import shutil

import numpy as np
import pytest

from astrid.compiler_api import compile_astrid
from nova_main import initialize_system


ROOT = Path(__file__).resolve().parents[2]
SPRITE_LIBRARY = ROOT / "astrid" / "progs" / "includes" / "sprite.ast"


RUNTIME_PROGRAM = r"""
include "includes/sprite.ast";

int main() {
    int source[8] = {0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88};
    int restored[8] = {0};

    // Byte-level and bulk VRAM storage/retrieval.
    if (sprite_vram_write(0x1234, 0x5A) != 1) { return 11; }
    if (sprite_vram_read(0x1234) != 0x5A) { return 12; }
    if (sprite_vram_fill(0x1234, 4, 0x77) != 1) { return 13; }
    if (sprite_vram_read(0x1237) != 0x77) { return 14; }
    if (sprite_vram_load(0, 0, source, 3) != 1) { return 14; }
    if (sprite_vram_read(2) != 0x33) { return 14; }
    if (sprite_vram_load(10, 20, source, 8) != 1) { return 15; }
    if (sprite_vram_save(10, 20, restored, 8) != 1) { return 16; }
    if (restored[0] != 0x11) { return 17; }
    if (restored[7] != 0x88) { return 18; }

    // The normal VRAM blit transfers software data to a layer and clears VRAM.
    set_layer(6);
    if (sprite_vram_blit(2) != 1) { return 19; }
    if (get_layer() != 6) { return 20; }
    if (sprite_vram_read(20 * 256 + 10) != 0) { return 21; }

    // Bitmap data remains in bank 1 while the active bank is restored to 0.
    if (sprite_bitmap_upload(1, 0x8000, source, 8) != 1) { return 31; }
    if (read_bank() != 0) { return 32; }
    if (sprite_bitmap_configure(1, 0x8000, 40, 40, 2, 4,
                                0x03, 0x00) != 1) { return 33; }
    if (sprite_bitmap_move(1, 48, 52) != 1) { return 34; }
    if (sprite_bitmap_disable(1) != 1) { return 35; }
    if (sprite_bitmap_enable(1) != 1) { return 36; }
    if (sprite_bitmap_blit(1, 1) != 1) { return 37; }
    if (read_bank() != 0) { return 38; }
    if (sprite_bitmap_blit_all(1) != 1) { return 39; }
    if (get_layer() != 6) { return 40; }

    // Primitive helpers draw on the requested layer and restore layer 6.
    if (sprite_primitive_clear(3) != 1) { return 51; }
    if (sprite_primitive_pixel(3, 10, 10, 0x2F) != 1) { return 52; }
    if (sprite_primitive_line(3, 20, 20, 24, 20, 0x3F) != 1) { return 53; }
    if (sprite_primitive_rect(3, 30, 30, 33, 32, 1, 0x4F) != 1) { return 54; }
    if (sprite_primitive_circle(3, 50, 50, 4, 1, 0x5F) != 1) { return 55; }
    if (get_layer() != 6) { return 56; }

    // Text erase clears full cells, so the old position leaves no trail.
    if (sprite_text_draw(4, 10, 40, "A", 0x1F) != 1) { return 61; }
    if (sprite_text_move(4, 10, 40, 30, 40, "A", 0x1F) != 1) { return 62; }
    if (get_layer() != 6) { return 63; }

    // Public operations reject invalid IDs, coordinates, and layer numbers.
    if (sprite_vram_write(65535, 0xA5) != 1) { return 71; }
    if (sprite_bitmap_configure(16, 0x8000, 0, 0, 8, 8, 3, 0) != 0) {
        return 72;
    }
    if (sprite_primitive_pixel(9, 0, 0, 0) != 0) { return 73; }
    if (sprite_text_move(4, 30, 40, -1, 40, "A", 0x1F) != 0) {
        return 74;
    }
    if (sprite_vram_write(65535, 0) != 1) { return 75; }
    return 0;
}
"""


BOUNDS_PROGRAM = r"""
include "includes/sprite.ast";

int main() {
    int pixels[2] = {1, 2};
    return sprite_bitmap_upload(1, 65535, pixels, 2);
}
"""


def _compile_and_run(tmp_path, source):
    include_dir = tmp_path / "includes"
    include_dir.mkdir()
    shutil.copyfile(SPRITE_LIBRARY, include_dir / "sprite.ast")
    source_path = tmp_path / "main.ast"
    asm_path = tmp_path / "main.asm"
    source_path.write_text(source, encoding="utf-8")

    assert compile_astrid(str(source_path), str(asm_path), log=None)
    from nova_assembler import Assembler
    assert Assembler(log=None, trace=False).assemble(str(asm_path))

    proc, mem, gfx, _kbd, _sound = initialize_system(enable_sound=False)
    proc.pc = mem.load(str(tmp_path / "main.bin"))
    cycles = 0
    while cycles < 5_000_000 and not proc.halted:
        proc.step()
        cycles += 1
    assert proc.halted, f"program did not halt after {cycles} cycles"
    return proc, mem, gfx, cycles


@pytest.mark.integration
def test_sprite_library_runtime_and_visible_pixels(tmp_path):
    proc, mem, gfx, cycles = _compile_and_run(tmp_path, RUNTIME_PROGRAM)

    assert proc.p0 == 0
    assert mem.current_bank == 0
    assert gfx.VL == 6
    assert gfx.vmode == 0

    scb = mem.read_bytes_direct(0xF010, 16)
    assert scb[:8] == [0x80, 0x00, 48, 52, 2, 4, 0x03, 0x00]
    assert scb[8:] == [0] * 8
    assert list(mem._bank_pages[1][:8]) == [0x11, 0x22, 0x33, 0x44,
                                              0x55, 0x66, 0x77, 0x88]

    # VRAM -> layer 2 retained the software frame before SBLIT cleared VRAM.
    assert np.all(gfx.get_layer_buffer_by_num(2)[20, 10:18] ==
                  [0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88])
    assert int((gfx.vram != 0).sum()) == 0

    bitmap = gfx.sprite_layers[0][52:56, 48:50]
    assert np.all(bitmap == [[0x11, 0x22], [0x33, 0x44],
                             [0x55, 0x66], [0x77, 0x88]])

    primitives = gfx.get_layer_buffer_by_num(3)
    assert primitives[10, 10] == 0x2F
    assert np.all(primitives[20, 20:25] == 0x3F)
    assert np.all(primitives[30:33, 30:34] == 0x4F)
    circle = primitives[45:56, 45:56]
    assert (circle == 0x5F).any()
    assert not (circle == 0x5F).all()

    text = gfx.get_layer_buffer_by_num(4)
    assert int((text[40:48, 10:18] != 0).sum()) == 0
    assert int((text[40:48, 30:38] != 0).sum()) > 0
    assert int((gfx.screen != 0).sum()) > 0
    print(f"PASS sprite library runtime ({cycles} cycles, visible pixels verified)")


@pytest.mark.unit
def test_sprite_library_range_guards(tmp_path):
    proc, _mem, _gfx, _cycles = _compile_and_run(tmp_path, BOUNDS_PROGRAM)
    assert proc.p0 == 0
