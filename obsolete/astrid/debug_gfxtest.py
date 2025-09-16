#!/usr/bin/env python3

import sys
sys.path.append('.')
from nova_cpu import CPU
from nova_memory import Memory
from nova_gfx import GFX
from nova_keyboard import NovaKeyboard
from nova_sound import NovaSound

def debug_gfxtest():
    """Debug the first few instructions of gfxtest.bin"""
    memory = Memory()
    graphics = GFX()
    keyboard = NovaKeyboard()
    sound = NovaSound()
    cpu = CPU(memory, graphics, keyboard, sound)
    
    # Load the gfxtest.bin program
    memory.load('astrid/gfxtest.bin')
    print("Program loaded")
    
    # Execute first 20 instructions with debug output
    for step in range(20):
        print(f"\n--- Step {step+1} ---")
        print(f"PC: 0x{cpu.pc:04X}")
        
        # Show the instruction bytes
        opcode = memory.read_byte(cpu.pc)
        arg1 = memory.read_byte(cpu.pc + 1) if cpu.pc + 1 < 0x10000 else 0
        arg2 = memory.read_byte(cpu.pc + 2) if cpu.pc + 2 < 0x10000 else 0
        arg3 = memory.read_byte(cpu.pc + 3) if cpu.pc + 3 < 0x10000 else 0
        print(f"Instruction: 0x{opcode:02X} 0x{arg1:02X} 0x{arg2:02X} 0x{arg3:02X}")
        
        # Show key registers
        print(f"SP: 0x{cpu.sp:04X}, FP: 0x{cpu.fp:04X}")
        print(f"R0: 0x{cpu.r0:02X}, R1: 0x{cpu.r1:02X}")
        
        try:
            old_pc = cpu.pc
            cpu.step()
            if cpu.pc == old_pc:
                print("ERROR: PC did not advance! Infinite loop detected.")
                break
        except Exception as e:
            print(f"ERROR during step: {e}")
            break
    
    print(f"\nFinal PC: 0x{cpu.pc:04X}")
    print(f"Final SP: 0x{cpu.sp:04X}, FP: 0x{cpu.fp:04X}")

if __name__ == "__main__":
    debug_gfxtest()
