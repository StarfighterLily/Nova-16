#!/usr/bin/env python3
"""
Integration tests for NoBASIC compiler
Tests compilation and execution of NoBASIC programs with profiling
"""

import sys
import os
import unittest
import subprocess
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from nobasic_compiler import NoBasicCompiler


class TestNoBasicIntegration(unittest.TestCase):
    """Integration tests for NoBASIC compiler"""

    def setUp(self):
        """Set up test environment"""
        self.compiler = NoBasicCompiler()
        self.test_dir = Path(__file__).parent

    def _compile_and_run(self, nobasic_code: str, test_name: str, cycles: int = 10000):
        """Helper to compile and run a NoBASIC program"""
        # Write NoBASIC source
        source_file = f"{test_name}.bas"
        with open(source_file, 'w', encoding='utf-8') as f:
            f.write(nobasic_code)

        # Compile
        asm_file = f"{test_name}.asm"
        self.compiler.compile_program(nobasic_code, asm_file)

        # Assemble
        bin_file = f"{test_name}.bin"
        assembler_path = Path(__file__).parent.parent.parent / "nova_assembler.py"
        result = subprocess.run([
            sys.executable, str(assembler_path), asm_file
        ], capture_output=True, text=True, cwd=self.test_dir)

        self.assertEqual(result.returncode, 0, f"Assembly failed: {result.stderr}")

        # Run headlessly
        emulator_path = Path(__file__).parent.parent.parent / "nova.py"
        result = subprocess.run([
            sys.executable, str(emulator_path), "--headless", bin_file, f"--cycles={cycles}"
        ], capture_output=True, text=True, cwd=self.test_dir)

        self.assertEqual(result.returncode, 0, f"Execution failed: {result.stderr}")

        return result.stdout

    def _compile_and_profile(self, nobasic_code: str, test_name: str, cycles: int = 10000):
        """Helper to compile and profile a NoBASIC program"""
        # Write NoBASIC source
        source_file = f"{test_name}.bas"
        with open(source_file, 'w', encoding='utf-8') as f:
            f.write(nobasic_code)

        # Compile
        asm_file = f"{test_name}.asm"
        self.compiler.compile_program(nobasic_code, asm_file)

        # Assemble
        bin_file = f"{test_name}.bin"
        assembler_path = Path(__file__).parent.parent.parent / "nova_assembler.py"
        result = subprocess.run([
            sys.executable, str(assembler_path), asm_file
        ], capture_output=True, text=True, cwd=self.test_dir)

        self.assertEqual(result.returncode, 0, f"Assembly failed: {result.stderr}")

        # Run with memory profiler
        profiler_path = Path(__file__).parent.parent.parent / "nova_memory_profiler.py"
        result = subprocess.run([
            sys.executable, str(profiler_path), bin_file,
            f"--cycles={cycles}", "--summary"
        ], capture_output=True, text=True, cwd=self.test_dir)

        self.assertEqual(result.returncode, 0, f"Profiling failed: {result.stderr}")

        return result.stdout

    def test_simple_disp(self):
        """Test simple Disp command"""
        nobasic_code = """
ClrHome
Disp "HELLO WORLD"
"""
        output = self._compile_and_run(nobasic_code, "test_simple_disp")
        # Check that graphics were drawn (text creates pixels on screen)
        self.assertIn("non-black pixels on screen", output)
        self.assertIn("Graphics:", output)

    def test_variable_assignment(self):
        """Test variable assignment and display"""
        nobasic_code = """
ClrHome
5→A
Disp A
"""
        output = self._compile_and_run(nobasic_code, "test_variable_assignment")
        # Check that graphics were drawn (number display creates pixels)
        self.assertIn("non-black pixels on screen", output)

    def test_arithmetic_expression(self):
        """Test arithmetic expressions"""
        nobasic_code = """
ClrHome
2+3→A
Disp A
"""
        output = self._compile_and_run(nobasic_code, "test_arithmetic_expression")
        # Check that graphics were drawn (result display creates pixels)
        self.assertIn("non-black pixels on screen", output)

    def test_for_loop(self):
        """Test For loop"""
        nobasic_code = """
ClrHome
For(I,1,5)
Disp I
End
"""
        output = self._compile_and_run(nobasic_code, "test_for_loop", cycles=50000)
        # Check that graphics were drawn (loop output creates pixels)
        self.assertIn("non-black pixels on screen", output)
        # Check that program completed successfully
        self.assertIn("Execution finished", output)

    def test_if_conditional(self):
        """Test If/Then conditional"""
        nobasic_code = """
ClrHome
5→A
If A=5
Then
Disp "TRUE"
End
"""
        output = self._compile_and_run(nobasic_code, "test_if_conditional")
        # Check that graphics were drawn (conditional output creates pixels)
        self.assertIn("non-black pixels on screen", output)

    def test_complex_program(self):
        """Test complex program with multiple features"""
        nobasic_code = """
ClrHome
10→A
For(I,1,A)
If I>5
Then
Disp I
End
End
"""
        output = self._compile_and_run(nobasic_code, "test_complex_program", cycles=100000)
        # Check that graphics were drawn (conditional loop output creates pixels)
        self.assertIn("non-black pixels on screen", output)
        # Check that program completed successfully
        self.assertIn("Execution finished", output)

    def test_memory_profiling(self):
        """Test memory profiling of compiled program"""
        nobasic_code = """
ClrHome
For(I,1,10)
I→A
End
Disp A
"""
        profile_output = self._compile_and_profile(nobasic_code, "test_memory_profiling", cycles=50000)
        # Should contain profiling information
        self.assertIn("Memory Profile", profile_output)

    def test_example_programs(self):
        """Test compilation of example programs from basic/ directory"""
        basic_dir = Path("../../basic")

        if basic_dir.exists():
            for bas_file in basic_dir.glob("*.bas"):
                with self.subTest(program=bas_file.name):
                    # Read the NoBASIC program
                    with open(bas_file, 'r') as f:
                        nobasic_code = f.read()

                    # Try to compile it
                    try:
                        asm_file = f"example_{bas_file.stem}.asm"
                        self.compiler.compile_program(nobasic_code, asm_file)

                        # Check that assembly file was created
                        self.assertTrue(Path(asm_file).exists(), f"Assembly file not created for {bas_file.name}")

                        # Try to assemble it
                        bin_file = f"example_{bas_file.stem}.bin"
                        assembler_path = Path(__file__).parent.parent.parent / "nova_assembler.py"
                        result = subprocess.run([
                            sys.executable, str(assembler_path), asm_file
                        ], capture_output=True, text=True, cwd=self.test_dir)

                        self.assertEqual(result.returncode, 0, f"Assembly failed for {bas_file.name}: {result.stderr}")

                        # Check that binary was created
                        self.assertTrue(Path(bin_file).exists(), f"Binary file not created for {bas_file.name}")

                    except Exception as e:
                        self.fail(f"Failed to compile {bas_file.name}: {e}")


if __name__ == '__main__':
    unittest.main()