"""Regression tests for compound assignment with function-call right sides.

The scalar compound path loaded the accumulator into a register and then
evaluated the RHS into the same register.  A user-function call result
therefore destroyed the left-hand value, turning ``x = x + f()`` into
``f() + f()``.
"""
import os
import sys
import tempfile

import pytest

# Path setup handled by tests/astrid/conftest.py
from nova_main import initialize_system


def compile_and_run(source, expected_r0=None, expected_p0=None,
                    max_cycles=2000000):
    """Compile, assemble, and run headlessly. Returns (proc, cycles, mem)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8') as f:
        f.write(source)
        source_path = f.name
    try:
        from astrid_compiler import main as compiler_main
        old_argv = sys.argv
        sys.argv = [old_argv[0], source_path, '-o',
                    source_path.replace('.ast', '.asm')]
        try:
            compiler_main()
        finally:
            sys.argv = old_argv

        asm_path = source_path.replace('.ast', '.asm')
        bin_path = source_path.replace('.ast', '.bin')
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)

        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(bin_path)
        cycle = 0
        while cycle < max_cycles and not proc.halted:
            proc.step()
            cycle += 1
        assert proc.halted, "Program did not halt"
        if expected_r0 is not None:
            assert proc.r0 == expected_r0, \
                f"Expected R0={expected_r0}, got {proc.r0}"
        if expected_p0 is not None:
            assert proc.p0 == expected_p0, \
                f"Expected P0={expected_p0}, got {proc.p0}"
        return proc, cycle, mem
    finally:
        os.unlink(source_path)
        for ext in ['.asm', '.bin', '.org', '.sym', '.nex']:
            path = source_path.replace('.ast', ext)
            if os.path.exists(path):
                os.unlink(path)


ADD_SOURCE = """
int s = 5;
int f() { return 7; }
int main() {
    s = s + f();
    return s;
}
"""


LOCAL_ADD_SOURCE = """
int f() { return 7; }
int main() {
    int s = 5;
    s = s + f();
    return s;
}
"""


ALL_OPERATORS_SOURCE = """
int add = 5;
int sub = 20;
int mul = 5;
int div = 21;
int mod = 20;
int band = 46;
int bor = 32;
int bxor = 47;
int f7() { return 7; }
int f3() { return 3; }
int main() {
    add = add + f7();
    sub = sub - f7();
    mul = mul * f3();
    div = div / f7();
    mod = mod % f7();
    band = band & f7();
    bor = bor | f7();
    bxor = bxor ^ f7();
    return add + sub + mul + div + mod + band + bor + bxor;
}
"""


@pytest.mark.cpu
def test_scalar_compound_add_preserves_target_across_call():
    """``s = s + f()`` must use the old value of ``s``, not the call result."""
    proc, cycles, mem = compile_and_run(ADD_SOURCE, expected_r0=12)
    print(f"PASS test_scalar_compound_add_preserves_target_across_call (cycles={cycles})")


@pytest.mark.cpu
def test_local_compound_add_preserves_target_across_call():
    """Locals use the same accumulator pattern and need the same protection."""
    proc, cycles, mem = compile_and_run(LOCAL_ADD_SOURCE, expected_r0=12)
    print(f"PASS test_local_compound_add_preserves_target_across_call (cycles={cycles})")


@pytest.mark.cpu
def test_all_scalar_compound_operators_preserve_target_across_call():
    """Every non-shift scalar compound operator must survive a call RHS."""
    expected = 12 + 13 + 15 + 3 + 6 + 6 + 39 + 40
    proc, cycles, mem = compile_and_run(ALL_OPERATORS_SOURCE, expected_r0=expected)
    print(f"PASS test_all_scalar_compound_operators_preserve_target_across_call (cycles={cycles})")
