#!/usr/bin/env python3
"""
NoBASIC Test Runner
Automatically compiles and tests NoBASIC programs using available tools.
"""

import os
import sys
import subprocess
import glob
from pathlib import Path

class NoBasicTestRunner:
    """Test runner for NoBASIC programs"""

    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.compiler = self.test_dir / "nobasic_compiler.py"
        self.assembler = self.test_dir / "nova_assembler.py"
        self.emulator = self.test_dir / "nova.py"
        self.graphics_monitor = self.test_dir / "nova_graphics_monitor.py"
        self.profiler = self.test_dir / "nova_profiler.py"
        self.disassembler = self.test_dir / "nova_disassembler.py"

    def find_test_files(self):
        """Find all .nob test files"""
        return list(self.test_dir.glob("test_*.nob"))

    def compile_program(self, nob_file):
        """Compile a NoBASIC program to assembly"""
        asm_file = nob_file.with_suffix('.asm')
        cmd = [sys.executable, str(self.compiler), str(nob_file), str(asm_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)
        return result.returncode == 0, result.stdout, result.stderr

    def assemble_program(self, asm_file):
        """Assemble assembly to binary"""
        cmd = [sys.executable, str(self.assembler), str(asm_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)
        return result.returncode == 0, result.stdout, result.stderr

    def run_program_headless(self, bin_file, cycles=10000):
        """Run program headlessly"""
        cmd = [sys.executable, str(self.emulator), "--headless", str(bin_file), "--cycles", str(cycles)]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)
        return result.returncode == 0, result.stdout, result.stderr

    def run_graphics_monitor(self, bin_file, cycles=10000):
        """Run graphics monitor on program"""
        export_prefix = bin_file.with_suffix('').name + "_monitor"
        cmd = [sys.executable, str(self.graphics_monitor), str(bin_file),
               "--cycles", str(cycles), "--export", export_prefix]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)
        return result.returncode == 0, result.stdout, result.stderr

    def run_profiler(self, bin_file, cycles=10000):
        """Profile program execution"""
        cmd = [sys.executable, str(self.profiler), "run", str(bin_file), "--cpu-profile", "--cycles", str(cycles)]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)
        return result.returncode == 0, result.stdout, result.stderr

    def run_disassembler(self, bin_file, cycles=10000):
        """Run disassembler on program"""
        cmd = [sys.executable, str(self.disassembler), str(bin_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)
        return result.returncode == 0, result.stdout, result.stderr

    def test_program(self, nob_file):
        """Test a single NoBASIC program"""
        print(f"\n{'='*60}")
        print(f"Testing: {nob_file.name}")
        print(f"{'='*60}")

        # Compile
        print("1. Compiling...")
        success, stdout, stderr = self.compile_program(nob_file)
        if not success:
            print(f"❌ Compilation failed: {stderr}")
            return False
        print("✅ Compilation successful")

        # Assemble
        asm_file = nob_file.with_suffix('.asm')
        print("2. Assembling...")
        success, stdout, stderr = self.assemble_program(asm_file)
        if not success:
            print(f"❌ Assembly failed: {stderr}")
            return False
        print("✅ Assembly successful")

        # Run headlessly
        bin_file = nob_file.with_suffix('.bin')
        print("3. Running headlessly...")
        success, stdout, stderr = self.run_program_headless(bin_file)
        if not success:
            print(f"❌ Execution failed: {stderr}")
            return False
        print("✅ Execution successful")

        # Extract final PC and cycle count
        lines = stdout.split('\n')
        final_pc = None
        cycles = None
        for line in lines:
            if "Final PC:" in line:
                final_pc = line.split(": ")[1]
            elif "Execution finished after" in line:
                cycles = line.split(" ")[3]

        print(f"   Final PC: {final_pc}, Cycles: {cycles}")

        # Run comprehensive analysis
        analysis_results = self.run_comprehensive_analysis(bin_file, nob_file)

        return True

    def run_comprehensive_analysis(self, bin_file, nob_file):
        """Run comprehensive analysis using all available tools"""
        analysis_results = {}

        # Run graphics monitor
        print("4. Running graphics monitor...")
        success, stdout, stderr = self.run_graphics_monitor(bin_file)
        if success:
            print("✅ Graphics monitor successful")
            # Extract pixel count
            lines = stdout.split('\n')
            for line in lines:
                if "Total non-black pixels" in line:
                    pixels = line.split(": ")[1]
                    analysis_results['pixels_drawn'] = pixels
                    print(f"   Graphics: {pixels} pixels drawn")
                    break
        else:
            print(f"❌ Graphics monitor failed: {stderr}")

        # Run profiler
        print("5. Running CPU profiler...")
        success, stdout, stderr = self.run_profiler(bin_file)
        if success:
            print("✅ CPU profiler successful")
            # Could extract more detailed metrics here
        else:
            print(f"❌ CPU profiler failed: {stderr}")

        # Run disassembler for code analysis
        print("6. Running disassembler...")
        success, stdout, stderr = self.run_disassembler(bin_file)
        if success:
            print("✅ Disassembler successful")
            # Count instructions
            lines = stdout.split('\n')
            code_lines = [line for line in lines if line.strip() and not line.startswith(';') and not line.startswith('ORG')]
            analysis_results['instruction_count'] = len(code_lines)
            print(f"   Instructions: {len(code_lines)}")
        else:
            print(f"❌ Disassembler failed: {stderr}")

        return analysis_results

    def run_all_tests(self):
        """Run all NoBASIC tests"""
        test_files = self.find_test_files()
        print(f"Found {len(test_files)} test files")

        passed = 0
        failed = 0

        for nob_file in test_files:
            if self.test_program(nob_file):
                passed += 1
            else:
                failed += 1

        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Total:  {passed + failed}")

        return failed == 0

def main():
    runner = NoBasicTestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()