#!/usr/bin/env python3

import sys
sys.path.append('.')
from nova_cpu import CPU
from nova_memory import Memory
from nova_gfx import GFX
from nova_keyboard import NovaKeyboard
from nova_sound import NovaSound

def debug_stuck_execution():
    """Debug why execution gets stuck at PC 0x0004"""
    memory = Memory()
    graphics = GFX()
    keyboard = NovaKeyboard()
    sound = NovaSound()
    cpu = CPU(memory, graphics, keyboard, sound)
    
    # Load the gfxtest.bin program
    memory.load('astrid/gfxtest.bin')
    print("Program loaded")
    
    # Execute step by step for the first 50 instructions
    prev_pc = None
    stuck_count = 0
    
    for step in range(1000):
        current_pc = cpu.pc
        
        # Check if PC is stuck
        if current_pc == prev_pc:
            stuck_count += 1
            if stuck_count > 3:
                print(f"\n*** PC STUCK at 0x{current_pc:04X} for {stuck_count} consecutive steps ***")
                break
        else:
            stuck_count = 0
        
        if step < 50 or (step % 100 == 0):
            print(f"\nStep {step+1}: PC=0x{current_pc:04X}")
            
            # Show the instruction
            try:
                opcode = memory.read_byte(current_pc)
                arg1 = memory.read_byte(current_pc + 1) if current_pc + 1 < 0x10000 else 0
                arg2 = memory.read_byte(current_pc + 2) if current_pc + 2 < 0x10000 else 0
                arg3 = memory.read_byte(current_pc + 3) if current_pc + 3 < 0x10000 else 0
                print(f"    Instruction: 0x{opcode:02X} 0x{arg1:02X} 0x{arg2:02X} 0x{arg3:02X}")
            except:
                print("    Could not read instruction")
            
            # Show key registers
            print(f"    SP: 0x{cpu.sp:04X}, FP: 0x{cpu.fp:04X}")
            print(f"    R0: 0x{cpu.r0:02X}, R1: 0x{cpu.r1:02X}")
        
        prev_pc = current_pc
        
        try:
            cpu.step()
            if step < 10:
                print(f"    After step: PC=0x{cpu.pc:04X}")
        except Exception as e:
            print(f"    ERROR during step: {e}")
            break
    
    print(f"\nFinal state:")
    print(f"PC: 0x{cpu.pc:04X}")
    print(f"SP: 0x{cpu.sp:04X}, FP: 0x{cpu.fp:04X}")
    print(f"Stuck count: {stuck_count}")

if __name__ == "__main__":
    debug_stuck_execution()
