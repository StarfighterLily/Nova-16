"""
NovaDOS Test Harness
Boots the kernel, seeds keyboard input, and steps the CPU.
"""
import pytest
import sys
import os

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nova.bus.eventbus import EventBus
from nova.bus.interrupt import InterruptController
from nova.memory.memory import Memory
from nova.peripherals.timer import Timer
import nova.graphics.gfx as gpu
import nova_keyboard as keyboard
import nova_uart as uart
from nova_cpu import CPU

KERNEL = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                       "NovaDOS", "build", "kernel.bin")


def boot_novados(keys=(), cycles_budget=200000):
    """Boot NovaDOS, optionally pre-seed key scan codes, step to a sentinel."""
    bus = EventBus()
    mem = Memory(bus=bus)
    gfx = gpu.GFX()
    kbd = keyboard.NovaKeyboard(bus=bus)
    intr = InterruptController(bus=bus, memory=mem)
    timer = Timer(bus=bus, interrupt_controller=intr)
    proc = CPU(mem, gfx, kbd, None, uart_device=uart.NovaUART(host_bridge=None),
               bus=bus, interrupt_controller=intr, timer_device=timer)
    intr.cpu = proc
    bus.subscribe("cpu.post_step", intr.check)

    entry = mem.load(KERNEL)
    proc.pc = entry

    for k in keys:
        if isinstance(k, int):
            kbd.add_key(k)
        elif len(k) == 1:
            kbd.add_key(ord(k))
        else:
            kbd.add_key(kbd.get_scan_code(k))

    return proc, mem, gfx, kbd


def type_cmd(proc, gfx, kbd, cmd, enter=True):
    """Type a command string into the keyboard buffer and add Enter."""
    for ch in cmd:
        kbd.add_key(ord(ch))
    if enter:
        kbd.add_key(0x93)  # Enter scan code


def run_until(proc, predicate, max_cycles=200000):
    """Step CPU until predicate(proc) is True or max_cycles reached."""
    for _ in range(max_cycles):
        if predicate(proc):
            return True
        try:
            proc.step()
        except Exception as e:
            raise RuntimeError(f"CPU exception at PC=0x{proc.pc:04X}: {e}")
    return False


def seed_bank(mem, bank, file_name, payload, entry_addr, file_type=0):
    """Seed an NDF volume into bank `bank` (window 0x8000-0xBFFF).

    Volume layout (NovaDOS NDF Phase 1):
      +0x0000  magic b"NDB1"
      +0x000E  1 byte entry count
      +0x0010  16-byte directory entries:
                 name[10] type(1) flags(1) start(2) len(2) entry(2)
      +0x0400  file bytes
    All words are big-endian.
    """
    mem.set_bank(bank)
    base = 0x8000
    # Volume header
    mem.write_bytes_direct(base + 0x0000, b"NDB1")
    mem.write_bytes_direct(base + 0x000E, [1])            # 1 entry
    # Directory entry
    name = file_name.ljust(10, b" ")[:10]
    start = 0x0400
    length = len(payload)
    entry = [
        *name,
        0,                                            # type: program
        0,                                            # flags
        (start >> 8) & 0xFF, start & 0xFF,            # start word
        (length >> 8) & 0xFF, length & 0xFF,          # length word
        (entry_addr >> 8) & 0xFF, entry_addr & 0xFF,  # entry word
    ]
    mem.write_bytes_direct(base + NDF_DIR_OFFSET, entry)
    # File data
    mem.write_bytes_direct(base + start, payload)
    mem.set_bank(0)


# NDF directory offset within the bank window (matches ndefs.asm)
NDF_DIR_OFFSET = 0x0010
