"""
Pytest configuration and shared fixtures for Nova-16 testing framework.
"""

import pytest
import numpy as np
import sys
import os

# Add the project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nova_memory as mem
import nova_cpu as cpu_mod
import nova_gfx as gpu
import nova_sound as sound
import nova_keyboard as keyboard


@pytest.fixture
def memory():
    """Create a fresh memory instance for testing."""
    return mem.Memory()


@pytest.fixture
def graphics():
    """Create a fresh graphics instance for testing."""
    return gpu.GFX()


@pytest.fixture
def sound_system():
    """Create a fresh sound system instance for testing."""
    return sound.NovaSound()


@pytest.fixture
def keyboard_device():
    """Create a fresh keyboard instance for testing."""
    return keyboard.NovaKeyboard()


@pytest.fixture
def cpu(memory, graphics, keyboard_device, sound_system):
    """Create a fresh CPU instance with all components for testing."""
    return cpu_mod.CPU(memory, graphics, keyboard_device, sound_system)


@pytest.fixture
def test_program():
    """Sample test program for assembler testing."""
    return """
    ; Simple test program
    MOV R0, 42
    MOV R1, 24
    ADD R0, R1
    HLT
    """


@pytest.fixture
def assembler():
    """Create an assembler instance for testing."""
    from nova_assembler import Assembler
    return Assembler()


@pytest.fixture
def disassembler():
    """Create a disassembler instance for testing."""
    from nova_disassembler import Disassembler
    return Disassembler()


# Test utilities
def create_test_binary(instructions):
    """Helper to create binary data from instruction list for testing."""
    # This would use the assembler to create binary
    # For now, return dummy data
    return bytes([0x00] * len(instructions))


def load_program_into_memory(memory, program_data, start_addr=0x0000):
    """Load program data into memory at specified address."""
    if isinstance(program_data, str):
        program_data = program_data.encode('utf-8')
    memory.memory[start_addr:start_addr + len(program_data)] = np.frombuffer(program_data, dtype=np.uint8)


def run_cpu_cycles(cpu, cycles):
    """Run CPU for specified number of cycles."""
    for _ in range(cycles):
        if cpu.halted:
            break
        cpu.step()


def assert_memory_equals(memory, address, expected_data):
    """Assert that memory contains expected data at address."""
    actual = memory.read_bytes_direct(address, len(expected_data))
    assert actual == list(expected_data), f"Memory mismatch at 0x{address:04X}: expected {expected_data}, got {actual}"


def assert_register_equals(cpu, register, expected_value):
    """Assert that register contains expected value."""
    if register.startswith('R'):
        reg_num = int(register[1:])
        actual = cpu.Rregisters[reg_num]
    elif register.startswith('P'):
        reg_num = int(register[1:])
        actual = cpu.Pregisters[reg_num]
    else:
        raise ValueError(f"Unknown register: {register}")
    
    assert actual == expected_value, f"Register {register} mismatch: expected {expected_value}, got {actual}"