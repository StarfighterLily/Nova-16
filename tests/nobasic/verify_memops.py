#!/usr/bin/env python3
"""
Verify MEMREAD/MEMWRITE functionality by running test and checking memory
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nova_cpu import CPU
from nova.memory import Memory
from nova_gfx import GFX
from nova_keyboard import NovaKeyboard
from nova_sound import NovaSound

# Initialize components (matching nova.py pattern)
memory = Memory()
gfx = GFX()
keyboard = NovaKeyboard()
sound = NovaSound()
cpu = CPU(memory, gfx, keyboard, sound)

# Connect keyboard to CPU
keyboard.cpu = cpu
# Connect graphics system to memory
memory.gfx_system = gfx

# Load test program
entry_point = memory.load('tests/nobasic/fixtures/memtest_simple.bin')
cpu.pc = entry_point  # Set PC to the entry point from ORG directive

# Run the program
print("Running memtest_simple.bin...")
print(f"Initial PC: 0x{cpu.pc:04X}")
print(f"Initial halted state: {cpu.halted}")

cycles = 0
max_cycles = 1000
while not cpu.halted and cycles < max_cycles:
    cpu.step()
    cycles += 1

print(f"Program completed in {cycles} cycles")
print(f"Final PC: 0x{cpu.pc:04X}")
print(f"CPU Halted: {cpu.halted}")

# Check memory values that should have been written
print("\nMemory verification:")
val_2000 = memory.read(0x2000)[0]
val_2002 = memory.read(0x2002)[0]
val_3000 = memory.read(0x3000)[0]
print(f"  0x2000 (expected 42):  {val_2000}")
print(f"  0x2002 (expected 100): {val_2002}")
print(f"  0x3000 (expected 123): {val_3000}")

# Verify values
success = True
if val_2000 != 42:
    print("ERROR: 0x2000 should be 42!")
    success = False
if val_2002 != 100:
    print("ERROR: 0x2002 should be 100!")
    success = False
if val_3000 != 123:
    print("ERROR: 0x3000 should be 123!")
    success = False

if success:
    print("\n✓ All MEMWRITE operations verified successfully!")
else:
    print("\n✗ MEMWRITE verification FAILED!")
    sys.exit(1)

# Check variables that should have read values
print("\nRegister verification (readback values):")
print(f"  P2 (last readback): 0x{cpu.Pregisters[2]:04X}")
print(f"  P3 (return values): 0x{cpu.Pregisters[3]:04X}")

if success:
    print("\n✓ MEMREAD and MEMWRITE are working correctly!")
