#!/usr/bin/env python3
"""
Quick memory dump utility to verify MEMREAD/MEMWRITE
"""
import sys
sys.path.insert(0, 'c:\\Code\\Nova')

from nova.memory import Memory

# Load the binary
memory = Memory()
memory.load('NoBASIC/tests/memtest_simple.bin')

# Check the values at the addresses we wrote to
print("Memory verification after running memtest_simple.bin:")
print(f"0x2000 (should be 42): {memory.read(0x2000)}")
print(f"0x2002 (should be 100): {memory.read(0x2002)}")
print(f"0x3000 (should be 123): {memory.read(0x3000)}")
