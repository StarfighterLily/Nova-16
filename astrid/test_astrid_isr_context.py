"""Regression tests for interrupt-handler (ISR) context preservation.

Root cause of the original starfield regression: the CPU's interrupt entry
pushes only PC + flags. The compiled timer_interrupt handler clobbered general
registers without saving them, so live register state in the interrupted
main program was corrupted across the interrupt. In starfield.ast this
manifested once scroll_y() calls lengthened the handler: the while(1)
loop's `MOV P7, 1; CMP P7, 0` sequence was split by an interrupt, P7 came
back as 0, `JZ` exited the "infinite" loop, main returned, and the program
hit HLT.

The compiler now emits a full register save/restore in the ISR prologue /
epilogue (before local allocation / after deallocation, before IRET).

These tests intentionally do NOT depend on the external ``starfield.ast``
file: that program is user-written and its contents (notably its timer
configuration) have changed over time, which made the historical
``test_starfield_survives_repeated_interrupts`` flaky -- ``starfield.ast``
programs its timer with a very slow divider (``TS=255, TM=255``), so only a
single interrupt would fire within the test's cycle budget. The starfield
scenario is therefore inlined below with a fast, deterministic timer, so the
test stays valid regardless of external program edits.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nova_main import initialize_system


# A self-contained starfield-style program: a register-heavy timer ISR that
# re-arms the timer, plus a main() that populates three star layers and then
# spins in an infinite loop. The timer is configured for a fast, deterministic
# fire rate (TM=16, TS=2 -> ~48 cycles per interrupt, the same proven
# configuration used by test_live_registers_survive_interrupt), guaranteeing
# multiple dispatches within the cycle budget regardless of external files.
_STARFIELD_SOURCE = """\
int ticks;

void draw_stars(int layer, int start, int finish, int step, int cmin, int cmax) {
    int p, x, y, color, rnd;
    set_layer(layer);
    for (p = start; p <= finish; p += step) {
        rnd = random();
        x = (rnd >> 8) & 0xFF;
        y = rnd & 0xFF;
        color = random_range(cmin, cmax);
        set_pos(x, y);
        write_screen(color);
    }
}

void timer_interrupt() {
    int a = random();
    int b = a * 3 + 7;
    int c = b ^ 0xF00F;
    ticks = ticks + c - c + 1;
    set_timer(0, 16, 2, 0);   // disable timer while mutating registers
    set_timer(0, 16, 2, 3);   // re-enable: TC=3 (enable + interrupt)
    iret();
}

void main() {
    set_vmode(1);
    set_pos(0, 0);
    draw_stars(1, 0, 65535, 32, 0, 4);
    draw_stars(2, 0, 65535, 128, 4, 7);
    draw_stars(3, 0, 65535, 256, 7, 15);
    sti();
    set_timer(0, 16, 2, 3);
    while (1) {
        // spin: live register state here is preserved by the ISR save/restore
    }
}
"""


def _compile_source(source):
    """Compile source text; return (asm_path, tmp_source)."""
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


def _cleanup(asm_path, tmp_source=None):
    paths = [asm_path.replace(".asm", ext) for ext in (".asm", ".bin", ".org", ".sym")]
    if tmp_source:
        paths.append(tmp_source)
    for p in paths:
        if os.path.exists(p):
            os.unlink(p)

def test_isr_emits_register_save_restore():
    """The compiled timer_interrupt must push/pop caller-saved registers.

    Driven by the inlined _STARFIELD_SOURCE so it does not depend on the
    external starfield.ast file. Any timer_interrupt() body triggers the
    unconditional full-register save/restore prologue/epilogue.
    """
    asm_path, tmp_src = _compile_source(_STARFIELD_SOURCE)
    try:
        with open(asm_path, encoding="utf-8") as f:
            text = f.read()
        start = text.find("func_timer_interrupt:")
        assert start >= 0, "timer_interrupt function not found in generated assembly"
        body = text[start:]
        # Prologue: registers pushed before locals are allocated
        assert "PUSH P0" in body, "ISR prologue missing register saves"
        assert "PUSH R9" in body, "ISR prologue missing R-register saves"
        # Epilogue: reverse-order pops immediately before IRET. Locate the real
        # IRET *instruction* line (a line whose stripped text is exactly "IRET")
        # rather than a bare "IRET" substring: the epilogue also emits a comment
        # containing "; Deallocate locals before IRET" whose embedded "IRET"
        # would otherwise shadow the real instruction. The line-strip scan is
        # indent-agnostic so it survives peephole reformatting of the .asm.
        idx_iret = -1
        offset = 0
        for line in body.splitlines(keepends=True):
            if line.strip() == "IRET":
                idx_iret = offset
                break
            offset += len(line)
        assert idx_iret >= 0, "IRET not found in ISR"
        tail = body[max(0, idx_iret - 400):idx_iret]
        assert "POP P0" in tail, "ISR epilogue missing register restores before IRET"
        assert "POP R9" in tail, "ISR epilogue missing R-register restores"
        print("PASS test_isr_emits_register_save_restore")
    finally:
        _cleanup(asm_path, tmp_src)



def test_starfield_survives_repeated_interrupts():
    """An inlined starfield scenario must keep running its while(1) loop across
    many timer interrupts without halting (register corruption regression),
    and must leave the star layers populated.

    Uses a fast, deterministic timer (TM=16, TS=2, TC=3) so at least two
    interrupts always fire within the cycle budget -- the historical failure
    was caused by starfield.ast's very slow timer divider yielding only a
    single dispatch.
    """
    asm_path, tmp_src = _compile_source(_STARFIELD_SOURCE)
    try:
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)
        bin_path = asm_path.replace(".asm", ".bin")

        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(bin_path)

        handler = mem.read_word_fast(0x0100)
        assert handler != 0, "timer vector not programmed"

        cycle = 0
        max_cycles = 300000
        dispatches = [0]
        intr_ctrl = proc.intr_ctrl
        orig_trigger = type(intr_ctrl)._trigger

        def counting_trigger(self, vector):
            dispatches[0] += 1
            orig_trigger(self, vector)

        type(intr_ctrl)._trigger = counting_trigger
        try:
            while cycle < max_cycles and not proc.halted:
                cycle += 1
                proc.step()
        finally:
            type(intr_ctrl)._trigger = orig_trigger

        assert not proc.halted, (
            f"starfield halted after {cycle} cycles "
            f"(ISR clobbered interrupted register state)")
        assert dispatches[0] >= 2, (
            f"expected >=2 timer interrupts, got {dispatches[0]}")
        nz1 = int((gfx.background_layers[0] != 0).sum())
        nz2 = int((gfx.background_layers[1] != 0).sum())
        nz3 = int((gfx.background_layers[2] != 0).sum())
        assert nz1 > 500 and nz2 > 100 and nz3 > 20, (
            f"star layers under-populated: {nz1}, {nz2}, {nz3}")
        print(f"PASS test_starfield_survives_repeated_interrupts "
              f"(cycles={cycle}, dispatches={dispatches[0]}, stars={nz1}/{nz2}/{nz3})")
    finally:
        _cleanup(asm_path, tmp_src)



def test_live_registers_survive_interrupt():
    """Reproduces the original starfield failure shape: a while(1) loop whose
    condition compiles to `MOV Px, 1; CMP Px, 0; JZ end`, hammered by a fast,
    register-heavy timer ISR. Without ISR register save/restore, an interrupt
    landing between the MOV and CMP leaves Px clobbered, JZ exits the
    'infinite' loop, and main returns early (P0 != 42)."""
    source = """
int ticks;

void timer_interrupt() {
    // Register-heavy body: multi-temporary expression evaluation clobbers
    // several P registers, exactly like the real starfield handler.
    int a = random();
    int b = a * 3 + 7;
    int c = b ^ 0xF00F;
    ticks = ticks + c - c + 1;
    iret();
}

int main() {
    sti();
    set_timer(0, 16, 2, 3);   // fire often: TM=16, TS=2 -> every ~48 cycles
    while (1) {
        if (ticks >= 100) {
            return 42;
        }
    }
}
"""
    asm_path, tmp_src = _compile_source(source)
    try:
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)
        bin_path = asm_path.replace(".asm", ".bin")

        proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
        proc.pc = mem.load(bin_path)
        cycle = 0
        max_cycles = 4000000
        while cycle < max_cycles and not proc.halted:
            cycle += 1
            proc.step()
        assert proc.halted, "test program did not halt"
        assert proc.p0 == 42, (
            f"Register state corrupted across interrupt: P0={proc.p0} "
            f"(expected 42); ticks={_guard_addr_value(asm_path, mem)}")
        print(f"PASS test_live_registers_survive_interrupt (cycles={cycle})")
    finally:
        _cleanup(asm_path, tmp_src)


def _guard_addr_value(asm_path, mem):
    """Read the gvar_ticks value via its symbol-table address."""
    sym_path = asm_path.replace(".asm", ".sym")
    with open(sym_path, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2 and parts[0] == "gvar_ticks":
                return mem.read_word_fast(int(parts[1], 16))
    raise AssertionError("gvar_ticks not found in symbol table")


if __name__ == "__main__":
    test_isr_emits_register_save_restore()
    test_starfield_survives_repeated_interrupts()
    test_live_registers_survive_interrupt()
    print("All ISR context-preservation tests passed!")

