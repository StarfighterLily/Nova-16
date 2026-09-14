"""Tests for Tier 4: generalized interrupt handlers and naked functions.

Covers:
- interrupt(N) attribute syntax for any vector 0-7
- naked function attribute (no register save/restore)
- Backward compatibility: timer_interrupt name still works
- Multiple interrupt handlers at different vectors
- Naked interrupt handler (no save/restore, programmer-managed)
"""
import os
import re
import sys
import tempfile

import pytest

from nova_main import initialize_system


def _compile_to_asm(source):
    """Compile Astrid source text; return (asm_path, tmp_source)."""
    fd = tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8')
    fd.write(source)
    fd.close()
    from astrid_compiler import main as compiler_main
    old_argv = sys.argv
    sys.argv = [old_argv[0], fd.name, '-o', fd.name.replace('.ast', '.asm')]
    try:
        compiler_main()
    finally:
        sys.argv = old_argv
    return fd.name.replace('.ast', '.asm'), fd.name


def _cleanup(asm_path, tmp_source=None):
    paths = [asm_path.replace('.asm', ext)
             for ext in ('.asm', '.bin', '.org', '.sym')]
    if tmp_source:
        paths.append(tmp_source)
    for p in paths:
        if os.path.exists(p):
            os.unlink(p)


def run_binary(bin_path, max_cycles=2000000):
    """Run a binary headlessly and return (proc, cycles, mem)."""
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry_point = mem.load(bin_path)
    proc.pc = entry_point
    cycle = 0
    while cycle < max_cycles and not proc.halted:
        cycle += 1
        proc.step()
    return proc, cycle, mem


def compile_and_run(source, expected_r0=None, expected_p0=None, max_cycles=2000000):
    """Compile Astrid source, assemble, and run. Returns (proc, cycles, mem)."""
    asm_path, tmp_src = _compile_to_asm(source)
    try:
        bin_path = asm_path.replace('.asm', '.bin')
        from nova_assembler import Assembler
        Assembler().assemble(asm_path)
        proc, cycles, mem = run_binary(bin_path, max_cycles=max_cycles)
        assert proc.halted, "Program did not halt"
        if expected_r0 is not None:
            assert proc.r0 == expected_r0, f"Expected R0={expected_r0}, got {proc.r0}"
        if expected_p0 is not None:
            assert proc.p0 == expected_p0, f"Expected P0={expected_p0}, got {proc.p0}"
        return proc, cycles, mem
    finally:
        _cleanup(asm_path, tmp_src)


def _sym_addr(sym_path, name):
    """Look up a symbol's address from an assembler .sym file.

    The .sym writer uppercases all symbol names (e.g. ``FUNC_UART_ISR``),
    so the lookup is case-insensitive.
    """
    want = name.upper()
    with open(sym_path, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2 and parts[0].upper() == want:
                return int(parts[1], 16)
    return None


class TestInterruptAttribute:
    """Tests for interrupt(N) attribute syntax."""

    def test_interrupt_vector_2_emits_vector_table(self):
        """interrupt(2) should emit DW func_uart_isr at vector 2."""
        source = """
int ticks;

interrupt(2) void uart_isr() {
    ticks = ticks + 1;
    iret();
}

void main() {
    while (1) {
        if (ticks >= 1) {
            return;
        }
    }
}
"""
        asm_path, tmp_src = _compile_to_asm(source)
        try:
            with open(asm_path, encoding='utf-8') as f:
                text = f.read()
            assert 'ORG 0x0100' in text, "Missing ORG 0x0100 for vector table"
            assert 'DW func_uart_isr' in text, "Missing DW func_uart_isr"
            assert 'vector 2' in text, "Missing vector 2 comment"
        finally:
            _cleanup(asm_path, tmp_src)

    def test_interrupt_handler_gets_save_restore(self):
        """Non-naked interrupt handler should emit register save/restore."""
        source = """
int ticks;

interrupt(3) void my_isr() {
    int a = 5;
    ticks = ticks + a;
    iret();
}

void main() {
    while (1) {
        if (ticks >= 1) {
            return;
        }
    }
}
"""
        asm_path, tmp_src = _compile_to_asm(source)
        try:
            with open(asm_path, encoding='utf-8') as f:
                text = f.read()
            start = text.find('func_my_isr:')
            assert start >= 0, "my_isr function not found"
            body = text[start:start + 2000]
            assert 'PUSH' in body, "Missing PUSH (register save) in ISR prologue"
            assert 'POP' in body, "Missing POP (register restore) in ISR epilogue"
            assert 'IRET' in body, "Missing IRET in ISR"
        finally:
            _cleanup(asm_path, tmp_src)

    def test_interrupt_vector_0_explicit(self):
        """interrupt(0) should work just like timer_interrupt."""
        source = """
int ticks;

interrupt(0) void my_timer() {
    ticks = ticks + 1;
    iret();
}

void main() {
    while (1) {
        if (ticks >= 1) {
            return;
        }
    }
}
"""
        asm_path, tmp_src = _compile_to_asm(source)
        try:
            with open(asm_path, encoding='utf-8') as f:
                text = f.read()
            assert 'DW func_my_timer' in text, "Missing DW func_my_timer"
            assert 'vector 0' in text, "Missing vector 0 comment"
        finally:
            _cleanup(asm_path, tmp_src)

    def test_multiple_interrupt_handlers(self):
        """Multiple interrupt handlers at different vectors."""
        source = """
int tick2;
int tick5;

interrupt(2) void isr2() {
    tick2 = tick2 + 1;
    iret();
}

interrupt(5) void isr5() {
    tick5 = tick5 + 1;
    iret();
}

void main() {
    return;
}
"""
        asm_path, tmp_src = _compile_to_asm(source)
        try:
            with open(asm_path, encoding='utf-8') as f:
                text = f.read()
            assert 'DW func_isr2' in text, "Missing DW func_isr2"
            assert 'DW func_isr5' in text, "Missing DW func_isr5"
            assert 'vector 2' in text, "Missing vector 2"
            assert 'vector 5' in text, "Missing vector 5"
        finally:
            _cleanup(asm_path, tmp_src)

    def test_nonzero_vector_lands_at_correct_offset(self):
        """interrupt(2) handler must be placed at 0x0100 + 4*2 = 0x0108.

        Regression: the vector table used to emit every DW straight after
        ``ORG 0x0100``, so a non-zero vector's entry landed in vector 0's
        slot (0x0100) and the real slot stayed 0x0000 -- the handler was
        never dispatched. Only vector 0 worked. Verify both the placement
        of the non-zero entry and that vector 0 is *not* aliased to it.
        """
        source = """
int ticks;

interrupt(2) void uart_isr() {
    ticks = ticks + 1;
    iret();
}

void main() {
    while (1) {
    }
}
"""
        asm_path, tmp_src = _compile_to_asm(source)
        try:
            bin_path = asm_path.replace('.asm', '.bin')
            from nova_assembler import Assembler
            assert Assembler().assemble(asm_path)
            proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
            mem.load(bin_path)
            handler_addr = _sym_addr(asm_path.replace('.asm', '.sym'),
                                     'func_uart_isr')
            assert handler_addr is not None, "func_uart_isr not in symbol table"
            # Vector 2 slot is at 0x0108.
            assert mem.read_word(0x0108) == handler_addr, (
                f"vector 2 slot (0x0108) should hold {handler_addr:#06x}, "
                f"got {mem.read_word(0x0108):#06x}")
            # Vector 0 must NOT alias the same handler (old pile-up bug).
            assert mem.read_word(0x0100) != handler_addr, (
                "vector 0 slot aliases the vector-2 handler; DW not padded")
            # Vector 1 must stay empty.
            assert mem.read_word(0x0104) == 0, "vector 1 slot should be empty"
        finally:
            _cleanup(asm_path, tmp_src)

    def test_keyboard_interrupt_vector2_fires_handler(self):
        """interrupt(2) handler runs when a key is pressed (runtime proof).

        Drives the real event-bus path: sti() + key_ctrl(1) enable the
        keyboard vector, a simulated key press publishes the key event, and
        the interrupt controller must dispatch to the handler, which bumps a
        global the main loop polls. This is the end-to-end scenario that
        atemp.ast exercises.
        """
        source = """
int fired;

interrupt(2) void kbd_int() {
    fired = fired + 1;
    iret();
}

void main() {
    sti();
    key_ctrl(1);
    while (1) {
        if (fired >= 1) {
            return;
        }
    }
}
"""
        asm_path, tmp_src = _compile_to_asm(source)
        try:
            bin_path = asm_path.replace('.asm', '.bin')
            from nova_assembler import Assembler
            assert Assembler().assemble(asm_path)
            proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
            entry = mem.load(bin_path)
            proc.pc = entry
            # Warm up: get past startup + sti + key_ctrl into the while loop.
            for _ in range(400):
                if proc.halted:
                    break
                proc.step()
            assert not proc.halted, "program halted before key press"
            # Simulate a key press; this publishes keyboard.key_pressed on
            # the bus, which the interrupt controller services on the next
            # CPU step (keyboard vector 2 -> handler at 0x0108).
            kbd.add_key(0x61)
            for _ in range(200000):
                if proc.halted:
                    break
                proc.step()
            assert proc.halted, "program did not halt after key press"
            # The handler must have bumped gvar_fired (globals start 0x8000).
            assert mem.read_word(0x8000) == 1, (
                "keyboard interrupt did not reach the handler")
        finally:
            _cleanup(asm_path, tmp_src)


class TestTimerInterruptBackwardCompat:
    """timer_interrupt name should still work (deprecated alias)."""

    def test_timer_interrupt_still_works(self):
        """void timer_interrupt() should still be treated as vector 0 ISR."""
        source = """
int ticks;

void timer_interrupt() {
    ticks = ticks + 1;
    iret();
}

void main() {
    while (1) {
        if (ticks >= 1) {
            return;
        }
    }
}
"""
        asm_path, tmp_src = _compile_to_asm(source)
        try:
            with open(asm_path, encoding='utf-8') as f:
                text = f.read()
            assert 'DW func_timer_interrupt' in text, "Missing DW func_timer_interrupt"
            assert 'vector 0' in text, "Missing vector 0 for timer_interrupt"
            start = text.find('func_timer_interrupt:')
            body = text[start:start + 2000]
            assert 'PUSH' in body, "Missing PUSH in timer_interrupt prologue"
            assert 'IRET' in body, "Missing IRET in timer_interrupt"
        finally:
            _cleanup(asm_path, tmp_src)


class TestNakedFunction:
    """Tests for naked function attribute."""

    def test_naked_isr_no_save_restore(self):
        """naked interrupt handler should NOT emit register save/restore."""
        source = """
int ticks;

naked interrupt(1) void fast_isr() {
    asm("MOV R0, 1");
    iret();
}

void main() {
    return;
}
"""
        asm_path, tmp_src = _compile_to_asm(source)
        try:
            with open(asm_path, encoding='utf-8') as f:
                text = f.read()
            start = text.find('func_fast_isr:')
            assert start >= 0, "fast_isr function not found"
            body = text[start:start + 1000]
            # Naked should NOT have PUSH P0..P7 sequence
            has_full_save = ('PUSH P0' in body and 'PUSH P1' in body
                             and 'PUSH P7' in body)
            assert not has_full_save, (
                "naked ISR should not have full register save/restore")
            assert 'IRET' in body, "Missing IRET in naked ISR"
        finally:
            _cleanup(asm_path, tmp_src)

    def test_naked_function_emits_label(self):
        """naked function should still emit a label."""
        source = """
naked void boot_stub() {
    asm("JMP main");
}

void main() {
    return;
}
"""
        asm_path, tmp_src = _compile_to_asm(source)
        try:
            with open(asm_path, encoding='utf-8') as f:
                text = f.read()
            assert 'func_boot_stub:' in text, "Missing func_boot_stub label"
        finally:
            _cleanup(asm_path, tmp_src)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
