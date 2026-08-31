"""Regression tests for the Astrid for-loop bare-step idiom and game level boundaries.

Two defects were fixed together:

1. **Bare for-loop steps silently did nothing.** ``for (int i = 0; i < 256; i + 8)``
   parsed the update clause as a plain expression (``BinaryOp``). ``generate_for``
   evaluated it into a scratch register and discarded the result -- no store back
   to ``i`` -- so the loop variable froze at its initial value and the loop ran
   forever. game.ast's level-boundary loops never advanced ``i``, so the game drew
   a single ``X ... X`` text fragment at (0, 0) instead of the level walls and
   never reached its input loop (the movement regression test failed at its very
   first key injection).

   ``generate_for`` now promotes a bare ``var op expr`` / ``expr op var`` update
   to an assignment back to the loop variable. Note the ExpressionSimplifier may
   canonicalize commutative ops constant-first (``i + 8`` -> ``8 + i``), so the
   loop variable can appear on EITHER side of the BinaryOp; generate_assignment
   mirrors such forms back to variable-first for the compound path.

2. **game.ast movement bounds didn't match the playfield.** The clamp logic used
   x in [16, 240] / y in [16, 232], but the intended sandbox is x in [8, 248] /
   y in [8, 240] (the player hugs the drawn boundary walls). The bounds were
   unreachable while the boundary loop was stuck, so the mismatch went unnoticed
   until the loop fix exposed it.

The boundary itself renders as: pass 1 draws a full X-glyph row across y=0,
``screen_rotate(0, 1)`` rolls that row onto the left edge, and pass 2 redraws the
top row -- giving top + left walls on layer 1.
"""
import os
import re
import shutil
import sys
import tempfile

import pytest

# Path setup handled by tests/astrid/conftest.py

from nova_main import initialize_system


def _compile_to_asm(source):
    """Compile Astrid source text; return (asm_path, tmp_source_path)."""
    fd = tempfile.NamedTemporaryFile(mode="w", suffix=".ast", delete=False,
                                     encoding="utf-8")
    fd.write(source)
    fd.close()
    from astrid_compiler import main as compiler_main
    old_argv = sys.argv
    sys.argv = [old_argv[0], fd.name, "-o", fd.name.replace(".ast", ".asm")]
    try:
        compiler_main()
    finally:
        sys.argv = old_argv
    return fd.name.replace(".ast", ".asm"), fd.name


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


def compile_and_run(source, expected_r0=None, max_cycles=2000000):
    """Compile, assemble, run to halt; return (proc, cycles)."""
    asm_path, tmp_src = _compile_to_asm(source)
    try:
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(asm_path.replace(".asm", ".bin"))
        cycles = 0
        while cycles < max_cycles and not proc.halted:
            cycles += 1
            proc.step()
        assert proc.halted, f"Program did not halt (cycles={cycles})"
        if expected_r0 is not None:
            assert proc.r0 == expected_r0, (
                f"Expected R0={expected_r0}, got {proc.r0}")
        return proc, cycles
    finally:
        _cleanup(asm_path, tmp_src)


def _update_section(asm_text, continue_label):
    """Lines between a for_continue label and the JMP back to the condition."""
    idx = asm_text.find(continue_label + ":")
    assert idx >= 0, f"{continue_label} not found in generated assembly"
    rest = asm_text[idx:]
    jmp = re.search(r"(?m)^\s*JMP\s+for_start", rest)
    assert jmp is not None, "no JMP back to loop start after continue label"
    return rest[:jmp.start()]


# ---------------------------------------------------------------------------
# Codegen: the bare step must emit a store-back
# ---------------------------------------------------------------------------

@pytest.mark.assembler
def test_bare_step_emits_store_back():
    """A bare `i + 8` update must emit a memory store after the ADD.

    Before the fix the update section ended at the ADD: the computed value
    lived only in a scratch register and the loop variable never advanced."""
    source = (
        "int main() {\n"
        "    int count = 0;\n"
        "    for (int i = 0; i < 32; i + 8) {\n"
        "        count += 1;\n"
        "    }\n"
        "    return count;\n"
        "}\n"
    )
    asm_path, tmp_src = _compile_to_asm(source)
    try:
        with open(asm_path, encoding="utf-8") as f:
            text = f.read()
        label = next(ln.strip().rstrip(":") for ln in text.splitlines()
                     if ln.startswith("for_continue_"))
        section = _update_section(text, label)
        assert re.search(r"\bADD\b", section), "step arithmetic missing"
        assert re.search(r"^\s*MOV\s+\[", section, re.MULTILINE), (
            "bare for-step must store the result back to the loop "
            f"variable; update section was:\n{section}")
        print(f"PASS test_bare_step_emits_store_back ({label})")
    finally:
        _cleanup(asm_path, tmp_src)


@pytest.mark.unit
def test_bare_step_wraps_const_first_form():
    """The ExpressionSimplifier canonicalizes `i + 8` to `8 + i`; the codegen
    must accept the loop variable on the RIGHT side too."""
    from astrid.lexer.lexer import Lexer
    from astrid.parser.parser import Parser, For, BinaryOp, Identifier
    ast = Parser(Lexer(
        "int main() { for (int i = 0; i < 32; i + 8) { } }"
    ).tokenize()).parse()
    loop = next(s for s in ast.functions[0].body if isinstance(s, For))
    update = loop.update
    assert isinstance(update, BinaryOp)
    assert isinstance(update.left, Identifier) or \
        isinstance(update.right, Identifier), (
        "loop variable missing from bare step expression")
    print("PASS test_bare_step_wraps_const_first_form")


# ---------------------------------------------------------------------------
# Runtime: bare-step loops must terminate and count correctly
# ---------------------------------------------------------------------------

LOOP_PLUS = (
    "int main() {\n"
    "    int count = 0;\n"
    "    for (int i = 0; i < 32; i + 8) {\n"
    "        count += 1;\n"
    "    }\n"
    "    return count;\n"
    "}\n"
)


@pytest.mark.integration
def test_bare_plus_step_loop_terminates():
    """for (int i = 0; i < 32; i + 8) must run exactly 4 iterations."""
    proc, cycles = compile_and_run(LOOP_PLUS, expected_r0=4)
    print(f"PASS test_bare_plus_step_loop_terminates (cycles={cycles})")


@pytest.mark.integration
def test_bare_minus_step_loop_terminates():
    """for (int i = 40; i > 0; i - 8) must run exactly 5 iterations."""
    source = (
        "int main() {\n"
        "    int count = 0;\n"
        "    for (int i = 40; i > 0; i - 8) {\n"
        "        count += 1;\n"
        "    }\n"
        "    return count;\n"
        "}\n"
    )
    proc, cycles = compile_and_run(source, expected_r0=5)
    print(f"PASS test_bare_minus_step_loop_terminates (cycles={cycles})")


@pytest.mark.integration
def test_const_first_spelling_matches_var_first():
    """`8 + i` written literally behaves like `i + 8` (both step by 8)."""
    const_first = LOOP_PLUS.replace("i + 8", "8 + i")
    _, cyc_a = compile_and_run(LOOP_PLUS, expected_r0=4)
    _, cyc_b = compile_and_run(const_first, expected_r0=4)
    print(f"PASS test_const_first_spelling_matches_var_first "
          f"(cycles={cyc_a}/{cyc_b})")


@pytest.mark.integration
def test_bare_step_final_value_reaches_condition():
    """After a bare-step loop the variable holds the first failing value."""
    source = (
        "int last;\n"
        "\n"
        "int main() {\n"
        "    for (last = 0; last < 30; last + 10) {\n"
        "    }\n"
        "    return last;\n"
        "}\n"
    )
    # 0, 10, 20 -> 30 fails the condition; last == 30
    proc, cycles = compile_and_run(source, expected_r0=30)
    print(f"PASS test_bare_step_final_value_reaches_condition (cycles={cycles})")


@pytest.mark.integration
def test_explicit_compound_step_still_works():
    """Explicit `i += 8` updates are unaffected by the bare-step promotion."""
    source = (
        "int main() {\n"
        "    int count = 0;\n"
        "    for (int i = 0; i < 40; i += 8) {\n"
        "        count += 1;\n"
        "    }\n"
        "    return count;\n"
        "}\n"
    )
    proc, cycles = compile_and_run(source, expected_r0=5)
    print(f"PASS test_explicit_compound_step_still_works (cycles={cycles})")


# ---------------------------------------------------------------------------
# Integration: game.ast draws the level boundaries
# ---------------------------------------------------------------------------

def _block_filled(layer, y0, y1, x0, x1):
    return int((layer[y0:y1, x0:x1] != 0).sum()) > 0


def test_game_draws_level_boundaries_headless():
    """game.ast must populate the whole top wall AND the left wall on layer 1.

    Regression: with the frozen loop variable only ONE 'X ... X' text
    fragment was drawn at (0, 0) -- a couple of glyphs near the corner --
    and screen_rotate plus the second pass never executed."""
    astrid_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'astrid', 'progs')
    src = os.path.join(astrid_dir, "game.ast")
    asm_path, tmp_src = _compile_ast_copy(src)
    try:
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(asm_path.replace(".asm", ".bin"))

        # Run until main hands control to the while(1) game loop: the
        # level-boundary for-loops must terminate for while_start to be
        # reached at all. Before the fix the frozen loop variable meant
        # this PC was never hit.
        loop_pc = None
        sym_path = asm_path.replace(".asm", ".sym")
        with open(sym_path, encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) == 2 and parts[0].startswith("while_start"):
                    loop_pc = int(parts[1], 16)
                    break
        assert loop_pc is not None, "while_start symbol not found"

        reached_loop = False
        cycles = 0
        max_cycles = 3000000
        while cycles < max_cycles and not proc.halted:
            cycles += 1
            proc.step()
            if proc.pc == loop_pc:
                reached_loop = True
                break

        assert not proc.halted, (
            f"game halted after {cycles} cycles (level-boundary loop "
            "must hand off to the while(1) game loop)")
        assert reached_loop, (
            f"while(1) game loop not reached within {cycles} cycles; "
            "the level-boundary loop is spinning again")

        layer1 = gfx.background_layers[0]

        # Top wall: every 8px column block across the top band has ink.
        top_blocks = [_block_filled(layer1, 0, 8, x, x + 8)
                      for x in range(0, 256, 8)]
        assert all(top_blocks), (
            f"top wall incomplete: {sum(top_blocks)}/32 blocks populated")

        # Left wall: screen_rotate rolled the first pass onto the left edge.
        left_blocks = [_block_filled(layer1, y, y + 8, 0, 8)
                       for y in range(0, 256, 8)]
        assert all(left_blocks), (
            f"left wall incomplete: {sum(left_blocks)}/32 blocks populated")

        total_ink = int((layer1 != 0).sum())
        assert total_ink > 1000, (
            f"layer 1 has only {total_ink} boundary pixels; the broken "
            "single-fragment draw produced far less")
        print(f"PASS test_game_draws_level_boundaries_headless "
              f"(cycles={cycles}, ink={total_ink}, "
              f"top={sum(top_blocks)}/32, left={sum(left_blocks)}/32)")
    finally:
        _cleanup(asm_path, tmp_src)


def test_game_movement_bounds_match_playfield():
    """chkKey clamps the player to x in [8, 248], y in [8, 240].

    Regression: the source clamped to [16, 240]/[16, 232], so mashing a
    direction key stopped 8 px short of the regression-tested playfield."""
    astrid_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'astrid', 'progs')
    src = os.path.join(astrid_dir, "game.ast")
    asm_path, tmp_src = _compile_ast_copy(src)
    try:
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(asm_path.replace(".asm", ".bin"))

        def read_x():
            return mem.read_word_fast(0x8000)

        def read_y():
            return mem.read_word_fast(0x8002)

        def run(n):
            c = 0
            while c < n and not proc.halted:
                c += 1
                proc.step()
            return c

        assert read_x() == 120 and read_y() == 120

        for _ in range(40):          # mash left ('a') until clamped
            kbd.add_key(97)
        run(200000)
        assert read_x() == 8, f"x must clamp at 8, got {read_x()}"

        for _ in range(40):          # mash down ('s')
            kbd.add_key(115)
        run(200000)
        assert read_y() == 240, f"y must clamp at 240, got {read_y()}"

        for _ in range(40):          # mash right ('d')
            kbd.add_key(100)
        run(200000)
        assert read_x() == 248, f"x must clamp at 248, got {read_x()}"

        for _ in range(40):          # mash up ('w')
            kbd.add_key(119)
        run(200000)
        assert read_y() == 8, f"y must clamp at 8, got {read_y()}"
        print("PASS test_game_movement_bounds_match_playfield")
    finally:
        _cleanup(asm_path, tmp_src)


if __name__ == "__main__":
    test_bare_step_emits_store_back()
    test_bare_step_wraps_const_first_form()
    test_bare_plus_step_loop_terminates()
    test_bare_minus_step_loop_terminates()
    test_const_first_spelling_matches_var_first()
    test_bare_step_final_value_reaches_condition()
    test_explicit_compound_step_still_works()
    test_game_draws_level_boundaries_headless()
    test_game_movement_bounds_match_playfield()
    print("All Astrid for-step/boundary tests passed!")


