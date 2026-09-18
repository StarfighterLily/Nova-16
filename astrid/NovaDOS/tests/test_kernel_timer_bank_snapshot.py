"""NovaDOS timer-heartbeat tests: the BANK snapshot path, exercised by the OS.

WHAT: the kernel arms the vector-0 timer heartbeat (NOVADOS_ENABLE_TIMER, set
in main() after NDF bring-up). These tests prove the ISR actually fires, that
every interrupt entry/IRET pair keeps the CPU's BANK snapshot stack balanced,
and that live timer pressure never corrupts the bank-1 NDF disk even though
DIR/TYPE run banked while ticks advance.

WHY: interrupt entry snapshots the BANK register and forces bank 0 for the
handler ("Pure Option B", nova/bus/interrupt.py); IRET restores it. With the
heartbeat armed, a tick landing between set_bank(1) and the closing
set_bank(0) in ndf_read8/ndf_write8 must be a safe deferral, not disk
corruption -- exactly the guarantee the NovaDOS kernel depends on.
"""
import os
import subprocess
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, _REPO_ROOT)

from nova_main import initialize_system  # noqa: E402

_KERNEL_SRC = os.path.join(_REPO_ROOT, "astrid", "NovaDOS", "src", "kernel", "kernel.ast")

ENTER = 0x0A


def _load_syms(bin_path):
    syms = {}
    with open(bin_path.replace(".bin", ".sym")) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                syms[parts[0].lower()] = int(parts[1], 16)
    return syms


def _assert_clean_halt(proc):
    assert proc.halted, f"kernel never halted (PC=0x{proc.pc:04X})"
    assert proc.pc in (0x100E, 0x100F), (
        f"kernel halted at 0x{proc.pc:04X}, expected the entry stub HLT")
    assert proc.sp == 0xFFFF and proc.fp == 0xFFFF, (
        f"frames not unwound: SP=0x{proc.sp:04X} FP=0x{proc.fp:04X}")


def _boot(kernel_binary, keys, max_cycles=300000):
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry = mem.load(kernel_binary)
    proc.pc = entry
    for k in keys:
        kbd.add_key(k)
    cycles = 0
    while cycles < max_cycles and not proc.halted:
        proc.step()
        cycles += 1
    return proc, mem, gfx, cycles


@pytest.fixture(scope="module")
def kernel_binary(tmp_path_factory):
    from nova_assembler import Assembler

    tmp = tmp_path_factory.mktemp("novedos_timer")
    asm_path = str(tmp / "kernel.asm")
    rc = subprocess.run(
        [sys.executable,
         os.path.join(_REPO_ROOT, "astrid", "astrid_compiler.py"),
         _KERNEL_SRC, "-o", asm_path, "--memory-layout", "bank-safe"],
        capture_output=True, text=True)
    assert rc.returncode == 0, f"Astrid compile failed:\n{rc.stdout}\n{rc.stderr}"
    assert Assembler(log=None, trace=False).assemble(asm_path)
    bin_path = asm_path.replace(".asm", ".bin")
    assert os.path.exists(bin_path)
    return bin_path


@pytest.mark.integration
@pytest.mark.memory
def test_timer_heartbeat_drives_isr_and_balances_bank_stack(kernel_binary):
    """The armed heartbeat must reach timer_isr through the real controller,
    and every entry/IRET pair must leave the BANK snapshot stack drained."""
    proc, mem, gfx, cycles = _boot(kernel_binary, ())
    _assert_clean_halt(proc)
    syms = _load_syms(kernel_binary)

    ticks = mem.read_word(syms["gvar_system_ticks"])
    assert ticks > 0, (
        "system_ticks never advanced -- the timer heartbeat is not armed, so "
        "the bank-snapshot path is never exercised by the kernel")
    assert mem.read_word(syms["gvar_pending_timer"]) >= 1, (
        "timer_isr ran but never latched pending_timer")

    # Nesting balance: one snapshot pushed per entry, popped per IRET.
    assert proc._bank_irq_stack == [], (
        f"BANK snapshot stack not drained: {proc._bank_irq_stack}")
    # The OS never leaves a disk bank mapped across halt.
    assert mem.current_bank == 0, (
        f"kernel halted with bank {mem.current_bank} visible, expected 0")
    # Boot still formats bank 1 exactly as before the heartbeat existed.
    assert bytes(mem._bank_pages[1][:4]) == b"NDF1"


@pytest.mark.integration
@pytest.mark.memory
@pytest.mark.graphics
def test_banked_disk_access_survives_interrupt_storm(kernel_binary):
    """DIR performs dozens of banked ndf_read8 brackets while the heartbeat
    fires; the disk page must come out byte-identical and the ISR's global
    updates must land in base RAM (never in the banked window)."""
    proc, mem, gfx, cycles = _boot(kernel_binary, (*map(ord, "DIR"), ENTER))
    _assert_clean_halt(proc)
    syms = _load_syms(kernel_binary)

    # The shell actually ran DIR (banked reads) with ticks flowing.
    assert mem.read_word(syms["gvar_shell_cmd"]) == 5
    ticks = mem.read_word(syms["gvar_system_ticks"])
    assert ticks > 0, "heartbeat did not fire during the DIR command"

    # NDF page 1 integrity: header, entry count, the BOOT directory entry
    # (16-byte record at 0x10: name + type/flags + size 5 + offset 0x400) and
    # the HELLO data bytes. Any ISR window write would scramble one of these.
    page = mem._bank_pages[1]
    assert bytes(page[:6]) == b"NDF1\x00\x01"
    assert bytes(page[0x10:0x18]) == b"BOOT\x00\x00\x00\x00"
    assert bytes(page[0x1A:0x1E]) == b"\x00\x05\x04\x00"
    assert bytes(page[0x400:0x405]) == b"HELLO"

    assert proc._bank_irq_stack == []
    assert mem.current_bank == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
