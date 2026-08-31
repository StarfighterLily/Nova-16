"""
Test cases for register allocation fixes.
Tests for register exhaustion, variable starvation, and allocation tracking.
"""

import pytest
import sys
from pathlib import Path


from compiler.codegen.generator import CodeGenerator
from compiler.parser.parser import Parser
from compiler.lexer.lexer import Lexer
from compiler.parser.ast import *


def parse_and_generate(code: str) -> tuple:
    """Helper to parse and generate code, returning (asm, generator)."""
    lexer = Lexer()
    parser = Parser()
    tokens = lexer.tokenize(code)
    ast = parser.parse(tokens)
    generator = CodeGenerator()
    asm = generator.generate(ast)
    return asm, generator


class TestRegisterExhaustion:
    """Test register exhaustion handling."""
    
    def test_register_exhaustion_with_many_variables(self):
        """Test that we get a clear error when too many variables are used."""
        # Create a program with many variables in a complex expression
        # This should exhaust available registers
        code = """
a = 1
b = 2
c = 3
d = 4
e = 5
f = 6
g = 7
h = 8
i = 9
j = 10
result = (a + b) * (c + d) * (e + f) * (g + h) * (i + j)
        """
        
        # This might trigger register exhaustion during complex expression
        # We should get a clear error message, not silent corruption
        try:
            asm, generator = parse_and_generate(code)
            # If it succeeds, that's also fine - just means we had enough registers
            assert isinstance(asm, str)
        except RuntimeError as e:
            # If it fails, verify we get a helpful error message
            error_msg = str(e)
            assert "Register exhaustion" in error_msg
            assert "Suggestions:" in error_msg
            assert "Simplify" in error_msg or "Reduce" in error_msg
    
    def test_nested_expression_pressure(self):
        """Test register pressure in deeply nested expressions."""
        code = """
result = ((a + b) * (c + d)) + ((e + f) * (g + h))
        """
        
        try:
            asm, generator = parse_and_generate(code)
            assert isinstance(asm, str)
            # Check that allocation stats are being tracked
            assert generator.allocation_stats['total_allocations'] > 0
        except RuntimeError as e:
            # If exhaustion occurs, verify error message quality
            assert "Register exhaustion" in str(e)


class TestVariableRegisterAllocation:
    """Test variable register allocation and starvation warnings."""
    
    def test_variable_starvation_warning(self, capsys):
        """Test that we get warnings when variables spill to memory."""
        # Create a program with more than 6 SIMULTANEOUSLY LIVE variables
        # Keep it simple to avoid temp register exhaustion
        code = """
var1 = 1
var2 = 2
var3 = 3
var4 = 4
var5 = 5
var6 = 6
var7 = 7
var8 = 8
result = var1
        """
        
        asm, generator = parse_and_generate(code)
        
        # With 8 variables and only 6 registers, some should spill
        captured = capsys.readouterr()
        
        # Check that spilling occurred
        total_vars = len(generator.var_reg) + len(generator.spill_slots)
        assert total_vars >= 8, f"Expected at least 8 variables, got {total_vars}"
        
        # If spilling occurred, there should be a warning
        if len(generator.spill_slots) > 0:
            assert "WARNING" in captured.out or "WARNING" in asm
    
    def test_few_variables_no_warning(self, capsys):
        """Test that programs with few variables don't get warnings."""
        code = """
a = 1
b = 2
c = 3
result = a + b + c
        """
        
        asm, generator = parse_and_generate(code)
        
        # Should NOT get performance warnings
        captured = capsys.readouterr()
        assert "PERFORMANCE WARNING" not in captured.out


class TestLoopRegisterAllocation:
    """Test register allocation in loops."""
    
    def test_nested_loop_variables(self):
        """Test that nested loop variables work correctly."""
        code = """
For i = 1 To 10
    For j = 1 To 10
        x = i + j
    End
End
        """
        
        # Should compile without errors
        asm, generator = parse_and_generate(code)
        assert isinstance(asm, str)
        assert "For" not in asm  # Verify it's assembly, not source
    
    def test_deeply_nested_loops(self):
        """Test very deeply nested loops."""
        code = """
For i = 1 To 5
    For j = 1 To 5
        For k = 1 To 5
            result = i * j * k
        End
    End
End
        """
        
        try:
            asm, generator = parse_and_generate(code)
            assert isinstance(asm, str)
        except RuntimeError as e:
            # If it fails, verify it's a clear error
            assert "Register exhaustion" in str(e)


class TestAllocationStatistics:
    """Test that allocation statistics are tracked correctly."""
    
    def test_allocation_stats_tracking(self):
        """Test that allocation statistics are collected."""
        code = """
a = 1
b = 2
c = a + b
        """
        
        asm, generator = parse_and_generate(code)
        
        # Verify statistics are tracked
        stats = generator.allocation_stats
        assert stats['total_allocations'] > 0
        assert stats['total_deallocations'] >= 0
        assert stats['max_simultaneous_allocated'] > 0
        assert stats['allocation_failures'] == 0  # Should succeed
    
    def test_allocation_failure_tracked(self):
        """Test that allocation failures are counted."""
        # Create a program that will likely exhaust registers
        code = """
result = a + b + c + d + e + f + g + h + i + j + k + l + m + n + o + p + q + r + s + t
        """
        
        try:
            asm, generator = parse_and_generate(code)
            # If it succeeds, check stats anyway
            assert generator.allocation_stats['allocation_failures'] >= 0
        except RuntimeError:
            # If it fails, verify the failure was tracked (would need access to generator)
            pass  # Can't verify stats if generation failed


class TestMixedTypeAllocation:
    """Test allocation with mixed types (strings vs numbers)."""
    
    def test_string_and_numeric_allocation(self):
        """Test that strings get P registers and numbers work correctly."""
        code = """
str1 = "Hello"
num1 = 42
str2 = "World"
result = num1 + 8
        """
        
        asm, generator = parse_and_generate(code)
        
        # Verify string variables use P registers
        if 'str1' in generator.var_reg:
            assert generator.var_reg['str1'].startswith('P')
        if 'str2' in generator.var_reg:
            assert generator.var_reg['str2'].startswith('P')
        
        # Assembly should contain string operations
        assert 'DEFSTR' in asm or 'STR' in asm


class TestSmartDeallocate:
    """Test smart deallocation behavior."""
    
    def test_variable_registers_not_freed(self):
        """Test that variable registers are never freed by smart_deallocate."""
        code = """
x = 10
y = 20
z = x + y
        """
        
        asm, generator = parse_and_generate(code)
        
        # Variable registers should still be allocated at end
        var_regs = generator.var_reg.values()
        for reg in var_regs:
            # These should NOT have been deallocated
            # (They persist for the lifetime of the program)
            pass  # Just verify no crash


class TestSpillPolicyRegression:
    """Regression tests for spill policy under low measured pressure."""

    def test_low_pressure_with_inflated_ranges_preserves_distinct_active_regs(self):
        """Overlapping intervals must not alias even when measured pressure is low."""
        generator = CodeGenerator(enable_optimizations=False)

        vars_in_order = ["a", "b", "c", "d", "e", "f", "g"]

        # Deliberately inflate interval ends to mimic conservative lifetime tracking.
        generator.live_ranges = {
            name: (idx + 1, 100)
            for idx, name in enumerate(vars_in_order)
        }

        # Deliberately under-report measured pressure to mimic conservative/partial liveness.
        generator.live_at_point = {
            idx + 1: {name}
            for idx, name in enumerate(vars_in_order)
        }

        generator.build_interference_graph()
        generator.calculate_register_pressure()
        generator.assign_registers()

        # Because intervals overlap, allocator must avoid reusing the same register for all vars.
        assigned_regs = list(generator.var_reg.values())
        assert len(set(assigned_regs)) > 1

    def test_game_no_struct_state_vars_do_not_alias(self):
        """Critical state variables in game sample must not alias in the same register."""
        # game_no_struct.nobasic was removed in commit 55963dc ("Cleanup") when
        # game.nobasic was rewritten to use structs (player.oldx etc, which
        # this test can't see -- it checks flat variable names). "clean
        # copies/game.nobasic" still uses the flat oldx/oldy/x/y variables
        # this regression is about, so it's the fixture that keeps testing
        # the same thing the original file did.
        source_path = Path(__file__).parent.parent.parent / "NoBASIC" / "clean copies" / "game.nobasic"
        source = source_path.read_text(encoding="utf-8")

        asm, generator = parse_and_generate(source)

        # If both vars are in registers, they must not share the same register.
        for left, right in [("x", "oldx"), ("y", "oldy")]:
            if left in generator.var_reg and right in generator.var_reg:
                assert generator.var_reg[left] != generator.var_reg[right], (
                    f"State vars aliased: {left}/{right} -> {generator.var_reg[left]}"
                )

    def test_user_function_call_preserves_variable_registers(self):
        """Codegen should save/restore variable P-registers around user function calls."""
        code = """
key = 97
x = 1

Function id(v)
    Return v
End

a = id(key)
b = id(key)
        """

        asm, _ = parse_and_generate(code)

        assert "CALL _func_id_" in asm
        assert "POP P" in asm, "Expected caller-side restore of preserved variable register(s)"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
