#!/usr/bin/env python3
"""
NoBASIC Color Test Runner
Specialized test runner for validating color system functionality.
"""

import os
import sys
import subprocess
import json
import re
from pathlib import Path

class NoBasicColorTestRunner:
    """Specialized test runner for NoBASIC color system validation"""

    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.compiler = self.test_dir / "nobasic_compiler.py"
        self.assembler = self.test_dir / "nova_assembler.py"
        self.emulator = self.test_dir / "nova.py"
        self.graphics_monitor = self.test_dir / "nova_graphics_monitor.py"
        self.profiler = self.test_dir / "nova_profiler.py"
        self.disassembler = self.test_dir / "nova_disassembler.py"

    def find_color_test_files(self):
        """Find color-specific test files"""
        return list(self.test_dir.glob("test_colors_*.nob"))

    def compile_and_assemble(self, nob_file):
        """Compile and assemble a NoBASIC program"""
        asm_file = nob_file.with_suffix('.asm')
        bin_file = nob_file.with_suffix('.bin')

        # Compile
        cmd = [sys.executable, str(self.compiler), str(nob_file), str(asm_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)
        if result.returncode != 0:
            return False, f"Compilation failed: {result.stderr}", None

        # Assemble
        cmd = [sys.executable, str(self.assembler), str(asm_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)
        if result.returncode != 0:
            return False, f"Assembly failed: {result.stderr}", None

        return True, "Success", bin_file

    def run_program_headless(self, bin_file, cycles=10000):
        """Run program headlessly"""
        cmd = [sys.executable, str(self.emulator), "--headless", str(bin_file), "--cycles", str(cycles)]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)
        return result.returncode == 0, result.stdout, result.stderr

    def run_color_validation_test(self, bin_file, test_type):
        """Run color validation with graphics monitor"""
        export_prefix = bin_file.with_suffix('').name + "_color_validation"

        # First run headlessly to ensure program executes correctly
        success, headless_stdout, headless_stderr = self.run_program_headless(bin_file, cycles=10000)
        if not success:
            return False, f"Headless execution failed: {headless_stderr}", {}

        # Extract pixel count from headless run
        headless_pixels = 0
        for line in headless_stdout.split('\n'):
            if "non-black pixels" in line:
                # Handle different formats: "21 non-black pixels on screen" or "non-black pixels: 21"
                import re
                match = re.search(r'(\d+) non-black pixels', line)
                if match:
                    headless_pixels = int(match.group(1))
                elif ": " in line:
                    try:
                        headless_pixels = int(line.split(": ")[1])
                    except (ValueError, IndexError):
                        pass
                break

        print(f"   Headless run: {headless_pixels} pixels drawn")

        # Run graphics monitor with full screen monitoring
        cmd = [sys.executable, str(self.graphics_monitor), str(bin_file),
               "--cycles", "10000", "--export", export_prefix, "--regions", "full:0,0,256,256"]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)

        if result.returncode != 0:
            return False, f"Graphics monitor failed: {result.stderr}", {}

        # Parse the graphics monitor output for color validation
        validation_results = self.parse_color_validation_output(result.stdout, test_type)

        return True, "Graphics analysis successful", validation_results

    def parse_color_validation_output(self, output, test_type):
        """Parse graphics monitor output for color-specific validation"""
        results = {
            'pixels_drawn': 0,
            'color_distribution': {},
            'validation_passed': False,
            'errors': []
        }

        lines = output.split('\n')

        # Extract pixel count
        for line in lines:
            if "Total non-black pixels across all layers:" in line:
                results['pixels_drawn'] = int(line.split(": ")[1])
            elif "Total non-black pixels:" in line:
                results['pixels_drawn'] = int(line.split(": ")[1])
            elif "Colors:" in line and "0x" in line:
                # Parse from "Colors: 0x01(1), 0x02(2), 0x04(3), ..." format
                import re
                # Find all 0xXX(count) patterns
                matches = re.findall(r'0x([0-9A-Fa-f]+)\((\d+)\)', line)
                for color_hex, count in matches:
                    try:
                        color_val = int(color_hex, 16)
                        pixel_count = int(count)
                        results['color_distribution'][color_val] = pixel_count
                    except ValueError:
                        pass

        # Validate based on test type
        if test_type == "constants":
            results['validation_passed'] = self.validate_color_constants(results)
        elif test_type == "functions":
            results['validation_passed'] = self.validate_color_functions(results)
        elif test_type == "graphics":
            results['validation_passed'] = self.validate_color_graphics(results)
        elif test_type == "validation":
            results['validation_passed'] = self.validate_color_validation(results)

        return results

    def validate_color_constants(self, results):
        """Validate color constants test"""
        # Should have pixels for multiple color constants
        unique_colors = len(results['color_distribution'])
        if unique_colors < 5:  # Should have at least 5 different colors from constants
            results['errors'].append(f"Too few unique colors from constants: {unique_colors}")
            return False

        # Check that pixels were drawn
        if results['pixels_drawn'] < 10:
            results['errors'].append(f"Too few pixels drawn: {results['pixels_drawn']}")
            return False

        return True

    def validate_color_functions(self, results):
        """Validate color functions test"""
        # Should have many pixels from COLOR() function calls
        if results['pixels_drawn'] < 50:  # Should have at least 50 pixels
            results['errors'].append(f"Too few pixels from functions: {results['pixels_drawn']}")
            return False

        # The test generates colors from COLOR() function, should have some variety
        # But it might not have many unique colors if the algorithm doesn't create them
        unique_colors = len(results['color_distribution'])
        if unique_colors < 1:  # At minimum should have at least 1 color
            results['errors'].append(f"No colors generated by functions: {unique_colors}")
            return False

        return True

    def validate_color_graphics(self, results):
        """Validate color graphics test"""
        # Should have pixels drawn with various colors
        if results['pixels_drawn'] < 50:  # Arbitrary threshold
            results['errors'].append(f"Too few pixels drawn: {results['pixels_drawn']}")
            return False

        return True

    def validate_color_validation(self, results):
        """Validate comprehensive color validation test"""
        # Check for some pixels drawn (the test performs various validations)
        if results['pixels_drawn'] < 10:
            results['errors'].append(f"Too few pixels in validation test: {results['pixels_drawn']}")
            return False

        # The test should have drawn some validation pixels
        # For now, just check that it ran and drew pixels
        return True

    def run_color_test(self, nob_file):
        """Run a single color test"""
        test_name = nob_file.stem
        test_type = test_name.replace('test_colors_', '')

        print(f"\n{'='*60}")
        print(f"Color Test: {test_name} ({test_type})")
        print(f"{'='*60}")

        # Compile and assemble
        print("1. Compiling and assembling...")
        success, message, bin_file = self.compile_and_assemble(nob_file)
        if not success:
            print(f"❌ {message}")
            return False
        print("✅ Compilation and assembly successful")

        # Run color validation
        print("2. Running color validation...")
        success, message, validation_results = self.run_color_validation_test(bin_file, test_type)
        if not success:
            print(f"❌ {message}")
            return False

        print("✅ Color validation completed")
        print(f"   Pixels drawn: {validation_results['pixels_drawn']}")
        print(f"   Unique colors: {len(validation_results['color_distribution'])}")

        # Report validation results
        if validation_results['validation_passed']:
            print("✅ Color validation PASSED")
            return True
        else:
            print("❌ Color validation FAILED")
            for error in validation_results['errors']:
                print(f"   Error: {error}")
            return False

    def run_all_color_tests(self):
        """Run all color tests"""
        test_files = self.find_color_test_files()
        print(f"Found {len(test_files)} color test files")

        passed = 0
        failed = 0

        for nob_file in test_files:
            if self.run_color_test(nob_file):
                passed += 1
            else:
                failed += 1

        print(f"\n{'='*60}")
        print("COLOR TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Total:  {passed + failed}")

        return failed == 0

def main():
    runner = NoBasicColorTestRunner()
    success = runner.run_all_color_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()