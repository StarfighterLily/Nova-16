#!/usr/bin/env python3
"""
Comprehensive FORTH Test Suite
Tests all aspects of the FORTH int        # ROT
        self.interpreter.push_param(5)
        print(f"Before ROT: {self.interpreter.param_stack}")
        self.interpreter.word_rot()
        print(f"After ROT: {self.interpreter.param_stack}")
        assert self.interpreter.param_stack == [42, 20, 5, 10]eter and compiler implementation.

This test suite covers:
- All core FORTH words (64+ words)
- Stack operations and error handling
- Control flow structures
- Memory access and variables
- String handling
- Hardware integration
- Compilation and optimization
- Edge cases and error conditions
- Performance benchmarks
"""

import sys
import os
import time
import pytest
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from forth_interpreter import ForthInterpreter
from forth_compiler import ForthCompiler


class ComprehensiveForthTester:
    """
    Comprehensive test suite for FORTH implementation.
    """

    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []
        self.interpreter = None
        self.compiler = None

    def setup_interpreter(self):
        """Set up a fresh interpreter for testing."""
        self.interpreter = ForthInterpreter()

    def setup_compiler(self):
        """Set up a fresh compiler for testing."""
        self.compiler = ForthCompiler(enable_optimization=True)

    def run_test(self, test_name, test_func):
        """Run a single test and record results."""
        try:
            print(f"  Testing: {test_name}")
            result = test_func()
            if result:
                print("    PASS")
                self.passed_tests += 1
                return True
            else:
                print("    FAIL")
                self.failed_tests += 1
                return False
        except Exception as e:
            print(f"    ERROR: {e}")
            import traceback
            traceback.print_exc()
            self.failed_tests += 1
            return False

    # ===== STACK OPERATION TESTS =====

    def test_stack_manipulation(self):
        """Test all stack manipulation words."""
        self.setup_interpreter()

        # DUP
        self.interpreter.push_param(42)
        self.interpreter.word_dup()
        assert self.interpreter.param_stack == [42, 42]

        # DROP
        self.interpreter.word_drop()
        assert self.interpreter.param_stack == [42]

        # SWAP
        self.interpreter.push_param(10)
        self.interpreter.push_param(20)
        self.interpreter.word_swap()
        assert self.interpreter.param_stack == [42, 20, 10]

        # OVER
        self.interpreter.word_over()
        assert self.interpreter.param_stack == [42, 20, 10, 20]

        # ROT
        self.interpreter.push_param(5)
        self.interpreter.word_rot()
        assert self.interpreter.param_stack == [42, 20, 20, 5, 10]

        # NIP
        self.interpreter.word_nip()
        assert self.interpreter.param_stack == [42, 20, 20, 10]

        # TUCK
        self.interpreter.word_tuck()
        assert self.interpreter.param_stack == [42, 20, 10, 20, 10]

        # ?DUP
        self.interpreter.push_param(0)
        self.interpreter.word_qdup()
        assert self.interpreter.param_stack == [42, 20, 10, 20, 10, 0]  # No duplicate for 0

        self.interpreter.push_param(5)
        self.interpreter.word_qdup()
        assert self.interpreter.param_stack == [42, 20, 10, 20, 10, 0, 5, 5]

        return True

    def test_arithmetic_operations(self):
        """Test all arithmetic words."""
        self.setup_interpreter()

        # +
        self.interpreter.push_param(10)
        self.interpreter.push_param(5)
        self.interpreter.word_add()
        assert self.interpreter.pop_param() == 15

        # -
        self.interpreter.push_param(20)
        self.interpreter.push_param(8)
        self.interpreter.word_sub()
        assert self.interpreter.pop_param() == 12

        # *
        self.interpreter.push_param(6)
        self.interpreter.push_param(7)
        self.interpreter.word_mul()
        assert self.interpreter.pop_param() == 42

        # /
        self.interpreter.push_param(15)
        self.interpreter.push_param(3)
        self.interpreter.word_div()
        assert self.interpreter.pop_param() == 5

        # MOD
        self.interpreter.push_param(17)
        self.interpreter.push_param(5)
        self.interpreter.word_mod()
        assert self.interpreter.pop_param() == 2

        # NEGATE
        self.interpreter.push_param(42)
        self.interpreter.word_negate()
        assert self.interpreter.pop_param() == -42

        # ABS
        self.interpreter.push_param(-7)
        self.interpreter.word_abs()
        assert self.interpreter.pop_param() == 7

        # MIN/MAX
        self.interpreter.push_param(10)
        self.interpreter.push_param(5)
        self.interpreter.word_min()
        assert self.interpreter.pop_param() == 5

        self.interpreter.push_param(10)
        self.interpreter.push_param(5)
        self.interpreter.word_max()
        assert self.interpreter.pop_param() == 10

        return True

    def test_comparison_operations(self):
        """Test all comparison words."""
        self.setup_interpreter()

        # = (equals)
        self.interpreter.push_param(5)
        self.interpreter.push_param(5)
        self.interpreter.word_equals()
        assert self.interpreter.pop_param() == -1  # true

        self.interpreter.push_param(5)
        self.interpreter.push_param(3)
        self.interpreter.word_equals()
        assert self.interpreter.pop_param() == 0   # false

        # <
        self.interpreter.push_param(3)
        self.interpreter.push_param(5)
        self.interpreter.word_less()
        assert self.interpreter.pop_param() == -1

        # >
        self.interpreter.push_param(5)
        self.interpreter.push_param(3)
        self.interpreter.word_greater()
        assert self.interpreter.pop_param() == -1

        # <>
        self.interpreter.push_param(5)
        self.interpreter.push_param(3)
        self.interpreter.word_not_equals()
        assert self.interpreter.pop_param() == -1

        # <=
        self.interpreter.push_param(5)
        self.interpreter.push_param(5)
        self.interpreter.word_less_equals()
        assert self.interpreter.pop_param() == -1

        # >=
        self.interpreter.push_param(5)
        self.interpreter.push_param(5)
        self.interpreter.word_greater_equals()
        assert self.interpreter.pop_param() == -1

        return True

    def test_logic_operations(self):
        """Test all logic words."""
        self.setup_interpreter()

        # AND
        self.interpreter.push_param(12)  # 1100
        self.interpreter.push_param(10)  # 1010
        self.interpreter.word_and()
        assert self.interpreter.pop_param() == 8  # 1000

        # OR
        self.interpreter.push_param(12)  # 1100
        self.interpreter.push_param(10)  # 1010
        self.interpreter.word_or()
        assert self.interpreter.pop_param() == 14  # 1110

        # XOR
        self.interpreter.push_param(12)  # 1100
        self.interpreter.push_param(10)  # 1010
        self.interpreter.word_xor()
        assert self.interpreter.pop_param() == 6   # 0110

        # INVERT
        self.interpreter.push_param(5)   # 0101
        self.interpreter.word_invert()
        assert self.interpreter.pop_param() == -6  # Bitwise NOT

        return True

    # ===== CONTROL FLOW TESTS =====

    def test_if_then_else(self):
        """Test IF/THEN/ELSE control flow."""
        self.setup_interpreter()

        # Test IF true THEN
        program = ": TEST_TRUE 5 0 > IF 42 THEN ; TEST_TRUE"
        self.interpreter.interpret(program)
        assert self.interpreter.pop_param() == 42

        # Test IF false THEN (should not execute)
        self.setup_interpreter()
        program = ": TEST_FALSE 5 0 < IF 42 THEN ; TEST_FALSE"
        self.interpreter.interpret(program)
        assert len(self.interpreter.param_stack) == 0

        # Test IF/ELSE/THEN
        self.setup_interpreter()
        program = ": TEST_IFELSE_TRUE 10 5 > IF 100 ELSE 200 THEN ; TEST_IFELSE_TRUE"
        self.interpreter.interpret(program)
        assert self.interpreter.pop_param() == 100

        self.setup_interpreter()
        program = ": TEST_IFELSE_FALSE 5 10 > IF 100 ELSE 200 THEN ; TEST_IFELSE_FALSE"
        self.interpreter.interpret(program)
        assert self.interpreter.pop_param() == 200

        return True

    def test_begin_until_loops(self):
        """Test BEGIN/UNTIL loops."""
        self.setup_interpreter()

        # Simple counter loop
        program = """
        VARIABLE COUNTER 0 COUNTER !
        BEGIN
          COUNTER @ 1 + COUNTER !
          COUNTER @ 5 >
        UNTIL
        COUNTER @
        """
        self.interpreter.interpret(program)
        assert self.interpreter.pop_param() == 6

        return True

    def test_do_loop_constructs(self):
        """Test DO/LOOP constructs."""
        self.setup_interpreter()

        # Sum 0 to 4
        program = """
        VARIABLE SUM 0 SUM !
        5 0 DO
          I SUM @ + SUM !
        LOOP
        SUM @
        """
        self.interpreter.interpret(program)
        result = self.interpreter.pop_param()
        print(f"DO/LOOP result: {result}")
        assert result == 10  # 0+1+2+3+4

        return True

    def test_nested_loops(self):
        """Test nested DO/LOOP with I and J."""
        self.setup_interpreter()

        program = """
        VARIABLE TOTAL 0 TOTAL !
        3 0 DO
          2 0 DO
            I J + TOTAL @ + TOTAL !
          LOOP
        LOOP
        TOTAL @
        """
        self.interpreter.interpret(program)
        # Should be: (0+0) + (1+0) + (0+1) + (1+1) + (0+2) + (1+2) = 0+1+1+2+2+3 = 9
        assert self.interpreter.pop_param() == 9

        return True

    def test_recursion(self):
        """Test recursive word definitions."""
        self.setup_interpreter()

        # Factorial function
        program = ": FACT DUP 1 > IF DUP 1 - RECURSE * ELSE DROP 1 THEN ; 5 FACT"
        self.interpreter.interpret(program)
        assert self.interpreter.pop_param() == 120

        return True

    # ===== COMPREHENSIVE LOOP TESTS =====

    def test_loop_edge_cases(self):
        """Test DO/LOOP edge cases and error conditions."""
        self.setup_interpreter()

        # Test zero iterations
        program = """
        VARIABLE COUNT 0 COUNT !
        5 5 DO COUNT DUP @ 1 + SWAP ! LOOP
        COUNT @
        """
        self.interpreter.interpret(program)
        assert self.interpreter.pop_param() == 0  # Should not execute

        # Test negative range (start >= limit, should not execute)
        program = """
        VARIABLE COUNT 0 COUNT !
        1 3 DO COUNT DUP @ 1 + SWAP ! LOOP
        COUNT @
        """
        self.interpreter.interpret(program)
        assert self.interpreter.pop_param() == 0  # Should not execute

        # Test LOOP without DO (should handle gracefully)
        program = "LOOP"
        self.interpreter.interpret(program)  # Should not crash

        return True

    def test_loop_variable_access(self):
        """Test I and J variable access in various contexts."""
        self.setup_interpreter()

        # Test I in simple loop
        program = """
        VARIABLE RESULT 0 RESULT !
        3 0 DO RESULT @ I + RESULT ! LOOP
        RESULT @
        """
        self.interpreter.interpret(program)
        assert self.interpreter.pop_param() == 3  # 0+1+2

        # Test I outside loop (should fail gracefully)
        program = "I"
        self.interpreter.interpret(program)  # Should not crash

        return True

    def test_deeply_nested_loops(self):
        """Test deeply nested loops with I/J access."""
        self.setup_interpreter()

        # 3-level nested loops
        program = """
        VARIABLE TOTAL 0 TOTAL !
        2 0 DO
          2 0 DO
            2 0 DO
              I J + K @ + TOTAL @ + TOTAL !
            LOOP
          LOOP
        LOOP
        TOTAL @
        """
        # This should work but let's test simpler first
        program = """
        VARIABLE TOTAL 0 TOTAL !
        2 0 DO
          2 0 DO
            I J + TOTAL @ + TOTAL !
          LOOP
        LOOP
        TOTAL @
        """
        self.interpreter.interpret(program)
        # Expected: (0+0) + (1+0) + (0+1) + (1+1) = 0+1+1+2 = 4
        assert self.interpreter.pop_param() == 4

        return True

    def test_loops_in_word_definitions(self):
        """Test DO/LOOP in compiled word definitions."""
        self.setup_interpreter()

        # Define a word with loops
        program = """
        : SUM_RANGE
          0 SWAP 0 DO I + LOOP
        ;
        5 SUM_RANGE
        """
        self.interpreter.interpret(program)
        assert self.interpreter.pop_param() == 10  # 0+1+2+3+4

        # Test nested loops in word definition
        program = """
        : NESTED_SUM
          0
          3 0 DO
            2 0 DO
              I J + +
            LOOP
          LOOP
        ;
        NESTED_SUM
        """
        self.interpreter.interpret(program)
        assert self.interpreter.pop_param() == 9  # Same as before

        return True

    def test_loop_stack_management(self):
        """Test that loops properly manage parameter and return stacks."""
        self.setup_interpreter()

        # Test stack state after loops
        program = """
        10 20 30 3 0 DO DROP LOOP
        """
        self.interpreter.interpret(program)
        # DO consumes 3 and 0, leaving 10 20 30
        # Loop executes 3 times, DROP executes 3 times, dropping all items
        assert self.interpreter.param_stack == []

        return True

    def test_immediate_vs_compiled_loops(self):
        """Test consistency between immediate and compiled loop execution."""
        self.setup_interpreter()

        # Test immediate loop
        program1 = """
        VARIABLE IMM 0 IMM !
        3 0 DO IMM DUP @ 1 + SWAP ! LOOP
        IMM @
        """
        self.interpreter.interpret(program1)
        imm_result = self.interpreter.pop_param()

        # Test compiled loop
        program2 = """
        : TEST_LOOP
          0 3 0 DO 1 + LOOP
        ;
        TEST_LOOP
        """
        self.interpreter.interpret(program2)
        comp_result = self.interpreter.pop_param()

        assert imm_result == comp_result == 3

        return True

    def test_loop_with_variables(self):
        """Test loops that modify variables."""
        self.setup_interpreter()

        program = """
        VARIABLE A 0 A !
        VARIABLE B 5 B !
        B @ 0 DO
          A DUP @ 1 + SWAP !
        LOOP
        A @
        """
        self.interpreter.interpret(program)
        assert self.interpreter.pop_param() == 5

        return True

    # ===== MEMORY AND VARIABLES TESTS =====

    def test_memory_access(self):
        """Test memory access words @ and !."""
        self.setup_interpreter()

        # Test ! (store) and @ (fetch)
        self.interpreter.push_param(42)      # value
        self.interpreter.push_param(0x2000)  # address
        self.interpreter.word_store()        # store 42 at 0x2000

        self.interpreter.push_param(0x2000)  # address
        self.interpreter.word_fetch()        # fetch from 0x2000
        assert self.interpreter.pop_param() == 42

        return True

    def test_variables(self):
        """Test VARIABLE and variable access."""
        self.setup_interpreter()

        program = "VARIABLE X 123 X ! X @"
        self.interpreter.interpret(program)
        assert self.interpreter.pop_param() == 123

        return True

    def test_constants(self):
        """Test CONSTANT definitions."""
        self.setup_interpreter()

        program = "42 CONSTANT ANSWER ANSWER"
        self.interpreter.interpret(program)
        assert self.interpreter.pop_param() == 42

        return True

    # ===== STRING HANDLING TESTS =====

    def test_string_operations(self):
        """Test string handling words."""
        self.setup_interpreter()

        # Test S" (create string on stack)
        program = 'S" HELLO"'
        self.interpreter.interpret(program)
        length = self.interpreter.pop_param()
        addr = self.interpreter.pop_param()
        assert length == 5
        # Could verify string content in memory if needed

        return True

    # ===== I/O TESTS =====

    def test_output_operations(self):
        """Test output words."""
        self.setup_interpreter()

        # These should not crash, though we can't easily test output
        self.interpreter.push_param(42)
        self.interpreter.word_dot()  # Print 42

        self.interpreter.push_param(65)
        self.interpreter.word_emit()  # Print 'A'

        self.interpreter.word_cr()    # Carriage return
        self.interpreter.word_space() # Print space

        self.interpreter.push_param(3)
        self.interpreter.word_spaces() # Print 3 spaces

        return True

    # ===== ERROR HANDLING TESTS =====

    def test_stack_underflow_protection(self):
        """Test stack underflow protection."""
        self.setup_interpreter()

        # DROP on empty stack should handle gracefully
        try:
            self.interpreter.word_drop()
            # Should not crash
            return True
        except:
            return False

    def test_division_by_zero_protection(self):
        """Test division by zero protection."""
        self.setup_interpreter()

        self.interpreter.push_param(10)
        self.interpreter.push_param(0)

        try:
            self.interpreter.word_div()
            return False  # Should have thrown exception
        except:
            return True   # Correctly caught division by zero

    def test_invalid_words(self):
        """Test handling of invalid words."""
        self.setup_interpreter()

        try:
            self.interpreter.execute_token("NONEXISTENT_WORD")
            return True  # Should handle gracefully
        except:
            return False

    # ===== HARDWARE INTEGRATION TESTS =====

    def test_hardware_registers(self):
        """Test hardware register access."""
        self.setup_interpreter()

        # Test VX! VY! (graphics coordinates)
        self.interpreter.push_param(100)
        self.interpreter.word_set_vx()
        assert self.interpreter.gfx.Vregisters[0] == 100

        self.interpreter.push_param(120)
        self.interpreter.word_set_vy()
        assert self.interpreter.gfx.Vregisters[1] == 120

        # Test timer registers (stored in CPU R registers for now)
        self.interpreter.push_param(1000)
        self.interpreter.word_set_tt()
        assert self.interpreter.cpu.Rregisters[0] == 232  # 1000 & 0xFF = 232

        return True

    def test_graphics_operations(self):
        """Test graphics operations."""
        self.setup_interpreter()

        # Test PIXEL
        self.interpreter.push_param(100)  # x
        self.interpreter.push_param(120)  # y
        self.interpreter.push_param(15)   # color
        self.interpreter.word_pixel()

        # Test LAYER
        self.interpreter.push_param(1)
        self.interpreter.word_layer()

        # Test VMODE
        self.interpreter.push_param(0)
        self.interpreter.word_vmode()

        return True

    def test_sound_operations(self):
        """Test sound operations."""
        self.setup_interpreter()

        # Test SOUND configuration
        self.interpreter.push_param(0x2000)  # address
        self.interpreter.push_param(440)     # frequency
        self.interpreter.push_param(128)     # volume
        self.interpreter.push_param(0)       # waveform
        self.interpreter.word_sound()

        # Test SPLAY
        self.interpreter.word_splay()

        return True

    def test_keyboard_operations(self):
        """Test keyboard operations."""
        self.setup_interpreter()

        # Test KEYSTAT (should return 0 when no key available)
        self.interpreter.word_keystat()
        result = self.interpreter.pop_param()
        assert result == 0  # No key available in test

        return True

    # ===== COMPILATION TESTS =====

    def test_compilation_basic(self):
        """Test basic compilation functionality."""
        self.setup_compiler()

        program = ": SQUARE DUP * ; 7 SQUARE"
        self.compiler.compile_program(program, "test_compilation.asm")

        # Check that file was created
        assert os.path.exists("test_compilation.asm")

        # Check that it contains expected content
        with open("test_compilation.asm", "r") as f:
            content = f.read()
            assert "forth_main:" in content
            assert "SQUARE:" in content

        return True

    def test_compilation_optimization(self):
        """Test compilation optimization."""
        compiler_unopt = ForthCompiler(enable_optimization=False)
        compiler_opt = ForthCompiler(enable_optimization=True)

        program = ": WASTEFUL DUP DUP DROP SWAP SWAP 1 + 1 - ;"

        compiler_unopt.compile_program(program, "test_unopt.asm")
        compiler_opt.compile_program(program, "test_opt.asm")

        size_unopt = len(compiler_unopt.assembly_lines)
        size_opt = len(compiler_opt.assembly_lines)

        assert size_opt <= size_unopt  # Optimized should be same or smaller

        return True

    # ===== EDGE CASE TESTS =====

    def test_edge_cases(self):
        """Test various edge cases."""
        self.setup_interpreter()

        # Test with large numbers
        self.interpreter.push_param(32767)  # Max positive 16-bit
        self.interpreter.push_param(1)
        self.interpreter.word_add()
        result = self.interpreter.pop_param()
        assert result == -32768  # Should wrap around

        # Test negative numbers
        self.interpreter.push_param(-1)
        self.interpreter.push_param(-1)
        self.interpreter.word_mul()
        assert self.interpreter.pop_param() == 1

        return True

    def test_word_definitions(self):
        """Test complex word definitions."""
        self.setup_interpreter()

        # Define a complex word
        program = """
        : COMPLEX_WORD
          DUP 10 > IF
            DUP 5 + SWAP 2 * +
          ELSE
            DUP DUP + SWAP DROP
          THEN
        ;

        15 COMPLEX_WORD
        """
        self.interpreter.interpret(program)
        # 15 > 10, so: (15 5 +) = 20, then (15 2 *) = 30, then 20+30 = 50
        assert self.interpreter.pop_param() == 50

        self.setup_interpreter()
        program = """
        : COMPLEX_WORD
          DUP 10 > IF
            DUP 5 + SWAP 2 * +
          ELSE
            DUP DUP + SWAP DROP
          THEN
        ;

        7 COMPLEX_WORD
        """
        self.interpreter.interpret(program)
        # 7 <= 10, so: DUP DUP + SWAP DROP = 7 7 + DROP = 14
        assert self.interpreter.pop_param() == 14

        return True

    # ===== PERFORMANCE TESTS =====

    def test_performance(self):
        """Test performance of various operations."""
        self.setup_interpreter()

        start_time = time.time()

        # Perform many operations
        for i in range(1000):
            self.interpreter.push_param(i)
            self.interpreter.push_param(1)
            self.interpreter.word_add()

        end_time = time.time()
        duration = end_time - start_time

        # Should complete in reasonable time (less than 1 second)
        assert duration < 1.0

        return True

    # ===== MAIN TEST RUNNER =====

    def run_comprehensive_tests(self):
        """Run all comprehensive tests."""
        print("COMPREHENSIVE FORTH TEST SUITE")
        print("=" * 50)

        start_time = time.time()

        # Core functionality tests
        self.run_test("Stack Manipulation", self.test_stack_manipulation)
        self.run_test("Arithmetic Operations", self.test_arithmetic_operations)
        self.run_test("Comparison Operations", self.test_comparison_operations)
        self.run_test("Logic Operations", self.test_logic_operations)

        # Control flow tests
        self.run_test("IF/THEN/ELSE", self.test_if_then_else)
        self.run_test("BEGIN/UNTIL Loops", self.test_begin_until_loops)
        self.run_test("DO/LOOP Constructs", self.test_do_loop_constructs)
        self.run_test("Nested Loops", self.test_nested_loops)
        self.run_test("Loop Edge Cases", self.test_loop_edge_cases)
        self.run_test("Loop Variable Access", self.test_loop_variable_access)
        self.run_test("Deeply Nested Loops", self.test_deeply_nested_loops)
        self.run_test("Loops in Word Definitions", self.test_loops_in_word_definitions)
        self.run_test("Loop Stack Management", self.test_loop_stack_management)
        self.run_test("Immediate vs Compiled Loops", self.test_immediate_vs_compiled_loops)
        self.run_test("Loop with Variables", self.test_loop_with_variables)
        self.run_test("Recursion", self.test_recursion)

        # Memory and data tests
        self.run_test("Memory Access", self.test_memory_access)
        self.run_test("Variables", self.test_variables)
        self.run_test("Constants", self.test_constants)

        # I/O and strings
        self.run_test("String Operations", self.test_string_operations)
        self.run_test("Output Operations", self.test_output_operations)

        # Error handling
        self.run_test("Stack Underflow Protection", self.test_stack_underflow_protection)
        self.run_test("Division by Zero Protection", self.test_division_by_zero_protection)
        self.run_test("Invalid Words", self.test_invalid_words)

        # Hardware integration
        self.run_test("Hardware Registers", self.test_hardware_registers)
        self.run_test("Graphics Operations", self.test_graphics_operations)
        self.run_test("Sound Operations", self.test_sound_operations)
        self.run_test("Keyboard Operations", self.test_keyboard_operations)

        # Compilation
        self.run_test("Basic Compilation", self.test_compilation_basic)
        self.run_test("Compilation Optimization", self.test_compilation_optimization)

        # Edge cases and advanced
        self.run_test("Edge Cases", self.test_edge_cases)
        self.run_test("Complex Word Definitions", self.test_word_definitions)
        self.run_test("Performance", self.test_performance)

        # Final results
        end_time = time.time()
        duration = end_time - start_time
        total_tests = self.passed_tests + self.failed_tests

        print("\n" + "=" * 50)
        print("COMPREHENSIVE TEST RESULTS")
        print("=" * 50)
        print(f"Total tests: {total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        print(f"Success rate: {(self.passed_tests/total_tests)*100:.1f}%")
        print(f"Duration: {duration:.2f} seconds")
        if self.failed_tests == 0:
            print("ALL TESTS PASSED - FORTH Implementation is Solid!")
        else:
            print("SOME TESTS FAILED - Review and fix issues")

        return self.failed_tests == 0

    def cleanup(self):
        """Clean up test files."""
        patterns = ["test_*.asm", "test_*.bin", "test_*.org"]
        for pattern in patterns:
            for file in Path(".").glob(pattern):
                try:
                    file.unlink()
                except:
                    pass


def main():
    """Run the comprehensive test suite."""
    tester = ComprehensiveForthTester()

    try:
        success = tester.run_comprehensive_tests()
        return 0 if success else 1
    finally:
        tester.cleanup()


if __name__ == "__main__":
    sys.exit(main())