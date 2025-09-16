#!/usr/bin/env python3
"""
NOVA-16 Performance Benchmark Runner
Runs the performance benchmark and analyzes result        print("\\n{label} (0x{start:04X}-0x{end:04X}):")
"""

import subprocess
import sys
import os
import time
from pathlib import Path

class NovaBenchmarkRunner:
    def __init__(self, benchmark_path="asm/performance_benchmark.bin"):
        self.benchmark_path = Path(benchmark_path)
        self.results = {}

    def run_benchmark(self, max_cycles=50000):
        """Run the benchmark in headless mode"""
        cmd = [
            "python", "nova.py",
            "--headless",
            str(self.benchmark_path),
            "--cycles", str(max_cycles)
        ]

        print(f"Running benchmark: {' '.join(cmd)}")
        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )

            end_time = time.time()
            execution_time = end_time - start_time

            print(f"Benchmark completed in {execution_time:.2f} seconds")
            print(f"Return code: {result.returncode}")
            if result.stdout:
                print("STDOUT:", result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            print("Benchmark timed out after 30 seconds")
            return False
        except Exception as e:
            print(f"Error running benchmark: {e}")
            return False

    def extract_results_from_memory(self):
        """Extract benchmark results from memory dump"""
        # For now, we'll need to modify the emulator to dump memory
        # or create a custom version that outputs results
        print("Note: Memory extraction requires emulator modification")
        print("Results would be extracted from addresses 0x2000-0x2020")

        # Placeholder for result extraction
        self.results = {
            'memory_throughput': 'Timer value from 0x2000',
            'memory_latency': 'Timer value from 0x2004',
            'ips': 'Timer value from 0x2008',
            'alu_ops': 'Timer value from 0x200C',
            'stack_ops': 'Timer value from 0x2010',
            'branch_ops': 'Timer value from 0x2014',
            'graphics_ops': 'Timer value from 0x2018',
            'timer_accuracy': 'Timer value from 0x201C'
        }

    def analyze_results(self):
        """Analyze the benchmark results"""
        print("\n=== NOVA-16 Performance Analysis ===")

        # Test parameters
        test_size = 0x1000  # 4096 bytes
        loop_count = 0x1000  # 4096 iterations

        print(f"Test Parameters:")
        print(f"  Memory test size: {test_size} bytes")
        print(f"  Loop iterations: {loop_count}")
        print(f"  Timer speed: 1 (base unit)")

        print("\nRaw Results:")
        for key, value in self.results.items():
            print(f"  {key}: {value}")

        print("\nPerformance Estimates:")
        print("  Note: Actual calculations require timer calibration")
        print("  Memory Throughput: ~X bytes/second")
        print("  Memory Latency: ~X cycles/access")
        print("  Instructions/Second: ~X IPS")
        print("  ALU Operations/Second: ~X ops/sec")
        print("  Stack Operations/Second: ~X ops/sec")
        print("  Branch Operations/Second: ~X ops/sec")
        print("  Graphics Operations/Second: ~X ops/sec")

    def create_memory_dump_emulator(self):
        """Create a modified emulator that dumps memory after execution"""
        print("Creating memory dump version of emulator...")

        # Read the original emulator
        with open("nova.py", "r") as f:
            emulator_code = f.read()

        # Create a modified version that dumps memory
        dump_code = '''
# Memory dump after execution
def dump_memory_range(memory, start, end, label):
    print(f"\\n{label} (0x{start:04X}-0x{end:04X}):")
    for addr in range(start, end, 2):
        if addr + 1 < end:
            value = (memory[addr] << 8) | memory[addr + 1]
            print(f"  0x{addr:04X}: 0x{value:04X}")

# After main loop
dump_memory_range(memory.data, 0x2000, 0x2020, "BENCHMARK RESULTS")
'''

        # Insert the dump code before the final print statements
        modified_code = emulator_code.replace(
            "print(f\"Final PC: 0x{proc.pc:04X}\")",
            dump_code + "\\nprint(f\"Final PC: 0x{proc.pc:04X}\")"
        )

        with open("nova_memory_dump.py", "w") as f:
            f.write(modified_code)

        print("Created nova_memory_dump.py")

    def run_with_memory_dump(self, max_cycles=50000):
        """Run benchmark with memory dumping"""
        if not Path("nova_memory_dump.py").exists():
            self.create_memory_dump_emulator()

        cmd = [
            "python", "nova_memory_dump.py",
            "--headless",
            str(self.benchmark_path),
            "--cycles", str(max_cycles)
        ]

        print(f"Running benchmark with memory dump: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                timeout=60
            )

            print("Memory dump output:")
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            print("Benchmark timed out")
            return False
        except Exception as e:
            print(f"Error: {e}")
            return False

def main():
    print("NOVA-16 Performance Benchmark Runner")
    print("=" * 40)

    runner = NovaBenchmarkRunner()

    # First, try running normally
    print("\\n1. Running benchmark...")
    success = runner.run_benchmark()

    if success:
        print("✓ Benchmark completed successfully")
    else:
        print("✗ Benchmark failed or timed out")

    # Try with memory dump
    print("\\n2. Running with memory dump...")
    success = runner.run_with_memory_dump()

    if success:
        print("✓ Memory dump completed")
    else:
        print("✗ Memory dump failed")

    # Analyze results
    runner.extract_results_from_memory()
    runner.analyze_results()

    print("\\n3. Recommendations:")
    print("  - Analyze timer calibration for accurate measurements")
    print("  - Compare results across different emulator versions")
    print("  - Identify performance bottlenecks")
    print("  - Optimize critical code paths")

if __name__ == "__main__":
    main()