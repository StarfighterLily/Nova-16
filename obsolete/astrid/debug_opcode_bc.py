#!/usr/bin/env python3

from nova_cpu import CPU
from nova_memory import Memory
from nova_gfx import GFX
from nova_keyboard import NovaKeyboard  
from nova_sound import NovaSound

def debug_execution():
    # Load the problematic binary
    memory = Memory()
    gfx = GFX()
    keyboard = NovaKeyboard()
    sound = NovaSound()
    cpu = CPU(memory, gfx, keyboard, sound)
    
    # Load the binary
    with open('astrid/test_function_calls_comprehensive.bin', 'rb') as f:
        data = f.read()
        for i, byte in enumerate(data):
            memory.write_byte(i, byte)
    
    print(f"Loaded {len(data)} bytes")
    
    # Execute step by step
    for cycle in range(30):
        print(f"\nCycle {cycle}: PC=0x{cpu.pc:04X}")
        
        # Show memory at PC
        opcode = memory.read_byte(cpu.pc)
        arg1 = memory.read_byte(cpu.pc + 1) if cpu.pc + 1 < len(data) else 0
        arg2 = memory.read_byte(cpu.pc + 2) if cpu.pc + 2 < len(data) else 0
        
        print(f"  Memory at PC: {opcode:02X} {arg1:02X} {arg2:02X}")
        
        if opcode == 0xBC:
            print(f"  ERROR: Found unknown opcode 0xBC at PC=0x{cpu.pc:04X}")
            print(f"  This should not happen - 0xBC is register code for FP, not an instruction")
            break
            
        try:
            cpu.step()
            print(f"  After step: PC=0x{cpu.pc:04X}")
        except Exception as e:
            print(f"  Exception: {e}")
            break
            
        if cpu.halted:
            print("  CPU halted")
            break

if __name__ == "__main__":
    debug_execution()
