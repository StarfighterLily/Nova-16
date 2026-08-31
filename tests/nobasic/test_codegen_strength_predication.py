"""Targeted tests for strength reduction and predicated comparison lowering."""

from compiler.codegen.generator import CodeGenerator
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.analyzer import SemanticAnalyzer


class TestCodegenStrengthPredication:
    def setup_method(self):
        self.lexer = Lexer()
        self.parser = Parser()
        self.analyzer = SemanticAnalyzer()
        self.generator = CodeGenerator()

    def generate_code(self, source: str) -> str:
        tokens = self.lexer.tokenize(source)
        program = self.parser.parse(tokens)
        self.analyzer.analyze(program)
        return self.generator.generate(program)

    def non_comment_lines(self, code: str) -> list[str]:
        return [line.strip() for line in code.splitlines() if line.strip() and not line.strip().startswith(";")]

    def test_strength_reduction_uses_shift_for_right_power_of_two_factor(self):
        code = self.generate_code("x = y * 8")
        lines = self.non_comment_lines(code)

        assert any(line == "SHL P1, 3" or line.endswith("SHL P1, 3") for line in lines) or any("SHL" in line and ", 3" in line for line in lines)
        assert not any(line.startswith("MUL") or " MUL " in line for line in lines)

    def test_strength_reduction_uses_shift_for_left_power_of_two_factor(self):
        code = self.generate_code("x = 8 * y")
        lines = self.non_comment_lines(code)

        assert any("SHL" in line and ", 3" in line for line in lines)
        assert not any(line.startswith("MUL") or " MUL " in line for line in lines)

    def test_division_by_power_of_two_stays_as_division(self):
        code = self.generate_code("x = y / 8")
        lines = self.non_comment_lines(code)

        assert any("DIV" in line for line in lines)
        assert not any("SHR" in line and ", 3" in line for line in lines)

    def test_equality_comparison_materializes_boolean_with_movz(self):
        code = self.generate_code("result = a = b")
        lines = self.non_comment_lines(code)

        assert any(line.startswith("CMP ") for line in lines)
        assert any(line.startswith("MOVZ ") for line in lines)
        assert not any(line.startswith("JZ ") or line.startswith("JMP ") for line in lines)

    def test_inequality_comparison_materializes_boolean_with_movnz(self):
        code = self.generate_code("result = a <> b")
        lines = self.non_comment_lines(code)

        assert any(line.startswith("CMP ") for line in lines)
        assert any(line.startswith("MOVNZ ") for line in lines)
        assert not any(line.startswith("JNZ ") or line.startswith("JMP ") for line in lines)

    def test_matrix_access_uses_shift_add_for_fixed_offsets(self):
        code = self.generate_code("x = MatA(1, 2)")
        lines = self.non_comment_lines(code)

        assert "MUL P3, 20" not in code
        assert "MUL P4, 2" not in code
        assert "SHL P3, 4" in code
        assert "SHL P4, 2" in code
        assert any(line == "SHL P4, 1" for line in lines)
        assert any(line == "ADD P3, P4" for line in lines)

    def test_list_builtins_use_shift_based_index_scaling(self):
        code = self.generate_code("fill(L1, 7)\ntotal = sum(L1)\navg = mean(L1)\nseq(L1, N, 1, 5)\nreverse(L1)")

        assert "MUL P1, 2" not in code
        assert "MUL P0, 2" not in code
        assert "MUL P3, 2" not in code
        assert code.count("SHL P1, 1") >= 3
        assert code.count("SHL P0, 1") >= 2
        assert "SHL P3, 1" in code

    def test_list_runtime_helper_uses_shift_based_scaling(self):
        code = self.generate_code("L1(1) = 10\nx = L1(2)")

        assert "_nb_list_elem_addr:" in code
        assert "MUL P2, 2" not in code
        assert "MUL P0, 2" not in code
        assert "SHL P2, 1" in code
        assert code.count("SHL P0, 1") >= 4