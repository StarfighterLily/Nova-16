import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nova_memory as mem
import nova_cpu as cpu_mod
import nova_gfx as gpu
import nova_sound as sound
import nova_keyboard as keyboard

# Create components
memory = mem.Memory()
graphics = gpu.GFX()
sound_system = sound.NovaSound()
keyboard_device = keyboard.NovaKeyboard()
cpu = cpu_mod.CPU(memory, graphics, keyboard_device, sound_system)

# Test program: MOV P0, 0; CMP P0, P0; CALLZ subroutine; HLT
# Subroutine: MOV P1, 0x1234; RET
program = [
    0x06, 0x08, 0xF1, 0x00, 0x00,  # MOV P0, 0
    0x2E, 0x00, 0xF1, 0xF1,        # CMP P0, P0
    0x9D, 0x02, 0x0E, 0x00,        # CALLZ 0x000E
    0x00,                           # HLT
    # Subroutine at 0x000C
    0x06, 0x08, 0xF2, 0x34, 0x12,  # MOV P1, 0x1234
    0x01                             # RET
]

memory.load_program(program)

print("Initial state:")
print(f"P0: {cpu.Pregisters[0]:04X}")
print(f"P1: {cpu.Pregisters[1]:04X}")
print(f"Z flag: {cpu.flags[7]}")
print(f"PC: {cpu.pc:04X}")

# Run MOV
cpu.step()
print("After MOV:")
print(f"P0: {cpu.Pregisters[0]:04X}")
print(f"P1: {cpu.Pregisters[1]:04X}")
print(f"Z flag: {cpu.flags[7]}")
print(f"PC: {cpu.pc:04X}")

# Run CMP
cpu.step()
print("After CMP:")
print(f"P0: {cpu.Pregisters[0]:04X}")
print(f"P1: {cpu.Pregisters[1]:04X}")
print(f"Z flag: {cpu.flags[7]}")
print(f"PC: {cpu.pc:04X}")

# Run CALLZ
cpu.step()
print("After CALLZ:")
print(f"P0: {cpu.Pregisters[0]:04X}")
print(f"P1: {cpu.Pregisters[1]:04X}")
print(f"Z flag: {cpu.flags[7]}")
print(f"PC: {cpu.pc:04X}")

# If called, run MOV in subroutine
if cpu.pc == 0x000E:
    cpu.step()
    print("After MOV in subroutine:")
    print(f"P0: {cpu.Pregisters[0]:04X}")
    print(f"P1: {cpu.Pregisters[1]:04X}")
    print(f"Z flag: {cpu.flags[7]}")
    print(f"PC: {cpu.pc:04X}")

    # Run RET
    cpu.step()
    print("After RET:")
    print(f"P0: {cpu.Pregisters[0]:04X}")
    print(f"P1: {cpu.Pregisters[1]:04X}")
    print(f"Z flag: {cpu.flags[7]}")
    print(f"PC: {cpu.pc:04X}")

# Run HLT
cpu.step()
print("After HLT:")
print(f"P0: {cpu.Pregisters[0]:04X}")
print(f"P1: {cpu.Pregisters[1]:04X}")
print(f"Z flag: {cpu.flags[7]}")
print(f"PC: {cpu.pc:04X}")
print(f"Halted: {cpu.halted}")