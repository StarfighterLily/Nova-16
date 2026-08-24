"""Regression tests for interrupt-handler (ISR) context preservation.

Root cause of the starfield regression: the CPU's interrupt entry pushes
only PC + flags. The compiled timer_interrupt handler clobbered general
registers without saving them, so live register state in the interrupted
main program was corrupted across the interrupt. In starfield.ast this
manifested once scroll_y() calls lengthened the handler: the while(1)
loop's `MOV P7, 1; CMP P7, 0` sequence was split by an interrupt, P7 came
back as 0, `JZ` exited the "infinite" loop, main returned, and the program
hit HLT.

The compiler now emits a full register save/restore in the ISR prologue /
epilogue (before local allocation / after deallocation, before IRET).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nova_main import initialize_system


def _compile_ast(path):
    """Compile a COPY of an existing .ast file; return (asm_path, tmp_source)."""
    import shutil
    import tempfile
    fd, tmp_src = tempfile.mkstemp(suffix=".ast")
    os.close(fd)
    shutil.copyfile(path, tmp_src)
    from astrid_compiler import main as compiler_main
    out = tmp_src.replace(".ast", ".asm")
    old_argv = sys.argv
    sys.argv = [old_argv[0], tmp_src, "-o", out]
    try:
        compiler_main()
    finally:
        sys.argv = old_argv
    return out, tmp_src


def _compile_source(source):
    """Compile source text; return (asm_path, tmp_source)."""
    import tempfile
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
    """The compiled timer_interrupt must push/pop caller-saved registers."""
    astrid_dir = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(astrid_dir, "starfield.ast")
    asm_path, tmp_src = _compile_ast(src)
    try:
        with open(asm_path, encoding="utf-8") as f:
            text = f.read()
        start = text.find("func_timer_interrupt:")
        assert start >= 0, "timer_interrupt function not found in generated assembly"
        body = text[start:]
        # Prologue: registers pushed before locals are allocated
        assert "PUSH P0" in body, "ISR prologue missing register saves"
        assert "PUSH R9" in body, "ISR prologue missing R-register saves"
        # Epilogue: reverse-order pops immediately before IRET. Use the FIRST
        # IRET after the ISR label: lazily-linked stubs (e.g. builtin_iret,
        # pulled in when parallax() calls iret()) are emitted after functions
        # and would otherwise be mistaken for the handler's epilogue.
        idx_iret = body.find("IRET")
        assert idx_iret >= 0, "IRET not found in ISR"
        tail = body[max(0, idx_iret - 400):idx_iret]
        assert "POP P0" in tail, "ISR epilogue missing register restores before IRET"
        assert "POP R9" in tail, "ISR epilogue missing R-register restores"
        print("PASS test_isr_emits_register_save_restore")
    finally:
        _cleanup(asm_path, tmp_src)


def test_starfield_survives_repeated_interrupts():
    """starfield.ast must keep running its while(1) loop across many timer
    interrupts without halting (register corruption regression)."""
    astrid_dir = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(astrid_dir, "starfield.ast")
    asm_path, tmp_src = _compile_ast(src)
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
    """Read the gvar_guard_ok value via its symbol-table address."""
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