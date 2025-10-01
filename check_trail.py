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
entry_point = mem.load('NoBASIC\\test_struct_trail.bin')
cpu.pc = entry_point

print(f"Running test_struct_trail.bin...")

# Run until halt or max cycles
for i in range(50000):
    cpu.step()
    if cpu.halted:
        break

print(f"\nCompleted in {i+1} cycles")
print(f"Final Ball.x (0x0120): {mem.read_word(0x0120)}")
print(f"Final Ball.y (0x0122): {mem.read_word(0x0122)}")
print(f"Final Ball.vx (0x0124): {mem.read_word(0x0124)}")
print(f"Final Ball.vy (0x0126): {mem.read_word(0x0126)}")

# Count pixels on each layer
for layer in range(5):
    pixel_count = 0
    for x in range(256):
        for y in range(256):
            # Check if pixel is non-zero on this layer
            pixel_val = gfx.layers[layer][y * 256 + x]
            if pixel_val != 0:
                pixel_count += 1
    print(f"Layer {layer}: {pixel_count} non-black pixels")

# Show some specific pixels
print(f"\nSample pixels on layer 0:")
print(f"  (50, 50): {gfx.layers[0][50 * 256 + 50]}")
print(f"  (53, 52): {gfx.layers[0][52 * 256 + 53]}")
print(f"  (56, 54): {gfx.layers[0][54 * 256 + 56]}")
print(f"  (100, 100): {gfx.layers[0][100 * 256 + 100]}")
