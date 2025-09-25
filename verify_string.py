import sys
sys.path.append('.')
from nova_memory import Memory
memory = Memory()
entry_point = memory.load_with_org_info('simple_string_test.bin', 'simple_string_test.org')
print('String at 0x4000:')
for i in range(12):
    addr = 0x4000 + i
    val = memory.read_byte(addr)
    if val == 0:
        print(f'  0x{addr:04X}: 0x{val:02X} (null)')
        break
    else:
        char = chr(val) if 32 <= val <= 126 else '?'
        print(f'  0x{addr:04X}: 0x{val:02X} ({char})')