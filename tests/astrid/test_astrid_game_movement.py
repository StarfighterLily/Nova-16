"""Regression tests for the Astrid game.ast fixes.

Three defects were fixed together:

1. **User-function calls leaked stack bytes.** `generate_call` pushed args,
   CALLed, then claimed "; Args consumed by callee" -- but only builtin
   stubs pop their own arguments. User functions end with
   `MOV SP, FP / POP FP / RET`, which restores SP to the frame base and
   leaves the caller's args on the stack. `main` calling `drawPlayer(x, y)`
   inside an infinite `while(1)` leaked 4 bytes per iteration; after enough
   keystrokes SP walked down through low memory, wrapped, and executed
   garbage (the reported 'Unknown register code: 0x12' crash). The codegen
   now emits `ADD SP, n*2 ; Caller cleans up args` after user-function calls.

2. `game.ast`'s main loop never called `chkKey()`, so the player could not
   move. Fixed the source; the regenerated game.asm has `CALL func_chkKey`
   at the top of the loop.

3. Parameters that shadow globals of the same name resolved to the GLOBAL
   instead of the FP-relative parameter slot (`_emit_var_load` checked
   `global_vars` before `local_vars`; `generate_address_of` too). In
   game.ast this made `drawPlayer(int x, int y)` read the global x/y
   instead of the passed-in coordinates. Fixed order to locals first
   (consistent with `_emit_var_store`).
"""
import os
import re
import shutil
import sys
import tempfile

# Path setup handled by tests/astrid/conftest.py

from nova_main import initialize_system
from astrid.codegen.codegen import CodeGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compile_to_asm(source):
    """Compile source text; return (asm_path, tmp_source_path).

    The caller must _cleanup() the returned path."""
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
    asm_path = fd.name.replace(".ast", ".asm")
    return asm_path, fd.name


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


def compile_and_run(source, expected_r0=None, expected_p0=None):
    asm_path, tmp_src = _compile_to_asm(source)
    try:
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)
        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(asm_path.replace(".asm", ".bin"))
        cycle = 0
        while cycle < 2000000 and not proc.halted:
            cycle += 1
            proc.step()
        assert proc.halted, f"Program did not halt (cycles={cycle})"
        if expected_r0 is not None:
            assert proc.r0 == expected_r0, f"Expected R0={expected_r0}, got {proc.r0}"
        if expected_p0 is not None:
            assert proc.p0 == expected_p0, f"Expected P0={expected_p0}, got {proc.p0}"
        return proc, cycle
    finally:
        _cleanup(asm_path, tmp_src)
# ---------------------------------------------------------------------------
# Codegen: caller-side argument cleanup
# ---------------------------------------------------------------------------

def test_user_function_call_emits_arg_cleanup():
    """Calls to USER functions must deallocate args after the return.

    Builtin stubs pop their own args (': Args consumed by callee'), but
    user functions restore SP to FP, leaving pushed args on the stack."""
    source = """
int add(int a, int b) {
    return a + b;
}
void main() {
    int r = add(3, 4);
}
"""
    asm_path, tmp_src = _compile_to_asm(source)
    try:
        with open(asm_path, encoding="utf-8") as f:
            text = f.read()
        assert "CALL func_add" in text
        assert re.search(r"ADD SP, 4\s*; Caller cleans up args", text), (
            "user-function call must clean up its 2 args (ADD SP, 4)"
        )
        print("PASS test_user_function_call_emits_arg_cleanup")
    finally:
        _cleanup(asm_path, tmp_src)


def test_builtin_calls_keep_callee_cleanup_comment():
    """Builtin calls must keep the existing 'Args consumed by callee' comment."""
    source = """
void main() {
    set_layer(0);
}
"""
    asm_path, tmp_src = _compile_to_asm(source)
    try:
        with open(asm_path, encoding="utf-8") as f:
            text = f.read()
        assert "CALL builtin_set_layer" in text
        assert "; Args consumed by callee" in text
        assert "; Caller cleans up args" not in text
        print("PASS test_builtin_calls_keep_callee_cleanup_comment")
    finally:
        _cleanup(asm_path, tmp_src)


# ---------------------------------------------------------------------------
# Bug 3: parameters shadowing globals
# ---------------------------------------------------------------------------

def test_param_shadows_global_read():
    """A param named like a global must read the PARAM, not the global.

    Before the fix `_emit_var_load` checked global_vars first, so `f(5)`
    read the global 100 instead of the param 5."""
    source = """
int gx = 100;

int f(int gx) {
    return gx + 1;
}

int main() {
    return f(5);
}
"""
    # f(5) -> param 5 + 1 = 6 (NOT 100 + 1 = 101)
    proc, cycles = compile_and_run(source, expected_r0=6)
    print(f"PASS test_param_shadows_global_read (cycles={cycles}, R0={proc.r0})")


def test_local_shadows_global_read():
    """A local named like a global reads the local (C scoping)."""
    source = """
int val = 100;

int main() {
    int val = 7;
    return val + 1;
}
"""
    proc, cycles = compile_and_run(source, expected_r0=8)
    print(f"PASS test_local_shadows_global_read (cycles={cycles}, R0={proc.r0})")


def test_address_of_param_shadows_global():
    """&param must resolve to the frame slot, not the global.

    Before the fix generate_address_of looked up globals first, so
    `&x` in a function whose param is named `x` returned the global
    address and dereferencing overwrote the global."""
    source = """
int x = 100;

void set(int x) {
    int *p = &x;
    *p = 5;
}

int main() {
    int tmp = 0;
    set(tmp);
    return x;   // global must be unchanged (100); param slot got 5
}
"""
    proc, cycles = compile_and_run(source, expected_r0=100)
    print(f"PASS test_address_of_param_shadows_global (cycles={cycles}, R0={proc.r0})")


def test_global_still_accessible_when_unshadowed():
    """Reaching a genuine global (no same-named local/param) still works."""
    source = """
int g = 21;

int main() {
    return g * 2;
}
"""
    proc, cycles = compile_and_run(source, expected_r0=42)
    print(f"PASS test_global_still_accessible_when_unshadowed (cycles={cycles}, R0={proc.r0})")
# ---------------------------------------------------------------------------
# Bug 2: game.ast wires chkKey into the main loop
# ---------------------------------------------------------------------------

def test_game_asm_wires_input_and_cleanup():
    """The regenerated game.asm must call chkKey(), use FP-relative params
    in drawPlayer, and clean up drawPlayer's args."""
    astrid_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'astrid', 'progs')
    asm_path = os.path.join(astrid_dir, "game.asm")
    with open(asm_path, encoding="utf-8") as f:
        text = f.read()
    assert "CALL func_chkKey" in text, "main must poll chkKey()"
    assert re.search(r"CALL func_drawPlayer\s*\n\s*ADD SP, 4 ; Caller cleans up args", text), (
        "drawPlayer call must clean up its 2 args"
    )
    # drawPlayer's body must reference its params, not the globals
    body = text.split("func_drawPlayer:")[1].split("; Function: main")[0]
    assert "[FP+4]" in body and "[FP+6]" in body, (
        "drawPlayer must read its x/y parameters from the frame"
    )
    assert "[0x8000]" not in body and "[0x8002]" not in body, (
        "drawPlayer must not read the shadowed globals"
    )
    print("PASS test_game_asm_wires_input_and_cleanup")


# ---------------------------------------------------------------------------
# Bug 1: full runtime stack-balance / movement regression
# ---------------------------------------------------------------------------

def test_game_movement_and_stack_stability_headless():
    """game.ast runs headlessly: keys move the character, bounds clamp,
    and the stack never drifts -- the original crash is gone."""
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

        # --- single-direction movement ---
        assert read_x() == 120 and read_y() == 120, (read_x(), read_y())
        for key, dx, dy in [(97, -8, 0), (100, 8, 0), (119, 0, -8), (115, 0, 8),
                            (128, -8, 0), (129, 8, 0), (130, 0, -8), (131, 0, 8)]:
            x0, y0 = read_x(), read_y()
            kbd.add_key(key)
            run(20000)
            assert read_x() == x0 + dx, f"key {key}: x moved wrong"
            assert read_y() == y0 + dy, f"key {key}: y moved wrong"

        # --- sand-box clamping: mash arrows; the character must stay in range ---
        for _ in range(40):
            kbd.add_key(97)      # left ('a')
        run(200000)
        assert read_x() == 8, f"x must clamp at 8, got {read_x()}"
        for _ in range(40):
            kbd.add_key(100)     # right ('d')
        # 8 -> 248 is 30 moves; one game-loop iteration costs ~2k cycles,
        # so give the mash enough budget to actually reach the clamp.
        run(150000)
        assert read_x() == 248, f"x must clamp at 248, got {read_x()}"
        for _ in range(40):
            kbd.add_key(115)     # down ('s')
        run(150000)
        assert read_y() == 240, f"y must clamp at 240, got {read_y()}"
        for _ in range(40):
            kbd.add_key(119)     # up ('w')
        run(150000)
        assert read_y() == 8, f"y must clamp at 8, got {read_y()}"

        # --- long run: stack must never drift; program must not halt/crash ---
        loop_pc = None
        sym_path = asm_path.replace(".asm", ".sym")
        with open(sym_path, encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) == 2 and parts[0].startswith("while_start"):
                    loop_pc = int(parts[1], 16)
        assert loop_pc is not None
        sp_samples = []
        for key in (97, 100, 115, 119, 128, 129, 130, 131):
            kbd.add_key(key)
        c = 0
        while c < 600000 and not proc.halted:
            c += 1
            proc.step()
            if proc.pc == loop_pc:
                sp_samples.append(proc.sp)
        assert not proc.halted, f"game halted after {c} cycles (stack corruption)"
        assert sp_samples, "expected to sample SP at the while loop top"
        assert len(set(sp_samples)) == 1, (
            f"SP drifted across iterations: {sorted(set(sp_samples))}"
        )
        # non-zero pixels rendered
        screen = gfx.screen
        assert int((screen != 0).sum()) > 0, "screen must show the player"
        print(f"PASS test_game_movement_headless (cycles={c}, SP_fixed=0x{sp_samples[0]:04X})")
    finally:
        _cleanup(asm_path, tmp_src)


# ---------------------------------------------------------------------------
# All tables remain consistent
# ---------------------------------------------------------------------------

def test_builtin_tables_still_consistent():
    """The arity/variant tables still cover every implemented label."""
    gen = CodeGenerator()
    impls = CodeGenerator.BUILTIN_IMPLEMENTATIONS
    for name, label in gen.builtin_functions.items():
        assert label in impls, f"{name} -> {label} missing impl"
    for arity_table in CodeGenerator.ARITY_BUILTINS.values():
        for label in arity_table.values():
            assert label in impls, f"arity stub {label} missing impl"
    print("PASS test_builtin_tables_still_consistent")


if __name__ == "__main__":
    test_user_function_call_emits_arg_cleanup()
    test_builtin_calls_keep_callee_cleanup_comment()
    test_param_shadows_global_read()
    test_local_shadows_global_read()
    test_address_of_param_shadows_global()
    test_global_still_accessible_when_unshadowed()
    test_game_asm_wires_input_and_cleanup()
    test_game_movement_and_stack_stability_headless()
    test_builtin_tables_still_consistent()
    print("All Astrid game/regression tests passed!")
