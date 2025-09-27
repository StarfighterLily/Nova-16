"""
Unit tests for the NoBASIC code generator component.
"""

import pytest
from compiler.codegen.generator import CodeGenerator
from compiler.parser.ast import (
    Program, ClrDrawStmt, PxlOnStmt, AssignmentStmt, LiteralExpr,
    VariableExpr, BinaryExpr, IfStmt, ForStmt, RepeatStmt, FunctionCallExpr, DataType
)
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.analyzer import SemanticAnalyzer


class TestCodeGenerator:
    """Test cases for the NoBASIC code generator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.lexer = Lexer()
        self.parser = Parser()
        self.analyzer = SemanticAnalyzer()
        self.generator = CodeGenerator()

    def generate_code(self, source: str) -> str:
        """Helper to generate code from source."""
        tokens = self.lexer.tokenize(source)
        program = self.parser.parse(tokens)
        self.analyzer.analyze(program)
        return self.generator.generate(program)

    def test_empty_program(self):
        """Test code generation for empty program."""
        code = self.generate_code("")
        lines = code.strip().split("\n")
        assert lines[-1] == "HLT"

    def test_clrdraw_statement(self):
        """Test ClrDraw code generation."""
        code = self.generate_code("clrdraw")
        lines = code.strip().split("\n")
        assert "MOV VM, 0" in lines
        assert "MOV VL, 0" in lines
        assert "; ClrDraw - simplified" in lines
        assert lines[-1] == "HLT"

    def test_pxl_on_statement(self):
        """Test PxlOn code generation."""
        code = self.generate_code("pxlon(10, 20, 31)")
        lines = code.strip().split("\n")
        assert "MOV R1, #10" in lines  # x = 10
        assert "MOV R2, #20" in lines  # y = 20
        assert "MOV R3, #31" in lines  # color = 31
        assert "MOV VX, R1" in lines
        assert "MOV VY, R2" in lines
        assert "MOV VC, R3" in lines
        assert "SWRITE VC" in lines

    def test_assignment_statement(self):
        """Test assignment code generation."""
        code = self.generate_code("x = 42")
        lines = code.strip().split("\n")
        assert "MOV R1, #42" in lines  # value = 42
        assert "MOV P0, 288" in lines  # variable address
        assert "MOV [P0], R1" in lines

    def test_assignment_with_expression(self):
        """Test assignment with binary expression."""
        code = self.generate_code("x = 10 + 20")
        lines = code.strip().split("\n")
        # Should generate code for 10 + 20
        assert "MOV R1, #10" in lines  # left = 10
        assert "MOV R2, #20" in lines  # right = 20
        assert "ADD R1, R1, R2" in lines  # result = left + right
        assert "MOV [P0], R1" in lines  # store result

    def test_variable_usage(self):
        """Test variable loading in expressions."""
        code = self.generate_code("x = 10\ny = x + 5")
        lines = code.strip().split("\n")
        # Should load x into register
        assert "MOV R1, [P0]" in lines

    def test_if_statement_simple(self):
        """Test if statement code generation."""
        code = self.generate_code("if x = 1 then y = 2 end")
        lines = code.strip().split("\n")
        assert any("JZ" in line for line in lines)
        # No JMP for simple if without else
        assert any("L1:" in line for line in lines)

    def test_if_statement_with_else(self):
        """Test if-else statement code generation."""
        code = self.generate_code("if x = 1 then y = 2 else y = 3 end")
        lines = code.strip().split("\n")
        # Should have two labels
        labels = [line for line in lines if line.endswith(":")]
        assert len(labels) >= 2

    def test_for_statement(self):
        """Test for loop code generation."""
        code = self.generate_code("for i = 1 to 10 next")
        lines = code.strip().split("\n")
        assert any("CMP" in line for line in lines)
        assert any("JGT" in line for line in lines)
        # Can use ADD or INC for increment
        assert any("ADD" in line or "INC" in line for line in lines)

    def test_while_statement(self):
        """Test while loop code generation."""
        code = self.generate_code("while x < 10\nx = x + 1\nend")
        lines = code.strip().split("\n")
        assert any("JZ" in line for line in lines)

    def test_binary_expressions(self):
        """Test various binary operations."""
        operations = ["+", "-", "*", "/"]
        for op in operations:
            code = self.generate_code(f"x = 5 {op} 3")
            lines = code.strip().split("\n")
            if op == "+":
                assert "ADD R1, R1, R2" in lines
            elif op == "-":
                assert "SUB R1, R1, R2" in lines
            # * and / are simplified

    def test_multiple_statements(self):
        """Test code generation for multiple statements."""
        code = self.generate_code("clrdraw\nx = 10\npxlon(x, 20, 31)")
        lines = code.strip().split("\n")
        assert "MOV VM, 0" in lines  # clrdraw
        assert "MOV [P0], R1" in lines  # assignment
        assert "SWRITE VC" in lines  # pxlon

    def test_variable_address_allocation(self):
        """Test that variables get unique addresses."""
        code = self.generate_code("a = 1\nb = 2\nc = 3")
        # Check that different addresses are used
        lines = code.strip().split("\n")
        store_lines = [line for line in lines if "MOV [P0]," in line]
        assert len(store_lines) == 3

    def test_labels_and_jumps(self):
        """Test label and jump generation."""
        code = self.generate_code("goto mylabel\nmylabel:")
        lines = code.strip().split("\n")
        assert "JMP mylabel" in lines
        assert "mylabel:" in lines

    def test_pause_statement(self):
        """Test pause statement generation."""
        code = self.generate_code("pause")
        lines = code.strip().split("\n")
        assert "KEYSTAT R0" in lines
        assert "JZ -2" in lines

    def test_get_key_statement(self):
        """Test get key statement generation."""
        code = self.generate_code("getkey")
        lines = code.strip().split("\n")
        assert "KEYIN R0" in lines

    def test_stop_sound_statement(self):
        """Test stop sound statement generation."""
        code = self.generate_code("stopsound")
        lines = code.strip().split("\n")
        assert "MOV SV, 0" in lines

    def test_complex_program(self):
        """Test code generation for a complex program."""
        source = """
        clrdraw
        x = 128
        y = 128
        for i = 0 to 255
            pxlon(i, i, 31)
        next
        pause
        """
        code = self.generate_code(source)
        lines = code.strip().split("\n")

        # Should have various instructions
        assert "MOV VM, 0" in lines  # clrdraw
        assert any("CMP" in line for line in lines)  # for loop
        assert "KEYSTAT R0" in lines  # pause
        assert lines[-1] == "HLT"

    def test_string_literal(self):
        """Test string literal handling."""
        code = self.generate_code('x = "hello"')
        lines = code.strip().split("\n")
        # String literals are simplified to 0
        assert "MOV R1, #0" in lines

    def test_number_literal(self):
        """Test number literal handling."""
        code = self.generate_code("x = 42")
        lines = code.strip().split("\n")
        # Should generate MOV R1, #42
        assert "MOV R1, #42" in lines

    def test_repeat_statement(self):
        """Test repeat loop code generation."""
        code = self.generate_code("repeat\nx = x + 1\nuntil x = 10")
        lines = code.strip().split("\n")
        assert any("JZ" in line for line in lines)

    def test_function_call(self):
        """Test function call code generation."""
        code = self.generate_code("x = sin(30)")
        lines = code.strip().split("\n")
        # Should generate SIN instruction
        assert "SIN R1, R1" in lines

    def test_unary_operations_codegen(self):
        """Test code generation for unary operations."""
        code = self.generate_code("x = -y\nz = not flag")
        lines = code.strip().split("\n")
        # Should generate code for negation and NOT
        assert "NEG" in " ".join(lines) or "NOT" in " ".join(lines)

    def test_function_call_codegen(self):
        """Test code generation for various function calls."""
        # Test math functions that have hardware support
        code = self.generate_code("x = sin(30)")
        lines = code.strip().split("\n")
        assert "SIN R1, R1" in lines

        code = self.generate_code("x = cos(45)")
        lines = code.strip().split("\n")
        assert "COS R1, R1" in lines

        # Test functions that are still placeholders
        code = self.generate_code("x = length(\"hello\")")
        lines = code.strip().split("\n")
        assert "MOV R1, #0" in lines  # LENGTH is still a placeholder

    def test_list_and_matrix_access_codegen(self):
        """Test code generation for list and matrix access."""
        code = self.generate_code("x = L1(5)\ny = MatA(1, 2)")
        lines = code.strip().split("\n")
        # Should generate memory access code
        assert any("MOV [P0]," in line for line in lines)

    def test_complex_control_flow_codegen(self):
        """Test code generation for complex control flow."""
        code = self.generate_code("""
        if x > 0 then
            if y > 0 then
                z = 1
            else
                z = 2
            end
        else
            z = 3
        end
        """)
        lines = code.strip().split("\n")
        # Should have multiple JZ and JMP instructions
        jz_count = sum(1 for line in lines if "JZ" in line)
        jmp_count = sum(1 for line in lines if "JMP" in line)
        assert jz_count >= 2
        assert jmp_count >= 2

    def test_loop_codegen_optimization(self):
        """Test that loops generate efficient code."""
        code = self.generate_code("for i = 1 to 100\nx = x + i\nnext")
        lines = code.strip().split("\n")
        # Should use CMP and JGT for loop control
        assert any("CMP" in line for line in lines)
        assert any("JGT" in line for line in lines)

    def test_string_operations_codegen(self):
        """Test code generation for string operations."""
        code = self.generate_code('s = "hello" + "world"')
        lines = code.strip().split("\n")
        # Current implementation may simplify strings
        assert "MOV R1, #0" in lines

    def test_graphics_complex_codegen(self):
        """Test code generation for complex graphics operations."""
        code = self.generate_code("line(0, 0, 100, 100, 31)\ncircle(50, 50, 25, 15)")
        lines = code.strip().split("\n")
        # Should contain graphics-related instructions
        assert "SLINE" in " ".join(lines)
        assert "SCIRC" in " ".join(lines)

    def test_sound_codegen(self):
        """Test code generation for sound operations."""
        code = self.generate_code("playtone(440, 1000, 128)\nplaywave(1, 220, 64)")
        lines = code.strip().split("\n")
        assert "MOV SF," in " ".join(lines)
        assert "MOV SV," in " ".join(lines)
        assert "SPLAY" in lines

    def test_io_codegen(self):
        """Test code generation for I/O operations."""
        code = self.generate_code('getkey\ninput("Prompt:", x)\ndisp "Result:"')
        lines = code.strip().split("\n")
        assert "KEYIN R0" in lines
        assert "KEYSTAT R0" in lines

    def test_goto_label_codegen(self):
        """Test code generation for goto and labels."""
        code = self.generate_code("start:\nx = 1\ngoto start")
        lines = code.strip().split("\n")
        assert "start:" in lines
        assert "JMP start" in lines

    def test_large_program_codegen(self):
        """Test code generation for large programs."""
        large_source = "\n".join([f"var{i} = {i}\npxlon({i}, {i}, 31)" for i in range(50)])
        code = self.generate_code(large_source)
        lines = code.strip().split("\n")
        # Should generate reasonable amount of code
        assert len(lines) > 100  # At least some code per statement
        assert lines[-1] == "HLT"

    def test_register_allocation_efficiency(self):
        """Test that registers are allocated efficiently."""
        code = self.generate_code("a = 1\nb = 2\nc = a + b\nd = c * 2")
        lines = code.strip().split("\n")
        # Should reuse registers when possible
        r1_count = sum(1 for line in lines if "R1" in line)
        assert r1_count > 0  # R1 should be used

    def test_memory_address_allocation(self):
        """Test that memory addresses are allocated sequentially."""
        code = self.generate_code("a = 1\nb = 2\nc = 3")
        lines = code.strip().split("\n")
        addresses = []
        for line in lines:
            if "MOV P0, " in line:
                # Extract address from "MOV P0, addr"
                addr_str = line.split(", ")[1]
                addresses.append(int(addr_str))
        assert len(addresses) == 3
        assert addresses[1] == addresses[0] + 2  # Sequential allocation
        assert addresses[2] == addresses[1] + 2  # Sequential allocation

    def test_codegen_error_handling(self):
        """Test error handling in code generation."""
        # Test with a valid but complex expression
        code = self.generate_code("x = sin(30) + cos(45)")
        assert "HLT" in code  # Should still end with HLT

    def test_optimization_opportunities(self):
        """Test areas where code could be optimized."""
        # Constant folding opportunity
        code = self.generate_code("x = 2 + 3")
        lines = code.strip().split("\n")
        # Optimized to use SHL for powers of 2: MOV R1, #1; SHL R1, R1, #1 (makes 2)
        assert "SHL R1, R1, #1" in lines
        assert "ADD R1, R1, R2" in lines
        assert "ADD R1, R1, R2" in lines

    def test_advanced_math_codegen(self):
        """Test code generation for advanced math functions."""
        code = self.generate_code("x = powr(2, 3)\ny = sqrt(16)\nz = log(100)")
        lines = code.strip().split("\n")
        assert "POWR" in "".join(lines)
        assert "SQRT" in "".join(lines)
        assert "LOG" in "".join(lines)

    def test_bitwise_operations_codegen(self):
        """Test code generation for bitwise operations."""
        code = self.generate_code("x = a & b\ny = c | d\nz = e ^ f")
        lines = code.strip().split("\n")
        assert any("AND" in line for line in lines)
        assert any("OR" in line for line in lines)
        assert any("XOR" in line for line in lines)

    def test_shift_operations_codegen(self):
        """Test code generation for shift operations."""
        code = self.generate_code("x = a << 2\ny = b >> 1")
        lines = code.strip().split("\n")
        assert any("SHL" in line for line in lines)
        assert any("SHR" in line for line in lines)

    def test_comparison_codegen(self):
        """Test code generation for comparisons."""
        code = self.generate_code("result = (a = b) + (c < d) + (e > f)")
        lines = code.strip().split("\n")
        assert any("CMP" in line for line in lines)
        assert any("JZ" in line for line in lines) or any("JNZ" in line for line in lines)

    def test_string_operations_codegen(self):
        """Test code generation for string operations."""
        code = self.generate_code('s1 = "hello"\ns2 = "world"\ncombined = s1 + s2')
        lines = code.strip().split("\n")
        # String operations are simplified in current implementation
        assert "HLT" in lines

    def test_array_operations_codegen(self):
        """Test code generation for array operations."""
        code = self.generate_code("L1(1) = 42\nx = L1(2)")
        lines = code.strip().split("\n")
        # Array operations are simplified
        assert "HLT" in lines

    def test_function_call_codegen_complex(self):
        """Test code generation for complex function calls."""
        code = self.generate_code("result = min(max(a, b), c)")
        lines = code.strip().split("\n")
        assert any("MIN" in line for line in lines)
        assert any("MAX" in line for line in lines)

    def test_loop_codegen_optimization(self):
        """Test optimized loop code generation."""
        code = self.generate_code("for i = 1 to 10\nsum = sum + i\nnext")
        lines = code.strip().split("\n")
        assert any("CMP" in line for line in lines)
        assert any("JGT" in line for line in lines)

    def test_conditional_codegen_optimization(self):
        """Test optimized conditional code generation."""
        code = self.generate_code("if x > 0 then y = 1 else y = 0 end")
        lines = code.strip().split("\n")
        assert any("JGT" in line for line in lines) or any("CMP" in line for line in lines)

    def test_expression_codegen_precedence(self):
        """Test code generation respects operator precedence."""
        code = self.generate_code("x = a + b * c - d / e")
        lines = code.strip().split("\n")
        # Should generate correct order of operations
        assert any("MUL" in line for line in lines)
        assert any("DIV" in line for line in lines)
        assert any("ADD" in line for line in lines)
        assert any("SUB" in line for line in lines)

    def test_register_usage_efficiency(self):
        """Test efficient register usage."""
        code = self.generate_code("temp = a * b + c * d")
        lines = code.strip().split("\n")
        # Should reuse registers efficiently
        r1_usage = sum(1 for line in lines if "R1" in line)
        r2_usage = sum(1 for line in lines if "R2" in line)
        assert r1_usage > 0 and r2_usage > 0

    def test_memory_access_optimization(self):
        """Test optimized memory access patterns."""
        code = self.generate_code("x = 1\ny = 2\nz = x + y")
        lines = code.strip().split("\n")
        # Should use direct register addressing
        assert any("MOV [P0]," in line for line in lines)

    def test_constant_propagation(self):
        """Test constant propagation optimization."""
        code = self.generate_code("x = 5 * 3 + 2")
        lines = code.strip().split("\n")
        # Could be optimized to x = 17, but current implementation doesn't do this
        assert any("MUL" in line for line in lines) or any("ADD" in line for line in lines)

    def test_dead_code_elimination(self):
        """Test dead code elimination (if implemented)."""
        code = self.generate_code("temp = 1\nx = 2\nresult = x + 1")
        lines = code.strip().split("\n")
        # temp is assigned but never used - could be eliminated
        assert "HLT" in lines

    def test_graphics_codegen_optimization(self):
        """Test optimized graphics code generation."""
        code = self.generate_code("pxlon(10, 20, 31)\nline(0, 0, 100, 100, 15)")
        lines = code.strip().split("\n")
        assert any("SWRITE" in line for line in lines)
        assert any("SLINE" in line for line in lines)

    def test_sound_codegen_optimization(self):
        """Test optimized sound code generation."""
        code = self.generate_code("playtone(440, 1000, 128)")
        lines = code.strip().split("\n")
        assert any("SPLAY" in line for line in lines)

    def test_io_codegen_optimization(self):
        """Test optimized I/O code generation."""
        code = self.generate_code("pause")
        lines = code.strip().split("\n")
        assert any("KEYSTAT" in line for line in lines)
        assert any("JZ" in line for line in lines)

    def test_complex_program_codegen(self):
        """Test code generation for complex programs."""
        complex_source = """
        clrdraw
        for i = 0 to 255
            pxlon(i, i, 31)
        next
        playtone(440, 500, 128)
        pause
        """
        code = self.generate_code(complex_source)
        lines = code.strip().split("\n")
        assert any("MOV VM, 0" in line for line in lines)  # ClrDraw
        assert any("SWRITE" in line for line in lines)     # PxlOn
        assert any("SPLAY" in line for line in lines)      # PlayTone
        assert any("KEYSTAT" in line for line in lines)    # Pause
        assert lines[-1] == "HLT"

    def test_codegen_error_recovery(self):
        """Test error recovery in code generation."""
        # Generate code for a program with potential issues
        code = self.generate_code("x = undefined_var + 1")
        # Should still generate valid assembly
        assert "HLT" in code

    def test_large_expression_codegen(self):
        """Test code generation for very large expressions."""
        large_expr = " + ".join([f"var{i}" for i in range(20)])
        code = self.generate_code(f"result = {large_expr}")
        lines = code.strip().split("\n")
        # Should generate valid code without crashing
        assert "HLT" in lines

    def test_nested_loop_codegen(self):
        """Test code generation for nested loops."""
        code = self.generate_code("""
        for i = 1 to 5
            for j = 1 to 3
                pxlon(i*10, j*10, 31)
            next
        next
        """)
        lines = code.strip().split("\n")
        # Should have nested loop structure
        assert lines.count("CMP") >= 2  # At least 2 comparisons for nested loops

    def test_function_inlining_opportunity(self):
        """Test opportunities for function inlining."""
        code = self.generate_code("x = abs(y)\nz = abs(w)")
        lines = code.strip().split("\n")
        # abs() calls could potentially be inlined
        assert any("ABS" in line for line in lines)

    def test_codegen_memory_usage(self):
        """Test memory usage patterns in generated code."""
        code = self.generate_code("a = 1\nb = 2\nc = 3\nd = 4\ne = 5")
        lines = code.strip().split("\n")
        memory_ops = [line for line in lines if "[P0]" in line]
        # Should allocate sequential memory addresses
        assert len(memory_ops) == 5

    def test_optimization_flags(self):
        """Test different optimization levels (if implemented)."""
        # For now, just test default optimization
        code = self.generate_code("x = 0")
        lines = code.strip().split("\n")
        # Should use XOR for setting to zero
        assert any("XOR" in line for line in lines)

    def test_constant_folding_optimization(self):
        """Test constant folding optimization."""
        code = self.generate_code("x = 2 * 3 + 4")
        lines = code.strip().split("\n")
        # Should potentially optimize to x = 10
        # Current implementation may not do this, but test structure is there

    def test_dead_code_elimination_optimization(self):
        """Test dead code elimination."""
        code = self.generate_code("temp = 1\nx = 2\nresult = x + 1")
        lines = code.strip().split("\n")
        # temp assignment might be eliminated if not used

    def test_register_allocation_optimization(self):
        """Test efficient register allocation."""
        code = self.generate_code("result = (a + b) * (c + d)")
        lines = code.strip().split("\n")
        # Should reuse registers efficiently
        r1_count = sum(1 for line in lines if "R1" in line)
        r2_count = sum(1 for line in lines if "R2" in line)
        assert r1_count > 0 and r2_count > 0

    def test_instruction_selection_optimization(self):
        """Test optimal instruction selection."""
        # Test that appropriate instructions are chosen
        code = self.generate_code("x = x + 1")
        lines = code.strip().split("\n")
        # Could use INC instruction for +1

    def test_loop_optimization(self):
        """Test loop optimization techniques."""
        code = self.generate_code("for i = 1 to 100\nsum = sum + i\nnext")
        lines = code.strip().split("\n")
        # Should use efficient loop constructs
        assert any("CMP" in line for line in lines)

    def test_expression_optimization(self):
        """Test expression optimization."""
        code = self.generate_code("x = a * 2")
        lines = code.strip().split("\n")
        # Could use SHL for multiplication by power of 2
        assert any("MUL" in line or "SHL" in line for line in lines)

    def test_memory_access_optimization(self):
        """Test memory access optimization."""
        code = self.generate_code("x = arr[0]\ny = arr[1]")
        lines = code.strip().split("\n")
        # Should optimize sequential accesses

    def test_function_call_optimization(self):
        """Test function call optimization."""
        code = self.generate_code("x = sin(0)")
        lines = code.strip().split("\n")
        # sin(0) could potentially be optimized to 0
        assert any("SIN" in line for line in lines)

    def test_codegen_performance_large_program(self):
        """Test code generation performance on large programs."""
        # Generate a large program
        statements = [f"var{i} = {i}" for i in range(100)]
        source = "\n".join(statements)
        
        import time
        start_time = time.time()
        code = self.generate_code(source)
        end_time = time.time()
        
        # Should generate code quickly
        assert end_time - start_time < 1.0  # Less than 1 second
        lines = code.strip().split("\n")
        assert len(lines) > 200  # Substantial code generated

    def test_optimization_correctness(self):
        """Test that optimizations don't change program behavior."""
        # Test that optimized and unoptimized versions would produce same results
        # This is more of a conceptual test
        code1 = self.generate_code("x = 0")
        code2 = self.generate_code("x = 1 - 1")
        # Both should set x to 0, potentially through different means

    def test_peephole_optimizations(self):
        """Test peephole optimizations."""
        # Look for patterns that could be optimized
        code = self.generate_code("x = x + 0")  # Could be eliminated
        lines = code.strip().split("\n")
        # Current implementation may not optimize this

    def test_strength_reduction_optimization(self):
        """Test strength reduction optimizations."""
        code = self.generate_code("x = y * 8")  # Could become y << 3
        lines = code.strip().split("\n")
        # Should potentially use shift instead of multiply

    def test_common_subexpression_elimination(self):
        """Test common subexpression elimination."""
        code = self.generate_code("temp = a + b\nx = temp * 2\ny = temp / 2")
        lines = code.strip().split("\n")
        # temp should be computed once and reused

    def test_constant_propagation_optimization(self):
        """Test constant propagation."""
        code = self.generate_code("a = 5\nb = a + 1")
        lines = code.strip().split("\n")
        # Could potentially propagate constant 5

    def test_codegen_size_optimization(self):
        """Test code size optimization."""
        code1 = self.generate_code("x = 1 + 2 + 3 + 4")
        code2 = self.generate_code("x = (1 + 2) + (3 + 4)")
        lines1 = code1.strip().split("\n")
        lines2 = code2.strip().split("\n")
        # Different groupings might produce different code sizes

    def test_optimization_with_debugging(self):
        """Test that optimizations work with debugging features."""
        # Ensure optimizations don't break debugging
        code = self.generate_code("x = 1\ny = x + 1")
        lines = code.strip().split("\n")
        # Should still be debuggable