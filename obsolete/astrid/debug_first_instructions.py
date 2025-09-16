#!/usr/bin/env python3

import sys
sys.path.append('.')
from nova_cpu import CPU
from nova_memory import Memory
from nova_gfx import GFX
from nova_keyboard import NovaKeyboard
from nova_sound import NovaSound

def debug_first_instructions():
    """Debug the first few instructions step by step"""
    memory = Memory()
    graphics = GFX()
    keyboard = NovaKeyboard()
    sound = NovaSound()
    cpu = CPU(memory, graphics, keyboard, sound)
    
    # Load the program
    memory.load('gfxtest.bin')
    print("Program loaded")
    
    # Execute first 10 instructions with detailed debug
    for step in range(10):
        print(f"\n=== Step {step+1} ===")
        print(f"PC: 0x{cpu.pc:04X}")
        
        # Show raw bytes
        bytes_at_pc = []
        for i in range(4):
            addr = (cpu.pc + i) & 0xFFFF
            byte = memory.read_byte(addr)
            bytes_at_pc.append(f"0x{byte:02X}")
        print(f"Bytes: {' '.join(bytes_at_pc)}")
        
        # Show registers before
        print(f"Before: SP=0x{cpu.sp:04X}, FP=0x{cpu.fp:04X}, R0=0x{cpu.r0:02X}")
        
        old_pc = cpu.pc
        try:
            cpu.step()
            if cpu.pc == old_pc:
                print("ERROR: PC did not advance!")
                break
                
            print(f"After:  SP=0x{cpu.sp:04X}, FP=0x{cpu.fp:04X}, R0=0x{cpu.r0:02X}")
            print(f"New PC: 0x{cpu.pc:04X}")
            
        except Exception as e:
            print(f"ERROR: {e}")
            break

if __name__ == "__main__":
    debug_first_instructions()
