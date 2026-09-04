"""Regression tests for sprttest.ast player ship rendering sync.

The original bug: movePlayer() updated the Player struct fields (x, y) but
did NOT call SCBwrite() to update the Sprite Control Block at 0xF000. This
meant the sprite was rendered at the old position visually, even though the
Player struct had the new position.

Since then the game switched from keyboard to mouse control: movePlayer()
now copies the mouse position registers (MX/MY) into SCB 0 on every update
tick, so the rendered sprite always matches the position the game logic is
using. These tests pin the current contract:

  1. SCB 0 x/y mirrors the MX/MY mouse registers after an update tick.
  2. The mirroring keeps working across successive mouse positions (the SCB
     is refreshed every tick, not just once).
"""
import os
import sys

# Path setup handled by tests/astrid/conftest.py

from nova_main import initialize_system


def _compile_ast_copy(src_path):
    """Compile a COPY of an existing .ast; return (asm_path, tmp_source)."""
    import shutil
    import tempfile
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


def _load_symbols(asm_path):
    """Parse the assembler's .sym file into {name: address}."""
    sym = {}
    with open(asm_path.replace(".asm", ".sym")) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split()
                if len(parts) == 2 and parts[1].startswith("0x"):
                    sym[parts[0]] = int(parts[1], 16)
    return sym


def _wait_for_scb(proc, mem, x, y, max_steps=800000):
    """Step until SCB 0 mirrors (x, y); the update tick runs every 2560
    loop iterations. Polls instead of counting steps so the test does not
    depend on exact instruction counts."""
    for _ in range(max_steps // 500):
        for _ in range(500):
            proc.step()
        scb_x = mem.read_byte_fast(0xF000 + 2)
        scb_y = mem.read_byte_fast(0xF000 + 3)
        if scb_x == x and scb_y == y:
            return True
    return False


def test_sprttest_player_scb_mirrors_mouse_position():
    """movePlayer() must copy MX/MY into SCB 0 so the sprite follows the mouse."""
    astrid_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'astrid', 'progs'
    )
    src = os.path.join(astrid_dir, "sprttest.ast")
    asm_path, tmp_src = _compile_ast_copy(src)
    try:
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(asm_path.replace(".asm", ".bin"))

        # Seed the mouse BEFORE the game starts; the starfield init is the
        # slow part, then loadPlayer() centers the ship and the first update
        # tick mirrors these registers into SCB 0.
        proc.mx = 100
        proc.my = 150
        assert _wait_for_scb(proc, mem, 100, 150), \
            "SCB 0 must mirror MX/MY after an update tick"

        print("PASS test_sprttest_player_scb_mirrors_mouse_position")
    finally:
        _cleanup(asm_path, tmp_src)


def test_sprttest_player_scb_tracks_successive_moves():
    """SCB 0 must track the mouse across successive update ticks."""
    astrid_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'astrid', 'progs'
    )
    src = os.path.join(astrid_dir, "sprttest.ast")
    asm_path, tmp_src = _compile_ast_copy(src)
    try:
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(asm_path.replace(".asm", ".bin"))

        for mx, my in [(10, 20), (200, 110), (55, 240)]:
            proc.mx = mx
            proc.my = my
            assert _wait_for_scb(proc, mem, mx, my), \
                f"SCB 0 must track successive mouse moves (target {mx},{my})"

        print("PASS test_sprttest_player_scb_tracks_successive_moves")
    finally:
        _cleanup(asm_path, tmp_src)


if __name__ == "__main__":
    test_sprttest_player_scb_mirrors_mouse_position()
    test_sprttest_player_scb_tracks_successive_moves()
    print("All sprttest movement tests passed!")
