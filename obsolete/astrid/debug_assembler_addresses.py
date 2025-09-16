#!/usr/bin/env python3

import sys
sys.path.append('.')
from nova_memory import Memory

def debug_assembler_addresses():
    """Debug which assembler line generates which address"""
    memory = Memory()
    memory.load('astrid/gfxtest.bin')
    
    print("Checking the instructions around the problem area:")
    print()
    
    # The assembler says:
    # Line 51: ['0x34', '0x00', '0xC3'] - should be JMP for_header_4 (0x00C3)
    # Line 56: ['0x34', '0x00', '0x4A'] - should be JMP for_header_0 (0x004A)
    
    # But the debug shows JMP 0x004A at address 0x0057
    
    # Let's find all JMP instructions in the binary
    for addr in range(0x0000, 0x0200):
        opcode = memory.read_byte(addr)
        if opcode == 0x34:  # JMP instruction
            arg1 = memory.read_byte(addr + 1)
            arg2 = memory.read_byte(addr + 2)
            target = (arg1 << 8) | arg2
            print(f"JMP at 0x{addr:04X}: target 0x{target:04X} (bytes: 0x{arg1:02X} 0x{arg2:02X})")

if __name__ == "__main__":
    debug_assembler_addresses()
