#!/usr/bin/env python3
"""
CPU Profiling Script for Nova-16 Emulator

This script provides various profiling options for analyzing CPU performance:
- Built-in CPU profiling (instruction counts, timing)
- cProfile integration
- Memory profiling
- Custom benchmarks

Usage:
    python cpu_profiler.py [options] <program.bin>

Options:
    --enable-cpu-profile    Enable built-in CPU profiling
    --cprofile             Use Python's cProfile
    --memory-profile       Profile memory usage
    --benchmark            Run performance benchmarks
    --cycles <n>           Run for n cycles then stop
    --report               Generate detailed profiling report
"""

import sys
import time
import cProfile
import pstats
import io
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

import nova_cpu as cpu
import nova_memory as mem
import nova_gfx as gpu
import nova_sound as sound
import nova_keyboard as kbd

class CPUProfiler:
    def __init__(self):
        self.cpu = None
        self.memory = None
        self.gfx = None
        self.keyboard = None
        self.sound = None

    def setup_system(self, program_path=None):
        """Initialize the Nova-16 system"""
        self.memory = mem.Memory()
        self.gfx = gpu.GFX()
        self.keyboard = kbd.NovaKeyboard()
        self.sound = sound.NovaSound()
        self.cpu = cpu.CPU(self.memory, self.gfx, self.keyboard, self.sound)

        if program_path:
            entry_point = self.memory.load(program_path)
            self.cpu.pc = entry_point
            print(f"Loaded {program_path}, entry point: 0x{entry_point:04X}")

    def run_with_builtin_profiling(self, max_cycles=10000):
        """Run CPU with built-in profiling"""
        print("Starting CPU with built-in profiling...")
        self.cpu.enable_profiling()

        start_time = time.time()
        cycles = 0

        try:
            while not self.cpu.halted and cycles < max_cycles:
                self.cpu.step()
                cycles += 1

                if cycles % 1000 == 0:
                    print(f"Executed {cycles} cycles...")

        except KeyboardInterrupt:
            print("\nProfiling interrupted by user")

        end_time = time.time()
        total_time = end_time - start_time

        print(f"\nExecution completed:")
        print(f"- Total cycles: {cycles}")
        print(f"- Total time: {total_time:.4f} seconds")
        print(f"- Average CPS: {cycles / total_time:.2f}")
        print(f"- Average IPS: {self.cpu.profile_data['instructions_executed'] / total_time:.2f}")

        print("\n" + self.cpu.get_profile_report())

    def run_with_cprofile(self, max_cycles=10000):
        """Run CPU with cProfile"""
        print("Starting CPU with cProfile...")

        pr = cProfile.Profile()
        pr.enable()

        cycles = 0
        try:
            while not self.cpu.halted and cycles < max_cycles:
                self.cpu.step()
                cycles += 1

                if cycles % 1000 == 0:
                    print(f"Executed {cycles} cycles...")

        except KeyboardInterrupt:
            print("\nProfiling interrupted by user")

        pr.disable()

        # Print profile results
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats(20)  # Top 20 functions
        print(s.getvalue())

    def benchmark_instruction_set(self):
        """Benchmark different types of instructions"""
        print("Running instruction set benchmarks...")

        # Test program with various instruction types
        benchmark_program = [
            0x06, 0x04, 0xE7, 0x00,  # MOV R0, 0     ; Load immediate
            0x06, 0x04, 0xE8, 0x01,  # MOV R1, 1     ; Load immediate
            0x08, 0x00, 0xE7, 0xE8,  # ADD R0, R1    ; Register arithmetic
            0x0A, 0x00, 0xE7, 0xE8,  # SUB R0, R1    ; Register arithmetic
            0x10, 0x00, 0xE7, 0xE8,  # AND R0, R1    ; Logical
            0x11, 0x00, 0xE7, 0xE8,  # OR R0, R1     ; Logical
            0x12, 0x00, 0xE7, 0xE8,  # XOR R0, R1    ; Logical
            0x06, 0x08, 0xF1, 0x00, 0x20,  # MOV [0x2000], R0  ; Memory write
            0x07, 0x08, 0xF1, 0x00, 0x20,  # MOV R0, [0x2000]  ; Memory read
            0x00  # HLT
        ]

        # Load benchmark program
        for i, byte in enumerate(benchmark_program):
            self.memory.write_byte(i, byte)

        self.cpu.pc = 0

        print("Benchmarking instruction execution...")
        self.cpu.enable_profiling()

        start_time = time.time()
        cycles = 0

        while not self.cpu.halted and cycles < 1000:
            self.cpu.step()
            cycles += 1

        end_time = time.time()
        total_time = end_time - start_time

        print(f"Benchmark completed in {total_time:.6f} seconds")
        print(f"Average time per instruction: {total_time / self.cpu.profile_data['instructions_executed'] * 1000000:.2f} μs")
        print(f"Instructions per second: {self.cpu.profile_data['instructions_executed'] / total_time:.2f}")

    def profile_memory_access_patterns(self):
        """Profile different memory access patterns"""
        print("Profiling memory access patterns...")

        # Create a program that accesses memory in different patterns
        memory_test_program = [
            # Sequential access
            0x06, 0x08, 0xF0, 0x00, 0x10,  # MOV R0, [0x1000]
            0x06, 0x08, 0xF0, 0x01, 0x10,  # MOV R0, [0x1001]
            0x06, 0x08, 0xF0, 0x02, 0x10,  # MOV R0, [0x1002]

            # Random access
            0x06, 0x08, 0xF0, 0x00, 0x20,  # MOV R0, [0x2000]
            0x06, 0x08, 0xF0, 0xFF, 0x2F,  # MOV R0, [0x2FFF]
            0x06, 0x08, 0xF0, 0x80, 0x15,  # MOV R0, [0x1580]

            # Stack operations
            0x1A,  # PUSH R0
            0x1B,  # POP R0

            0x00  # HLT
        ]

        # Load test program
        for i, byte in enumerate(memory_test_program):
            self.memory.write_byte(i, byte)

        self.cpu.pc = 0

        self.cpu.enable_profiling()
        start_time = time.time()

        while not self.cpu.halted:
            self.cpu.step()

        end_time = time.time()
        total_time = end_time - start_time

        print(f"Memory access profiling completed:")
        print(f"- Total memory accesses: {self.cpu.profile_data['memory_accesses']}")
        print(f"- Time: {total_time:.6f} seconds")
        print(f"- Accesses per second: {self.cpu.profile_data['memory_accesses'] / total_time:.2f}")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    profiler = CPUProfiler()

    # Parse command line arguments
    args = sys.argv[1:]
    program_path = None
    enable_cpu_profile = False
    use_cprofile = False
    memory_profile = False
    benchmark = False
    max_cycles = 10000

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '--enable-cpu-profile':
            enable_cpu_profile = True
        elif arg == '--cprofile':
            use_cprofile = True
        elif arg == '--memory-profile':
            memory_profile = True
        elif arg == '--benchmark':
            benchmark = True
        elif arg == '--cycles' and i + 1 < len(args):
            max_cycles = int(args[i + 1])
            i += 1
        elif not arg.startswith('--'):
            program_path = arg
        i += 1

    # Setup system
    profiler.setup_system(program_path)

    if benchmark:
        profiler.benchmark_instruction_set()
    elif memory_profile:
        profiler.profile_memory_access_patterns()
    elif use_cprofile:
        profiler.run_with_cprofile(max_cycles)
    elif enable_cpu_profile:
        profiler.run_with_builtin_profiling(max_cycles)
    else:
        print("Please specify a profiling option:")
        print("  --enable-cpu-profile    Use built-in CPU profiling")
        print("  --cprofile             Use Python's cProfile")
        print("  --memory-profile       Profile memory access patterns")
        print("  --benchmark           Run instruction benchmarks")

if __name__ == "__main__":
    main()