#!/usr/bin/env python3
"""
Test starfield HLT issue specifically
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nova_cpu import CPU
from nova_memory import Memory
from nova_gfx import GFX
from nova_keyboard import NovaKeyboard
from nova_sound import NovaSound

def test_starfield_halt():
    # Initialize system
    memory = Memory()
    gfx = GFX()
    keyboard = NovaKeyboard()
    sound = NovaSound()
    cpu = CPU(memory, gfx, keyboard, sound)
    
    # Load the actual starfield binary
    with open('starfield.bin', 'rb') as f:
        data = f.read()
    
    for i, byte in enumerate(data):
        memory.write(i, byte)
    
    print("Testing starfield HLT issue:")
    print(f"Byte at 0x004F: 0x{data[0x004F]:02X}")
    
    # Set PC to just before HLT
    cpu.pc = 0x004C  # MOV SP, FP
    
    print(f"Starting at PC=0x{cpu.pc:04X}")
    
    # Step through the final instructions
    for step in range(10):
        if cpu.halted:
            print(f"Step {step}: CPU is halted at PC=0x{cpu.pc:04X}")
            break
            
        print(f"Step {step}: PC=0x{cpu.pc:04X}, halted={cpu.halted}")
        
        # Check what instruction we're about to execute
        opcode = int(memory.read(cpu.pc))
        print(f"  About to execute opcode: 0x{opcode:02X}")
        
        # Check for the HLT instruction specifically
        if opcode == 0x00:
            print(f"  *** HLT INSTRUCTION DETECTED ***")
            print(f"  Timer enabled: {cpu.timer_enabled}")
            print(f"  Global interrupts: {int(cpu._flags[5])}")
            if hasattr(cpu, 'interrupts'):
                print(f"  Timer interrupt enabled: {cpu.interrupts[0]}")
        
        # Step one instruction
        cpu.step()
        
        print(f"  After step: PC=0x{cpu.pc:04X}, halted={cpu.halted}")
        
        # If we just executed HLT, check why it didn't halt
        if opcode == 0x00 and not cpu.halted:
            print(f"  *** ERROR: HLT INSTRUCTION DID NOT HALT CPU! ***")
            print(f"  Checking instruction table...")
            instruction = cpu.instruction_table.get(0x00)
            if instruction:
                print(f"  HLT instruction found: {instruction}")
            else:
                print(f"  *** HLT INSTRUCTION NOT IN TABLE! ***")

if __name__ == "__main__":
    test_starfield_halt()
