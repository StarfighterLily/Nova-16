import nova_memory as mem

m = mem.Memory()

# Simulate INT stack pushes
sp = 0xFFFF
print(f'Initial SP: {sp:04X}')

# Push PC
sp = (sp - 2) & 0xFFFF
m.write_word(sp, 0x0100)
print(f'After pushing PC: SP={sp:04X}, memory at {sp:04X}={m.read_word(sp):04X}')

# Push flags  
sp = (sp - 2) & 0xFFFF
m.write_word(sp, 0x00FF)
print(f'After pushing flags: SP={sp:04X}, memory at {sp:04X}={m.read_word(sp):04X}')

print(f'Memory layout:')
print(f'  {0xFFFB:04X}: {m.read_byte(0xFFFB):02X} {m.read_byte(0xFFFC):02X} (flags)')
print(f'  {0xFFFD:04X}: {m.read_byte(0xFFFD):02X} {m.read_byte(0xFFFE):02X} (PC)')