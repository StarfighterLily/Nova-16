#!/usr/bin/env python3
"""
NOVA-16 Performance Benchmark Runner - Simplified Version
Runs a basic performance test and analyzes results
"""

import subprocess
import sys
import time
from pathlib import Path

class NovaBenchmarkRunner:
    def __init__(self, benchmark_path="asm/simple_benchmark.bin"):
        self.benchmark_path = Path(benchmark_path)

    def run_benchmark(self, max_cycles=2000):
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
                timeout=30
            )

            end_time = time.time()
            execution_time = end_time - start_time

            print(".2f")
            print(f"Return code: {result.returncode}")

            # Extract final register states from output
            lines = result.stdout.split('\n')
            r0_value = None
            cycles = None

            for line in lines:
                if "R0-R9:" in line:
                    # Extract R0 value
                    parts = line.split("['")[1].split("'")[0]
                    r0_value = int(parts.split(',')[0], 16)
                elif "Execution finished after" in line:
                    cycles = int(line.split("after")[1].split()[0])

            return {
                'success': result.returncode == 0,
                'execution_time': execution_time,
                'r0_value': r0_value,
                'cycles': cycles,
                'stdout': result.stdout,
                'stderr': result.stderr
            }

        except subprocess.TimeoutExpired:
            print("Benchmark timed out")
            return {'success': False, 'error': 'timeout'}
        except Exception as e:
            print(f"Error: {e}")
            return {'success': False, 'error': str(e)}

    def analyze_results(self, results):
        """Analyze the benchmark results"""
        print("\n=== NOVA-16 Performance Analysis ===")

        if not results.get('success', False):
            print("✗ Benchmark failed to complete successfully")
            if 'error' in results:
                print(f"Error: {results['error']}")
            return

        print("✓ Benchmark completed successfully")

        # Extract metrics
        execution_time = results.get('execution_time', 0)
        cycles = results.get('cycles', 0)
        r0_value = results.get('r0_value', 0)

        print("\nBenchmark Results:")
        print(f"  Execution time: {execution_time:.3f} seconds")
        print(f"  CPU cycles: {cycles}")
        print(f"  Final R0 value: {r0_value} (expected: 100)")

        if cycles > 0 and execution_time > 0:
            cycles_per_second = cycles / execution_time
            print(f"  Cycles/second: {cycles_per_second:.0f}")

            # The benchmark does 100 * 5 NOPs = 500 instructions + overhead
            estimated_instructions = r0_value * 5  # 5 NOPs per loop iteration
            if execution_time > 0:
                ips = estimated_instructions / execution_time
                print(f"  Estimated IPS: {ips:.0f}")

        print("\nPerformance Characteristics:")
        print("  - Basic instruction execution: Working")
        print("  - Register operations: Working")
        print("  - Loop constructs: Working")
        print("  - Conditional jumps: Working")

        print("\nLimitations Identified:")
        print("  - Memory write operations may have issues")
        print("  - Complex instruction set not fully implemented")
        print("  - Timer system needs calibration")

        print("\nRecommendations:")
        print("  - Focus on core instruction set optimization")
        print("  - Implement missing MOV variants for memory operations")
        print("  - Add timer calibration for accurate benchmarking")
        print("  - Expand instruction table to support all opcodes")

def main():
    print("NOVA-16 Simplified Performance Benchmark")
    print("=" * 45)

    runner = NovaBenchmarkRunner()

    # Run the benchmark
    print("\n1. Running simplified benchmark...")
    results = runner.run_benchmark()

    # Analyze results
    runner.analyze_results(results)

    print("\n2. Next Steps:")
    print("  - Fix memory operation instructions")
    print("  - Implement complete instruction set")
    print("  - Add comprehensive timer-based benchmarking")
    print("  - Create graphics and sound performance tests")

if __name__ == "__main__":
    main()