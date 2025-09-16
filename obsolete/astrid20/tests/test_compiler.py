#!/usr/bin/env python3
"""Comprehensive test suite for Astrid 2.0 compiler."""

import sys
import os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from astrid2.main import AstridCompiler


class TestCompilerIntegration:
    """Integration tests for the full compiler pipeline."""

    def setup_method(self):
        self.compiler = AstridCompiler()

    def test_basic_program_compilation(self):
        """Test compilation of a basic program."""
        code = """
        void main() {
            int8 x = 42;
            int16 y = 1000;
            if (x > 20) {
                y = y + 1;
            }
        }
        """
        asm = self.compiler.compile(code, "test.ast")
        assert "ORG 0x1000" in asm
        assert "STI" in asm
        assert "main:" in asm
        assert "HLT" in asm

    def test_builtin_graphics_functions(self):
        """Test compilation with graphics builtin functions."""
        code = """
        void main() {
            int8 x = 10;
            int8 y = 20;
            int8 color = 15;
            set_pixel(x, y, color);
        }
        """
        asm = self.compiler.compile(code, "test.ast")
        assert "MOV VX," in asm
        assert "MOV VY," in asm
        assert "SWRITE" in asm

    def test_control_flow_structures(self):
        """Test various control flow structures."""
        code = """
        void main() {
            int8 i = 0;
            while (i < 10) {
                i = i + 1;
            }
            for (int8 j = 0; j < 5; j = j + 1) {
                // loop body
            }
        }
        """
        asm = self.compiler.compile(code, "test.ast")
        # Should compile without errors
        assert len(asm) > 0

    def test_hardware_types(self):
        """Test all hardware-specific types."""
        code = """
        void main() {
            pixel p = 128;
            color c = 0x1F;
            sound s = 220;
            layer l = 1;
            sprite spr = 0;
            interrupt irq = 0;
        }
        """
        asm = self.compiler.compile(code, "test.ast")
        assert len(asm) > 0

    def test_arithmetic_operations(self):
        """Test arithmetic operations."""
        code = """
        void main() {
            int8 a = 10;
            int8 b = 20;
            int8 c = a + b;
            int8 d = a * b;
            int8 e = b - a;
            int8 f = b / a;
        }
        """
        asm = self.compiler.compile(code, "test.ast")
        assert "ADD" in asm or "+" in asm  # Depending on codegen
        assert len(asm) > 0


class TestLexer:
    """Unit tests for the lexer."""

    def test_token_recognition(self):
        """Test that all tokens are properly recognized."""
        from astrid2.lexer.lexer import Lexer
        from astrid2.lexer.tokens import TokenType

        code = "void main() { int8 x = 42; if (x > 20) return; }"
        lexer = Lexer()
        tokens = lexer.tokenize(code)

        # Check for expected token types
        token_types = [t.type for t in tokens]
        assert TokenType.VOID in token_types
        assert TokenType.INT8 in token_types
        assert TokenType.IF in token_types
        assert TokenType.RETURN in token_types


class TestParser:
    """Unit tests for the parser."""

    def test_ast_generation(self):
        """Test that AST is properly generated."""
        from astrid2.lexer.lexer import Lexer
        from astrid2.parser.parser import Parser

        code = "void main() { int8 x = 42; }"
        lexer = Lexer()
        tokens = lexer.tokenize(code)

        parser = Parser()
        ast = parser.parse(tokens)

        assert len(ast.functions) == 1
        assert ast.functions[0].name == "main"


class TestCodeGenerator:
    """Unit tests for code generation."""

    def test_register_allocation(self):
        """Test register allocation works correctly."""
        code = """
        void main() {
            int8 a = 1;
            int8 b = 2;
            int8 c = a + b;
            int16 d = 1000;
            int16 e = d + 1;
        }
        """
        compiler = AstridCompiler()
        asm = compiler.compile(code, "test.ast")

        # Should use R registers for int8 and P registers for int16
        assert "MOV R" in asm  # R registers for int8
        assert "MOV P" in asm  # P registers for int16


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
