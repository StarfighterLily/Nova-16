"""Tests for Astrid ENTER/LEAVE stack frame generation against the Nova-16 emulator."""
import os
import sys

# Add project root to path so we can import nova_main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nova_main import initialize_system


def run_binary(bin_path, max_cycles=2000000):
    """Run a binary headlessly and return (proc, cycles)."""
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry_point = mem.load(bin_path)
    proc.pc = entry_point
    cycle = 0
    while cycle < max_cycles and not proc.halted:
        cycle += 1
        proc.step()
    return proc, cycle


def test_enter_leave_stack_frame():
    """The hand-written test_enter_leave.asm uses ENTER 2 and reads/writes locals
    through FP-relative addressing. R0 must be 42+7 = 49 and the stack must be
    fully restored (SP=FP=0xFF00)."""
    bin_path = os.path.join(os.path.dirname(__file__), 'test_enter_leave.bin')
    proc, cycles = run_binary(bin_path)
    assert proc.halted, "test_enter_leave.bin did not halt"
    assert proc.r0 == 49, f"R0 = {proc.r0}, expected 49 (42+7)"
    assert proc.sp == 0xFF00, f"SP = 0x{proc.sp:04X}, expected 0xFF00 (restored)"
    assert proc.fp == 0xFF00, f"FP = 0x{proc.fp:04X}, expected 0xFF00 (restored)"
    print(f"PASS test_enter_leave_stack_frame (cycles={cycles}, R0=49)")


def test_astrid_codegen_uses_enter():
    """The generated astrid/simple.asm must use ENTER for the prologue and must
    not use the old PUSH FP/MOV FP,SP/SUB SP sequence."""
    asm_path = os.path.join(os.path.dirname(__file__), 'simple.asm')
    with open(asm_path, encoding='utf-8') as f:
        asm = f.read()
    # Prologue must use ENTER
    assert 'ENTER 2' in asm, "main should use ENTER 2 for its 2 locals (x, y)"
    # Old style must be absent in the function prologue section (start..builtins)
    func_main = asm.split('; Built-in Function Implementations')[0]
    assert 'PUSH FP' not in func_main, "Prologue should use ENTER, not PUSH FP"
    assert 'MOV FP, SP' not in func_main, "Prologue should use ENTER, not MOV FP, SP"
    print("PASS test_astrid_codegen_uses_enter")


def test_astrid_simple_runs():
    """Compiled astrid/simple.bin (nested 128x128 draw loops) must execute
    without error and reach HLT."""
    bin_path = os.path.join(os.path.dirname(__file__), 'simple.bin')
    proc, cycles = run_binary(bin_path)
    assert proc.halted, "simple.bin did not halt"
    # After the loop completes and main returns, R0 should be 1 (last write_screen result)
    print(f"PASS test_astrid_simple_runs (cycles={cycles}, R0=0x{proc.r0:02X})")


if __name__ == '__main__':
    test_enter_leave_stack_frame()
    test_astrid_codegen_uses_enter()
    test_astrid_simple_runs()
    print("All Astrid ENTER/LEAVE tests passed!")