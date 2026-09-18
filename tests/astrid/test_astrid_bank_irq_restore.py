"""Bank snapshot across real timer interrupts, from compiled Astrid.

WHAT: proves the "Pure Option B" BANK snapshot (nova/bus/interrupt.py) works
end-to-end through the Astrid toolchain: a timer ISR fires while the mainline
holds a non-zero bank mapped in the 0x8000-0xBFFF window.

WHY: the NovaDOS kernel runs its NDF disk layer in the bank window, and its
timer ISR can land between set_bank(bank) and the closing set_bank(0). The
hardware contract under test is:
  1. interrupt entry snapshots the entry bank and forces bank 0 for the
     handler (the ISR's own globals / any window access see base RAM), and
  2. IRET pops the snapshot, handing the disk bank back to the interrupted
     code, so the banked access resumes with the right page still mapped.
Without that contract an ISR touching window addresses would silently hit the
disk page (corrupting it), and a handler that switched banks would break the
interrupted access's bracketing.
"""
import os
import sys

import pytest

# Path setup handled by tests/astrid/conftest.py
from nova_main import initialize_system


_SOURCE = """\
// Bank-snapshot probe: mainline holds bank 2 mapped while >= 3 timer
// interrupts fire. timer_isr must run with bank 0 (it only touches base-RAM
// globals), and every IRET must hand bank 2 back.
volatile int ticks;
volatile int bank_after;
volatile int marker;
volatile int spin;

interrupt(0) void timer_isr() {
    ticks = ticks + 1;
    iret();
}

void main() {
    spin = 0;
    marker = 0;
    bank_after = 0;
    set_bank(2);
    poke(0x8200, 0x5A);        // marker byte lives in bank page 2
    sti();
    set_timer(0, 16, 2, 3);    // fire every ~(2+1)*16 = 48 cycles
    while (ticks < 3) {
        spin = spin + 1;       // spin with bank 2 mapped across >= 3 IRQs
    }
    bank_after = read_bank();  // must be 2: IRET restored the snapshot
    marker = peek(0x8200);     // window must still map page 2 (0x5A)
    set_bank(0);
    cli();
    halt();
}
"""


def _load_syms(bin_path):
    syms = {}
    with open(bin_path.replace(".bin", ".sym")) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                syms[parts[0].lower()] = int(parts[1], 16)
    return syms


@pytest.fixture(scope="module")
def probe_binary(tmp_path_factory):
    from astrid.compiler_api import compile_astrid
    from nova_assembler import Assembler

    tmp = tmp_path_factory.mktemp("bank_irq_probe")
    src_path = str(tmp / "bank_irq_probe.ast")
    with open(src_path, "w", encoding="utf-8") as f:
        f.write(_SOURCE)
    asm_path = str(tmp / "bank_irq_probe.asm")
    # bank-safe layout keeps the probe's globals OUT of the window it banks
    # (same constraint the NovaDOS kernel builds under).
    assert compile_astrid(src_path, asm_path, memory_layout="bank-safe", log=None)
    assert Assembler(log=None, trace=False).assemble(asm_path)
    bin_path = asm_path.replace(".asm", ".bin")
    assert os.path.exists(bin_path)
    return bin_path


@pytest.mark.integration
@pytest.mark.memory
@pytest.mark.cpu
def test_bank_survives_timer_interrupts(probe_binary):
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry = mem.load(probe_binary)
    proc.pc = entry
    syms = _load_syms(probe_binary)

    cycles = 0
    while cycles < 200000 and not proc.halted:
        cycles += 1
        proc.step()

    assert proc.halted, f"probe never halted (PC=0x{proc.pc:04X})"
    ticks = mem.read_word(syms["gvar_ticks"])
    assert ticks >= 3, f"ISR ran only {ticks} times; snapshot path untested"

    # IRET restored the interrupted bank every time: the mainline woke up
    # with page 2 still mapped, not the forced entry bank 0.
    bank_after = mem.read_word(syms["gvar_bank_after"])
    assert bank_after == 2, (
        f"read_bank() after the IRQ storm was {bank_after}, expected 2 -- "
        "IRET failed to restore the entry bank")

    # The window still maps page 2 after the interrupts, so the marker byte
    # poked before sti() reads back 0x5A. If entry had NOT forced bank 0 the
    # ISR could have scribbled over the disk page; if IRET lost the restore
    # this peek would read base RAM (0x00) instead of page 2.
    marker = mem.read_word(syms["gvar_marker"])
    assert marker == 0x5A, f"banked marker byte is {marker:#04X}, expected 0x5A"

    # The ISR itself must have run on bank 0: page 2's marker byte survived.
    assert mem._bank_pages[2][0x200] == 0x5A, (
        "bank page 2 was corrupted by ISR traffic")

    # Every entry/IRET pair is balanced, and the machine rests on bank 0.
    assert proc._bank_irq_stack == [], (
        f"BANK snapshot stack not drained: {proc._bank_irq_stack}")
    assert mem.current_bank == 0, (
        f"machine halted with bank {mem.current_bank} visible, expected 0")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
