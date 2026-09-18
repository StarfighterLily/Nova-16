"""Pure Option B: BANK is preserved across interrupt entry/IRET.

No ISA or stack-frame change: the interrupt controller snapshots the entry
BANK onto the CPU's nesting stack and forces bank 0 visible for the handler;
IRET pops the snapshot and restores it.
"""
import pytest

import nova_main as M
from core.exec import _iret
from core.flags import Flags


def _system():
    return M.initialize_system(enable_sound=False)


@pytest.mark.unit
@pytest.mark.cpu
def test_bus_trigger_preserves_bank():
    proc, mem, gfx, kbd, snd = _system()
    proc.Pregisters[8] = 0xFF00
    mem.write_word(0x0100, 0x3000)
    mem.set_bank(3)
    proc.flags_obj[Flags.I] = 1
    proc.interrupts[0] = 1
    proc.intr_ctrl._trigger(0)
    assert mem.current_bank == 0
    assert proc._bank_irq_stack == [3]
    _iret(proc)
    assert mem.current_bank == 3
    assert proc._bank_irq_stack == []


@pytest.mark.unit
@pytest.mark.cpu
def test_legacy_trigger_preserves_bank():
    proc, mem, gfx, kbd, snd = _system()
    proc.Pregisters[8] = 0xFF00
    mem.write_word(0x0100, 0x3000)
    mem.set_bank(5)
    proc.flags_obj[Flags.I] = 1
    proc._trigger_interrupt(0)
    assert mem.current_bank == 0
    assert proc._bank_irq_stack == [5]
    _iret(proc)
    assert mem.current_bank == 5
    assert proc._bank_irq_stack == []


@pytest.mark.unit
@pytest.mark.cpu
def test_nested_interrupts_unwind_lifo():
    proc, mem, gfx, kbd, snd = _system()
    proc.Pregisters[8] = 0xFF00
    mem.write_word(0x0100, 0x3000)
    mem.write_word(0x0104, 0x3100)
    proc.flags_obj[Flags.I] = 1
    proc.interrupts[0] = 1
    proc.interrupts[1] = 1
    mem.set_bank(2)
    proc.intr_ctrl._trigger(0)
    assert (mem.current_bank, proc._bank_irq_stack) == (0, [2])
    mem.set_bank(7)  # handler itself uses a bank
    proc.flags_obj[Flags.I] = 1
    proc.intr_ctrl._trigger(1)
    assert (mem.current_bank, proc._bank_irq_stack) == (0, [2, 7])
    _iret(proc)
    assert (mem.current_bank, proc._bank_irq_stack) == (7, [2])
    _iret(proc)
    assert (mem.current_bank, proc._bank_irq_stack) == (2, [])


@pytest.mark.unit
@pytest.mark.cpu
def test_bank_zero_entry_is_noop():
    proc, mem, gfx, kbd, snd = _system()
    proc.Pregisters[8] = 0xFF00
    mem.write_word(0x0100, 0x3000)
    mem.set_bank(0)
    proc.flags_obj[Flags.I] = 1
    proc.interrupts[0] = 1
    proc.intr_ctrl._trigger(0)
    assert mem.current_bank == 0
    assert proc._bank_irq_stack == [0]
    _iret(proc)
    assert mem.current_bank == 0
    assert proc._bank_irq_stack == []
