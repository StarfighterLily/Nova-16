#!/usr/bin/env python3
"""Debug the disassembler opcode mapping"""

from nova_disassembler import create_reverse_maps
from opcodes import opcodes

def debug_opcodes():
    """Debug how opcodes are being mapped"""
    
    opcode_map, register_map = create_reverse_maps()
    
    print("Opcode map for JMP instructions:")
    for opcode, (mnemonic, size) in opcode_map.items():
        if "JMP" in mnemonic:
            print(f"  0x{opcode:02X}: {mnemonic} (size: {size})")
    
    print("\nOpcode 0x34 details:")
    if 0x34 in opcode_map:
        print(f"  Mapped to: {opcode_map[0x34]}")
    else:
        print("  Not found in opcode_map!")
    
    print("\nAll opcodes starting with JMP in original list:")
    for mnemonic, opcode_str, size in opcodes:
        if "JMP" in mnemonic:
            opcode_val = int(opcode_str, 16)
            print(f"  {mnemonic}: {opcode_str} (0x{opcode_val:02X}) size={size}")

if __name__ == "__main__":
    debug_opcodes()
