"""Diagnostic: step through simple.bin and print each PC to find where it halts."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nova_main import initialize_system

proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False)
entry_point = mem.load('astrid/simple.bin')
proc.pc = entry_point

print(f"Entry: 0x{entry_point:04X}")
for i in range(40):
    pc_before = proc.pc
    proc.step()
    print(f"cycle {i+1:2d}: PC 0x{pc_before:04X} -> 0x{proc.pc:04X} halted={proc.halted}")
    if proc.halted:
        print("HALTED")
        break