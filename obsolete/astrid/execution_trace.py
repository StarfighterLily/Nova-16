#!/usr/bin/env python3
"""
Comprehensive execution trace tool for verifying function calls
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nova_cpu import CPU
from nova_memory import Memory
from nova_gfx import GFX
from nova_keyboard import NovaKeyboard
from nova_sound import NovaSound

def trace_execution(binary_file, max_cycles=1000):
    """Trace execution step by step to verify function calls"""
    
    print("="*80)
    print("NOVA-16 EXECUTION TRACE")
    print("="*80)
    
    # Initialize system
    memory = Memory()
    gfx = GFX()  # GFX doesn't take memory parameter
    keyboard = NovaKeyboard()
    sound = NovaSound()
    cpu = CPU(memory, gfx, keyboard, sound)
    
    # Load program
    try:
        with open(binary_file, 'rb') as f:
            data = f.read()
        
        # Load ORG information if available
        org_file = binary_file.replace('.bin', '.org')
        if os.path.exists(org_file):
            print(f"Loading ORG information from {org_file}")
            memory.load_with_org_info(binary_file, org_file)
        else:
            print(f"Loading {binary_file} at address 0x0000")
            for i, byte in enumerate(data):
                memory.write(i, byte)
        
        print(f"Program loaded: {len(data)} bytes")
        print(f"Initial PC: 0x{cpu.pc:04X}")
        
    except FileNotFoundError:
        print(f"Error: File {binary_file} not found")
        return
    
    # Track function calls
    function_calls = []
    call_stack = []
    cycle_count = 0
    
    print("\nExecution trace:")
    print("-" * 40)
    
    try:
        while cycle_count < max_cycles and not cpu.halted:
            pc_before = cpu.pc
            instruction = memory.read(cpu.pc)
            
            # Decode instruction to check for CALL/RET
            if instruction == 0x69:  # CALL instruction
                addr = memory.read(cpu.pc + 1) | (memory.read(cpu.pc + 2) << 8)
                function_calls.append((cycle_count, pc_before, addr))
                call_stack.append(pc_before)
                print(f"Cycle {cycle_count:5d}: PC=0x{pc_before:04X} CALL 0x{addr:04X}")
            elif instruction == 0x6A:  # RET instruction  
                if call_stack:
                    call_pc = call_stack.pop()
                    print(f"Cycle {cycle_count:5d}: PC=0x{pc_before:04X} RET (returning to caller at 0x{call_pc:04X})")
                else:
                    print(f"Cycle {cycle_count:5d}: PC=0x{pc_before:04X} RET (stack empty)")
            elif instruction == 0x00:  # HLT
                print(f"Cycle {cycle_count:5d}: PC=0x{pc_before:04X} HLT")
                break
            
            # Step one instruction
            cpu.step()
            cycle_count += 1
            
            # Check for significant changes
            if cycle_count % 100 == 0:
                print(f"Cycle {cycle_count:5d}: PC=0x{cpu.pc:04X} (continuing...)")
                
    except Exception as e:
        print(f"Execution error at cycle {cycle_count}: {e}")
    
    print(f"\nExecution completed after {cycle_count} cycles")
    print(f"Final PC: 0x{cpu.pc:04X}")
    print(f"CPU Halted: {cpu.halted}")
    
    # Analyze function calls
    print(f"\nFunction call analysis:")
    print(f"Total function calls: {len(function_calls)}")
    
    for i, (cycle, pc, addr) in enumerate(function_calls):
        print(f"  Call {i+1}: Cycle {cycle}, from 0x{pc:04X} to 0x{int(addr):04X}")
    
    # Graphics analysis
    pixel_count = 0
    layer_counts = {}
    
    for layer in range(9):
        count = 0
        for y in range(256):
            for x in range(256):
                pixel = gfx.get_pixel(layer, x, y)
                if pixel != 0:
                    count += 1
                    pixel_count += 1
        if count > 0:
            layer_counts[layer] = count
    
    print(f"\nGraphics analysis:")
    print(f"Total pixels drawn: {pixel_count}")
    print(f"Layer pixel counts: {layer_counts}")
    
    return {
        'cycle_count': cycle_count,
        'function_calls': function_calls,
        'pixel_count': pixel_count,
        'layer_counts': layer_counts
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python execution_trace.py <binary_file>")
        sys.exit(1)
    
    trace_execution(sys.argv[1], max_cycles=50000)
