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
entry_point = mem.load('NoBASIC\\test_struct_sprite_v3.bin')
cpu.pc = entry_point

print("Running sprite test with cycle-by-cycle tracking...\n")

# Run through first 3 frames
for cycle in range(5000):
    cpu.step()
    
    # Print struct values every 200 cycles
    if cycle % 200 == 0:
        x = mem.read_word(0x0120)
        y = mem.read_word(0x0122)
        vx = mem.read_word(0x0124)
        vy = mem.read_word(0x0126)
        print(f"Cycle {cycle:4d}: Sprite.x={x:3d}, Sprite.y={y:3d}, Sprite.vx={vx:2d}, Sprite.vy={vy:2d}, PC=0x{cpu.pc:04X}")
    
    if cpu.halted:
        break

print(f"\nProgram finished after {cycle} cycles")
print(f"Final Sprite.x: {mem.read_word(0x0120)}")
print(f"Final Sprite.y: {mem.read_word(0x0122)}")

# Check pixels on layer 1
pixel_count = 0
for x in range(256):
    for y in range(256):
        if gfx.layers[1][y * 256 + x] != 0:
            pixel_count += 1
            if pixel_count <= 10:  # Show first 10 pixels
                print(f"  Pixel at ({x}, {y})")

print(f"\nTotal pixels on layer 1: {pixel_count}")
