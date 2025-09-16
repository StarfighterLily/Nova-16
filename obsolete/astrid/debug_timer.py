#!/usr/bin/env python3

"""
Debug script to investigate timer behavior in gfxtest.asm
"""

import nova_memory as mem
import nova_cpu as cpu_module
import nova_gfx as gfx
import nova_keyboard as keyboard
import nova_sound as sound
import struct

def debug_timer_program():
    # Initialize the system
    memory = mem.Memory()
    graphics = gfx.GFX()
    keyboard_device = keyboard.NovaKeyboard(memory)
    sound_system = sound.NovaSound()
    sound_system.set_memory_reference(memory)
    
    processor = cpu_module.CPU(memory, graphics, keyboard_device, sound_system)
    
    # Load the gfxtest.bin program
    with open("asm/gfxtest.org", "r") as f:
        org_data = f.read().strip().split('\n')
    
    with open("asm/gfxtest.bin", "rb") as f:
        program_data = f.read()
    
    # Parse ORG file and load program
    current_pos = 0
    for line in org_data:
        line = line.strip()
        if line and not line.startswith('#'):
            parts = line.split()
            addr = int(parts[0], 16)
            size = int(parts[1])
            
            # Load this section
            section_data = program_data[current_pos:current_pos + size]
            for i, byte in enumerate(section_data):
                memory.write(addr + i, byte)
            
            current_pos += size
            print(f"Loaded {size} bytes at 0x{addr:04X}")
    
    # Set starting PC
    processor.pc = 0x1000
    
    print("=== Initial State ===")
    print(f"PC: 0x{processor.pc:04X}")
    print(f"Interrupt flag: {processor.interrupt_flag}")
    
    # Run for a few cycles and monitor timer state
    for cycle in range(500):
        # Check timer state before stepping
        timer_status = processor.get_timer_status()
        
        # Print timer status every 50 cycles or when significant changes occur
        if cycle % 50 == 0 or timer_status['counter'] > 0 or timer_status['enabled']:
            print(f"\nCycle {cycle}:")
            print(f"  PC: 0x{processor.pc:04X}")
            print(f"  Timer Status: {timer_status}")
            print(f"  Interrupt flag: {processor.interrupt_flag}")
            print(f"  Timer interrupt enabled: {processor.interrupts[0]}")
            
            # Print timer registers
            print(f"  TT (counter): {processor.timer[0]}")
            print(f"  TM (modulo): {processor.timer[1]}")
            print(f"  TC (control): {processor.timer[2]:02X} (binary: {processor.timer[2]:08b})")
            print(f"  TS (speed): {processor.timer[3]}")
        
        try:
            processor.step()
        except Exception as e:
            print(f"Error at cycle {cycle}, PC 0x{processor.pc:04X}: {e}")
            break
        
        # Check if we've reached the infinite loop
        if processor.pc == 0x104D:  # LOOP2 address
            print(f"\nReached infinite loop at cycle {cycle}")
            break
    
    print("\n=== Final Timer State ===")
    final_status = processor.get_timer_status()
    print(f"Timer Status: {final_status}")

if __name__ == "__main__":
    debug_timer_program()
