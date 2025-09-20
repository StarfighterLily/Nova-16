#!/usr/bin/env python3
"""
Example: CPU Profiling Integration with Nova-16 GUI

This example shows how to integrate CPU profiling into the main emulator
and collect performance data during normal operation.
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def profile_cpu_during_execution():
    """Example of profiling CPU during normal GUI execution"""

    # Import after path setup
    import nova_cpu as cpu
    import nova_memory as mem
    import nova_gfx as gpu
    import nova_sound as sound
    import nova_keyboard as kbd
    import nova_gui as gui

    # Setup system
    memory = mem.Memory()
    gfx = gpu.GFX()
    keyboard = kbd.NovaKeyboard()
    sound_sys = sound.NovaSound()
    cpu_instance = cpu.CPU(memory, gfx, keyboard, sound_sys)

    # Load a test program
    try:
        entry_point = memory.load("asm/gfxtest.bin")
        cpu_instance.pc = entry_point
        print(f"Loaded test program, entry point: 0x{entry_point:04X}")
    except FileNotFoundError:
        print("Test program not found. Creating a simple test program...")

        # Create a simple test program
        test_program = [
            0x06, 0x04, 0xE7, 0x00,  # MOV R0, 0
            0x06, 0x04, 0xE8, 0x01,  # MOV R1, 1
            0x08, 0x00, 0xE7, 0xE8,  # ADD R0, R1
            0x00  # HLT
        ]

        for i, byte in enumerate(test_program):
            memory.write_byte(i, byte)
        cpu_instance.pc = 0

    # Enable CPU profiling
    cpu_instance.enable_profiling()
    print("CPU profiling enabled")

    # Run the GUI (this will start profiling automatically)
    try:
        gui.main(cpu_instance, memory, gfx, keyboard)
    except KeyboardInterrupt:
        print("\nGUI interrupted")

    # Generate profiling report
    print("\n" + "="*50)
    print("CPU PROFILING REPORT")
    print("="*50)
    print(cpu_instance.get_profile_report())

def profile_specific_cpu_methods():
    """Example of profiling specific CPU methods using decorators"""

    import nova_cpu as cpu
    import nova_memory as mem
    import nova_gfx as gpu

    # Setup system
    memory = mem.Memory()
    gfx = gpu.GFX()
    cpu_instance = cpu.CPU(memory, gfx)

    # Enable profiling
    cpu_instance.enable_profiling()

    # Example: Profile fetch_byte method specifically
    @cpu_instance.profile_method("fetch_byte_operation")
    def test_fetch_operations():
        for _ in range(1000):
            cpu_instance.fetch_byte()

    print("Profiling fetch operations...")
    test_fetch_operations()

    print("\nProfiling report for fetch operations:")
    print(cpu_instance.get_profile_report())

def benchmark_cpu_performance():
    """Run comprehensive CPU benchmarks"""

    import nova_cpu as cpu
    import nova_memory as mem
    import nova_gfx as gpu

    memory = mem.Memory()
    gfx = gpu.GFX()
    cpu_instance = cpu.CPU(memory, gfx)

    # Create benchmark program
    benchmark_code = [
        # Arithmetic operations
        0x06, 0x04, 0xE7, 0x05,  # MOV R0, 5
        0x06, 0x04, 0xE8, 0x03,  # MOV R1, 3
        0x08, 0x00, 0xE7, 0xE8,  # ADD R0, R1
        0x0A, 0x00, 0xE7, 0xE8,  # SUB R0, R1

        # Logical operations
        0x10, 0x00, 0xE7, 0xE8,  # AND R0, R1
        0x11, 0x00, 0xE7, 0xE8,  # OR R0, R1
        0x12, 0x00, 0xE7, 0xE8,  # XOR R0, R1

        # Memory operations
        0x06, 0x08, 0xF1, 0x00, 0x20,  # MOV [0x2000], R0
        0x07, 0x08, 0xF1, 0x00, 0x20,  # MOV R0, [0x2000]

        # Jump operations
        0x0E, 0x08, 0xF0, 0x00, 0x00,  # JMP 0x0000 (loop back)

        0x00  # HLT (shouldn't reach here due to loop)
    ]

    # Load benchmark
    for i, byte in enumerate(benchmark_code):
        memory.write_byte(i, byte)

    cpu_instance.pc = 0
    cpu_instance.enable_profiling()

    print("Running CPU benchmark for 10,000 cycles...")

    start_time = time.time()
    cycles = 0

    while cycles < 10000 and not cpu_instance.halted:
        cpu_instance.step()
        cycles += 1

    end_time = time.time()
    total_time = end_time - start_time

    print("\nBenchmark Results:")
    print(f"- Cycles executed: {cycles}")
    print(f"- Total time: {total_time:.4f} seconds")
    print(f"- Cycles per second: {cycles / total_time:.2f}")
    print(f"- Instructions per second: {cpu_instance.profile_data['instructions_executed'] / total_time:.2f}")
    print(f"- Memory accesses: {cpu_instance.profile_data['memory_accesses']}")

    print("\nDetailed profiling report:")
    print(cpu_instance.get_profile_report())

if __name__ == "__main__":
    print("Nova-16 CPU Profiling Examples")
    print("=" * 40)

    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "gui":
            profile_cpu_during_execution()
        elif mode == "methods":
            profile_specific_cpu_methods()
        elif mode == "benchmark":
            benchmark_cpu_performance()
        else:
            print("Usage: python cpu_profiling_example.py [gui|methods|benchmark]")
    else:
        print("Available profiling modes:")
        print("  gui       - Profile CPU during GUI execution")
        print("  methods   - Profile specific CPU methods")
        print("  benchmark - Run comprehensive CPU benchmarks")
        print("\nExample: python cpu_profiling_example.py benchmark")