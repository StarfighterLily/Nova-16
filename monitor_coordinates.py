#!/usr/bin/env python3
"""
Monitor VX/VY values just before SWRITE to see coordinate patterns
"""

import sys
import os

# Add the parent directory to the path to import nova modules
sys.path.insert(0, os.path.dirname(__file__))

from nova_cpu import CPU
from nova_memory import Memory
from nova_gfx import GFX
from nova_keyboard import NovaKeyboard
from nova_sound import NovaSound

def monitor_graphics_coordinates():
    """Monitor VX/VY values just before SWRITE instructions."""
    
    print("=== Graphics Coordinate Monitor ===")
    
    # Create system components
    memory = Memory()
    gfx = GFX()
    keyboard = NovaKeyboard()
    sound = NovaSound()
    cpu = CPU(memory, gfx, keyboard, sound)
    
    # Load the program
    entry_point = memory.load("astrid/gfxtest_small.bin")
    cpu.pc = entry_point
    
    pixel_count = 0
    max_cycles = 10000
    
    for cycle in range(max_cycles):
        # Check if we're about to execute a SWRITE (pixel write)
        current_opcode = memory.read_byte(cpu.pc)
        if current_opcode == 0x51:  # SWRITE opcode
            pixel_count += 1
            
            # Get VX, VY values
            vx = cpu.gfx.Vregisters[0]  # VX register
            vy = cpu.gfx.Vregisters[1]  # VY register
            
            print(f"Pixel {pixel_count}: VX={vx}, VY={vy}")
            
            if pixel_count >= 30:  # Only trace first 30 pixels
                break
        
        try:
            cpu.step()
            
            if cpu.halted:
                print("CPU halted")
                break
                
        except Exception as e:
            print(f"Error at cycle {cycle}, PC 0x{cpu.pc:04X}: {e}")
            break
    
    print(f"\nTotal pixels drawn: {pixel_count}")

if __name__ == "__main__":
    monitor_graphics_coordinates()
