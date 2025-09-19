#!/usr/bin/env python3
"""
FORTH Performance Benchmarker for Nova-16
Tests and measures performance improvements from optimization.

Phase 4D: Performance benchmarking and integration testing.
"""

import sys
import os
import time
import subprocess
from typing import Dict, List, Tuple, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from forth_compiler import ForthCompiler


class ForthBenchmarker:
    """
    Performance benchmarker for FORTH compilation and execution.
    Measures improvements from optimization passes.
    """

    def __init__(self):
        self.results = {}
        self.test_programs = {}
        self._create_test_programs()

    def _create_test_programs(self):
        """Create a suite of test programs for benchmarking."""
        
        # Simple arithmetic test
        self.test_programs["arithmetic"] = """
            : SQUARE DUP * ;
            : CUBE DUP SQUARE * ;
            5 SQUARE .
            3 CUBE .
        """
        
        # Stack manipulation test
        self.test_programs["stack_ops"] = """
            : TEST_STACK 
                1 2 3 DUP DROP SWAP OVER DUP DUP DROP DROP ;
            TEST_STACK
        """
        
        # Control flow test
        self.test_programs["control_flow"] = """
            : COUNTDOWN
                DUP . 1 - DUP 0 > 
                IF COUNTDOWN THEN DROP ;
            5 COUNTDOWN
        """
        
        # Variable and constant test
        self.test_programs["variables"] = """
            VARIABLE COUNTER
            42 CONSTANT ANSWER
            10 COUNTER !
            COUNTER @ .
            ANSWER .
        """
        
        # Complex computation test
        self.test_programs["complex"] = """
            : FACTORIAL
                DUP 1 > IF 
                    DUP 1 - FACTORIAL * 
                THEN ;
            : SUM-OF-SQUARES
                0 SWAP 1 + 1 DO
                    I DUP * +
                LOOP ;
            5 FACTORIAL .
            10 SUM-OF-SQUARES .
        """

    def benchmark_compilation(self, test_name: str, program: str) -> Dict[str, float]:
        """Benchmark compilation time and code size for a test program."""
        results = {}
        
        # Test unoptimized compilation
        print(f"\nBenchmarking {test_name} (unoptimized)...")
        start_time = time.time()
        compiler_unopt = ForthCompiler(enable_optimization=False)
        
        try:
            compiler_unopt.compile_program(program, f"bench_{test_name}_unopt.asm")
            unopt_time = time.time() - start_time
            unopt_size = len(compiler_unopt.assembly_lines)
            results["unoptimized_time"] = unopt_time
            results["unoptimized_size"] = unopt_size
            print(f"  Unoptimized: {unopt_time:.4f}s, {unopt_size} lines")
        except Exception as e:
            print(f"  Unoptimized compilation failed: {e}")
            results["unoptimized_time"] = float('inf')
            results["unoptimized_size"] = 0
        
        # Test optimized compilation
        print(f"Benchmarking {test_name} (optimized)...")
        start_time = time.time()
        compiler_opt = ForthCompiler(enable_optimization=True)
        
        try:
            compiler_opt.compile_program(program, f"bench_{test_name}_opt.asm")
            opt_time = time.time() - start_time
            opt_size = len(compiler_opt.assembly_lines)
            results["optimized_time"] = opt_time
            results["optimized_size"] = opt_size
            print(f"  Optimized: {opt_time:.4f}s, {opt_size} lines")
            
            # Calculate improvements
            if results["unoptimized_time"] != float('inf'):
                time_improvement = ((unopt_time - opt_time) / unopt_time) * 100
                size_improvement = ((unopt_size - opt_size) / unopt_size) * 100
                results["time_improvement"] = time_improvement
                results["size_improvement"] = size_improvement
                print(f"  Improvements: {time_improvement:.1f}% time, {size_improvement:.1f}% size")
            
        except Exception as e:
            print(f"  Optimized compilation failed: {e}")
            results["optimized_time"] = float('inf')
            results["optimized_size"] = 0
        
        return results

    def benchmark_execution(self, test_name: str) -> Dict[str, int]:
        """Benchmark execution performance of compiled programs."""
        results = {}
        
        # Test unoptimized execution
        unopt_asm = f"bench_{test_name}_unopt.asm"
        unopt_bin = f"bench_{test_name}_unopt.bin"
        
        if os.path.exists(unopt_asm):
            try:
                # Assemble unoptimized
                subprocess.run([
                    sys.executable, "../nova_assembler.py", unopt_asm
                ], capture_output=True, cwd=".")
                
                if os.path.exists(unopt_bin):
                    # Run unoptimized
                    result = subprocess.run([
                        sys.executable, "../nova.py", "--headless", unopt_bin, "--cycles", "10000"
                    ], capture_output=True, text=True, cwd=".")
                    
                    # Extract cycle count from output
                    cycles = self._extract_cycles(result.stdout)
                    results["unoptimized_cycles"] = cycles
                    print(f"  Unoptimized execution: {cycles} cycles")
                    
            except Exception as e:
                print(f"  Unoptimized execution failed: {e}")
                results["unoptimized_cycles"] = 0
        
        # Test optimized execution
        opt_asm = f"bench_{test_name}_opt.asm"
        opt_bin = f"bench_{test_name}_opt.bin"
        
        if os.path.exists(opt_asm):
            try:
                # Assemble optimized
                subprocess.run([
                    sys.executable, "../nova_assembler.py", opt_asm
                ], capture_output=True, cwd=".")
                
                if os.path.exists(opt_bin):
                    # Run optimized
                    result = subprocess.run([
                        sys.executable, "../nova.py", "--headless", opt_bin, "--cycles", "10000"
                    ], capture_output=True, text=True, cwd=".")
                    
                    # Extract cycle count from output
                    cycles = self._extract_cycles(result.stdout)
                    results["optimized_cycles"] = cycles
                    print(f"  Optimized execution: {cycles} cycles")
                    
                    # Calculate improvement
                    if "unoptimized_cycles" in results and results["unoptimized_cycles"] > 0:
                        improvement = ((results["unoptimized_cycles"] - cycles) / results["unoptimized_cycles"]) * 100
                        results["execution_improvement"] = improvement
                        print(f"  Execution improvement: {improvement:.1f}% fewer cycles")
                    
            except Exception as e:
                print(f"  Optimized execution failed: {e}")
                results["optimized_cycles"] = 0
        
        return results

    def _extract_cycles(self, output: str) -> int:
        """Extract cycle count from Nova-16 execution output."""
        for line in output.split('\n'):
            if "finished after" in line and "cycles" in line:
                try:
                    # Extract number from "Execution finished after X cycles"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "after" and i + 1 < len(parts):
                            return int(parts[i + 1])
                except (ValueError, IndexError):
                    continue
        return 0

    def run_benchmark_suite(self):
        """Run complete benchmark suite and generate report."""
        print("=== FORTH Performance Benchmark Suite ===")
        print("Phase 4D: Optimization & Integration Testing")
        print()
        
        for test_name, program in self.test_programs.items():
            print(f"Running benchmark: {test_name}")
            print("-" * 50)
            
            # Benchmark compilation
            comp_results = self.benchmark_compilation(test_name, program)
            self.results[test_name] = comp_results
            
            # Benchmark execution  
            exec_results = self.benchmark_execution(test_name)
            self.results[test_name].update(exec_results)
            
            print()
        
        # Generate summary report
        self.generate_report()

    def generate_report(self):
        """Generate comprehensive benchmark report."""
        print("=== BENCHMARK RESULTS SUMMARY ===")
        print()
        
        total_compile_improvement = 0
        total_size_improvement = 0
        total_exec_improvement = 0
        successful_tests = 0
        
        print(f"{'Test':<15} {'Comp Time':<12} {'Code Size':<12} {'Execution':<12}")
        print(f"{'Name':<15} {'Improv %':<12} {'Improv %':<12} {'Improv %':<12}")
        print("-" * 60)
        
        for test_name, results in self.results.items():
            comp_improv = results.get("time_improvement", 0)
            size_improv = results.get("size_improvement", 0)
            exec_improv = results.get("execution_improvement", 0)
            
            print(f"{test_name:<15} {comp_improv:>10.1f}% {size_improv:>10.1f}% {exec_improv:>10.1f}%")
            
            if comp_improv != 0:
                total_compile_improvement += comp_improv
                total_size_improvement += size_improv
                total_exec_improvement += exec_improv
                successful_tests += 1
        
        print("-" * 60)
        
        if successful_tests > 0:
            avg_compile = total_compile_improvement / successful_tests
            avg_size = total_size_improvement / successful_tests
            avg_exec = total_exec_improvement / successful_tests
            
            print(f"{'AVERAGE':<15} {avg_compile:>10.1f}% {avg_size:>10.1f}% {avg_exec:>10.1f}%")
        
        print()
        print("=== OPTIMIZATION EFFECTIVENESS ===")
        print(f"Tests completed: {len(self.test_programs)}")
        print(f"Successful optimizations: {successful_tests}")
        
        if successful_tests > 0:
            print(f"Average compilation speedup: {avg_compile:.1f}%")
            print(f"Average code size reduction: {avg_size:.1f}%")
            print(f"Average execution speedup: {avg_exec:.1f}%")
            
            # Overall assessment
            if avg_size > 5 or avg_exec > 5:
                print("✓ OPTIMIZATION: Significant improvements achieved")
            elif avg_size > 0 or avg_exec > 0:
                print("~ OPTIMIZATION: Modest improvements achieved")
            else:
                print("⚠ OPTIMIZATION: Limited improvements detected")
        
        print()
        print("Phase 4D Optimization & Integration: BENCHMARK COMPLETE")

    def cleanup(self):
        """Clean up temporary benchmark files."""
        patterns = ["bench_*.asm", "bench_*.bin", "bench_*.org"]
        for pattern in patterns:
            for file in Path(".").glob(pattern):
                try:
                    file.unlink()
                except:
                    pass


def main():
    """Run the benchmark suite."""
    benchmarker = ForthBenchmarker()
    
    try:
        benchmarker.run_benchmark_suite()
    finally:
        # Clean up temporary files
        benchmarker.cleanup()


if __name__ == "__main__":
    main()
