"""Diagnostic: trace the Astrid NovaDOS kernel's final execution steps.

WHY: the kernel halts at 0x0181 instead of the entry stub's HLT at 0x100E.
This script steps the CPU and prints the PC/SP/FP trace for the last stretch
plus the scheduler globals, so we can see WHICH return address went bad.

Run: py -3.13 astrid/NovaDOS/build/diag_kernel.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

from nova_main import initialize_system

_HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(_HERE, "kernel.bin")
SYM = os.path.join(_HERE, "kernel.sym")


def load_syms():
    syms = {}
    with open(SYM) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                syms[parts[0].lower()] = int(parts[1], 16)
    return syms


def main():
    syms = load_syms()
    demo_hits = syms.get("gvar_demo_hits")
    print(f"func_main      = 0x{syms.get('func_main', 0):04X}")
    print(f"func_demo_task = 0x{syms.get('func_demo_task', 0):04X}")
    print(f"func_timer_isr = 0x{syms.get('func_timer_isr', 0):04X}")
    print(f"gvar_demo_hits = 0x{demo_hits:04X}")

    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
    entry = mem.load(BIN)
    proc.pc = entry
    print(f"entry = 0x{entry:04X}")

    trace = []
    n = 0
    while n < 300000 and not proc.halted:
        proc.step()
        n += 1
        trace.append((n, proc.pc, proc.sp, proc.fp))
        if len(trace) > 120:
            trace.pop(0)

    print(f"\nsteps = {n}, halted = {proc.halted}, final PC = 0x{proc.pc:04X}")
    print(f"SP = 0x{proc.sp:04X}  FP = 0x{proc.fp:04X}")
    print(f"demo_hits = {mem.read_word(demo_hits) if demo_hits else '?'}")
    print("\nlast 40 steps (step, PC, SP, FP):")
    for step, pc, sp, fp in trace[-40:]:
        print(f"  {step:6d}  PC=0x{pc:04X}  SP=0x{sp:04X}  FP=0x{fp:04X}")


if __name__ == "__main__":
    main()