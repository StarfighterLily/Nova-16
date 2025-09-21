#!/usr/bin/env python3

import sys
import os
import tempfile
sys.path.append(os.path.dirname(__file__))

from nova_cpu import CPU
from nova_memory import Memory
from nova_gfx import GFX
from nova_assembler import Assembler

def debug_memory_writes():
    """Debug memory write operations."""

    # Create components
    memory = Memory()
    graphics = GFX()
    cpu = CPU(memory, graphics, None, None)
    assembler = Assembler()

    program = """
    ORG 0x1000

    ; Test different MOV operations
    MOV [0x2000], 100        ; 8-bit immediate
    MOV [0x2100], 200        ; 16-bit immediate
    MOV [0x2200], 300        ; 16-bit immediate

    HLT
    """

    # Write program to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.asm', delete=False) as f:
        f.write(program)
        temp_file = f.name

    try:
        # Assemble the program
        success = assembler.assemble(temp_file)
        if not success:
            print("Assembly failed")
            return

        # Load the binary into memory
        bin_file = temp_file.replace('.asm', '.bin')
        entry_point = memory.load(bin_file)
        cpu.pc = entry_point if entry_point != 0 else 0x1000

        print("=== BEFORE EXECUTION ===")
        print("Memory at test addresses:")
        for addr in [0x2000, 0x2100, 0x2200]:
            val = memory.read_byte(addr)
            print(f"  0x{addr:04X}: 0x{val:02X}")

        # Run the program
        while not cpu.halted:
            cpu.step()

        print("\n=== AFTER EXECUTION ===")
        print("Memory at test addresses:")
        for addr in [0x2000, 0x2100, 0x2200]:
            val = memory.read_byte(addr)
            print(f"  0x{addr:04X}: 0x{val:02X}")

        # Also check if word writes worked
        print("\nWord reads:")
        for addr in [0x2000, 0x2100, 0x2200]:
            val = memory.read_word(addr)
            print(f"  0x{addr:04X}: 0x{val:04X}")

    finally:
        # Clean up temp files
        try:
            os.unlink(temp_file)
            os.unlink(temp_file.replace('.asm', '.bin'))
            os.unlink(temp_file.replace('.asm', '.org'))
            os.unlink(temp_file.replace('.asm', '.sym'))
        except:
            pass

if __name__ == "__main__":
    debug_memory_writes()