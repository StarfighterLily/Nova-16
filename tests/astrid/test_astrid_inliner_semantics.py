"""Regression tests for the Astrid function inliner and dead-function pass.

Found while repairing NovaDOS (2026-10-15). The inliner pasted callee bodies
into call sites with three semantic holes, plus a size problem:

1. **Callee locals were not renamed.** An inlined ``int i;`` landed in the
   caller's scope, so a callee loop over ``i`` reset the caller's own ``i``.
   NovaDOS's poll loop never terminated once ``wake_sleepers`` was inlined.
2. **Arguments were substituted textually.** ``f(next())`` with a parameter
   used twice called ``next()`` twice (and zero times for an unused one).
3. **``return`` inside a callee returned from the caller.** An early
   ``return;`` in a void helper ended the *calling* function.
4. **Size.** Eligibility counted only top-level statements, so a whole
   if/else-if chain counted as one; nothing bounded copies x call sites; and
   the out-of-line body was always emitted too.
"""
import os
import tempfile

import pytest

# Path setup is handled by tests/astrid/conftest.py
from nova_main import initialize_system


def _build(source, defines=None):
    from astrid.compiler_api import compile_astrid
    from nova_assembler import Assembler
    tmpdir = tempfile.mkdtemp(prefix='astrid_inline_')
    src = os.path.join(tmpdir, 'prog.ast')
    asm = os.path.join(tmpdir, 'prog.asm')
    with open(src, 'w', encoding='utf-8') as f:
        f.write(source)
    compile_astrid(src, asm, log=lambda m: None, defines=defines,
                   assemble_callback=lambda p, v, e: bool(Assembler().assemble(str(p))))
    with open(asm, encoding='utf-8') as f:
        asm_text = f.read()
    return asm, asm_text


def _run(asm, max_cycles=200000):
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
            if len(parts) == 2:
                syms[parts[0].lower()] = int(parts[1], 16)
    return proc, mem, syms


def _build_and_run(source):
    asm, text = _build(source)
    proc, mem, syms = _run(asm)
    assert proc.halted, 'program did not terminate'
    return mem, syms, text


def test_callee_locals_do_not_capture_caller_variables():
    mem, syms, _ = _build_and_run("""
int flags[4];
int outer = 0;
void scan() {
    int i;
    for (i = 0; i < 4; i = i + 1) { flags[i] = flags[i] + 1; }
}
void main() {
    int i;
    i = 0;
    while (i < 3) { scan(); i = i + 1; outer = outer + 1; }
}
""")
    assert mem.read_word(syms['gvar_outer']) == 3
    assert [mem.read_word(syms['gvar_flags'] + 2 * k) for k in range(4)] == [3] * 4


def test_caller_argument_named_like_callee_local():
    mem, syms, _ = _build_and_run("""
int out = 0;
void put(int v) { int i; i = 100; out = out + v + i; }
void main() { int i; i = 5; put(i); }
""")
    assert mem.read_word(syms['gvar_out']) == 105


def test_argument_side_effects_run_exactly_once():
    mem, syms, _ = _build_and_run("""
int calls = 0;
int seen = 0;
int next() { calls = calls + 1; return calls * 10; }
void twice(int v) { seen = v + v; }
void never(int v) { seen = seen + 1; }
void main() { twice(next()); never(next()); }
""")
    assert mem.read_word(syms['gvar_calls']) == 2
    assert mem.read_word(syms['gvar_seen']) == 21


def test_return_in_callee_does_not_end_caller():
    mem, syms, _ = _build_and_run("""
int log = 0;
void maybe(int c) { if (c == 1) { return; } log = log + c; }
void main() { maybe(1); log = log + 100; maybe(2); log = log + 1000; }
""")
    assert mem.read_word(syms['gvar_log']) == 1102


def test_dead_functions_are_not_emitted():
    _, text = _build("""
int g = 0;
void unused() { g = 7; }
void helper() { g = g + 1; }
int via_pointer(int v) { return v + 1; }
int (*fp)(int) = &via_pointer;
void main() { helper(); g = fp(g); }
""")
    assert 'func_unused:' not in text
    assert 'func_via_pointer:' in text   # reachable only through &via_pointer


def test_function_called_only_from_asm_is_kept():
    _, text = _build("""
int g = 0;
void from_asm() { g = 9; }
void main() { asm("CALL func_from_asm"); }
""")
    assert 'func_from_asm:' in text


def test_large_dispatch_chain_is_not_inlined():
    # One top-level if/else-if statement with many arms used to count as a
    # single statement and was copied into every call site.
    source = """
int r = 0;
void dispatch(int c) {
    if (c == 1) { r = 1; } else if (c == 2) { r = 2; } else if (c == 3) { r = 3; }
    else if (c == 4) { r = 4; } else if (c == 5) { r = 5; } else { r = 9; }
}
void main() { dispatch(1); dispatch(2); dispatch(3); }
"""
    _, text = _build(source)
    assert text.count('CALL func_dispatch') == 3


def test_inlined_function_pointer_locals_and_parameters():
    # run_at() is inlined: its local function pointer is renamed, and so must
    # be the call through it; a called parameter stays a variable even when
    # the argument is a literal address.
    mem, syms, _ = _build_and_run("""
int hits = 0;
void target() { hits = hits + 1; }
void run_at(int addr) { int (*entry)(); entry = addr; entry(); }
void apply(int (*cb)()) { cb(); }
void main() { run_at(&target); apply(&target); }
""")
    assert mem.read_word(syms['gvar_hits']) == 2
