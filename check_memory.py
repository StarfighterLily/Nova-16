import sys
sys.path.append('.')
from nova_memory import Memory
from nova_cpu import CPU
from nova_gfx import GFX
from nova_sound import NovaSound
from nova_keyboard import NovaKeyboard

memory = Memory()
entry_point = memory.load_with_org_info('mid_test.bin', 'mid_test.org')

# Create dummy components
gfx = GFX()
sound = NovaSound()
keyboard = NovaKeyboard(memory)

# Create CPU
cpu = CPU(memory, gfx, keyboard, sound)
cpu.pc = entry_point  # Set PC to entry point

# Run the program
cycles = 0
max_cycles = 100  # Lower limit to see where it stops
while cycles < max_cycles:
    cpu.step()
    cycles += 1
    if cpu.pc == 0x104D:  # Halt loop
        break

print(f'Executed {cycles} cycles, PC: 0x{cpu.pc:04X}')

# Check memory at 0x6000
print('Memory at 0x6000 (after execution):')
for i in range(10):
    addr = 0x6000 + i
    val = memory.read_byte(addr)
    if val == 0:
        print(f'  0x{addr:04X}: 0x{val:02X} (null)')
    else:
        char = chr(val) if 32 <= val <= 126 else '?'
        print(f'  0x{addr:04X}: 0x{val:02X} ({char})')

# Create dummy components
gfx = GFX()
sound = NovaSound()
keyboard = NovaKeyboard(memory)

# Create CPU
cpu = CPU(memory, gfx, keyboard, sound)
cpu.pc = entry_point  # Set PC to entry point

# Run the program
cycles = 0
max_cycles = 200  # Lower limit to see where it stops
while cycles < max_cycles:
    cpu.step()
    cycles += 1
    if cpu.pc == 0x1046:  # Halt loop
        break

print(f'Executed {cycles} cycles, PC: 0x{cpu.pc:04X}')

# Check memory at 0x6000
print('Memory at 0x6000 (after execution):')
for i in range(10):
    addr = 0x6000 + i
    val = memory.read_byte(addr)
    if val == 0:
        print(f'  0x{addr:04X}: 0x{val:02X} (null)')
    else:
        char = chr(val) if 32 <= val <= 126 else '?'
        print(f'  0x{addr:04X}: 0x{val:02X} ({char})')