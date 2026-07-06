"""
Pytest configuration and shared fixtures for Nova-16 testing framework.
"""

import pytest
import numpy as np
import sys
import os

# Add the project root and NoBASIC folder to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NoBASIC'))

import nova_memory as mem
import nova_cpu as cpu_mod
import nova_gfx as gpu
import nova_sound as sound
import nova_keyboard as keyboard
from opcodes import opcodes as opcode_definitions


OPCODE_VALUES = {name: int(value, 16) for name, value, _ in opcode_definitions}


def pytest_configure(config):
    """Register custom markers used by the test suite."""
    config.addinivalue_line("markers", "assembler: Tests related to the assembler pipeline")


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
def bus():
    """Create a fresh event bus for testing."""
    from nova.bus.eventbus import EventBus
    return EventBus()


@pytest.fixture
def cpu_with_timer(bus, memory, graphics, keyboard_device, sound_system):
    """Create a CPU instance wired with event bus, timer, and interrupt controller."""
    from nova.bus.interrupt import InterruptController
    from nova.peripherals.timer import Timer

    intr = InterruptController(bus, cpu=None, memory=memory)
    timer = Timer(bus, interrupt_controller=intr)
    cpu = cpu_mod.CPU(
        memory, graphics, keyboard_device, sound_system,
        bus=bus, interrupt_controller=intr, timer_device=timer
    )
    intr.cpu = cpu
    intr.memory = memory
    return cpu


@pytest.fixture
def memory_with_bus(bus, graphics):
    """Create a memory instance connected to an event bus and graphics."""
    from nova.memory import Memory
    memory = Memory(bus=bus)
    # Wire graphics sprite engine to the same bus so SCB events are received
    graphics._sprites.bus = bus
    bus.subscribe('memory.scb_written', graphics._sprites._on_scb_write)
    return memory


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
    memory.memory[start_addr:start_addr + len(program_data)] = bytes(program_data)


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


def opcode_value(name):
    """Return the current opcode/register encoding for a mnemonic from opcodes.py."""
    return OPCODE_VALUES[name]
