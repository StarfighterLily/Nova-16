"""Regression tests for two Astrid codegen defects found through the 3D demos.

1. **The for-loop wrap check stopped loops early.** ``generate_for`` guards a
   counting loop against 16-bit wrap-around by saving the variable before the
   update and exiting when ``new < old`` (unsigned, JC). That test was applied
   to every loop regardless of direction or signedness:

   * a signed counter crossing zero (``for (signed int k = -2; k <= 2; k++)``)
     went 0xFFFF -> 0x0000, which compares as a wrap, so the loop stopped at
     -1 -- cube3d's ground grid drew 4 of its 10 lines and room3d's floor and
     ceiling beams 2 of 6;
   * every decrementing loop (``i--``, ``i -= n``) has ``new < old`` on its
     first step, so it ran exactly once;
   * the guard it was written for, ``p += 32`` near 0xFFFF, was never emitted
     at all: the ExpressionSimplifier canonicalizes the update to
     ``p = 32 + p`` and the detector only looked for the variable on the left.

   The check now follows the update's direction (+/-, with a negative constant
   step reversing it) and the condition's signedness (signed loops wrap only on
   32767 <-> -32768 overflow, via JLT/JGT).

2. **&& and || did not short-circuit.** The generic binary-operator path
   evaluated both operands eagerly before dispatching on the operator, and the
   &&/|| branches then evaluated the right operand a second time inside their
   short-circuit sequence. Every right operand therefore ran unconditionally
   (``p != 0 && p->x`` dereferenced anyway, side effects ran twice) and an
   n-term chain grew exponentially in code size.
"""
import os
import re
import tempfile

import pytest

# Path setup is handled by tests/astrid/conftest.py
from nova_main import initialize_system


def _build_and_run(source, max_cycles=200000):
    """Compile+assemble Astrid source text, run it, return (proc, mem, asm, syms)."""
    from astrid.compiler_api import compile_astrid
    from nova_assembler import Assembler
    tmpdir = tempfile.mkdtemp(prefix='astrid_loop_sc_')
    src = os.path.join(tmpdir, 'prog.ast')
    asm = os.path.join(tmpdir, 'prog.asm')
    with open(src, 'w', encoding='utf-8') as f:
        f.write(source)
    compile_astrid(src, asm, log=lambda m: None,
                   assemble_callback=lambda p, v, e: bool(Assembler().assemble(str(p))))
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    proc.pc = mem.load(asm[:-4] + '.bin')
    cycles = 0
    while not proc.halted and cycles < max_cycles:
        proc.step()
        cycles += 1
    syms = {}
    with open(asm[:-4] + '.sym') as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2 and not line.startswith('#'):
                try:
                    syms[parts[0].lower()] = int(parts[1], 0)
                except ValueError:
                    pass
    with open(asm, encoding='utf-8') as f:
        asm_text = f.read()
    return proc, mem, asm_text, syms


def _words(mem, addr, n):
    vals = [mem.read_word(addr + 2 * i) for i in range(n)]
    return [v - 0x10000 if v & 0x8000 else v for v in vals]


LOOP_SOURCE = """
signed int r[8] = { 0, 0, 0, 0, 0, 0, 0, 0 };

void main() {
    for (signed int k = -2; k <= 2; k++) { r[0] = r[0] + 1; }
    for (int i = 10; i > 0; i--) { r[1] = r[1] + 1; }
    for (int i = 0; i < 10; i += 3) { r[2] = r[2] + 1; }
    for (unsigned int p = 0xFFF0; p < 0xFFFF; p += 32) { r[3] = r[3] + 1; }
    for (signed int j = 5; j >= -5; j -= 2) { r[4] = r[4] + 1; }
    for (signed int m = -3; m < 3; m += 2) { r[5] = r[5] + 1; }
    for (unsigned int d = 5; d > 0; d--) { r[6] = r[6] + 1; }
    for (signed int n = 32760; n < 32767; n += 4) { r[7] = r[7] + 1; }
    halt();
}
"""


def test_for_loop_trip_counts():
    proc, mem, asm, syms = _build_and_run(LOOP_SOURCE)
    assert proc.halted, 'a loop failed to terminate (wrap guard missing)'
    got = _words(mem, syms['gvar_r'], 8)
    assert got == [
        5,    # signed counter crossing zero runs all five values
        10,   # decrementing loop is not mistaken for a wrap
        4,    # ordinary stepped increment
        1,    # unsigned p += 32 from 0xFFF0 wraps -> guard exits after one pass
        6,    # signed decrement by 2 across zero
        3,    # signed increment by 2 across zero
        5,    # unsigned decrement to zero
        2,    # signed overflow past 32767 -> guard exits
    ], got


def test_signed_wrap_check_uses_signed_jump():
    """A signed counting loop's guard must not use the unsigned JC test."""
    _, _, asm, _ = _build_and_run(LOOP_SOURCE)
    first_loop = asm.split('for_end_1:')[0].split('for_continue_2:')[1]
    assert 'JLT for_end_1' in first_loop
    assert 'JC for_end_1' not in first_loop


SHORT_CIRCUIT_SOURCE = """
signed int r[8] = { 0, 0, 0, 0, 0, 0, 0, 0 };
signed int hits[4] = { 0, 0, 0, 0 };

signed int t(signed int k, signed int v) {
    hits[k] = hits[k] + 1;
    return v;
}

void clear() {
    hits[0] = 0;
    hits[1] = 0;
    hits[2] = 0;
    hits[3] = 0;
}

void main() {
    if (t(0, 1) || t(1, 0) || t(2, 0) || t(3, 0)) { r[0] = 1; }
    r[1] = hits[0] * 1000 + hits[1] * 100 + hits[2] * 10 + hits[3];
    clear();
    if (t(0, 0) || t(1, 0) || t(2, 0) || t(3, 0)) { r[2] = 1; }
    r[3] = hits[0] * 1000 + hits[1] * 100 + hits[2] * 10 + hits[3];
    clear();
    if (t(0, 0) && t(1, 1) && t(2, 1)) { r[4] = 1; }
    r[5] = hits[0] * 100 + hits[1] * 10 + hits[2];
    clear();
    if (t(0, 1) && t(1, 1) && t(2, 1)) { r[6] = 1; }
    r[7] = hits[0] * 100 + hits[1] * 10 + hits[2];
    halt();
}
"""


def test_logical_operators_short_circuit():
    proc, mem, asm, syms = _build_and_run(SHORT_CIRCUIT_SOURCE)
    assert proc.halted
    got = _words(mem, syms['gvar_r'], 8)
    assert got == [
        1, 1000,   # || stops at the first true term
        0, 1111,   # all false: every term evaluated exactly once
        0, 100,    # && stops at the first false term
        1, 111,    # all true: every term evaluated exactly once
    ], got


def test_logical_chain_code_is_linear():
    """An n-term || emits one short-circuit block per operator, not 2^n."""
    source = """
    signed int x = 300;
    signed int r = 0;
    void main() {
        if (x < 0 || x > 255 || x == 7 || x == 9 || x == 11 || x == 13) { r = 1; }
        halt();
    }
    """
    proc, mem, asm, syms = _build_and_run(source)
    assert proc.halted
    assert mem.read_word(syms['gvar_r']) == 1
    assert len(re.findall(r'^sc_true_\d+:', asm, re.M)) == 5
