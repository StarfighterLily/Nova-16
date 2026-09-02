"""Regression test for sprttest.ast player ship movement.

The original bug: movePlayer() updated the Player struct fields (x, y) but
did NOT call SCBwrite() to update the Sprite Control Block at 0xF000. This
meant the sprite was rendered at the old position visually, even though the
Player struct had the new position.

The fix: call SCBwrite() after updating the player's position to sync the
SCB with the new position.
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


def test_sprttest_player_moves_and_scb_syncs():
    """Player movement must update BOTH the Player struct and the SCB.

    Before the fix, only the Player struct was updated; the SCB (which
    controls where the sprite is rendered) stayed at the old position.
    """
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

        # Run for a bit to let loadPlayer execute
        for _ in range(10000):
            proc.step()

        # Verify initial state: Player struct and SCB should match
        player_x = mem.read_word_fast(0x8012 + 0)
        player_y = mem.read_word_fast(0x8012 + 2)
        scb_x = mem.read_byte_fast(0xF000 + 2)
        scb_y = mem.read_byte_fast(0xF000 + 3)
        assert player_x == scb_x, f"Initial x mismatch: Player={player_x}, SCB={scb_x}"
        assert player_y == scb_y, f"Initial y mismatch: Player={player_y}, SCB={scb_y}"

        # Test all four directions
        for key, expected_dx, expected_dy in [(119, 0, -4), (115, 0, 4), (97, -4, 0), (100, 4, 0)]:
            x0, y0 = mem.read_word_fast(0x8012 + 0), mem.read_word_fast(0x8012 + 2)
            sx0, sy0 = mem.read_byte_fast(0xF000 + 2), mem.read_byte_fast(0xF000 + 3)
            kbd.add_key(key)
            # Run enough cycles for the key to be processed
            for _ in range(200000):
                proc.step()
            x1, y1 = mem.read_word_fast(0x8012 + 0), mem.read_word_fast(0x8012 + 2)
            sx1, sy1 = mem.read_byte_fast(0xF000 + 2), mem.read_byte_fast(0xF000 + 3)
            pdx, pdy = x1 - x0, y1 - y0
            sdx, sdy = sx1 - sx0, sy1 - sy0

            # Both Player struct AND SCB must move by the same amount
            assert pdx == expected_dx, f"Key {key}: Player dx expected {expected_dx}, got {pdx}"
            assert pdy == expected_dy, f"Key {key}: Player dy expected {expected_dy}, got {pdy}"
            assert sdx == expected_dx, f"Key {key}: SCB dx expected {expected_dx}, got {sdx}"
            assert sdy == expected_dy, f"Key {key}: SCB dy expected {expected_dy}, got {sdy}"

        print("PASS test_sprttest_player_moves_and_scb_syncs")
    finally:
        _cleanup(asm_path, tmp_src)


def test_sprttest_player_scb_matches_after_move():
    """After moving, Player struct and SCB must always match."""
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

        # Run for a bit to let loadPlayer execute
        for _ in range(10000):
            proc.step()

        # Move in several directions and verify Player/SCB sync after each
        for key in (119, 115, 97, 100, 119, 100):
            kbd.add_key(key)
            for _ in range(200000):
                proc.step()
            player_x = mem.read_word_fast(0x8012 + 0)
            player_y = mem.read_word_fast(0x8012 + 2)
            scb_x = mem.read_byte_fast(0xF000 + 2)
            scb_y = mem.read_byte_fast(0xF000 + 3)
            assert player_x == scb_x, f"After key {key}: Player x={player_x} != SCB x={scb_x}"
            assert player_y == scb_y, f"After key {key}: Player y={player_y} != SCB y={scb_y}"

        print("PASS test_sprttest_player_scb_matches_after_move")
    finally:
        _cleanup(asm_path, tmp_src)


if __name__ == "__main__":
    test_sprttest_player_moves_and_scb_syncs()
    test_sprttest_player_scb_matches_after_move()
    print("All sprttest movement tests passed!")
