"""
Tests for the NoBASIC LLVM IR code generator.
"""

import pytest
from compiler.codegen.llvm_ir_generator import LLVMIRGenerator
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.analyzer import SemanticAnalyzer


class TestLLVMIRGenerator:
    """Test cases for the NoBASIC LLVM IR generator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.lexer = Lexer()
        self.parser = Parser()
        self.analyzer = SemanticAnalyzer()
        self.generator = LLVMIRGenerator()

    def generate_llvm(self, source: str) -> str:
        """Helper to generate LLVM IR from source."""
        tokens = self.lexer.tokenize(source)
        program = self.parser.parse(tokens)
        self.analyzer.analyze(program)
        return self.generator.generate(program)

    def test_empty_program(self):
        """Test LLVM IR generation for empty program."""
        code = self.generate_llvm("")
        assert "define i32 @main()" in code

    def test_math_function_sin(self):
        """Test sin function generates extern declaration."""
        code = self.generate_llvm("x = sin(30)")
        assert "declare i16 @sin(i16)" in code
        assert "x" in code

    def test_math_function_cos(self):
        """Test cos function generates extern declaration."""
        code = self.generate_llvm("x = cos(45)")
        assert "declare i16 @cos(i16)" in code

    def test_math_function_sqrt(self):
        """Test sqrt function generates extern declaration."""
        code = self.generate_llvm("x = sqrt(16)")
        assert "declare i16 @sqrt(i16)" in code

    def test_math_function_abs(self):
        """Test abs function generates extern declaration."""
        code = self.generate_llvm("x = abs(-5)")
        assert "declare i16 @abs(i16)" in code

    def test_math_function_powr(self):
        """Test powr function generates extern declaration."""
        code = self.generate_llvm("x = powr(2, 3)")
        assert "declare i16 @powr(i16, i16)" in code

    def test_math_function_min_max(self):
        """Test min/max functions generate extern declarations."""
        code = self.generate_llvm("x = min(a, b)\ny = max(c, d)")
        assert "declare i16 @min(i16, i16)" in code
        assert "declare i16 @max(i16, i16)" in code

    def test_random_functions(self):
        """Test random functions generate extern declarations."""
        code = self.generate_llvm("x = rand()\ny = rndr(1, 10)\nrandomize(42)")
        assert "declare i16 @rand()" in code
        assert "declare i16 @rndr(i16, i16)" in code
        assert "declare void @randomize(i16)" in code

    def test_string_functions(self):
        """Test string functions generate extern declarations."""
        code = self.generate_llvm('x = strlen("hello")\nstrcpy(a, b)\nstrcat(c, d)')
        assert "declare i16 @strlen(i8*)" in code
        assert "declare void @strcpy(i8*, i8*)" in code
        assert "declare void @strcat(i8*, i8*)" in code

    def test_string_functions_streq(self):
        """Test strcmp function generates extern declaration."""
        code = self.generate_llvm('x = strcmp(a, b, 5)')
        assert "declare i16 @strcmp(i8*, i8*, i16)" in code

    def test_memory_access_functions(self):
        """Test memread/memwrite generate extern declarations."""
        code = self.generate_llvm("x = memread(0x100)\nmemwrite(0x200, y)")
        assert "declare i16 @memread(i16)" in code
        assert "declare void @memwrite(i16, i16)" in code

    def test_graphics_functions(self):
        """Test graphics functions generate proper LLVM IR."""
        code = self.generate_llvm("clrdraw\npxlon(10, 20, 31)")
        assert "declare void @clrdraw()" in code
        assert "declare void @pxlon(i16, i16, i16)" in code

    def test_sound_functions(self):
        """Test sound functions generate proper LLVM IR."""
        code = self.generate_llvm("playtone(440, 1000, 128)\nstopsound")
        assert "declare void @playtone(i16, i16, i16)" in code
        assert "declare void @stopsound()" in code

    def test_input_output_functions(self):
        """Test input/disp functions generate proper LLVM IR."""
        code = self.generate_llvm('disp("Hello")\ngetkey')
        assert "declare void @disp(i8*)" in code
        assert "declare i16 @getkey()" in code

    def test_serial_functions(self):
        """Test serial functions generate proper LLVM IR."""
        code = self.generate_llvm("serout(a)\nserin(x)\nserstat(status)")
        assert "declare void @serout(i16)" in code
        assert "declare i16 @serin()" in code
        assert "declare i16 @serstat()" in code

    def test_user_function(self):
        """Test user function generates proper LLVM IR."""
        code = self.generate_llvm("""
        function add(a, b)
            return a + b
        end
        x = add(1, 2)
        """)
        assert "define i16 @_func_add" in code
        assert "@_func_add" in code
        assert "ret i16 0" not in code.split("}")[0]  # No double ret in function

    def test_for_loop(self):
        """Test for loop generates proper LLVM IR."""
        code = self.generate_llvm("for i = 1 to 10\npxlon(i, i, 31)\nnext")
        assert "for.cond" in code
        assert "for.body" in code
        assert "for.end" in code

    def test_while_loop(self):
        """Test while loop generates proper LLVM IR."""
        code = self.generate_llvm("while x < 10\nx = x + 1\nend")
        assert "while.cond" in code
        assert "while.body" in code
        assert "while.end" in code

    def test_repeat_loop(self):
        """Test repeat loop generates proper LLVM IR."""
        code = self.generate_llvm("repeat\nx = x + 1\nuntil x = 10")
        assert "repeat.body" in code
        assert "repeat.cond" in code
        assert "repeat.end" in code

    def test_if_else(self):
        """Test if-else generates proper LLVM IR."""
        code = self.generate_llvm("if x > 0 then\ny = 1\nelse\ny = 0\nend")
        assert "if.then" in code
        assert "if.else" in code
        assert "if.end" in code

    def test_comparison_operators(self):
        """Test comparison operators generate proper LLVM IR."""
        code = self.generate_llvm("x = a = b\ny = a <> b\nz = a < b\nw = a > b")
        assert "icmp eq" in code
        assert "icmp ne" in code
        assert "icmp slt" in code
        assert "icmp sgt" in code

    def test_logical_operators(self):
        """Test logical operators generate proper LLVM IR."""
        code = self.generate_llvm("if x and y then\na = 1\nend")
        # Logical AND in conditions generates 'and i1'
        assert "and i1" in code or "icmp ne" in code

    def test_binary_arithmetic(self):
        """Test binary arithmetic operators generate proper LLVM IR."""
        code = self.generate_llvm("x = a + b - c * d")
        assert "add i16" in code
        assert "sub i16" in code
        assert "mul i16" in code

    def test_bitwise_operators(self):
        """Test bitwise operators generate proper LLVM IR."""
        # Use raw strings to avoid escape issues
        code = self.generate_llvm(r"x = a & b" + "\n" + r"y = c | d" + "\n" + r"z = e ^ f")
        assert "and i16" in code
        assert "or i16" in code
        assert "xor i16" in code

    def test_shift_operators(self):
        """Test shift operators generate proper LLVM IR."""
        code = self.generate_llvm("x = a << 2")
        assert "shl i16" in code

    def test_unary_operators(self):
        """Test unary operators generate proper LLVM IR."""
        # NOT in an expression context generates icmp eq + zext
        code = self.generate_llvm("x = not b")
        assert "icmp eq" in code  # NOT becomes icmp eq + zext

    def test_increment_decrement(self):
        """Test increment/decrement operators generate proper LLVM IR."""
        code = self.generate_llvm("x++\ny--\nz = ++w\nt = --v")
        assert "add i16" in code
        assert "sub i16" in code

    def test_string_literal(self):
        """Test string literal generates proper LLVM IR."""
        code = self.generate_llvm('x = "hello"')
        assert "private unnamed_addr constant" in code
        assert "getelementptr" in code

    def test_target_triple(self):
        """Test x86-64 target triple is emitted."""
        code = self.generate_llvm("x = 1")
        assert 'target triple = "x86_64-pc-windows-msvc"' in code

    def test_global_variables(self):
        """Test global variables are emitted."""
        code = self.generate_llvm("x = 1\ny = 2\nz = 3")
        assert "@g_x" in code
        assert "@g_y" in code
        assert "@g_z" in code
        assert "global i16 0" in code

    def test_complex_program(self):
        """Test complex program generates valid LLVM IR."""
        code = self.generate_llvm("""
        clrdraw
        for i = 0 to 255
            pxlon(i, i, 31)
        next
        pause
        """)
        assert "declare void @clrdraw()" in code
        assert "declare void @pxlon" in code
        assert "declare void @pause()" in code
        assert "define i32 @main()" in code