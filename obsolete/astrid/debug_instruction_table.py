#!/usr/bin/env python3
"""
Debug instruction mapping to find what 0x05 maps to
"""

import sys
import os

# Add the parent directory to the path to import nova modules
sys.path.insert(0, os.path.dirname(__file__))

from instructions import create_instruction_table

def debug_instruction_table():
    """Debug the instruction table to see what 0x05 maps to."""
    
    print("=== Debugging Instruction Table ===")
    
    table = create_instruction_table()
    
    # Check what 0x05 maps to
    instr_05 = table.get(0x05)
    print(f"Opcode 0x05 maps to: {instr_05}")
    
    # Show instructions around 0x05
    print("\nInstructions around 0x05:")
    for opcode in range(0x00, 0x10):
        instr = table.get(opcode)
        if instr:
            print(f"  0x{opcode:02X}: {instr.name} ({instr.__class__.__name__})")
        else:
            print(f"  0x{opcode:02X}: <undefined>")
    
    print(f"\nTotal instructions defined: {len(table)}")
    
    # Look for MOV-like instructions
    print("\nLooking for MOV-like instructions:")
    for opcode, instr in table.items():
        if 'mov' in instr.name.lower() or 'Mov' in instr.__class__.__name__:
            print(f"  0x{opcode:02X}: {instr.name} ({instr.__class__.__name__})")

if __name__ == "__main__":
    debug_instruction_table()
