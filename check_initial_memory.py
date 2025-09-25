import sys
sys.path.append('.')
from nova_memory import Memory

memory = Memory()
memory.load_with_org_info('simple_string_test.bin', 'simple_string_test.org')

print('String at 0x4000:')
for i in range(12):
    addr = 0x4000 + i
    val = memory.read_byte(addr)
    char = chr(val) if val != 0 else '(null)'
    print(f'  0x{addr:04X}: 0x{val:02X} {char}')

print()
print('Memory at 0x6000 (before execution):')
for i in range(10):
    addr = 0x6000 + i
    val = memory.read_byte(addr)
    print(f'  0x{addr:04X}: 0x{val:02X}')