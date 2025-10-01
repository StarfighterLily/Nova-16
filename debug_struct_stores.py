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
entry = mem.load('NoBASIC\\test_struct_trail.bin')
cpu.pc = entry

print("Tracing struct updates in first loop iteration:\n")

# Run until initialization is done (30 cycles)
for i in range(30):
    cpu.step()

print(f"After init (30 cycles):")
print(f"  Ball.x={mem.read_word(0x0120)}, Ball.y={mem.read_word(0x0122)}")
print(f"  Ball.vx={mem.read_word(0x0124)}, Ball.vy={mem.read_word(0x0126)}")
print(f"  P0={cpu.Pregisters[0]}, P1={cpu.Pregisters[1]}, P2={cpu.Pregisters[2]}")
print(f"  PC=0x{cpu.pc:04X}\n")

# Now step through watching for the problematic load
print("Tracing loads from Ball.x:\n")
for i in range(100):
    old_pc = cpu.pc
    old_p0 = cpu.Pregisters[0]
    old_r3 = cpu.Rregisters[3]
    
    # Check if P0 points to Ball.x
    if old_p0 == 288:
        word_val = mem.read_word(288)
        byte_val = mem.read_byte(288)
        print(f"Cycle {30+i}: PC=0x{old_pc:04X}, P0=288")
        print(f"  Memory[288] as word: {word_val}, as byte: {byte_val}")
        print(f"  R3 before: {old_r3}")
    
    cpu.step()
    
    new_r3 = cpu.Rregisters[3]
    
    # Show R3 after if it changed and P0 was 288
    if old_p0 == 288 and new_r3 != old_r3:
        print(f"  R3 after: {new_r3}\n")
    
    #Stop after first few iterations
    if i > 50:
        break

print(f"\nAfter 130 cycles total:")
print(f"  Ball.x={mem.read_word(0x0120)}, Ball.y={mem.read_word(0x0122)}")
print(f"  P2 (loop counter)={cpu.Pregisters[2]}")
