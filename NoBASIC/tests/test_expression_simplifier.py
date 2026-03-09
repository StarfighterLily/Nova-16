"""Tests for expression simplification and its codegen integration."""

import re

from compiler.codegen.generator import CodeGenerator
from compiler.codegen.optimizations import ExpressionSimplifier
from compiler.lexer.lexer import Lexer
from compiler.parser.ast import BinaryExpr, DataType, FunctionCallExpr, LiteralExpr, VariableExpr
from compiler.parser.parser import Parser
from compiler.semantic.analyzer import SemanticAnalyzer


class TestExpressionSimplifier:
    """Unit tests for tree-level expression simplification."""

    def setup_method(self):
        self.simplifier = ExpressionSimplifier(debug=False)

    def test_constant_folding_nested_expression(self):
        expr = BinaryExpr(
            left=LiteralExpr(2, DataType.NUMBER),
            operator="*",
            right=BinaryExpr(
                left=LiteralExpr(3, DataType.NUMBER),
                operator="+",
                right=LiteralExpr(4, DataType.NUMBER),
            ),
        )

        simplified, cost = self.simplifier.simplify_expression(expr)

        assert isinstance(simplified, LiteralExpr)
        assert simplified.value == 14
        assert cost == 1

    def test_algebraic_identity_rules(self):
        expr = BinaryExpr(
            left=VariableExpr("x"),
            operator="+",
            right=LiteralExpr(0, DataType.NUMBER),
        )

        simplified, _ = self.simplifier.simplify_expression(expr)

        assert isinstance(simplified, VariableExpr)
        assert simplified.name == "x"

    def test_constant_propagation_from_context(self):
        expr = BinaryExpr(
            left=VariableExpr("a"),
            operator="+",
            right=LiteralExpr(3, DataType.NUMBER),
        )

        simplified, _ = self.simplifier.simplify_expression(expr, context={"constants": {"a": 5}})

        assert isinstance(simplified, LiteralExpr)
        assert simplified.value == 8

    def test_cse_lite_reuses_equivalent_subtrees(self):
        left = BinaryExpr(VariableExpr("a"), "+", VariableExpr("b"))
        right = BinaryExpr(VariableExpr("b"), "+", VariableExpr("a"))
        expr = BinaryExpr(left=left, operator="*", right=right)

        simplified, _ = self.simplifier.simplify_expression(expr)

        assert isinstance(simplified, BinaryExpr)
        assert isinstance(simplified.left, BinaryExpr)
        assert simplified.left is simplified.right

    def test_function_calls_are_not_folded(self):
        expr = BinaryExpr(
            left=FunctionCallExpr(name="rnd", arguments=[]),
            operator="+",
            right=LiteralExpr(0, DataType.NUMBER),
        )

        simplified, cost = self.simplifier.simplify_expression(expr)

        assert isinstance(simplified, FunctionCallExpr)
        assert cost >= 1


class TestExpressionSimplifierIntegration:
    """Integration tests that verify simplification is used by code generation."""

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

    def test_codegen_uses_constant_propagation_between_assignments(self):
        code = self.generate_code("a = 5\nb = a + 3")

        assert re.search(r"MOV\s+\w+,\s*8\b", code) or ("MOV R1, 1" in code and "SHL R1, 3" in code)

    def test_codegen_elides_add_zero_operation(self):
        code = self.generate_code("x = 9\ny = x + 0")

        assert "ADD" not in code
