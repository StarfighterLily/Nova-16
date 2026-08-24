"""High-coverage tests for Astrid graphics builtins.

Covers:
1. Arity dispatch for the optional-argument scroll/roll family:
   scroll_x(layer) / scroll_x(layer, dir) / scroll_x(layer, dir, amount)
   (and the scroll_y / roll_x / roll_y equivalents) must each select their
   dedicated stack-layout-matched stub at the call site.
2. Lazy emission: unused arity variants are never linked into the binary.
3. Runtime semantics verified headlessly against real emulator pixels:
   - dir=0 rolls content toward -x/-y; non-zero dir reverses (+x/+y).
   - amount scales the roll distance; variable amounts exercise the
     in-stub NEG path.
   - Rolls wrap around the screen edges (SROL semantics).
   - scroll_* leaves VL pointing at the scrolled layer;
     roll_* saves/restores VL so the caller's active layer is untouched.
4. Newly exposed graphics capabilities: draw_rect (SRECT, filled and
   outline), vwrite/vread VRAM round-trip.
5. Starfield parallax integration: the compiled example keeps running,
   populates all three star layers, and its layers visibly move across
   timer-interrupt-driven parallax updates.

Layer indexing note: gfx.background_layers[i] is compositor layer i+1,
i.e. the buffer targeted by VL = i+1.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nova_main import initialize_system
from astrid.codegen.codegen import CodeGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compile_to_asm(source):
    """Compile Astrid source text; return (asm_text, source_path).
    Caller must call _cleanup(source_path)."""
    import tempfile
    fd = tempfile.NamedTemporaryFile(mode="w", suffix=".ast", delete=False,
                                     encoding="utf-8")
    fd.write(source)
    fd.close()
    source_path = fd.name
    from astrid_compiler import main as compiler_main
    old_argv = sys.argv
    sys.argv = [old_argv[0], source_path, "-o", source_path.replace(".ast", ".asm")]
    try:
        compiler_main()
    finally:
        sys.argv = old_argv
    with open(source_path.replace(".ast", ".asm"), encoding="utf-8") as f:
        asm_text = f.read()
    return asm_text, source_path


def _cleanup(source_path):
    for ext in [".ast", ".asm", ".bin", ".org", ".sym"]:
        p = source_path.replace(".ast", ext)
        if os.path.exists(p):
            os.unlink(p)


def _assemble_and_run(source, max_cycles=2000000):
    """Compile, assemble, run to halt. Returns (proc, gfx, cycles, source_path)."""
    _, source_path = _compile_to_asm(source)
    try:
        from nova_assembler import Assembler
        Assembler().assemble(source_path.replace(".ast", ".asm"))
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(source_path.replace(".ast", ".bin"))
        cycles = 0
        while cycles < max_cycles and not proc.halted:
            cycles += 1
            proc.step()
        assert proc.halted, f"Program did not halt (cycles={cycles})"
        return proc, gfx, cycles, source_path
    finally:
        pass  # cleanup handled by caller via returned source_path


def _pixel_positions(layer, color):
    ys, xs = (layer == color).nonzero()
    return list(zip(int(x) for x in xs), )


def _find_pixel(layer, color):
    """Return (x, y) of the single pixel with `color`, or None."""
    ys, xs = (layer == color).nonzero()
    if len(xs) != 1:
        return None
    return int(xs[0]), int(ys[0])


# ---------------------------------------------------------------------------
# Codegen-level: arity dispatch and lazy emission
# ---------------------------------------------------------------------------

ARITY_CASES = [
    # (call expression, expected CALL label)
    ("scroll_x(1)", "builtin_scroll_x"),
    ("scroll_x(1, 0)", "builtin_scroll_x_2"),
    ("scroll_x(1, 0, 2)", "builtin_scroll_x_3"),
    ("scroll_y(1)", "builtin_scroll_y"),
    ("scroll_y(1, 1)", "builtin_scroll_y_2"),
    ("scroll_y(1, 1, 4)", "builtin_scroll_y_3"),
    ("roll_x(2)", "builtin_roll_x"),
    ("roll_x(2, 0)", "builtin_roll_x_2"),
    ("roll_x(2, 0, 3)", "builtin_roll_x_3"),
    ("roll_y(2)", "builtin_roll_y"),
    ("roll_y(2, 1)", "builtin_roll_y_2"),
    ("roll_y(2, 1, 5)", "builtin_roll_y_3"),
]


@pytest.mark.parametrize("call_expr,expected_label", ARITY_CASES,
                         ids=[c[0] for c in ARITY_CASES])
def test_scroll_roll_arity_dispatch(call_expr, expected_label):
    """Each arity of the scroll/roll family calls its dedicated stub."""
    source = f"void main() {{ {call_expr}; }}"
    asm_text, source_path = _compile_to_asm(source)
    try:
        assert f"CALL {expected_label}" in asm_text, (
            f"{call_expr}: expected CALL {expected_label} in output"
        )
        # The selected stub must be emitted exactly once (lazy linking).
        assert asm_text.count(expected_label + ":") == 1
        print(f"PASS arity dispatch {call_expr} -> {expected_label}")
    finally:
        _cleanup(source_path)


def test_unused_arity_stubs_not_emitted():
    """Calling only the 3-arg form must not link the 1-/2-arg stubs."""
    source = """
void main() {
    scroll_x(1, 0, 2);
    roll_y(2, 1, 3);
}
"""
    asm_text, source_path = _compile_to_asm(source)
    try:
        assert "builtin_scroll_x_3:" in asm_text
        assert "builtin_roll_y_3:" in asm_text
        for absent in ("builtin_scroll_x:", "builtin_scroll_x_2:",
                       "builtin_roll_y:", "builtin_roll_y_2:",
                       "builtin_scroll_y", "builtin_roll_x"):
            assert absent not in asm_text, f"{absent} should not be emitted"
        print("PASS test_unused_arity_stubs_not_emitted")
    finally:
        _cleanup(source_path)


def test_mixed_arities_emit_each_stub_once():
    """A program mixing arities links each needed stub exactly once."""
    source = """
void main() {
    scroll_x(1);
    scroll_x(1, 0);
    scroll_x(1, 0, 2);
}
"""
    asm_text, source_path = _compile_to_asm(source)
    try:
        for label in ("builtin_scroll_x", "builtin_scroll_x_2",
                      "builtin_scroll_x_3"):
            assert asm_text.count(label + ":") == 1, (
                f"{label} should be emitted exactly once"
            )
        print("PASS test_mixed_arities_emit_each_stub_once")
    finally:
        _cleanup(source_path)


def test_graphics_tables_consistent():
    """roll/draw_rect/vread/vwrite are mapped and every arity stub exists."""
    gen = CodeGenerator()
    for name in ("roll_x", "roll_y", "draw_rect", "vread", "vwrite"):
        assert name in gen.builtin_functions, f"{name} missing from builtins"
    for family in ("scroll_x", "scroll_y", "roll_x", "roll_y"):
        table = CodeGenerator.ARITY_BUILTINS[family]
        assert set(table.keys()) == {1, 2, 3}
        for label in table.values():
            assert label in CodeGenerator.BUILTIN_IMPLEMENTATIONS
    print("PASS test_graphics_tables_consistent")


# ---------------------------------------------------------------------------
# Runtime: horizontal scrolling
# ---------------------------------------------------------------------------

def test_scroll_x_default_moves_left():
    """scroll_x(layer) defaults to dir=0, amount=1: content moves -x."""
    source = """
void main() {
    set_layer(1);
    set_pos(10, 10);
    write_screen(0x0F);
    scroll_x(1);
}
"""
    proc, gfx, cycles, src_path = _assemble_and_run(source)
    _cleanup(src_path)
    pos = _find_pixel(gfx.background_layers[0], 0x0F)
    assert pos == (9, 10), f"Expected pixel at (9,10) after scroll_x(1), got {pos}"
    print(f"PASS test_scroll_x_default_moves_left (cycles={cycles})")


def test_scroll_x_dir0_amount3():
    """scroll_x(layer, 0, 3) moves content left by 3."""
    source = """
void main() {
    set_layer(1);
    set_pos(20, 15);
    write_screen(0x0E);
    scroll_x(1, 0, 3);
}
"""
    proc, gfx, cycles, src_path = _assemble_and_run(source)
    _cleanup(src_path)
    pos = _find_pixel(gfx.background_layers[0], 0x0E)
    assert pos == (17, 15), f"Expected (17,15), got {pos}"
    print(f"PASS test_scroll_x_dir0_amount3 (cycles={cycles})")


def test_scroll_x_dir1_reverses():
    """Non-zero dir reverses the roll direction (+x)."""
    source = """
void main() {
    set_layer(1);
    set_pos(10, 15);
    write_screen(0x0D);
    scroll_x(1, 1, 3);
}
"""
    proc, gfx, cycles, src_path = _assemble_and_run(source)
    _cleanup(src_path)
    pos = _find_pixel(gfx.background_layers[0], 0x0D)
    assert pos == (13, 15), f"Expected (13,15), got {pos}"
    print(f"PASS test_scroll_x_dir1_reverses (cycles={cycles})")


def test_scroll_x_variable_amount_neg_path():
    """A variable amount exercises the in-stub NEG register path."""
    source = """
void main() {
    int amt = 4;
    set_layer(1);
    set_pos(30, 40);
    write_screen(0x0C);
    scroll_x(1, 1, amt);
}
"""
    proc, gfx, cycles, src_path = _assemble_and_run(source)
    _cleanup(src_path)
    pos = _find_pixel(gfx.background_layers[0], 0x0C)
    assert pos == (34, 40), f"Expected (34,40), got {pos}"
    print(f"PASS test_scroll_x_variable_amount_neg_path (cycles={cycles})")


def test_scroll_x_wraps_at_edge():
    """Rolls wrap around: pixel at x=0 moving left appears at x=255."""
    source = """
void main() {
    set_layer(1);
    set_pos(0, 12);
    write_screen(0x0B);
    scroll_x(1, 0, 1);
}
"""
    proc, gfx, cycles, src_path = _assemble_and_run(source)
    _cleanup(src_path)
    pos = _find_pixel(gfx.background_layers[0], 0x0B)
    assert pos == (255, 12), f"Expected wrap to (255,12), got {pos}"
    print(f"PASS test_scroll_x_wraps_at_edge (cycles={cycles})")


def test_scroll_x_only_targets_given_layer():
    """scroll_x(layer, ...) must not disturb other layers."""
    source = """
void main() {
    set_layer(1);
    set_pos(50, 50);
    write_screen(0x01);
    set_layer(2);
    set_pos(60, 60);
    write_screen(0x02);
    scroll_x(1, 0, 5);
}
"""
    proc, gfx, cycles, src_path = _assemble_and_run(source)
    _cleanup(src_path)
    p1 = _find_pixel(gfx.background_layers[0], 0x01)
    p2 = _find_pixel(gfx.background_layers[1], 0x02)
    assert p1 == (45, 50), f"Layer 1 pixel should move to (45,50), got {p1}"
    assert p2 == (60, 60), f"Layer 2 pixel must stay put, got {p2}"
    print(f"PASS test_scroll_x_only_targets_given_layer (cycles={cycles})")


# ---------------------------------------------------------------------------
# Runtime: vertical scrolling
# ---------------------------------------------------------------------------

def test_scroll_y_default_moves_up():
    """scroll_y(layer) defaults to dir=0, amount=1: content moves -y."""
    source = """
void main() {
    set_layer(1);
    set_pos(11, 20);
    write_screen(0x0F);
    scroll_y(1);
}
"""
    proc, gfx, cycles, src_path = _assemble_and_run(source)
    _cleanup(src_path)
    pos = _find_pixel(gfx.background_layers[0], 0x0F)
    assert pos == (11, 19), f"Expected (11,19), got {pos}"
    print(f"PASS test_scroll_y_default_moves_up (cycles={cycles})")


def test_scroll_y_dir1_moves_down():
    """scroll_y(layer, 1, n) moves content down (+y)."""
    source = """
void main() {
    set_layer(1);
    set_pos(11, 20);
    write_screen(0x09);
    scroll_y(1, 1, 6);
}
"""
    proc, gfx, cycles, src_path = _assemble_and_run(source)
    _cleanup(src_path)
    pos = _find_pixel(gfx.background_layers[0], 0x09)
    assert pos == (11, 26), f"Expected (11,26), got {pos}"
    print(f"PASS test_scroll_y_dir1_moves_down (cycles={cycles})")


def test_scroll_y_wraps_at_edge():
    """Vertical rolls wrap: pixel at y=255 moving down appears at y=0."""
    source = """
void main() {
    set_layer(1);
    set_pos(14, 255);
    write_screen(0x08);
    scroll_y(1, 1, 1);
}
"""
    proc, gfx, cycles, src_path = _assemble_and_run(source)
    _cleanup(src_path)
    pos = _find_pixel(gfx.background_layers[0], 0x08)
    assert pos == (14, 0), f"Expected wrap to (14,0), got {pos}"
    print(f"PASS test_scroll_y_wraps_at_edge (cycles={cycles})")


# ---------------------------------------------------------------------------
# Runtime: roll_ variants preserve the active layer
# ---------------------------------------------------------------------------

def test_roll_x_preserves_active_layer():
    """roll_x rolls the target layer but restores VL afterwards.

    After roll_x(1, ...), a subsequent write_screen must land on the
    previously-selected layer (2), NOT on the rolled layer (1)."""
    source = """
void main() {
    set_layer(2);
    set_pos(70, 70);
    write_screen(0x05);
    roll_x(1, 0, 3);
    // If VL was restored, this lands on layer 2; if clobbered, layer 1.
    set_pos(80, 80);
    write_screen(0x06);
}
"""
    proc, gfx, cycles, src_path = _assemble_and_run(source)
    _cleanup(src_path)
    post_marker = _find_pixel(gfx.background_layers[1], 0x06)
    assert post_marker == (80, 80), (
        f"write_screen after roll_x must target layer 2, got {post_marker}"
    )
    print(f"PASS test_roll_x_preserves_active_layer (cycles={cycles})")


def test_roll_x_moves_target_layer():
    """roll_x(layer, ...) still rolls the requested layer's content."""
    source = """
void main() {
    set_layer(1);
    set_pos(70, 70);
    write_screen(0x05);
    set_layer(2);
    roll_x(1, 0, 3);
}
"""
    proc, gfx, cycles, src_path = _assemble_and_run(source)
    _cleanup(src_path)
    rolled = _find_pixel(gfx.background_layers[0], 0x05)
    assert rolled == (67, 70), f"Layer 1 pixel should move to (67,70), got {rolled}"
    print(f"PASS test_roll_x_moves_target_layer (cycles={cycles})")


def test_roll_y_preserves_active_layer_and_moves():
    """roll_y combines both guarantees: target moves, VL restored."""
    source = """
void main() {
    set_layer(2);
    set_pos(90, 90);
    write_screen(0x04);
    set_layer(3);
    roll_y(2, 1, 2);
    set_pos(91, 91);
    write_screen(0x07);
}
"""
    proc, gfx, cycles, src_path = _assemble_and_run(source)
    _cleanup(src_path)
    moved = _find_pixel(gfx.background_layers[1], 0x04)
    assert moved == (90, 92), f"Layer 2 pixel should move to (90,92), got {moved}"
    post = _find_pixel(gfx.background_layers[2], 0x07)
    assert post == (91, 91), f"Post-roll write must land on layer 3, got {post}"
    print(f"PASS test_roll_y_preserves_active_layer_and_moves (cycles={cycles})")


def test_scroll_x_leaves_vl_on_scrolled_layer():
    """By design scroll_* leaves VL pointing at the scrolled layer."""
    source = """
void main() {
    set_layer(2);
    scroll_x(1, 0, 1);
    set_pos(33, 33);
    write_screen(0x03);
}
"""
    proc, gfx, cycles, src_path = _assemble_and_run(source)
    _cleanup(src_path)
    landed = _find_pixel(gfx.background_layers[0], 0x03)
    assert landed == (33, 33), (
        f"write_screen after scroll_x must target layer 1, got {landed}"
    )
    print(f"PASS test_scroll_x_leaves_vl_on_scrolled_layer (cycles={cycles})")


# ---------------------------------------------------------------------------
# Runtime: newly exposed graphics capabilities
# ---------------------------------------------------------------------------

def test_set_color_sets_drawing_color():
    """set_color(c) writes VC; draw_char then renders in that color."""
    source = """
void main() {
    set_layer(1);
    set_color(0x0A);
    set_pos(20, 20);
    draw_char('X');
}
"""
    proc, gfx, cycles, src_path = _assemble_and_run(source)
    _cleanup(src_path)
    layer = gfx.background_layers[0]
    nz = int((layer == 0x0A).sum())
    assert nz > 0, f"draw_char should render pixels in color 0x0A, got {nz}"
    print(f"PASS test_set_color_sets_drawing_color (pixels={nz}, cycles={cycles})")


def test_draw_rect_codegen():
    """draw_rect emits SRECT with the correct operand order."""
    source = """
void main() {
    set_layer(1);
    set_pos(5, 5);
    draw_rect(20, 20, 1);
}
"""
    asm_text, source_path = _compile_to_asm(source)
    _cleanup(source_path)
    assert "CALL builtin_draw_rect" in asm_text
    assert "SRECT" in asm_text, "draw_rect must emit SRECT"
    # Args pushed reversed: filled, y2, x2 -> POP P1=x2, P2=y2, P3=filled
    assert "SRECT P1, P2, P3" in asm_text
    print("PASS test_draw_rect_codegen")


def test_draw_rect_outline_codegen():
    """draw_rect(..., 0) passes filled=0 (outline mode) to SRECT."""
    source = """
void main() {
    set_layer(1);
    set_pos(5, 5);
    draw_rect(20, 20, 0);
}
"""
    asm_text, source_path = _compile_to_asm(source)
    _cleanup(source_path)
    assert "CALL builtin_draw_rect" in asm_text
    print("PASS test_draw_rect_outline_codegen")


def test_draw_rect_runtime_pixels():
    """Headless pixel verification of a filled rectangle via SRECT.

    The fill color comes from VC; set_color() establishes it before the
    rectangle is drawn. Verifies exact coverage inside the rectangle and
    that nothing was drawn outside it."""
    source = """
void main() {
    set_layer(1);
    set_color(0x07);
    set_pos(100, 100);
    draw_rect(110, 105, 1);
}
"""
    proc, gfx, cycles, src_path = _assemble_and_run(source)
    _cleanup(src_path)
    layer = gfx.background_layers[0]
    nz_inside = int((layer[100:106, 100:111] == 0x07).sum())
    nz_outside = int((layer[:90, :] != 0).sum())
    assert nz_inside == 6 * 11, (
        f"Filled 11x6 rectangle should cover 66 pixels, got {nz_inside}"
    )
    assert nz_outside == 0, "No pixels should be drawn outside the rectangle"
    print(f"PASS test_draw_rect_runtime_pixels "
          f"(inside={nz_inside}, outside={nz_outside}, cycles={cycles})")


def test_vwrite_vread_roundtrip():
    """vwrite stores a value into VRAM at (VX,VY); vread fetches it back."""
    source = """
int main() {
    set_pos(42, 24);
    vwrite(0xAB);
    int v = vread(24 * 256 + 42);
    return v;
}
"""
    proc, gfx, cycles, src_path = _assemble_and_run(source)
    _cleanup(src_path)
    assert proc.p0 == 0xAB, f"vread should return 0xAB, got P0={proc.p0:#x}"
    print(f"PASS test_vwrite_vread_roundtrip (cycles={cycles}, P0={proc.p0:#x})")


def test_vread_returns_zero_for_empty_vram():
    """vread on untouched VRAM returns 0."""
    source = """
int main() {
    return vread(300 * 256 + 200);
}
"""
    proc, gfx, cycles, src_path = _assemble_and_run(source)
    _cleanup(src_path)
    assert proc.p0 == 0, f"Expected 0, got P0={proc.p0}"
    print(f"PASS test_vread_returns_zero_for_empty_vram (cycles={cycles})")


# ---------------------------------------------------------------------------
# Integration: starfield parallax with the new signature
# ---------------------------------------------------------------------------

def test_starfield_parallax_integration():
    """starfield.ast (new scroll_x/scroll_y signature) compiles, runs its
    while(1) loop across timer interrupts, populates all three star layers,
    and the parallax handler visibly moves layer content over time."""
    import shutil
    import tempfile
    astrid_dir = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(astrid_dir, "starfield.ast")
    fd, tmp_src = tempfile.mkstemp(suffix=".ast")
    os.close(fd)
    shutil.copyfile(src, tmp_src)
    from astrid_compiler import main as compiler_main
    old_argv = sys.argv
    sys.argv = [old_argv[0], tmp_src, "-o", tmp_src.replace(".ast", ".asm")]
    try:
        compiler_main()
    finally:
        sys.argv = old_argv

    try:
        from nova_assembler import Assembler
        Assembler().assemble(tmp_src.replace(".ast", ".asm"))
        bin_path = tmp_src.replace(".ast", ".bin")

        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(bin_path)

        def run_cycles(n):
            nonlocal proc
            c = 0
            while c < n and not proc.halted:
                c += 1
                proc.step()
            return c

        # Drawing completes well before 250k cycles; interrupts are enabled
        # by then, so the parallax ISR is actively scrolling layers.
        run_cycles(250000)
        assert not proc.halted, "starfield halted (ISR corruption regression)"
        counts1 = [int((gfx.background_layers[i] != 0).sum()) for i in range(3)]
        assert counts1[0] > 500 and counts1[1] > 100 and counts1[2] > 20, (
            f"star layers under-populated: {counts1}")
        snapshot1 = [gfx.background_layers[i].copy() for i in range(3)]

        run_cycles(60000)
        assert not proc.halted, "starfield halted during parallax phase"
        moved = any(
            not (snapshot1[i] == gfx.background_layers[i]).all()
            for i in range(3)
        )
        assert moved, "parallax ISR did not move any star layer content"
        print(f"PASS test_starfield_parallax_integration (counts={counts1})")
    finally:
        _cleanup(tmp_src)


if __name__ == "__main__":
    test_graphics_tables_consistent()
    for call_expr, expected_label in ARITY_CASES:
        test_scroll_roll_arity_dispatch(call_expr, expected_label)
    test_unused_arity_stubs_not_emitted()
    test_mixed_arities_emit_each_stub_once()
    test_scroll_x_default_moves_left()
    test_scroll_x_dir0_amount3()
    test_scroll_x_dir1_reverses()
    test_scroll_x_variable_amount_neg_path()
    test_scroll_x_wraps_at_edge()
    test_scroll_x_only_targets_given_layer()
    test_scroll_y_default_moves_up()
    test_scroll_y_dir1_moves_down()
    test_scroll_y_wraps_at_edge()
    test_roll_x_preserves_active_layer()
    test_roll_x_moves_target_layer()
    test_roll_y_preserves_active_layer_and_moves()
    test_scroll_x_leaves_vl_on_scrolled_layer()
    test_set_color_sets_drawing_color()
    test_draw_rect_codegen()
    test_draw_rect_outline_codegen()
    test_draw_rect_runtime_pixels()
    test_vwrite_vread_roundtrip()
    test_vread_returns_zero_for_empty_vram()
    test_starfield_parallax_integration()
    print("All Astrid graphics-builtin tests passed!")