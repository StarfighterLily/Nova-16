#!/usr/bin/env python3
"""Disassemble around builtin_screen_fill (0x11E2)."""
import sys
sys.path.insert(0, '.')

with open('astrid/starsystem/starsys.bin', 'rb') as f:
    data = f.read()

print(f"Binary size: {len(data)}")

addr = 0x11E2
offset = addr - 0x0120 + 17
print(f"builtin_screen_fill at addr 0x{addr:04X}, binary offset {offset}")
print()
print("Bytes at builtin_screen_fill:")
hex_bytes = []
for i in range(offset, min(offset + 25, len(data))):
    hex_bytes.append(f"{data[i]:02X}")
print(" ".join(hex_bytes))