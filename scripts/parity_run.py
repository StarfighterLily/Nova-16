"""Parity harness: run a .bin under the Python Nova-16 reference and dump
the state that the Star port's tests/run_bin.exe prints.

Usage:
    py -3.13 scripts/parity_run.py <program.bin> [max_cycles]

Kept in `scripts/` (not part of the shipped emulator) so the same evidence
line can be compared byte-for-byte against run_bin.exe output when bringing
the two emulators into sync.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import nova_main as M


def main():
    bin_path = sys.argv[1]
    max_cycles = int(sys.argv[2]) if len(sys.argv) > 2 else 200000

    proc, mem, gfx, kbd, snd = M.initialize_system(enable_sound=False)
    entry = mem.load(bin_path)
    proc.pc = entry

    cycles = 0
    while cycles < max_cycles and not proc.halted:
        try:
            proc.step()
        except Exception as exc:  # noqa: BLE001 - report and stop, like run_bin
            print(f"ERROR at PC=0x{proc.pc:04X}: {exc}")
            break
        cycles += 1

    regs = [int(r) & 0xFF for r in proc.Rregisters[:10]]
    pregs = [int(p) & 0xFFFF for p in proc.Pregisters[:10]]
    print(f"cycles={cycles}")
    print(f"pc=0x{proc.pc:04X} halted={proc.halted}")
    print("R=" + " ".join(f"{r:02X}" for r in regs))
    print("P=" + " ".join(f"{p:04X}" for p in pregs))
    print(f"BANK={int(mem.current_bank)}")
    print(f"IVT[4]=0x{mem.read_word(0x0110):04X} IVT[0]=0x{mem.read_word(0x0100):04X}")


if __name__ == '__main__':
    main()
