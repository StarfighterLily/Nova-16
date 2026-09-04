"""End-to-end validation of the asteroid field in astrid/progs/sprttest.ast.

Drives the real compiled binary through the full Asteroids-style split chain:

    large (gen 0) -> 2x medium (gen 1)
    medium        -> 2x small  (gen 2) each
    small         -> 2x tiny   (gen 3) each
    tiny (gen 3)  -> destroyed, no further splits

Missiles are driven by writing the Missile struct directly -- the exact state
checkMissileHits() scans -- so the test is deterministic without a mouse.
The test parks the CPU straight into main()'s game loop (skipping the slow
starfield init) and seeds a single controlled gen-0 rock, then walks the
whole ladder. Rocks only move/get hit inside the game's update ticks
((counter % 2560) == 0); each round parks the counter just below 2560 and
waits for exactly one tick, which also keeps the periodic spawnWave()
(counter % 40820) from ever firing during the walk.

Each round fires a single missile at one rock's exact next position and
asserts precisely one rock died, splitting into two children at the impact
point unless it was already the final generation. Targets are chosen with
enough clearance from every other rock that no stray rock can absorb the hit;
if the field is too crowded (e.g. freshly split siblings are still co-located)
the test lets the field drift a tick and retries.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

from nova_main import initialize_system

# astrid_compiler lives under <root>/astrid; the astrid test package adds it
# via its own conftest, but integration tests must add it themselves.
_ASTRID_DIR = str(Path(__file__).resolve().parent.parent.parent / "astrid")
if _ASTRID_DIR not in sys.path:
    sys.path.insert(0, _ASTRID_DIR)

TICK = 2560             # game update cadence: (counter % 2560) == 0
N_SLOTS = 28            # rocks[] size in sprttest.ast
STRIDE_BYTES = 12       # struct Asteroid: 6 x 16-bit fields
RADII = {0: 9, 1: 6, 2: 4, 3: 2}
FIELDS = ("x", "y", "dx", "dy", "gen", "alive")


def _find_counter_addr(asm_path, sym):
    """Derive main()'s spilled `counter` address from the compiled assembly.

    The Astrid compiler spills main()'s `counter` local to a fixed slot in the
    spill region, but the exact address shifts as the source changes, so it
    must not be hardcoded. The loop reloads it every iteration with
    `MOV Pn, [addr]` a few instructions after the while_start label (past the
    `MOV P0,1 / CMP / JZ` preamble), so we locate that label in the listing
    and return the address of the first such load -- robust to recompilation.
    """
    label = next((n for n in sym if n.startswith("while_start_")), None)
    assert label is not None, "could not locate while_start label in .sym"

    import re
    load_re = re.compile(r"^\s*MOV\s+P\d+,\s*\[(0x[0-9A-Fa-f]+)\]\s*$")
    with open(asm_path) as f:
        lines = f.readlines()
    start = next((i for i, ln in enumerate(lines) if ln.strip() == label + ":"), None)
    assert start is not None, f"label {label}: not found in assembly"
    for line in lines[start + 1:]:
        m = load_re.match(line.rstrip())
        if m:
            return int(m.group(1), 16)
    assert False, "could not find counter spill load in main loop"


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


def _load_symbols(asm_path):
    sym = {}
    with open(asm_path.replace(".asm", ".sym")) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split()
                if len(parts) == 2 and parts[1].startswith("0x"):
                    sym[parts[0]] = int(parts[1], 16)
    return sym


def _signed(value):
    return value - 0x10000 if value & 0x8000 else value


def _read_rocks(mem, rocks_base):
    rocks = []
    for slot in range(N_SLOTS):
        base = rocks_base + slot * STRIDE_BYTES
        values = [_signed(mem.read_word_fast(base + k * 2)) for k in range(6)]
        rock = dict(zip(FIELDS, values))
        rock["slot"] = slot
        rocks.append(rock)
    return rocks


def _alive(rocks):
    return [r for r in rocks if r["alive"]]


def _gen_counts(rocks):
    counts = {}
    for rock in _alive(rocks):
        counts[rock["gen"]] = counts.get(rock["gen"], 0) + 1
    return counts


def _wait_next_update_tick(proc, mem, counter_addr, timeout_steps=1200000):
    """Wait for the next game update tick to *complete*.

    The update tick (updateMissile/updateAsteroids/checkShipCollision/
    checkMissileHits) fires when the game counter becomes a multiple of 2560.
    The counter is sampled every 256 instructions; once a multiple is observed
    the tick has fired, and stepping until the counter leaves that multiple
    guarantees its side effects are visible. The counter wraps to 0 at 40820
    (main() spawns a fresh wave there), so we never rely on absolute counter
    ordering -- we only react to observed multiples, which are always valid
    regardless of the wrap.
    """
    steps = 0
    while steps < timeout_steps:
        for _ in range(256):
            proc.step()
        steps += 256
        cur = mem.read_word_fast(counter_addr)
        if cur and cur % TICK == 0:
            # tick fired (or is mid-flight); finish it off
            for _ in range(8192):
                proc.step()
                if mem.read_word_fast(counter_addr) % TICK != 0:
                    return True
    return False


def _drift_one_tick(proc, mem, counter_addr):
    """Let the field advance exactly one update tick with no missile armed.

    Parks the counter just below 2560 so the very next iteration fires an
    update tick; the counter therefore never approaches the %40820 wave
    reset, keeping every tick deterministic for the test."""
    mem.write_word_fast(counter_addr, TICK - 1)
    return _wait_next_update_tick(proc, mem, counter_addr)


def _fire_missile_1(proc, mem, counter_addr, missile_base, x, y):
    """Arm missile 1 so it sits exactly at (x, y) when checkMissileHits runs,
    then force the next update tick to fire promptly.

    updateMissile() subtracts 6 from my1 before the hit check in the same
    tick, hence the +6 compensation on y. Parking the counter just below 2560
    makes each kill cost exactly one tick and avoids the periodic spawnWave()
    at counter % 40820, so the field state stays fully deterministic."""
    mem.write_word_fast(missile_base + 0, 1)        # pmissile1 = 1
    mem.write_word_fast(missile_base + 2, x)        # mx1
    mem.write_word_fast(missile_base + 4, y + 6)    # my1
    mem.write_word_fast(missile_base + 6, 0)        # pmissile2 = 0
    mem.write_word_fast(missile_base + 12, 0)       # pmissile3 = 0
    mem.write_word_fast(counter_addr, TICK - 1)     # next iteration -> tick


def _kill_one(proc, mem, counter_addr, missile_base, rocks_base, target_gen=None):
    """Destroy exactly one rock with missile 1 and verify the split rules.

    If target_gen is given, only rocks of that generation are eligible to be
    the missile's target (so a split ladder for generation N cannot
    accidentally destroy a freshly-spawned N+1 child). Clearance is still
    computed against EVERY alive rock, so the missile can never strafe into a
    non-eligible rock either.

    Returns the generation of the destroyed rock, or None if no rock of the
    target generation (or any generation, if target_gen is None) remains.
    """
    for _attempt in range(15):
        rocks = _read_rocks(mem, rocks_base)
        alive = _alive(rocks)
        candidates = [r for r in alive
                      if target_gen is None or r["gen"] == target_gen]
        if not candidates:
            return None

        # Next positions (the game moves every rock inside the coming tick).
        nxt = {id(r): ((r["x"] + r["dx"]) % 256, (r["y"] + r["dy"]) % 256)
               for r in alive}

        # Pick the candidate rock with the best clearance from every other
        # rock's next position; the missile must not be able to hit anything
        # else. All alive rocks count toward the clearance check so a
        # non-candidate can't absorb the hit.
        best = None
        best_clear = -1
        best_need = 0
        for rock in candidates:
            nx, ny = nxt[id(rock)]
            clear = 1 << 30
            need = 0
            for other in alive:
                if other is rock:
                    continue
                ox, oy = nxt[id(other)]
                dx = min((nx - ox) % 256, (ox - nx) % 256)
                dy = min((ny - oy) % 256, (oy - ny) % 256)
                clear = min(clear, max(dx, dy))
                need = max(need, RADII[rock["gen"]] + RADII[other["gen"]] + 2)
            if clear > best_clear:
                best, best_clear, best_need = (rock, nx, ny), clear, need

        if best_clear <= best_need:
            # Field too crowded (e.g. fresh siblings still together): drift a
            # tick so positions spread out, then re-evaluate.
            assert _drift_one_tick(proc, mem, counter_addr), "tick never completed"
            continue

        rock, nx, ny = best
        gen = rock["gen"]
        before = len(alive)
        before_counts = _gen_counts(rocks)

        _fire_missile_1(proc, mem, counter_addr, missile_base, nx, ny)
        assert _wait_next_update_tick(proc, mem, counter_addr), "tick never completed"

        after_alive = _alive(_read_rocks(mem, rocks_base))
        expected = before + (1 if gen < 3 else -1)
        assert len(after_alive) == expected, (
            f"gen {gen} kill: expected {expected} alive rocks, "
            f"got {len(after_alive)}")

        counts = _gen_counts(_read_rocks(mem, rocks_base))
        assert counts.get(gen, 0) == before_counts.get(gen, 0) - 1, (
            f"exactly one gen {gen} rock must die: {before_counts} -> {counts}")

        if gen < 3:
            # Exactly two children of the next generation spawn at the
            # impact point, with diverging velocities.
            children = [r for r in after_alive
                        if r["gen"] == gen + 1 and r["x"] == nx and r["y"] == ny]
            assert len(children) == 2, (
                f"gen {gen} rock must split into two children at the "
                f"impact point, found {len(children)}")
            children.sort(key=lambda r: r["dx"], reverse=True)
            assert children[0]["dx"] > children[1]["dx"], \
                "children must diverge horizontally"
            assert children[0]["dy"] < children[1]["dy"], \
                "children must diverge vertically"

        return gen
    pytest.fail("could not find a separable target within the retry budget")


@pytest.mark.integration
def test_asteroid_field_split_chain_and_rendering():
    astrid_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'astrid', 'progs'
    )
    src = os.path.join(astrid_dir, "sprttest.ast")
    asm_path, tmp_src = _compile_ast_copy(src)
    try:
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)

        sym = _load_symbols(asm_path)
        missile_base = sym["gvar_Missile"]
        rocks_base = sym["gvar_rocks"]
        # Derive the compiler-assigned counter spill slot from the assembly so
        # the test never breaks when the allocator picks a different address.
        counter_addr = _find_counter_addr(asm_path, sym)

        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(asm_path.replace(".asm", ".bin"))

        # --- Deterministic field: park the program directly in main()'s game loop.
        # The loop reads/writes only statics and globals, so it runs fine
        # without main()'s prologue -- and this skips the (very slow)
        # starfield init. We zero the loop counter so the first update and
        # draw ticks fire promptly.
        loop_labels = [name for name in sym if name.startswith("while_start_")]
        assert loop_labels, "could not locate main()'s while-loop label in .sym"
        proc.pc = sym[loop_labels[0]]
        mem.write_word_fast(counter_addr, 0)

        # Replace the (never-seeded, since we skipped the prologue) field
        # with a single controllable gen-0 rock so the full 1->2->4->8 split
        # ladder can be observed without interference from spawnWave().
        for slot in range(N_SLOTS):
            base = rocks_base + slot * STRIDE_BYTES
            mem.write_word_fast(base + 10, 0)                # alive = 0
        mem.write_word_fast(rocks_base + 0, 128)             # x
        mem.write_word_fast(rocks_base + 2, 128)             # y
        mem.write_word_fast(rocks_base + 4, 2)               # dx
        mem.write_word_fast(rocks_base + 6, 1)               # dy
        mem.write_word_fast(rocks_base + 8, 0)               # gen = 0
        mem.write_word_fast(rocks_base + 10, 1)              # alive = 1
        assert _gen_counts(_read_rocks(mem, rocks_base)) == {0: 1}, \
            "test seed must be exactly one gen 0 rock"

        # --- Rendering: tick 2560 moves rocks, tick 5120 moves + draws them
        # on layer 4 (the asteroid-dedicated layer) with filled circles.
        assert _wait_next_update_tick(proc, mem, counter_addr), "first update tick never completed"
        assert _wait_next_update_tick(proc, mem, counter_addr), "second update tick never completed"
        layer4_pixels = int((gfx.background_layers[3] != 0).sum())
        assert layer4_pixels > 100, (
            f"asteroids must be drawn on layer 4, found {layer4_pixels} pixels")

        # --- Full split ladder: kill each generation out of existence
        def kill_all_of_gen(gen, cap=40):
            killed = 0
            while _gen_counts(_read_rocks(mem, rocks_base)).get(gen, 0) > 0:
                # Constrain the shot to this generation so a freshly spawned
                # child of the next generation can't absorb it.
                assert _kill_one(proc, mem, counter_addr, missile_base, rocks_base,
                                target_gen=gen) == gen
                killed += 1
                assert killed <= cap, "split ladder did not terminate"
            return killed

        k0 = kill_all_of_gen(0)
        counts = _gen_counts(_read_rocks(mem, rocks_base))
        assert counts == {1: 2 * k0}, \
            f"gen 0 splits must yield 2 gen 1 each: {counts}"

        k1 = kill_all_of_gen(1)
        counts = _gen_counts(_read_rocks(mem, rocks_base))
        assert counts == {2: 2 * k1}, \
            f"gen 1 splits must yield 2 gen 2 each: {counts}"

        k2 = kill_all_of_gen(2)
        counts = _gen_counts(_read_rocks(mem, rocks_base))
        assert counts == {3: 2 * k2}, \
            f"gen 2 splits must yield 2 gen 3 each: {counts}"

        k3 = kill_all_of_gen(3)
        assert k3 == 2 * k2, "every gen 2 split must produce a destructible gen 3"
        assert _alive(_read_rocks(mem, rocks_base)) == [], \
            "field must be empty after the final generation is destroyed"

        print(f"PASS asteroid split chain: {k0} large -> {2*k0} medium -> "
              f"{4*k0} small -> {8*k0} tiny -> destroyed")
    finally:
        _cleanup(asm_path, tmp_src)


# ---------------------------------------------------------------------------
# Player-rock collision & damage
# ---------------------------------------------------------------------------
# checkShipCollision() reads the ship position from SCB 0 (0xF000+2/+3 --
# loadPlayer() parks it at (128, 128)), and for every alive rock whose
# bounding box (radius + 4) covers that point applies Player.hit -= 8>>gen.
# Player.hit is a *signed* field: a gen-0 hit (dmg 8) against hit=4 leaves
# hit=-4, and main()'s `while (Player.hit > 0)` must exit via the compiler's
# signed comparison (JGT on overflow XOR sign). These tests drive the real
# binary through one update tick with a rock parked on the ship and assert
# both the damage bookkeeping and the loop-exit behavior.

PLAYER_HIT_OFFSET = 4    # struct Player { x, y, hit } -> hit is word 2


def _setup_player_collision_env(asm_path, sym, mem, proc, counter_addr,
                                rocks_base, player_base, hit_value):
    """Park the CPU in main()'s game loop and seed one gen-0 rock exactly on
    the ship. Returns the address of Player.hit.

    The ship's SCB position is refreshed from mouse_pos() by movePlayer()
    inside every update tick (before checkShipCollision reads it back), and
    parking at while_start skips loadPlayer() -- so the mouse device is
    parked at (128, 128) to hold the ship on the rock."""
    loop_labels = [name for name in sym if name.startswith("while_start_")]
    assert loop_labels, "could not locate main()'s while-loop label in .sym"
    proc.pc = sym[loop_labels[0]]
    mem.write_word_fast(counter_addr, TICK - 1)   # next iteration -> update tick
    proc.mouse.move_to(128, 128)                  # ship follows mouse_pos()

    player_hit_addr = player_base + PLAYER_HIT_OFFSET
    mem.write_word_fast(player_hit_addr, hit_value & 0xFFFF)

    # Clear the field and park one gen-0 rock (radius 9 -> hit box 13)
    # dead-center on the ship at (128, 128) so checkShipCollision must fire.
    for slot in range(N_SLOTS):
        mem.write_word_fast(rocks_base + slot * STRIDE_BYTES + 10, 0)  # alive
    mem.write_word_fast(rocks_base + 0, 128)             # x
    mem.write_word_fast(rocks_base + 2, 128)             # y
    mem.write_word_fast(rocks_base + 4, 0)               # dx (stay put)
    mem.write_word_fast(rocks_base + 6, 0)               # dy (stay put)
    mem.write_word_fast(rocks_base + 8, 0)               # gen = 0
    mem.write_word_fast(rocks_base + 10, 1)              # alive = 1
    return player_hit_addr


@pytest.mark.integration
def test_player_takes_hit_and_loses_health():
    """A rock on the ship must register: Player.hit -= 8 (gen-0 dmg) and the
    rock is destroyed, while the game loop keeps running (hit still > 0)."""
    astrid_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'astrid', 'progs'
    )
    src = os.path.join(astrid_dir, "sprttest.ast")
    asm_path, tmp_src = _compile_ast_copy(src)
    try:
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)

        sym = _load_symbols(asm_path)
        rocks_base = sym["gvar_rocks"]
        player_base = sym["gvar_Player"]
        counter_addr = _find_counter_addr(asm_path, sym)

        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(asm_path.replace(".asm", ".bin"))

        player_hit_addr = _setup_player_collision_env(
            asm_path, sym, mem, proc, counter_addr, rocks_base, player_base,
            hit_value=10)

        # One update tick: checkShipCollision applies 10 - (8 >> 0) = 2.
        assert _wait_next_update_tick(proc, mem, counter_addr), \
            "collision tick never completed"

        hit = _signed(mem.read_word_fast(player_hit_addr))
        assert hit == 2, f"Player.hit must drop 10 -> 2 after a gen-0 hit, got {hit}"
        assert _read_rocks(mem, rocks_base)[0]["alive"] == 0, \
            "colliding rock must be destroyed"

        # hit == 2 > 0: the loop must still be running (PC not past the loop).
        while_end = next((n for n in sym if n.startswith("while_end_")), None)
        assert while_end is not None, "while_end label missing from .sym"
        for _ in range(2000):
            proc.step()
            assert proc.pc != sym[while_end], \
                "game loop must keep running while Player.hit > 0"

        print("PASS player hit registers: Player.hit 10 -> 2, rock destroyed")
    finally:
        _cleanup(asm_path, tmp_src)


@pytest.mark.integration
def test_player_death_exits_loop_on_negative_hit():
    """With hit=4 a gen-0 hit (dmg 8) drives Player.hit to -4. The game loop
    condition `Player.hit > 0` must use the compiler's SIGNED comparison so
    the negative value terminates the loop -- an unsigned compare would read
    0xFFFC > 0 and spin forever."""
    astrid_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'astrid', 'progs'
    )
    src = os.path.join(astrid_dir, "sprttest.ast")
    asm_path, tmp_src = _compile_ast_copy(src)
    try:
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)

        sym = _load_symbols(asm_path)
        rocks_base = sym["gvar_rocks"]
        player_base = sym["gvar_Player"]
        counter_addr = _find_counter_addr(asm_path, sym)
        while_end = next((n for n in sym if n.startswith("while_end_")), None)
        assert while_end is not None, "while_end label missing from .sym"
        while_end_addr = sym[while_end]

        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(asm_path.replace(".asm", ".bin"))

        player_hit_addr = _setup_player_collision_env(
            asm_path, sym, mem, proc, counter_addr, rocks_base, player_base,
            hit_value=4)

        # Step until the loop condition fails and PC lands on while_end.
        # The update tick fires on the very first iteration (counter was
        # parked at TICK-1), applying 4 - 8 = -4, then the signed `> 0`
        # check exits the loop a few instructions later.
        steps = 0
        while proc.pc != while_end_addr and steps < 200000:
            proc.step()
            steps += 1
        assert proc.pc == while_end_addr, (
            f"game loop must exit when Player.hit goes negative "
            f"(stepped {steps} instrs, PC=0x{proc.pc:04X}, "
            f"hit={_signed(mem.read_word_fast(player_hit_addr))})")

        hit = _signed(mem.read_word_fast(player_hit_addr))
        assert hit == -4, f"Player.hit must be -4 after the lethal hit, got {hit}"

        print("PASS player death: Player.hit 4 -> -4, game loop exited via "
              "signed comparison")
    finally:
        _cleanup(asm_path, tmp_src)


if __name__ == "__main__":
    test_asteroid_field_split_chain_and_rendering()
    test_player_takes_hit_and_loses_health()
    test_player_death_exits_loop_on_negative_hit()
    print("All asteroid field tests passed!")

