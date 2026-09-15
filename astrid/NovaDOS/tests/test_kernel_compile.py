"""Tests for the Astrid-based NovaDOS kernel (astrid/NovaDOS/src/kernel/).

WHAT: compiles the Astrid kernel sources to assembly + binary, then runs them
headlessly on the real Nova-16 emulator and asserts structural properties of
the generated binary (memory layout, vector table, entry stub).

WHY: the Astrid NovaDOS is compiled with the Astrid->Nova-16 codegen, not the
legacy assembly pipeline. These tests guard the *compiler* contract for NovaDOS
specifically -- that the codegen lays out segments so the entry stub at 0x1000
is never overwritten by the ISR code/data region. This is the regression guard
for the "Unknown opcode: F8" bug (see docs/notes/start.md, 2026-09-15).
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


def _run(cmd, **kw):
    res = subprocess.run(cmd, capture_output=True, text=True, **kw)
    return res.returncode, res.stdout, res.stderr


def _load_syms(bin_path):
    sym_path = bin_path.replace(".bin", ".sym")
    syms = {}
    with open(sym_path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                syms[parts[0].lower()] = int(parts[1], 16)
    return syms


@pytest.fixture(scope="module")
def kernel_binary(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("novedos_kernel")
    asm_path = str(tmp / "kernel.asm")
    bin_path = str(tmp / "kernel.bin")
    rc, out, err = _run([
        sys.executable,
        os.path.join(_REPO_ROOT, "astrid", "astrid_compiler.py"),
        _KERNEL_SRC, "-o", asm_path,
    ])
    assert rc == 0, f"Astrid compile failed:\n{out}\n{err}"
    assert os.path.exists(asm_path)
    from nova_assembler import Assembler
    ok = Assembler(log=None, trace=False).assemble(asm_path)
    assert ok, "Assembler failed"
    assert os.path.exists(bin_path)
    return bin_path


def test_entry_stub_is_intact(kernel_binary):
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry = mem.load(kernel_binary)
    assert entry == 0x1000
    stub = bytes(mem._mem[0x1000:0x100F])
    # Stub layout (15 bytes): MOV SP,0xFFFF / MOV FP,0xFFFF / CALL func_main / HLT
    assert stub[0] == 0x06, f"expected MOV opcode at 0x1000, got 0x{stub[0]:02X}"
    assert stub[1] == 0x08, "expected mode byte (reg+imm16) at 0x1001"
    assert stub[3:5] == bytes([0xFF, 0xFF]), "SP immediate should be 0xFFFF"
    assert stub[5] == 0x06, f"expected MOV opcode at 0x1005, got 0x{stub[5]:02X}"
    assert stub[8:10] == bytes([0xFF, 0xFF]), "FP immediate should be 0xFFFF"
    assert stub[10] == 0x2F, f"expected CALL opcode at 0x100A, got 0x{stub[10]:02X}"
    assert stub[14] == 0x00, f"expected HLT (0x00) at 0x100E, got 0x{stub[14]:02X}"


def test_vector_table_points_into_kernel_code(kernel_binary):
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    mem.load(kernel_binary)
    syms = _load_syms(kernel_binary)
    timer_handler = syms.get("func_timer_isr")
    assert timer_handler is not None
    vec0 = mem.read_word(0x0100)
    assert vec0 == timer_handler, (
        f"IVT vector 0 points to 0x{vec0:04X}, "
        f"expected func_timer_isr 0x{timer_handler:04X}")


def test_code_does_not_overlap_stub(kernel_binary):
    org_path = kernel_binary.replace(".bin", ".org")
    with open(org_path) as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    segments = []
    for line in lines:
        parts = line.split()
        assert len(parts) == 3
        start = int(parts[0], 16)
        length = int(parts[1])
        segments.append((start, length))
    stub_seg = (0x1000, 15)
    assert stub_seg in segments
    for start, length in segments:
        end = start + length
        if start != 0x1000:
            assert end <= 0x1000 or start >= 0x100F, (
                f"segment [{start:#x}-{end:#x}] overlaps stub [0x1000-0x100F]")


def test_kernel_runs_without_opcode_crash(kernel_binary):
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry = mem.load(kernel_binary)
    proc.pc = entry
    syms = _load_syms(kernel_binary)
    main_addr = syms.get("func_main")
    assert main_addr is not None
    cycles = 0
    max_cycles = 20000
    error = None
    while cycles < max_cycles and not proc.halted:
        cycles += 1
        try:
            proc.step()
        except Exception as e:
            error = e
            break
    # Must NOT fail with "Unknown opcode" -- that was the bug being fixed.
    assert error is None or "Unknown opcode" not in str(error), (
        f"Kernel crashed with opcode error at PC 0x{proc.pc:04X}: {error}")
    assert cycles > 100, (
        f"Kernel exited too early after {cycles} cycles (PC=0x{proc.pc:04X})")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
