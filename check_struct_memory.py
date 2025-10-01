from nova_memory import Memory
from nova_cpu import CPU
from nova_gfx import GFX
from nova_keyboard import NovaKeyboard
from nova_sound import NovaSound

# Initialize system
mem = Memory()
gfx = GFX()
kbd = NovaKeyboard()
snd = NovaSound()
cpu = CPU(mem, gfx, kbd, snd)

# Connect components
kbd.cpu = cpu
mem.gfx_system = gfx

# Load program
entry_point = mem.load('NoBASIC\\test_struct_simple.bin')
cpu.pc = entry_point

print(f"Initial Point.x (0x0120): {mem.read_word(0x0120)}")
print(f"Initial Point.y (0x0122): {mem.read_word(0x0122)}")

# Run for 500 cycles
for i in range(500):
    if i < 20 or (i > 100 and i < 120) or i >= 480:
        x_val = mem.read_word(0x0120)
        print(f"Cycle {i}: Point.x = {x_val}, P2 = {cpu.Pregisters[2]}, PC = 0x{cpu.pc:04X}")
    cpu.step()
    if cpu.halted:
        break

print(f"\nAfter {i+1} cycles:")
print(f"Point.x (0x0120): {mem.read_word(0x0120)}")
print(f"Point.y (0x0122): {mem.read_word(0x0122)}")
print(f"Loop counter P2: {cpu.Pregisters[2]}")
print(f"Loop counter R0: {cpu.Rregisters[0]}")
print(f"PC: 0x{cpu.pc:04X}")

print(f"\nAfter {i+1} cycles:")
print(f"Point.x (0x0120): {mem.read_word(0x0120)}")
print(f"Point.y (0x0122): {mem.read_word(0x0122)}")
print(f"Loop counter P2: {cpu.Pregisters[2]}")
print(f"Loop counter R0: {cpu.Rregisters[0]}")
print(f"PC: 0x{cpu.pc:04X}")

# Check how many pixels are set
pixel_count = 0
for x in range(256):
    for y in range(256):
        if gfx.read_pixel(x, y, 1) != 0:  # Layer 1
            pixel_count += 1
print(f"\nTotal non-black pixels on layer 1: {pixel_count}")
