#!/usr/bin/env python3
"""
Debug HLT behavior
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nova_cpu import CPU
from nova_memory import Memory
from nova_gfx import GFX
from nova_keyboard import NovaKeyboard
from nova_sound import NovaSound

def debug_halt():
    # Initialize system
    memory = Memory()
    gfx = GFX()
    keyboard = NovaKeyboard()
    sound = NovaSound()
    cpu = CPU(memory, gfx, keyboard, sound)
    
    # Load a simple HLT program
    # MOV SP, 0xF000; HLT
    program = [
        0x07, 0xBB, 0xF0, 0x00,  # MOV SP, 0xF000
        0x00                      # HLT
    ]
    
    for i, byte in enumerate(program):
        memory.write(i, byte)
    
    print("Testing HLT behavior:")
    print(f"Initial halted state: {cpu.halted}")
    
    # Step through instructions
    for step in range(10):
        print(f"Step {step}: PC=0x{cpu.pc:04X}, halted={cpu.halted}")
        if cpu.halted:
            print("CPU is halted, should not step further")
            break
        
        # Check what instruction we're about to execute
        opcode = int(memory.read(cpu.pc))
        print(f"  About to execute opcode: 0x{opcode:02X}")
        
        # Step one instruction
        cpu.step()
        
        print(f"  After step: PC=0x{cpu.pc:04X}, halted={cpu.halted}")
        
        # Check if timer/interrupts are affecting halted state
        print(f"  Timer enabled: {cpu.timer_enabled}")
        print(f"  Global interrupts: {cpu._flags[5]}")
        print(f"  Timer interrupt enabled: {cpu.interrupts[0] if hasattr(cpu, 'interrupts') else 'N/A'}")

if __name__ == "__main__":
    debug_halt()
