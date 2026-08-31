"""Regression tests for game.ast sword swing and player flicker fixes.

Two reported defects:

1. **Sword sprite never appeared.** The `key == 101` branch of chkKey() had
   an empty body -- swordSwing() was defined but never called from anywhere,
   so pressing 'e' did nothing. The source now calls swordSwing(), which
   draws the "--" glyph pair on layer 5 at x +/- 8 when a facing is set.

2. **Character flickered on key press.** chkKey() saved oldx/oldy for ANY
   key press, including non-movement keys like 'e'. drawPlayer() then drew
   the sprite at the current position and immediately erased the SAME cells
   with color 0 (old == current), blanking the freshly drawn player between
   compositor refreshes -- visible as flicker exactly when a key was held.
   drawPlayer() now erases the previous position ONLY when it differs from
   the current one (and erases before drawing, as defense in depth).

Also covers the playfield clamp alignment: right/down bounds are 248/240 so
the player can hug all four boundary walls drawn by the level loops.
"""
import os
import shutil
import sys
import tempfile

# Path setup handled by tests/astrid/conftest.py

from nova_main import initialize_system


def _compile_ast_copy(src_path):
    """Compile a COPY of an existing .ast; return (asm_path, tmp_source)."""
    fd, tmp_src = tempfile.mkstemp(suffix=".ast")
    os.close(fd)
    shutil.copyfile(src_path, tmp_src)
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

def _boot_game(asm_path):
    """Assemble + load the compiled game; return (proc, mem, gfx, kbd)."""
    from nova_assembler import Assembler
    Assembler().assemble(asm_path)
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    proc.pc = mem.load(asm_path.replace(".asm", ".bin"))
    return proc, mem, gfx, kbd


def _compile_to_asm(source):
    """Compile source text; return (asm_path, tmp_source_path).
    Caller must _cleanup(asm_path, tmp_src)."""
    fd = tempfile.NamedTemporaryFile(mode="w", suffix=".ast", delete=False,
                                     encoding="utf-8")
    fd.write(source)
    fd.close()
    from astrid_compiler import main as compiler_main
    out = fd.name.replace(".ast", ".asm")
    old_argv = sys.argv
    sys.argv = [old_argv[0], fd.name, "-o", out]
    try:
        compiler_main()
    finally:
        sys.argv = old_argv
    return out, fd.name




def test_sword_sprite_appears_on_swing_key():
    """Pressing 'd' (face right) then 'e' must draw the sword on layer 5.

    Regression: the `key == 101` branch was empty, so no sword pixels ever
    appeared regardless of keys pressed."""
    astrid_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'astrid', 'progs')
    asm_path, tmp_src = _compile_ast_copy(os.path.join(astrid_dir, "game.ast"))
    try:
        proc, mem, gfx, kbd = _boot_game(asm_path)

        def run(n):
            c = 0
            while c < n and not proc.halted:
                c += 1
                proc.step()
            return c

        run(100000)                     # reach the while(1) game loop
        assert not proc.halted

        # Face right and settle so facing == 2.
        kbd.add_key(100)
        run(30000)
        x = mem.read_word_fast(0x8000)
        y = mem.read_word_fast(0x8002)

        # Baseline: no ink in the sword cell to the right of the player.
        # Layer 5 is a sprite layer: sprite_layers[VL - 5] -> index 0.
        # The swing draws at (x + 8, y + 8): the row of the player's X glyph.
        layer5 = gfx.sprite_layers[0]
        sy = y + 8
        before = int((layer5[sy:sy + 8, x + 8:x + 16] != 0).sum())

        # Sample finely after 'e': with counter > 4 the auto-clear erases
        # the sword within a few thousand cycles, so a coarse wait would
        # miss it entirely.
        kbd.add_key(101)                # 'e' -> swordSwing()
        peak = 0
        c = 0
        while c < 30000 and not proc.halted:
            c += 1
            proc.step()
            if c % 250 == 0:
                peak = max(peak, int((layer5[sy:sy + 8,
                                            x + 8:x + 16] != 0).sum()))
        assert not proc.halted

        assert before == 0, f"sword cell should start empty, had {before} px"
        assert peak > 0, (
            f"no sword pixels appeared at ({x + 8},{sy}) after pressing 'e'; "
            "swordSwing() is still never invoked")
        print(f"PASS test_sword_sprite_appears_on_swing_key "
              f"(sword px={peak} at x+8={x + 8}, y+8={sy})")
    finally:
        _cleanup(asm_path, tmp_src)


def test_no_flicker_on_nonmovement_key():
    """A non-movement key ('e') must NOT make oldx/oldy equal the live
    position (the flicker source: drawPlayer would erase its own sprite).

    Regression: chkKey() updated oldx/oldy for any key, so after 'e'
    oldx == x and drawPlayer blanked the just-drawn player each frame."""
    astrid_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'astrid', 'progs')
    asm_path, tmp_src = _compile_ast_copy(os.path.join(astrid_dir, "game.ast"))
    try:
        proc, mem, gfx, kbd = _boot_game(asm_path)

        def read(name):
            base = {"x": 0x8000, "y": 0x8002,
                    "oldx": 0x8004, "oldy": 0x8006}[name]
            return mem.read_word_fast(base)

        def run(n):
            c = 0
            while c < n and not proc.halted:
                c += 1
                proc.step()
            return c

        run(100000)
        assert not proc.halted

        # Move once: old becomes the pre-move position, distinct from live.
        kbd.add_key(100)                # 'd': 120 -> 128, old = 120
        run(30000)
        assert read("x") == 128 and read("oldx") == 120, \
            (read("x"), read("oldx"))

        # Press 'e' repeatedly: position must not move AND the saved old
        # position must stay distinct from the live one (no self-erase).
        for _ in range(5):
            kbd.add_key(101)
        run(150000)
        assert read("x") == 128, f"'e' moved the player: x={read('x')}"
        assert read("oldx") != read("x") or read("oldy") != read("y"), (
            f"flicker regression: old==current after non-movement key "
            f"(old=({read('oldx')},{read('oldy')}), "
            f"cur=({read('x')},{read('y')}))")

        # And the player must still be visibly rendered after all that.
        layer5 = gfx.sprite_layers[0]       # compositor/sprite layer 5
        px = int((layer5[read("y"):read("y") + 16,
                         read("x"):read("x") + 8] != 0).sum())
        assert px > 0, "player sprite vanished after non-movement keys"
        print(f"PASS test_no_flicker_on_nonmovement_key "
              f"(player px={px}, old=({read('oldx')},{read('oldy')}), "
              f"cur=({read('x')},{read('y')}))")
    finally:
        _cleanup(asm_path, tmp_src)


def test_player_hugs_all_four_walls():
    """The clamps must let the player reach every boundary wall:
    x in [8, 248], y in [8, 240]."""
    astrid_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'astrid', 'progs')
    asm_path, tmp_src = _compile_ast_copy(os.path.join(astrid_dir, "game.ast"))
    try:
        proc, mem, gfx, kbd = _boot_game(asm_path)

        def read(addr):
            return mem.read_word_fast(addr)

        def run(n):
            c = 0
            while c < n and not proc.halted:
                c += 1
                proc.step()
            return c

        run(100000)
        mash_budget = 200000            # ~30 moves * ~2k cycles/iteration
        for key, addr, expected in [
            (97, 0x8000, 8),            # left  -> x == 8
            (115, 0x8002, 240),         # down  -> y == 240
            (100, 0x8000, 248),         # right -> x == 248
            (119, 0x8002, 8),           # up    -> y == 8
        ]:
            for _ in range(40):
                kbd.add_key(key)
            run(mash_budget)
            got = read(addr)
            assert got == expected, \
                f"key {key}: expected {addr:#06X}=={expected}, got {got}"
        print("PASS test_player_hugs_all_four_walls")
    finally:
        _cleanup(asm_path, tmp_src)


def test_global_string_arg_skips_itos():
    """write_text(<global string var>, c) must pass the pointer, not ITOS it.

    Regression: _is_string_or_binary_expr only consulted LOCAL var_types,
    so the file-scope `string sword;` was treated as an int and
    write_text(sword, 0x1F) emitted `ITOS P5, P4` -- converting the
    variable's POINTER (0x251C) into the digit string "9500" on screen
    instead of the sword dashes."""
    source = """
string msg;

void show() {
    set_layer(5);
    set_pos(10, 10);
    write_text(msg, 0x1F);
}

void main() {
    msg = "Hi";
    show();
}
"""
    asm_path, tmp_src = _compile_to_asm(source)
    try:
        with open(asm_path, encoding="utf-8") as f:
            text = f.read()
        assert "ITOS" not in text, (
            "global string passed to write_text must not be ITOS-converted:\n"
            + text)
        assert "gvar_msg" in text
        print("PASS test_global_string_arg_skips_itos")
    finally:
        _cleanup(asm_path, tmp_src)


def test_sword_shows_dashes_not_digits():
    """Pressing 'd' then 'e' must draw exactly the '--' glyphs on layer 5.

    Regression: game.ast's global `string sword` was ITOS-converted at its
    write_text call site, rendering the decimal digits of the string's
    address (0x251C = "9500") instead of the sword. Verified pixel-for-
    pixel against a reference TEXT render of '--' at an identical cell."""
    astrid_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'astrid', 'progs')
    asm_path, tmp_src = _compile_ast_copy(os.path.join(astrid_dir, "game.ast"))
    try:
        proc, mem, gfx, kbd = _boot_game(asm_path)

        # Reference render of "--" on layer 5 via a tiny hand-written stub.
        ref_asm = os.path.join(astrid_dir, "_ref_dashes.asm")
        with open(ref_asm, "w", encoding="ascii") as f:
            f.write(
                "ORG 0x1000\n"
                "start:\n"
                "MOV SP, 0xFF00\n"
                "MOV VL, 5\n"
                "MOV VX, 100\n"
                "MOV VY, 100\n"
                "MOV VC, 0x1F\n"
                "MOV P0, ref_str\n"
                "TEXT P0\n"
                "HLT\n"
                "ref_str: DEFSTR \"--\"\n"
            )
        try:
            from nova_assembler import Assembler
            Assembler().assemble(ref_asm)
            rproc, rmem, rgfx, _, _ = initialize_system(enable_sound=False)
            rproc.pc = rmem.load(ref_asm.replace(".asm", ".bin"))
            c = 0
            while c < 100000 and not rproc.halted:
                c += 1
                rproc.step()
            reference = (rgfx.sprite_layers[0][100:108, 100:116] != 0)
        finally:
            for ext in (".asm", ".bin", ".org", ".sym"):
                p = ref_asm.replace(".asm", ext)
                if os.path.exists(p):
                    os.unlink(p)

        def run(n):
            c = 0
            while c < n and not proc.halted:
                c += 1
                proc.step()
            return c

        run(150000)
        kbd.add_key(100)                # 'd': face right
        run(40000)
        x = mem.read_word_fast(0x8000)
        y = mem.read_word_fast(0x8002)

        kbd.add_key(101)                # 'e': swordSwing()
        run(3000)                       # catch it during its short lifetime

        layer5 = gfx.sprite_layers[0]
        sy = y + 8                      # swing draws at (x +/- 8, y + 8)
        cell = (layer5[sy:sy + 8, x + 8:x + 24] != 0)
        assert (cell == reference).all(), (
            f"sword cell renders {int(cell.sum())} ink px but '--' renders "
            f"{int(reference.sum())}; digits are being drawn again")
        print(f"PASS test_sword_shows_dashes_not_digits "
              f"(ink={int(cell.sum())} px at ({x + 8},{sy}))")
    finally:
        _cleanup(asm_path, tmp_src)


# ---------------------------------------------------------------------------
# Platform semantics: the TEXT erase idiom clearSwing() relies on
# ---------------------------------------------------------------------------

_ERASE_PROBE = (
    "ORG 0x1000\n"
    "start:\n"
    "MOV SP, 0xFF00\n"
    "; Phase 1: draw '--' at (100,100) layer 5, color 0x1F\n"
    "MOV VL, 5\n"
    "MOV VX, 100\n"
    "MOV VY, 100\n"
    "MOV VC, 0x1F\n"
    "MOV P0, s_dash\n"
    "TEXT P0\n"
    "HLT\n"
    "; Phase 2: try to erase with two spaces, color 0\n"
    "phase2:\n"
    "MOV VX, 100\n"
    "MOV VY, 100\n"
    "MOV VC, 0x00\n"
    "MOV P0, s_sp\n"
    "TEXT P0\n"
    "HLT\n"
    "; Phase 3: erase by rewriting the same glyphs in black\n"
    "phase3:\n"
    "MOV VX, 100\n"
    "MOV VY, 100\n"
    "MOV VC, 0x00\n"
    "MOV P0, s_dash\n"
    "TEXT P0\n"
    "HLT\n"
    "s_dash: DEFSTR \"--\"\n"
    "s_sp:   DEFSTR \"  \"\n"
)


def _run_erase_probe():
    """Assemble and run the erase probe; return (ink_draw, ink_spaces,
    ink_black)."""
    probe = os.path.join(tempfile.gettempdir(), "_erase_probe.asm")
    with open(probe, "w", encoding="ascii") as f:
        f.write(_ERASE_PROBE)
    try:
        from nova_assembler import Assembler
        Assembler().assemble(probe)
        syms = {}
        with open(probe.replace(".asm", ".sym"), encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) == 2:
                    syms[parts[0]] = int(parts[1], 16)

        proc, mem, gfx, _, _ = initialize_system(enable_sound=False)
        mem.load(probe.replace(".asm", ".bin"))
        layer5 = gfx.sprite_layers[0]

        def run_to(target):
            proc.halted = False
            proc.pc = target
            c = 0
            while c < 50000 and not proc.halted:
                c += 1
                proc.step()

        run_to(syms["start"])
        ink_draw = int((layer5[100:108, 100:116] != 0).sum())
        run_to(syms["phase2"])
        ink_spaces = int((layer5[100:108, 100:116] != 0).sum())
        run_to(syms["phase3"])
        ink_black = int((layer5[100:108, 100:116] != 0).sum())
        return ink_draw, ink_spaces, ink_black
    finally:
        for ext in (".asm", ".bin", ".org", ".sym"):
            p = probe.replace(".asm", ext)
            if os.path.exists(p):
                os.unlink(p)


def test_space_glyph_write_is_noop():
    """write_text("  ", c) must write ZERO pixels.

    Platform semantics behind the clearSwing regression: TEXT only writes
    pixels where the glyph bitmap has bits set (_write_char_bitmap does
    target_slice[visible_matrix] = color), and the space glyph is blank.
    Any erase strategy built on spaces can never work."""
    ink_draw, ink_spaces, _ = _run_erase_probe()
    assert ink_draw > 0, "probe failed to draw dashes"
    assert ink_spaces == ink_draw, (
        f"space-glyph write changed pixels ({ink_draw} -> {ink_spaces}); "
        "spaces are NOT no-ops anymore -- revisit the erase idiom docs")
    print(f"PASS test_space_glyph_write_is_noop "
          f"(draw={ink_draw}, after-spaces={ink_spaces})")


def test_same_glyph_black_erase_clears_cell():
    """Rewriting the SAME glyphs with color 0 fully erases them.

    This is the only working TEXT-based erase idiom and what drawPlayer,
    enemy, and clearSwing all rely on."""
    ink_draw, _, ink_black = _run_erase_probe()
    assert ink_draw > 0
    assert ink_black == 0, (
        f"rewrite-in-black left {ink_black} ink px; erase idiom broken")
    print("PASS test_same_glyph_black_erase_clears_cell")


def test_swing_auto_clears_and_player_survives():
    """Full cycle on the real game: swing -> sword appears; auto-clear
    erases it at the SWING-TIME cell; player sprite stays intact.

    Regression: clearSwing used write_text("  ", 0x00), a pixel-level
    no-op, so swung swords stayed on screen forever. It now rewrites the
    dashes in black at the remembered swx/swy cell."""
    astrid_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'astrid', 'progs')
    asm_path, tmp_src = _compile_ast_copy(os.path.join(astrid_dir, "game.ast"))
    try:
        proc, mem, gfx, kbd = _boot_game(asm_path)

        # Player instance base address from the symbol table. game.ast now
        # keeps player state in `struct Player {...} Player`, whose fields
        # are word slots: x=+0x00, y=+0x02, ..., swinging=+0x10.
        gvar_Player = None
        with open(asm_path.replace(".asm", ".sym"), encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) == 2 and parts[0] == "gvar_Player":
                    gvar_Player = int(parts[1], 16)
        assert gvar_Player is not None, "gvar_Player symbol not found"

        def run(n):
            c = 0
            while c < n and not proc.halted:
                c += 1
                proc.step()
            return c

        layer5 = gfx.sprite_layers[0]
        run(150000)
        kbd.add_key(100)                # 'd': face right
        run(40000)
        x = mem.read_word_fast(gvar_Player + 0x00)
        y = mem.read_word_fast(gvar_Player + 0x02)
        sx, sy = x + 8, y + 8           # facing==2 swing cell

        kbd.add_key(101)                # 'e': swordSwing()
        peak_ink = 0
        ever_swinging = 0
        c = 0
        while c < 200000 and not proc.halted:
            c += 1
            proc.step()
            if c % 250 == 0:
                peak_ink = max(peak_ink,
                               int((layer5[sy:sy + 8, sx:sx + 16] != 0).sum()))
                ever_swinging = max(ever_swinging,
                                    mem.read_word_fast(gvar_Player + 0x10))

        assert not proc.halted
        assert ever_swinging == 1, "swinging flag was never set"
        assert peak_ink == 12, (
            f"sword dash glyphs should render 12 ink px, peaked at {peak_ink}")

        # After the timeout the sword cell must be empty; player intact.
        final_ink = int((layer5[sy:sy + 8, sx:sx + 16] != 0).sum())
        px = mem.read_word_fast(gvar_Player + 0x00)
        py = mem.read_word_fast(gvar_Player + 0x02)
        player_px = int((layer5[py:py + 16, px:px + 8] != 0).sum())
        assert final_ink == 0, (
            f"sword not cleared after timeout: {final_ink} ink px remain "
            "(clearSwing regression)")
        assert player_px > 0, "auto-clear wiped the player sprite"
        print(f"PASS test_swing_auto_clears_and_player_survives "
              f"(peak={peak_ink} px, cleared, player={player_px} px)")
    finally:
        _cleanup(asm_path, tmp_src)


if __name__ == "__main__":
    test_sword_sprite_appears_on_swing_key()
    test_no_flicker_on_nonmovement_key()
    test_player_hugs_all_four_walls()
    test_global_string_arg_skips_itos()
    test_sword_shows_dashes_not_digits()
    test_space_glyph_write_is_noop()
    test_same_glyph_black_erase_clears_cell()
    test_swing_auto_clears_and_player_survives()
    print("All sword/flicker regression tests passed!")


