#!/usr/bin/env python3

# Debug script to test the disassembler parsing logic

import sys
sys.path.append('.')
from opcodes import opcodes

def create_reverse_maps():
    """
    Creates reverse lookup maps from the opcodes list for quick disassembly.
    """
    opcode_map = {}
    register_map = {}
    
    # A set of all register mnemonics for quick checking
    reg_mnemonics = { f"R{i}" for i in range(10) } | { f"P{i}" for i in range(10) } | { "VM", "VX", "VY" } | { "VL", "TT", "TM", "TC", "TS", "SF", "SV", "SW", "SA" }

    for mnemonic, opcode_str, size in opcodes:
        opcode_val = int( opcode_str, 16 )

        # Handle all register types (direct, indirect, indexed, high/low byte)
        if mnemonic in reg_mnemonics or mnemonic.endswith( ':' ) or mnemonic.startswith( ':' ) or mnemonic in ['SP', 'FP']:
            # Determine register type based on opcode range
            if 0xBF <= opcode_val <= 0xC8:  # R indirect
                reg_name = f"R{opcode_val - 0xBF}"
                register_map[ opcode_val ] = f"[{reg_name}]"
            elif 0xC9 <= opcode_val <= 0xD2:  # P indirect
                reg_name = f"P{opcode_val - 0xC9}"
                register_map[ opcode_val ] = f"[{reg_name}]"
            elif 0xD3 <= opcode_val <= 0xD4:  # V indirect
                reg_name = "VX" if opcode_val == 0xD3 else "VY"
                register_map[ opcode_val ] = f"[{reg_name}]"
            elif 0xE9 <= opcode_val <= 0xF2:  # R indexed
                reg_name = f"R{opcode_val - 0xE9}"
                register_map[ opcode_val ] = f"R{opcode_val - 0xE9}_indexed"
            elif 0xF3 <= opcode_val <= 0xFB:  # P indexed (P0-P8)
                reg_name = f"P{opcode_val - 0xF3}"
                register_map[ opcode_val ] = f"P{opcode_val - 0xF3}_indexed"
            elif opcode_val == 0xFC:  # FP indexed (P9)
                register_map[ opcode_val ] = "FP_indexed"
            elif 0xFD <= opcode_val <= 0xFE:  # V indexed
                reg_name = "VX" if opcode_val == 0xFD else "VY"
                register_map[ opcode_val ] = f"{reg_name}_indexed"
            elif 0xD5 <= opcode_val <= 0xDE:  # P high byte
                reg_name = f"P{opcode_val - 0xD5}"
                register_map[ opcode_val ] = f"{reg_name}:"
            elif 0xDF <= opcode_val <= 0xE8:  # P low byte
                reg_name = f"P{opcode_val - 0xDF}"
                register_map[ opcode_val ] = f":{reg_name}"
            else:
                # Direct register - use the actual mnemonic from opcodes list
                register_map[ opcode_val ] = mnemonic
        else:
            # It's a standard instruction
            opcode_map[ opcode_val ] = ( mnemonic, size )
            
    return opcode_map, register_map

# Test the specific instruction
test_bytes = bytes([0x0B, 0xFC, 0xFC, 0xA9])  # MOV [FP-4], R0
opcode_map, register_map = create_reverse_maps()

print("Testing instruction: 0B FC FC A9")
print("Opcode 0x0B mapping:", opcode_map.get(0x0B, "NOT FOUND"))
print("Register 0xFC mapping:", register_map.get(0xFC, "NOT FOUND"))
print("Register 0xA9 mapping:", register_map.get(0xA9, "NOT FOUND"))

# Check if 0x0B is in the opcode map
if 0x0B in opcode_map:
    mnemonic, size = opcode_map[0x0B]
    print(f"Found opcode 0x0B: {mnemonic}, size: {size}")
else:
    print("Opcode 0x0B not found in opcode_map!")

# Print some entries from opcode_map for reference
print("\nFirst 20 opcode_map entries:")
for i, (opcode, (mnem, sz)) in enumerate(sorted(opcode_map.items())[:20]):
    print(f"  0x{opcode:02X}: {mnem} (size {sz})")
