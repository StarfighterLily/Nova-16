#!/usr/bin/env python3

import sys
import os
import tempfile
sys.path.append(os.path.dirname(__file__))

from nova_cpu import CPU
from nova_memory import Memory
from nova_gfx import GFX
from nova_assembler import Assembler

def debug_sprite_setup():
    """Debug sprite control block setup and rendering"""

    # Create components
    memory = Memory()
    graphics = GFX()
    cpu = CPU(memory, graphics, None, None)
    assembler = Assembler()

    program = """
    ORG 0x1000

    ; Set up sprite 0
    MOV [0xF000], 0x2000     ; Sprite data address
    MOV [0xF002], 10         ; X position
    MOV [0xF003], 20         ; Y position
    MOV [0xF004], 4          ; Width
    MOV [0xF005], 4          ; Height
    MOV [0xF006], 0x01       ; Active flag

    ; Fill sprite 0 data (4x4 = 16 bytes)
    MOV [0x2000], 100
    MOV [0x2001], 101
    MOV [0x2002], 102
    MOV [0x2003], 103
    MOV [0x2004], 104
    MOV [0x2005], 105
    MOV [0x2006], 106
    MOV [0x2007], 107
    MOV [0x2008], 108
    MOV [0x2009], 109
    MOV [0x200A], 110
    MOV [0x200B], 111
    MOV [0x200C], 112
    MOV [0x200D], 113
    MOV [0x200E], 114
    MOV [0x200F], 115

    ; Execute SPBLITALL
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

        print("=== BEFORE EXECUTION ===")
        print("Sprite control block 0:")
        for i in range(16):
            addr = 0xF000 + i
            val = memory.read_byte(addr)
            print(f"  0x{addr:04X}: 0x{val:02X}")

        print("\nSprite data:")
        for i in range(16):
            addr = 0x2000 + i
            val = memory.read_byte(addr)
            print(f"  0x{addr:04X}: 0x{val:02X}")

        # Run the program with debug
        step_count = 0
        while not cpu.halted and step_count < 50:  # Limit steps to prevent infinite loop
            print(f"\nStep {step_count}: PC=0x{cpu.pc:04X}")
            
            # Read the opcode at current PC
            if cpu.pc < cpu.memory.size:
                opcode = cpu.memory.read_byte(cpu.pc)
                print(f"  Opcode: 0x{opcode:02X}")
            
            try:
                cpu.step()
                step_count += 1
            except Exception as e:
                print(f"Error at step {step_count}: {e}")
                break

        print("\n=== AFTER EXECUTION ===")
        print("Sprite control block 0:")
        for i in range(16):
            addr = 0xF000 + i
            val = memory.read_byte(addr)
            print(f"  0x{addr:04X}: 0x{val:02X}")

        # Check sprite parsing
        sprite = graphics.get_sprite_control_block(0, memory)
        print(f"\nParsed sprite 0: {sprite}")

        # Check sprite layers
        print(f"\nSprite layer 5 (index 0):")
        layer_data = graphics.sprite_layers[0][18:25, 8:15]  # Around sprite position
        print(layer_data)

        print(f"\nSprite layer 6 (index 1):")
        layer_data = graphics.sprite_layers[1][18:25, 8:15]  # Around sprite position
        print(layer_data)

        # Composite and check screen
        graphics.composite_layers()
        print(f"\nScreen at sprite position (20,10): {graphics.screen[20, 10]}")
        print(f"Screen area around sprite:")
        print(graphics.screen[18:25, 8:15])

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
    debug_sprite_setup()