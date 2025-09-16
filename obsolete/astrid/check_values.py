#!/usr/bin/env python3

import nova_memory
import nova_cpu, nova_gfx, nova_keyboard, nova_sound

# Load the program
mem = nova_memory.Memory()
with open('astrid/test_simple_arithmetic.bin', 'rb') as f:
    data = f.read()
    for i, byte in enumerate(data):
        mem.write(0x0000 + i, byte)

# Create components
gfx = nova_gfx.GFX()
kbd = nova_keyboard.NovaKeyboard()
snd = nova_sound.NovaSound()
cpu = nova_cpu.CPU(mem, gfx, kbd, snd)

# Execute cycles
for i in range(40):
    try:
        cpu.step()
    except Exception as e:
        print(f'Stopped at cycle {i}: {e}')
        break

# Check variables
print(f'x (0xFFE0): {mem.read(0xFFE0, 1)[0]}')
print(f'y (0xFFDC): {mem.read(0xFFDC, 1)[0]}')
print(f'sum (0xFFD8): {mem.read(0xFFD8, 1)[0]}')
print(f'product (0xFFD6): {mem.read(0xFFD6, 1)[0]}')
print(f'difference (0xFFD4): {mem.read(0xFFD4, 1)[0]}')
print(f'quotient (0xFFD2): {mem.read(0xFFD2, 1)[0]}')
