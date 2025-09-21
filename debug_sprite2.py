#!/usr/bin/env python3

import sys
import os
import tempfile
sys.path.append(os.path.dirname(__file__))

from nova_cpu import CPU
from nova_memory import Memory
from nova_gfx import GFX
from nova_assembler import Assembler

def debug_sprite_layering():
    """Debug sprite layering with background."""

    # Create components
    memory = Memory()
    graphics = GFX()
    cpu = CPU(memory, graphics, None, None)
    assembler = Assembler()

    program = """
    ORG 0x1000

    ; Set up background layer 1
    MOV VM, 0          ; Coordinate mode
    MOV VL, 1          ; Background layer 1
    MOV VX, 40
    MOV VY, 40
    MOV R0, 50
    SWRITE R0          ; Write background pixel

    ; Set up sprite on layer 5
    MOV [0xF000], 0x2000     ; Sprite data address
    MOV [0xF002], 38         ; X position
    MOV [0xF003], 38         ; Y position
    MOV [0xF004], 4          ; Width
    MOV [0xF005], 4          ; Height
    MOV [0xF006], 0x01       ; Active flag

    ; Fill sprite data
    MOV [0x2000], 150
    MOV [0x2001], 150
    MOV [0x2002], 150
    MOV [0x2003], 150
    MOV [0x2004], 150
    MOV [0x2005], 150
    MOV [0x2006], 150
    MOV [0x2007], 150
    MOV [0x2008], 150
    MOV [0x2009], 150
    MOV [0x200A], 150
    MOV [0x200B], 150
    MOV [0x200C], 150
    MOV [0x200D], 150
    MOV [0x200E], 150
    MOV [0x200F], 150

    ; Render sprites
    SPBLITALL

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

        # Run the program
        while not cpu.halted:
            cpu.step()

        print("=== DEBUG INFO ===")
        print("Sprite control block 0:")
        for i in range(16):
            addr = 0xF000 + i
            val = memory.read_byte(addr)
            print(f"  0x{addr:04X}: 0x{val:02X}")

        print("\nSprite data at 0x2000:")
        for i in range(16):
            addr = 0x2000 + i
            val = memory.read_byte(addr)
            print(f"  0x{addr:04X}: 0x{val:02X}")

        sprite = graphics.get_sprite_control_block(0, memory)
        print(f"\nParsed sprite 0: {sprite}")

        print("=== LAYER DEBUG ===")
        print("Background layer 1 around (40,40):")
        print(graphics.background_layers[0][38:43, 38:43])

        print("\nSprite layer 5 around (38,38):")
        print(graphics.sprite_layers[0][36:43, 36:43])

        # Composite and check
        graphics.composite_layers()
        print("\nFinal screen around (38,38):")
        print(graphics.screen[36:43, 36:43])

        print(f"\nSpecific checks:")
        print(f"Background at (40,40): {graphics.screen[40, 40]}")
        print(f"Sprite at (38,38): {graphics.screen[38, 38]}")

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
    debug_sprite_layering()