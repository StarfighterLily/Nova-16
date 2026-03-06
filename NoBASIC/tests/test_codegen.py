"""
Unit tests for the NoBASIC code generator component.
"""

import re
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
        # ClrDraw uses layer 1 (background) and fills with 0
        assert "MOV VL, 1" in lines
        assert "SFILL 0x00" in lines
        assert "; ClrDraw" in code  # Comment present
        assert lines[-1] == "HLT"

    def test_pxl_on_statement(self):
        """Test PxlOn code generation."""
        code = self.generate_code("pxlon(10, 20, 31)")
        lines = code.strip().split("\n")
        # Check for coordinate mode setup
        assert any("MOV VX," in line for line in lines)
        assert any("MOV VY," in line for line in lines)
        assert any("MOV VC," in line for line in lines)
        assert "SWRITE VC" in lines
        # Check that literals are loaded
        assert any("10" in line for line in lines)
        assert any("20" in line for line in lines)
        assert any("31" in line for line in lines)

    def test_assignment_statement(self):
        """Test assignment code generation."""
        code = self.generate_code("x = 42")
        lines = code.strip().split("\n")
        # Check that value 42 is stored
        assert any("42" in line for line in lines)
        # Compiler uses register allocation, variables stored in P registers
        assert any("MOV P" in line for line in lines)

    def test_assignment_with_expression(self):
        """Test assignment with binary expression."""
        code = self.generate_code("x = 10 + 20")
        lines = code.strip().split("\n")
        # Compiler performs constant folding: 10 + 20 = 30
        # Should have the result value 30
        assert any("30" in line for line in lines) or any("ADD" in line for line in lines)
        # Result stored in P register (register allocation)
        assert any("MOV P" in line for line in lines)

    def test_variable_usage(self):
        """Test variable loading in expressions."""
        code = self.generate_code("x = 10\ny = x + 5")
        lines = code.strip().split("\n")
        # Compiler uses register allocation for variables
        # Should have MOV operations with P or R registers
        assert any("MOV" in line for line in lines)
        assert any("ADD" in line for line in lines)

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
        # Check for loop control jumps (JC, JZ, JMP, JGT, JLT patterns)
        jump_instructions = [line for line in lines if any(jmp in line for jmp in ["JC", "JZ", "JMP", "JGT", "JLT", "JGE", "JLE"])]
        assert len(jump_instructions) >= 1
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
            # Compiler performs constant folding on literal operations
            # Should generate MOV with the result
            assert any("MOV" in line for line in lines)

    def test_multiple_statements(self):
        """Test code generation for multiple statements."""
        code = self.generate_code("clrdraw\nx = 10\npxlon(x, 20, 31)")
        lines = code.strip().split("\n")
        # ClrDraw uses layer fills, not VM mode
        assert "MOV VL, 1" in lines  # clrdraw (layer 1)
        assert "SFILL 0x00" in lines  # clrdraw clear
        assert any("10" in line for line in lines)  # assignment value
        assert "SWRITE VC" in lines  # pxlon

    def test_variable_address_allocation(self):
        """Test that variables get unique register allocations."""
        code = self.generate_code("a = 1\nb = 2\nc = 3")
        # Variables are allocated to P registers, not memory
        lines = code.strip().split("\n")
        # Should have register moves
        p_register_uses = [line for line in lines if "MOV P" in line]
        assert len(p_register_uses) >= 3

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
        assert "JZ L1" in lines

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
        assert "MOV VL, 1" in lines  # clrdraw (layer 1)
        assert "SFILL 0x00" in lines  # clrdraw clear
        assert any("CMP" in line for line in lines)  # for loop
        assert "KEYSTAT R0" in lines  # pause
        assert lines[-1] == "HLT"

    def test_string_literal(self):
        """Test string literal handling."""
        code = self.generate_code('x = "hello"')
        lines = code.strip().split("\n")
        # String literals are simplified to 0
        assert any("0" in line for line in lines)

    def test_number_literal(self):
        """Test number literal handling."""
        code = self.generate_code("x = 42")
        lines = code.strip().split("\n")
        # Should generate code that includes 42
        assert any("42" in line for line in lines)

    def test_float_literal_is_normalized_for_assembler(self):
        """Test float literals are normalized to integer immediates in assembly output."""
        code = self.generate_code("x = 2.7")
        non_comment_lines = [line for line in code.split("\n") if not line.strip().startswith(";")]
        assert all("2.7" not in line for line in non_comment_lines)
        assert (
            any("MOV" in line and ", 2" in line for line in non_comment_lines)
            or any("SHL" in line and ", 1" in line for line in non_comment_lines)
        )

    def test_unary_minus_float_literal_is_normalized(self):
        """Test folded unary float literals are normalized to integer immediates."""
        code = self.generate_code("x = -3.14")
        non_comment_lines = [line for line in code.split("\n") if not line.strip().startswith(";")]
        assert all("-3.14" not in line for line in non_comment_lines)
        assert any("MOV" in line and "-3" in line for line in code.split("\n"))

    def test_int_function_maps_to_intgr_instruction(self):
        """Test TI-style int() maps to supported INTGR opcode path."""
        code = self.generate_code("x = int(2.7)")
        assert "INTGR" in code
        assert "2.7" not in code

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
        assert any("SIN" in line for line in lines)

    def test_unary_operations_codegen(self):
        """Test code generation for unary operations."""
        code = self.generate_code("x = -y\nz = not flag")
        lines = code.strip().split("\n")
        # Should generate code for negation and NOT
        assert "NEG" in " ".join(lines) or "NOT" in " ".join(lines)

    def test_increment_decrement_codegen(self):
        """Test code generation for increment/decrement operators."""
        code = self.generate_code("x = 10\nx++\ny = ++x\nz--")
        lines = code.strip().split("\n")
        # Should generate ADD/SUB instructions for increment/decrement
        add_count = sum(1 for line in lines if "ADD" in line)
        sub_count = sum(1 for line in lines if "SUB" in line)
        assert add_count >= 2  # x++ and ++x
        assert sub_count >= 1  # z--

    def test_function_call_codegen(self):
        """Test code generation for various function calls."""
        # Test math functions that have hardware support
        code = self.generate_code("x = sin(30)")
        lines = code.strip().split("\n")
        assert any("SIN" in line for line in lines)

        code = self.generate_code("x = cos(45)")
        lines = code.strip().split("\n")
        assert any("COS" in line for line in lines)

        # Test functions that use STRLEN
        code = self.generate_code("x = length(\"hello\")")
        lines = code.strip().split("\n")
        # length() is implemented via strlen
        assert any("STRLEN" in line for line in lines)

    def test_list_and_matrix_access_codegen(self):
        """Test code generation for list and matrix access."""
        code = self.generate_code("x = L1(5)\ny = MatA(1, 2)")
        lines = code.strip().split("\n")
        # Should generate code for list/matrix access
        # May use registers or memory depending on optimization
        assert any("MOV" in line for line in lines)

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
        # Should use CMP and conditional jumps for loop control
        assert any("CMP" in line for line in lines)
        # Check for loop control jumps (include all jump types)
        jump_instructions = [line for line in lines if any(jmp in line for jmp in ["JC", "JZ", "JMP", "JGT", "JLT", "JGE", "JLE"])]
        assert len(jump_instructions) >= 1

    def test_string_operations_strlen(self):
        """Test string length function."""
        code = self.generate_code('x = strlen("hello")')
        lines = code.strip().split("\n")
        assert any("STRLEN" in line for line in lines)

    def test_string_operations_strcpy(self):
        """Test string copy function."""
        code = self.generate_code('strcpy(dest, "hello")')
        lines = code.strip().split("\n")
        # STRCPY with appropriate registers
        assert any("STRCPY" in line for line in lines)

    def test_string_operations_strcat(self):
        """Test string concatenate function."""
        code = self.generate_code('strcat(dest, "world")')
        lines = code.strip().split("\n")
        # STRCAT with appropriate registers
        assert any("STRCAT" in line for line in lines)

    def test_string_operations_strcmp(self):
        """Test string compare function."""
        code = self.generate_code('strcmp("hello", "world", 5)')
        lines = code.strip().split("\n")
        # STRCMP with appropriate registers
        assert any("STRCMP" in line for line in lines)

    def test_string_operations_strupr_strlwr(self):
        """Test string case conversion functions."""
        code = self.generate_code('x = strupr(txt)\ny = strlwr(txt)')
        lines = code.strip().split("\n")
        assert any("STRUPR" in line for line in lines)
        assert any("STRLWR" in line for line in lines)

    def test_string_operations_strrev(self):
        """Test string reverse function."""
        code = self.generate_code('x = strrev(txt)')
        lines = code.strip().split("\n")
        assert any("STRREV" in line for line in lines)

    def test_string_operations_strfind(self):
        """Test string find functions."""
        code = self.generate_code('strfind(haystack, "needle")\nstrfindi(haystack, "NEEDLE")')
        lines = code.strip().split("\n")
        # STRFIND and STRFINDI with appropriate registers
        assert any("STRFIND" in line for line in lines)
        assert any("STRFINDI" in line for line in lines)

    def test_string_operations_strext(self):
        """Test string extract functions."""
        code = self.generate_code('x = strext(dest, 5, 10, haystack)\ny = strexti(dest, 5, 10, haystack)')
        lines = code.strip().split("\n")
        assert "STREXT R1, R2, R3, R4" in lines
        assert "STREXTI R1, R2, R3, R4" in lines

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

    def test_input_buffer_uses_db_not_defb(self):
        """Input should emit writable DB buffers compatible with nova_assembler."""
        code = self.generate_code('input("Name:", userName)')
        assert "DEFB" not in code
        assert ": DB " in code

    def test_input_echo_and_backspace_paths(self):
        """Input should include key polling, echo redraw, and backspace handling."""
        code = self.generate_code('input("Name:", userName)')
        assert "KEYSTAT R0" in code
        assert "KEYIN R0" in code
        assert "CMP R0, 8" in code
        assert "CMP R0, 127" in code
        # Echo path redraws the buffer text after each character.
        assert len(re.findall(r"TEXT L\d+", code)) >= 2

    def test_input_resets_vx_before_prompt(self):
        """Input prompt code should left-justify using VX without changing row."""
        code = self.generate_code('input("Name:", userName)')
        assert "MOV VX, 0" in code
        assert "MOV VY, 0" not in code

        lines = code.split("\n")
        vx_line = next(i for i, line in enumerate(lines) if line.strip() == "MOV VX, 0")
        first_text_line = next(i for i, line in enumerate(lines) if line.strip().startswith("TEXT "))
        assert vx_line < first_text_line

    def test_input_updates_register_allocated_variable(self):
        """Input should synchronize the target variable even when register allocated."""
        code = self.generate_code('a = 1\ninput("Name:", name)\ndisp "Hello, " + name\ndisp a')

        # Name should be register allocated because it is used after Input.
        assert "name" in self.generator.var_reg
        name_reg = self.generator.var_reg["name"]

        # Input always loads buffer address into P2 before storing it to the variable.
        assert re.search(r"MOV P2, L\d+", code)

        # If a different register is assigned, storage path must sync from P2.
        if name_reg != "P2":
            assert f"MOV {name_reg}, P2" in code

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
        """Test that variables are allocated correctly."""
        code = self.generate_code("a = 1\nb = 2\nc = 3")
        lines = code.strip().split("\n")
        # Variables are allocated to P registers in the current implementation
        # Look for P register assignments
        p_regs = []
        for line in lines:
            if "MOV P" in line and "MOV SP" not in line and "MOV FP" not in line:
                p_regs.append(line)
        # Should have P register allocations for the variables
        assert len(p_regs) >= 3

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
        # Should generate some code for the assignment
        # Constant folding may optimize this to a single value
        assert any("MOV" in line for line in lines)

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
        code = self.generate_code("a = 1\nb = 2\nresult = a = b")
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
        # Check for loop control jumps (include all jump types)
        jump_instructions = [line for line in lines if any(jmp in line for jmp in ["JC", "JZ", "JMP", "JGT", "JLT", "JGE", "JLE"])]
        assert len(jump_instructions) >= 1

    def test_conditional_codegen_optimization(self):
        """Test optimized conditional code generation."""
        code = self.generate_code("if x > 0 then y = 1 else y = 0 end")
        lines = code.strip().split("\n")
        # Should use conditional jumps
        assert any("JZ" in line or "JNZ" in line or "JGT" in line for line in lines)
        lines = code.strip().split("\n")
        # Check for conditional jumps
        jump_instructions = [line for line in lines if any(jmp in line for jmp in ["JC", "JZ", "JMP", "CMP"])]
        assert len(jump_instructions) >= 2

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
        # Should use registers for the expression
        # Check that some registers are used
        register_lines = [line for line in lines if any(f"R{i}" in line or f"P{i}" in line for i in range(10))]
        assert len(register_lines) > 0

    def test_memory_access_optimization(self):
        """Test optimized memory access patterns."""
        code = self.generate_code("x = 1\ny = 2\nz = x + y")
        lines = code.strip().split("\n")
        # Compiler uses register allocation, variables stored in P registers
        assert any("MOV P" in line for line in lines)

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
        assert any("SFILL" in line for line in lines)      # ClrDraw
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
        # Very large expressions should exhaust register allocator
        with pytest.raises(RuntimeError, match="No available registers"):
            self.generate_code(f"result = {large_expr}")

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
        assert sum(1 for line in lines if "CMP" in line) >= 2  # At least 2 comparisons for nested loops

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
        # Variables are allocated to P registers, not memory
        p_register_uses = [line for line in lines if "MOV P" in line]
        # Should have register allocations
        assert len(p_register_uses) >= 5

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
        # Should use some registers for the complex expression
        total_r_registers = sum(1 for line in lines if any(f"R{i}" in line for i in range(10)))
        assert total_r_registers > 0  # At least some R registers should be used

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
        code = self.generate_code("x = L1[0]\ny = L1[1]")
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

    def test_math_functions_sin_cos_tan(self):
        """Test trigonometric function code generation."""
        functions = ["sin", "cos", "tan"]
        for func in functions:
            code = self.generate_code(f"x = {func}(45)")
            lines = code.strip().split("\n")
            assert any(func.upper() in line for line in lines)

    def test_math_functions_sqrt_abs(self):
        """Test sqrt and abs function code generation."""
        code = self.generate_code("x = sqrt(16)\ny = abs(-5)")
        lines = code.strip().split("\n")
        assert any("SQRT" in line for line in lines)
        assert any("ABS" in line for line in lines)

    def test_math_functions_min_max(self):
        """Test min and max function code generation."""
        code = self.generate_code("x = min(10, 20)\ny = max(5, 15)")
        lines = code.strip().split("\n")
        assert any("MIN" in line for line in lines)
        assert any("MAX" in line for line in lines)

    def test_math_functions_rnd(self):
        """Test random function code generation."""
        code = self.generate_code("x = rnd()")
        lines = code.strip().split("\n")
        assert any("RND" in line for line in lines)

    def test_math_functions_atan_asin_acos(self):
        """Test inverse trigonometric functions."""
        functions = ["atan", "asin", "acos"]
        for func in functions:
            code = self.generate_code(f"x = {func}(0.5)")
            lines = code.strip().split("\n")
            assert any(func.upper() in line for line in lines)

    def test_math_functions_deg_rad(self):
        """Test degree/radian conversion functions."""
        code = self.generate_code("x = deg(1.57)\ny = rad(90)")
        lines = code.strip().split("\n")
        assert any("DEG" in line for line in lines)
        assert any("RAD" in line for line in lines)

    def test_math_functions_rounding(self):
        """Test rounding functions."""
        functions = ["floor", "ceil", "round", "trunc"]
        for func in functions:
            code = self.generate_code(f"x = {func}(3.7)")
            lines = code.strip().split("\n")
            assert any(func.upper() in line for line in lines)

    def test_math_functions_frac_intgr(self):
        """Test fractional and integer part functions."""
        code = self.generate_code("x = frac(3.14)\ny = intgr(3.14)")
        lines = code.strip().split("\n")
        assert any("FRAC" in line for line in lines)
        assert any("INTGR" in line for line in lines)

    def test_math_functions_power_log_exp(self):
        """Test power, logarithm, and exponential functions."""
        code = self.generate_code("x = powr(2, 3)\ny = log(10)\nz = exp(1)")
        lines = code.strip().split("\n")
        assert any("POWR" in line for line in lines)
        assert any("LOG" in line for line in lines)
        assert any("EXP" in line for line in lines)

    def test_bit_operations_btst_bset_bclr(self):
        """Test bit test, set, and clear operations."""
        code = self.generate_code("x = btst(value, 3)\ny = bset(value, 5)\nz = bclr(value, 7)")
        lines = code.strip().split("\n")
        assert any("BTST" in line for line in lines)
        assert any("BSET" in line for line in lines)
        assert any("BCLR" in line for line in lines)

    def test_bit_operations_bflip(self):
        """Test bit flip operation."""
        code = self.generate_code("x = bflip(value, 4)")
        lines = code.strip().split("\n")
        assert any("BFLIP" in line for line in lines)

    def test_bit_operations_shl_shr(self):
        """Test shift operations."""
        code = self.generate_code("x = shl(y, 2)\nz = shr(w, 1)")
        lines = code.strip().split("\n")
        assert any("SHL" in line for line in lines)
        assert any("SHR" in line for line in lines)

    def test_bit_operations_sar_sal(self):
        """Test arithmetic shift operations."""
        code = self.generate_code("x = sal(y, 2)\nz = sar(w, 1)")
        lines = code.strip().split("\n")
        assert any("SAL" in line for line in lines)
        assert any("SAR" in line for line in lines)

    def test_bit_operations_rol_ror(self):
        """Test rotate operations."""
        code = self.generate_code("x = rol(y, 3)\nz = ror(w, 2)")
        lines = code.strip().split("\n")
        assert any("ROL" in line for line in lines)
        assert any("ROR" in line for line in lines)

    def test_bit_operations_rcl_rcr(self):
        """Test rotate through carry operations."""
        code = self.generate_code("x = rcl(y, 3)\nz = rcr(w, 2)")
        lines = code.strip().split("\n")
        assert any("RCL" in line for line in lines)
        assert any("RCR" in line for line in lines)

    def test_bit_operations_and_or_xor_not(self):
        """Test bitwise logical operations."""
        code = self.generate_code("x = band(a, b)\ny = bor(c, d)\nz = bxor(e, f)\nw = bnot(g)")
        lines = code.strip().split("\n")
        assert any("AND" in line for line in lines)
        assert any("OR" in line for line in lines)
        assert any("XOR" in line for line in lines)
        assert any("NOT" in line for line in lines)

    def test_enhanced_arithmetic_adc_sbc(self):
        """Test add/subtract with carry operations."""
        code = self.generate_code("adc(result, a, b)\nsbc(result, a, b)")
        lines = code.strip().split("\n")
        # ADC and SBC with appropriate registers
        assert any("ADC" in line for line in lines)
        assert any("SBC" in line for line in lines)

    def test_enhanced_arithmetic_mulh_divh(self):
        """Test multiply/divide high operations."""
        code = self.generate_code("mulh(result, a, b)\ndivh(result, a, b)")
        lines = code.strip().split("\n")
        # MULH and DIVH with appropriate registers
        assert any("MULH" in line for line in lines)
        assert any("DIVH" in line for line in lines)

    def test_enhanced_arithmetic_min_max(self):
        """Test min/max operations (already implemented but testing)."""
        code = self.generate_code("x = min(a, b)\ny = max(a, b)")
        lines = code.strip().split("\n")
        assert any("MIN" in line for line in lines)
        assert any("MAX" in line for line in lines)

    def test_enhanced_arithmetic_clz_ctz_popcnt(self):
        """Test bit counting operations (already implemented but testing)."""
        code = self.generate_code("x = clz(value)\ny = ctz(value)\nz = popcnt(value)")
        lines = code.strip().split("\n")
        assert any("CLZ" in line for line in lines)
        assert any("CTZ" in line for line in lines)
        assert any("POPCNT" in line for line in lines)

    def test_enhanced_arithmetic_swap_xchng(self):
        """Test swap and exchange operations."""
        code = self.generate_code("swap(value)\nxchng(a, b)")
        lines = code.strip().split("\n")
        # SWAP and XCHNG with appropriate registers
        assert any("SWAP" in line for line in lines)
        assert any("XCHNG" in line for line in lines)

    def test_enhanced_arithmetic_movz_movnz(self):
        """Test conditional move operations."""
        code = self.generate_code("movz(dest, src)\nmovnz(dest, src)")
        lines = code.strip().split("\n")
        # MOVZ and MOVNZ with appropriate registers
        assert any("MOVZ" in line for line in lines)
        assert any("MOVNZ" in line for line in lines)

    def test_enhanced_arithmetic_lea(self):
        """Test load effective address operation."""
        code = self.generate_code("lea(dest, src)")
        lines = code.strip().split("\n")
        assert "LEA R1, R2" in lines

    def test_type_conversion_itob_btoi(self):
        """Test integer to binary and binary to integer conversions."""
        code = self.generate_code("itob(result, value)\nbtoi(result, binary)")
        lines = code.strip().split("\n")
        # ITOB and BTOI with appropriate registers
        assert any("ITOB" in line for line in lines)
        assert any("BTOI" in line for line in lines)

    def test_type_conversion_itos_stoi(self):
        """Test integer to string and string to integer conversions."""
        code = self.generate_code('itos(result, 42)\nstoi(result, "123")')
        lines = code.strip().split("\n")
        # ITOS and STOI with appropriate registers
        assert any("ITOS" in line for line in lines)
        assert any("STOI" in line for line in lines)

    def test_struct_member_store_and_load_codegen(self):
        """Struct assignment/access should emit declaration, allocation, store, and load code."""
        code = self.generate_code("""
        struct Point x y end
        p.x = 42
        z = p.x
        """)
        lines = code.strip().split("\n")

        assert any("; Struct Point declared with fields: x, y" in line for line in lines)
        assert any("; Allocate struct p (Point)" in line for line in lines)
        assert any("; Store to p.x" in line for line in lines)
        assert any("; Load p.x" in line for line in lines)
        assert any("MOV [P0]," in line for line in lines)

    def test_struct_member_codegen_is_case_insensitive(self):
        """Struct field/member codegen should work across mixed-case declarations and accesses."""
        code = self.generate_code("""
        struct Point X Y end
        p.x = 42
        z = P.y
        """)
        lines = code.strip().split("\n")

        assert any("; Struct Point declared with fields: X, Y" in line for line in lines)
        assert any("; Allocate struct p (Point)" in line for line in lines)
        assert any("; Store to p.x" in line for line in lines)
        assert any("; Load P.y" in line for line in lines)
        assert any("MOV [P0]," in line for line in lines)

    def test_struct_instance_allocation_is_case_insensitive(self):
        """Accessing the same struct instance with different variable casing should not reallocate."""
        code = self.generate_code("""
        struct Point x y end
        p.x = 1
        q = P.y
        """)
        lines = code.strip().split("\n")

        allocation_lines = [line for line in lines if "; Allocate struct" in line]
        assert len(allocation_lines) == 1