"""
Unit tests for the NoBASIC parser component.
"""

import pytest
from compiler.parser.parser import Parser
from compiler.parser.ast import (
    Program, ClrDrawStmt, PxlOnStmt, PxlOffStmt, AssignmentStmt,
    LiteralExpr, VariableExpr, BinaryExpr, IfStmt, ForStmt, WhileStmt,
    PauseStmt, GroupingExpr, RepeatStmt, FunctionCallExpr, ListAccessExpr,
    MatrixAccessExpr, UnaryExpr, GotoStmt, LabelStmt, LineStmt, CircleStmt,
    TextStmt, SRolStmt, SRotStmt, SShftStmt, SFlipStmt,
    PlayToneStmt, PlayWaveStmt, StopSoundStmt, SetChannelStmt,
    GetKeyStmt, InputStmt, DispStmt, VarDeclarationStmt, FunctionDefStmt,
    ReturnStmt, StructDeclarationStmt, MemberAccessExpr, VarScope
)
from compiler.lexer.lexer import Lexer
from compiler.utils.error import ParserError


class TestParser:
    """Test cases for the NoBASIC parser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.lexer = Lexer()
        self.parser = Parser()

    def parse_source(self, source: str) -> Program:
        """Helper to parse source code."""
        tokens = self.lexer.tokenize(source)
        return self.parser.parse(tokens)

    def test_empty_program(self):
        """Test parsing an empty program."""
        program = self.parse_source("")
        assert isinstance(program, Program)
        assert len(program.statements) == 0

    def test_clrdraw_statement(self):
        """Test parsing ClrDraw statement."""
        program = self.parse_source("clrdraw")
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], ClrDrawStmt)

    def test_pxl_on_statement(self):
        """Test parsing PxlOn statement."""
        program = self.parse_source("pxlon(10, 20, 31)")
        assert len(program.statements) == 1
        stmt = program.statements[0]
        assert isinstance(stmt, PxlOnStmt)
        assert isinstance(stmt.x, LiteralExpr)
        assert stmt.x.value == 10
        assert isinstance(stmt.y, LiteralExpr)
        assert stmt.y.value == 20
        assert isinstance(stmt.color, LiteralExpr)
        assert stmt.color.value == 31

    def test_pxl_off_statement(self):
        """Test parsing PxlOff statement."""
        program = self.parse_source("pxloff(10, 20)")
        assert len(program.statements) == 1
        stmt = program.statements[0]
        assert isinstance(stmt, PxlOffStmt)
        assert isinstance(stmt.x, LiteralExpr)
        assert stmt.x.value == 10
        assert isinstance(stmt.y, LiteralExpr)
        assert stmt.y.value == 20

    def test_screen_transform_statements(self):
        """Test parsing screen transform statements."""
        program = self.parse_source("scrroll(0, 5)\nscrrotate(1, 45)\nscrshift(1, 2)\nscrflip(0)")
        assert len(program.statements) == 4

        srol_stmt = program.statements[0]
        assert isinstance(srol_stmt, SRolStmt)
        assert isinstance(srol_stmt.axis, LiteralExpr)
        assert srol_stmt.axis.value == 0
        assert isinstance(srol_stmt.amount, LiteralExpr)
        assert srol_stmt.amount.value == 5

        srot_stmt = program.statements[1]
        assert isinstance(srot_stmt, SRotStmt)
        assert isinstance(srot_stmt.direction, LiteralExpr)
        assert srot_stmt.direction.value == 1
        assert isinstance(srot_stmt.amount, LiteralExpr)
        assert srot_stmt.amount.value == 45

        sshft_stmt = program.statements[2]
        assert isinstance(sshft_stmt, SShftStmt)
        assert isinstance(sshft_stmt.axis, LiteralExpr)
        assert sshft_stmt.axis.value == 1
        assert isinstance(sshft_stmt.amount, LiteralExpr)
        assert sshft_stmt.amount.value == 2

        sflip_stmt = program.statements[3]
        assert isinstance(sflip_stmt, SFlipStmt)
        assert isinstance(sflip_stmt.axis, LiteralExpr)
        assert sflip_stmt.axis.value == 0

    def test_assignment_statement(self):
        """Test parsing assignment statement."""
        program = self.parse_source("x = 42")
        assert len(program.statements) == 1
        stmt = program.statements[0]
        assert isinstance(stmt, AssignmentStmt)
        assert isinstance(stmt.variable, VariableExpr)
        assert stmt.variable.name == "x"
        assert isinstance(stmt.expression, LiteralExpr)
        assert stmt.expression.value == 42

    def test_assignment_with_expression(self):
        """Test parsing assignment with binary expression."""
        program = self.parse_source("x = 10 + 20 * 2")
        assert len(program.statements) == 1
        stmt = program.statements[0]
        assert isinstance(stmt, AssignmentStmt)
        assert isinstance(stmt.variable, VariableExpr)
        assert stmt.variable.name == "x"
        assert isinstance(stmt.expression, BinaryExpr)
        assert stmt.expression.operator == "+"
        assert isinstance(stmt.expression.left, LiteralExpr)
        assert stmt.expression.left.value == 10
        assert isinstance(stmt.expression.right, BinaryExpr)
        assert stmt.expression.right.operator == "*"

    def test_if_statement_simple(self):
        """Test parsing simple if statement."""
        program = self.parse_source("if x = 1 then y = 2 end")
        assert len(program.statements) == 1
        stmt = program.statements[0]
        assert isinstance(stmt, IfStmt)
        assert isinstance(stmt.condition, BinaryExpr)
        assert stmt.condition.operator == "="
        assert isinstance(stmt.then_branch, list)
        assert len(stmt.then_branch) == 1
        assert isinstance(stmt.then_branch[0], AssignmentStmt)
        assert stmt.else_branch is None

    def test_if_statement_with_else(self):
        """Test parsing if-else statement."""
        program = self.parse_source("if x = 1 then y = 2 else y = 3 end")
        assert len(program.statements) == 1
        stmt = program.statements[0]
        assert isinstance(stmt, IfStmt)
        assert isinstance(stmt.then_branch, list)
        assert len(stmt.then_branch) == 1
        assert isinstance(stmt.then_branch[0], AssignmentStmt)
        assert isinstance(stmt.else_branch, list)
        assert len(stmt.else_branch) == 1
        assert isinstance(stmt.else_branch[0], AssignmentStmt)

    def test_for_statement(self):
        """Test parsing for loop."""
        program = self.parse_source("for i = 1 to 10 step 2 next")
        assert len(program.statements) == 1
        stmt = program.statements[0]
        assert isinstance(stmt, ForStmt)
        assert stmt.variable == "i"
        assert isinstance(stmt.start, LiteralExpr)
        assert stmt.start.value == 1
        assert isinstance(stmt.end, LiteralExpr)
        assert stmt.end.value == 10
        assert isinstance(stmt.step, LiteralExpr)
        assert stmt.step.value == 2

    def test_for_statement_no_step(self):
        """Test parsing for loop without step."""
        program = self.parse_source("for i = 1 to 10 next")
        assert len(program.statements) == 1
        stmt = program.statements[0]
        assert isinstance(stmt, ForStmt)
        assert stmt.step is None

    def test_while_statement(self):
        """Test parsing while loop."""
        program = self.parse_source("while x < 10 y = y + 1 end")
        assert len(program.statements) == 1
        stmt = program.statements[0]
        assert isinstance(stmt, WhileStmt)
        assert isinstance(stmt.condition, BinaryExpr)
        assert stmt.condition.operator == "<"
        assert len(stmt.body) == 1
        assert isinstance(stmt.body[0], AssignmentStmt)

    def test_repeat_statement(self):
        """Test parsing Repeat statement."""
        program = self.parse_source("repeat\nx = x + 1\nuntil x = 10")
        assert len(program.statements) == 1
        stmt = program.statements[0]
        assert isinstance(stmt, RepeatStmt)
        assert len(stmt.body) == 1
        assert isinstance(stmt.body[0], AssignmentStmt)
        assert isinstance(stmt.body[0].variable, VariableExpr)
        assert stmt.body[0].variable.name == "x"
        assert isinstance(stmt.condition, BinaryExpr)
        assert stmt.condition.operator == "="
        assert isinstance(stmt.condition.left, VariableExpr)
        assert stmt.condition.left.name == "x"
        assert isinstance(stmt.condition.right, LiteralExpr)
        assert stmt.condition.right.value == 10

    def test_multiple_statements(self):
        """Test parsing multiple statements."""
        program = self.parse_source("clrdraw\nx = 10\npxlon(x, 20, 31)")
        assert len(program.statements) == 3
        assert isinstance(program.statements[0], ClrDrawStmt)
        assert isinstance(program.statements[1], AssignmentStmt)
        assert isinstance(program.statements[2], PxlOnStmt)

    def test_literal_expressions(self):
        """Test parsing literal expressions."""
        # Test number literal
        program = self.parse_source("x = 123")
        expr = program.statements[0].expression
        assert isinstance(expr, LiteralExpr)
        assert expr.value == 123

        # Test string literal
        program = self.parse_source('x = "hello"')
        expr = program.statements[0].expression
        assert isinstance(expr, LiteralExpr)
        assert expr.value == "hello"

    def test_variable_expressions(self):
        """Test parsing variable expressions."""
        program = self.parse_source("x = y")
        expr = program.statements[0].expression
        assert isinstance(expr, VariableExpr)
        assert expr.name == "y"

    def test_binary_expressions(self):
        """Test parsing binary expressions."""
        program = self.parse_source("x = a + b * c")
        expr = program.statements[0].expression
        assert isinstance(expr, BinaryExpr)
        assert expr.operator == "+"
        assert isinstance(expr.left, VariableExpr)
        assert expr.left.name == "a"
        assert isinstance(expr.right, BinaryExpr)
        assert expr.right.operator == "*"

    def test_operator_precedence(self):
        """Test operator precedence."""
        program = self.parse_source("x = 1 + 2 * 3")
        expr = program.statements[0].expression
        # Should be 1 + (2 * 3)
        assert isinstance(expr, BinaryExpr)
        assert expr.operator == "+"
        assert isinstance(expr.right, BinaryExpr)
        assert expr.right.operator == "*"

    def test_parenthesized_expression(self):
        """Test parenthesized expressions."""
        program = self.parse_source("x = (1 + 2) * 3")
        expr = program.statements[0].expression
        # Should be (1 + 2) * 3
        assert isinstance(expr, BinaryExpr)
        assert expr.operator == "*"
        assert isinstance(expr.left, GroupingExpr)
        assert isinstance(expr.left.expression, BinaryExpr)
        assert expr.left.expression.operator == "+"
        assert isinstance(expr.right, LiteralExpr)
        assert expr.right.value == 3

    def test_function_call(self):
        """Test parsing function calls."""
        program = self.parse_source("x = sin(30)")
        expr = program.statements[0].expression
        assert isinstance(expr, FunctionCallExpr)
        assert expr.name == "sin"
        assert len(expr.arguments) == 1
        assert isinstance(expr.arguments[0], LiteralExpr)
        assert expr.arguments[0].value == 30

    def test_complex_program(self):
        """Test parsing a complex program."""
        source = """
        clrdraw
        x = 128
        y = 128
        for i = 0 to 255
            pxlon(i, i, 31)
        next
        pause
        """
        program = self.parse_source(source)
        assert len(program.statements) == 5  # clrdraw, x=, y=, for, pause
        assert isinstance(program.statements[0], ClrDrawStmt)
        assert isinstance(program.statements[1], AssignmentStmt)
        assert isinstance(program.statements[2], AssignmentStmt)
        assert isinstance(program.statements[3], ForStmt)
        assert isinstance(program.statements[4], PauseStmt)
        # Check for loop body
        for_stmt = program.statements[3]
        assert len(for_stmt.body) == 1
        assert isinstance(for_stmt.body[0], PxlOnStmt)

    def test_parse_error_unexpected_token(self):
        """Test error for unexpected token."""
        with pytest.raises(ParserError):
            self.parse_source("unexpected")

    def test_parse_error_missing_end(self):
        """Test error for missing end keyword."""
        with pytest.raises(ParserError):
            self.parse_source("if x = 1 then y = 2")  # Missing end or else

    def test_nested_if_statements(self):
        """Test nested if statements."""
        program = self.parse_source("if x = 1 then if y = 2 then z = 3 end end")
        assert len(program.statements) == 1
        outer_if = program.statements[0]
        assert isinstance(outer_if, IfStmt)
        assert len(outer_if.then_branch) == 1
        inner_if = outer_if.then_branch[0]
        assert isinstance(inner_if, IfStmt)

    def test_complex_expressions(self):
        """Test complex nested expressions."""
        program = self.parse_source("x = (a + b) * (c - d) / e")
        expr = program.statements[0].expression
        assert isinstance(expr, BinaryExpr)
        assert expr.operator == "/"
        assert isinstance(expr.left, BinaryExpr)
        assert expr.left.operator == "*"

    def test_function_call_with_multiple_args(self):
        """Test function calls with multiple arguments."""
        program = self.parse_source("x = max(a, b)")
        expr = program.statements[0].expression
        assert isinstance(expr, FunctionCallExpr)
        assert expr.name == "max"
        assert len(expr.arguments) == 2
        assert isinstance(expr.arguments[0], VariableExpr)
        assert expr.arguments[0].name == "a"
        assert isinstance(expr.arguments[1], VariableExpr)
        assert expr.arguments[1].name == "b"

    def test_array_access_expressions(self):
        """Test array/list access expressions."""
        program = self.parse_source("x = L1(5) + MatA(1, 2)")
        expr = program.statements[0].expression
        assert isinstance(expr, BinaryExpr)
        assert isinstance(expr.left, ListAccessExpr)
        assert isinstance(expr.right, MatrixAccessExpr)

    def test_unary_expressions(self):
        """Test unary expressions like NOT and negation."""
        program = self.parse_source("x = not y\nz = -a")
        assert len(program.statements) == 2
        # First statement: x = not y
        not_expr = program.statements[0].expression
        assert isinstance(not_expr, UnaryExpr)
        assert not_expr.operator == "not"
        # Second statement: z = -a
        neg_expr = program.statements[1].expression
        assert isinstance(neg_expr, UnaryExpr)
        assert neg_expr.operator == "-"

    def test_empty_blocks(self):
        """Test control structures with empty blocks."""
        program = self.parse_source("if true then end\nwhile false end\nrepeat until true")
        assert len(program.statements) == 3
        assert isinstance(program.statements[0], IfStmt)
        assert len(program.statements[0].then_branch) == 0
        assert isinstance(program.statements[1], WhileStmt)
        assert len(program.statements[1].body) == 0
        assert isinstance(program.statements[2], RepeatStmt)
        assert len(program.statements[2].body) == 0

    def test_goto_and_labels(self):
        """Test goto statements and labels."""
        program = self.parse_source("label1:\nx = 1\ngoto label1")
        assert len(program.statements) == 3
        assert isinstance(program.statements[0], LabelStmt)
        assert program.statements[0].label == "label1"
        assert isinstance(program.statements[1], AssignmentStmt)
        assert isinstance(program.statements[2], GotoStmt)
        assert program.statements[2].label == "label1"

    def test_graphics_statements_complex(self):
        """Test complex graphics statements."""
        program = self.parse_source("line(0, 0, 100, 100, 31)\ncircle(50, 50, 25, true)\ntext(10, 10, \"Hello\", 15)")
        assert len(program.statements) == 3
        assert isinstance(program.statements[0], LineStmt)
        assert isinstance(program.statements[1], CircleStmt)
        assert isinstance(program.statements[2], TextStmt)

    def test_sound_statements(self):
        """Test sound-related statements."""
        program = self.parse_source("playtone(440, 1000, 128)\nplaywave(1, 220, 64)\nstopsound\nsetchannel(2)")
        assert len(program.statements) == 4
        assert isinstance(program.statements[0], PlayToneStmt)
        assert isinstance(program.statements[1], PlayWaveStmt)
        assert isinstance(program.statements[2], StopSoundStmt)
        assert isinstance(program.statements[3], SetChannelStmt)

    def test_io_statements(self):
        """Test input/output statements."""
        program = self.parse_source('getkey\ninput("Enter value:", x)\ndisp "Result:"\npause')
        assert len(program.statements) == 4
        assert isinstance(program.statements[0], GetKeyStmt)
        assert isinstance(program.statements[1], InputStmt)
        assert isinstance(program.statements[2], DispStmt)
        assert isinstance(program.statements[3], PauseStmt)

    def test_parse_error_missing_semicolon(self):
        """Test error for missing statement separators."""
        # NoBASIC doesn't require semicolons, so this should work
        program = self.parse_source("x = 1 y = 2")
        assert len(program.statements) == 2

    def test_parse_error_invalid_expression(self):
        """Test error for invalid expressions."""
        with pytest.raises(ParserError):
            self.parse_source("x = +")  # Incomplete expression

    def test_parse_error_unclosed_parentheses(self):
        """Test error for unclosed parentheses."""
        with pytest.raises(ParserError):
            self.parse_source("x = (1 + 2")

    def test_parse_error_unmatched_end(self):
        """Test error for unmatched end keywords."""
        with pytest.raises(ParserError):
            self.parse_source("if true then x = 1 end end")

    def test_large_program(self):
        """Test parsing a large program with many statements."""
        large_source = "\n".join([f"x{i} = {i}" for i in range(100)])
        program = self.parse_source(large_source)
        assert len(program.statements) == 100
        for i, stmt in enumerate(program.statements):
            assert isinstance(stmt, AssignmentStmt)
            assert isinstance(stmt.variable, VariableExpr)
            assert stmt.variable.name == f"x{i}"
            assert stmt.expression.value == i

    def test_expression_precedence_complex(self):
        """Test complex operator precedence."""
        program = self.parse_source("x = a + b * c - d / e ^ f")
        expr = program.statements[0].expression
        # Should be: (a + (b * c)) - (d / (e ^ f))
        assert isinstance(expr, BinaryExpr)
        assert expr.operator == "-"
        assert isinstance(expr.left, BinaryExpr)
        assert expr.left.operator == "+"

    def test_nested_function_calls(self):
        """Test nested function calls."""
        program = self.parse_source("x = sin(cos(30))")
        expr = program.statements[0].expression
        assert isinstance(expr, FunctionCallExpr)
        assert expr.name == "sin"
        assert isinstance(expr.arguments[0], FunctionCallExpr)
        assert expr.arguments[0].name == "cos"

    def test_array_access_complex(self):
        """Test complex array access expressions."""
        program = self.parse_source("x = arr[1 + 2] + mat[3, 4]")
        stmt = program.statements[0]
        assert isinstance(stmt.expression, BinaryExpr)
        left = stmt.expression.left
        right = stmt.expression.right
        assert isinstance(left, ListAccessExpr)
        assert isinstance(left.index, BinaryExpr)
        assert isinstance(right, MatrixAccessExpr)

    def test_unary_operators_multiple(self):
        """Test multiple unary operators."""
        program = self.parse_source("x = - - y")
        expr = program.statements[0].expression
        assert isinstance(expr, UnaryExpr)
        assert expr.operator == "-"
        assert isinstance(expr.expression, UnaryExpr)
        assert expr.expression.operator == "-"

    def test_mixed_expressions(self):
        """Test expressions mixing different types."""
        program = self.parse_source("x = (a + func(b)) * (c - d)")
        expr = program.statements[0].expression
        assert isinstance(expr, BinaryExpr)
        assert expr.operator == "*"

    def test_empty_function_call(self):
        """Test function calls with no arguments."""
        program = self.parse_source("x = rand()")
        expr = program.statements[0].expression
        assert isinstance(expr, FunctionCallExpr)
        assert expr.name == "rand"
        assert len(expr.arguments) == 0

    def test_function_call_many_args(self):
        """Test function calls with many arguments."""
        program = self.parse_source("result = max(a, b, c, d, e)")
        expr = program.statements[0].expression
        assert isinstance(expr, FunctionCallExpr)
        assert expr.name == "max"
        assert len(expr.arguments) == 5

    def test_string_concatenation(self):
        """Test string concatenation expressions."""
        program = self.parse_source('x = "hello" + " " + "world"')
        expr = program.statements[0].expression
        assert isinstance(expr, BinaryExpr)
        assert expr.operator == "+"
        assert isinstance(expr.left, BinaryExpr)
        assert isinstance(expr.left.left, LiteralExpr)
        assert expr.left.left.value == "hello"

    def test_complex_if_statement(self):
        """Test complex if-else if chains."""
        source = """
        if x = 1 then
            y = 2
        else if x = 2 then
            y = 3
        else
            y = 4
        end
        """
        program = self.parse_source(source)
        stmt = program.statements[0]
        assert isinstance(stmt, IfStmt)
        assert stmt.else_branch is not None
        # The else if should be parsed as nested if in else

    def test_nested_loops(self):
        """Test nested loop structures."""
        source = """
        for i = 1 to 10
            for j = 1 to 5
                pxlon(i, j, 31)
            next
        next
        """
        program = self.parse_source(source)
        outer_loop = program.statements[0]
        assert isinstance(outer_loop, ForStmt)
        inner_loop = outer_loop.body[0]
        assert isinstance(inner_loop, ForStmt)

    def test_while_with_complex_condition(self):
        """Test while loops with complex conditions."""
        program = self.parse_source("while x > 0 and y < 10\nx = x - 1\nend")
        stmt = program.statements[0]
        assert isinstance(stmt, WhileStmt)
        assert isinstance(stmt.condition, BinaryExpr)
        assert stmt.condition.operator == "and"

    def test_repeat_until_complex(self):
        """Test repeat-until with complex conditions."""
        program = self.parse_source("repeat\nx = x + 1\nuntil x >= 10 or flag = 1")
        stmt = program.statements[0]
        assert isinstance(stmt, RepeatStmt)
        assert isinstance(stmt.condition, BinaryExpr)
        assert stmt.condition.operator == "or"

    def test_goto_and_labels(self):
        """Test goto statements and labels."""
        program = self.parse_source("goto mylabel\nmylabel:\nx = 1")
        assert len(program.statements) == 3
        assert isinstance(program.statements[0], GotoStmt)
        assert isinstance(program.statements[1], LabelStmt)
        assert isinstance(program.statements[2], AssignmentStmt)

    def test_graphics_statements_complex(self):
        """Test complex graphics statements."""
        program = self.parse_source("line(10, 20, 30, 40, 31)\ncircle(50, 50, 25, 15)\ntext(10, 10, \"Hello\", 31)")
        assert len(program.statements) == 3
        assert isinstance(program.statements[0], LineStmt)
        assert isinstance(program.statements[1], CircleStmt)
        assert isinstance(program.statements[2], TextStmt)

    def test_sound_statements_complex(self):
        """Test complex sound statements."""
        program = self.parse_source("playtone(440, 1000, 128)\nplaywave(1, 220, 64)\nsetchannel(2)")
        assert len(program.statements) == 3
        assert isinstance(program.statements[0], PlayToneStmt)
        assert isinstance(program.statements[1], PlayWaveStmt)
        assert isinstance(program.statements[2], SetChannelStmt)

    def test_parse_error_invalid_token(self):
        """Test error for invalid tokens."""
        with pytest.raises(ParserError):
            self.parse_source("x = @invalid")

    def test_parse_error_incomplete_if(self):
        """Test error for incomplete if statements."""
        with pytest.raises(ParserError):
            self.parse_source("if x = 1 then")

    def test_parse_error_incomplete_for(self):
        """Test error for incomplete for loops."""
        with pytest.raises(ParserError):
            self.parse_source("for i = 1 to")

    def test_parse_error_mismatched_brackets(self):
        """Test error for mismatched brackets."""
        with pytest.raises(ParserError):
            self.parse_source("x = arr[1")

    def test_parse_error_invalid_function_call(self):
        """Test error for invalid function calls."""
        with pytest.raises(ParserError):
            self.parse_source("x = func(")

    def test_parse_error_unexpected_eof(self):
        """Test error for unexpected end of file."""
        with pytest.raises(ParserError):
            self.parse_source("if x = 1 then y = 2")

    def test_very_deep_nesting(self):
        """Test very deeply nested expressions."""
        # Create a deeply nested expression
        nested = "x"
        for i in range(10):
            nested = f"({nested} + 1)"
        program = self.parse_source(f"y = {nested}")
        assert isinstance(program.statements[0], AssignmentStmt)

    def test_many_statements(self):
        """Test parsing many statements."""
        statements = [f"x{i} = {i}" for i in range(1000)]
        source = "\n".join(statements)
        program = self.parse_source(source)
        assert len(program.statements) == 1000

    def test_whitespace_insensitive(self):
        """Test that parsing is whitespace insensitive."""
        sources = [
            "x=1",
            "x = 1",
            "x\t=\t1",
            "x\n=\n1",
            "  x  =  1  "
        ]
        for source in sources:
            program = self.parse_source(source)
            assert len(program.statements) == 1
            assert isinstance(program.statements[0], AssignmentStmt)

    def test_comments_ignored(self):
        """Test that comments are properly ignored."""
        source = """
        // This is a comment
        x = 1 // Another comment
        // More comments
        y = 2
        """
        program = self.parse_source(source)
        assert len(program.statements) == 2
        assert all(isinstance(stmt, AssignmentStmt) for stmt in program.statements)

    def test_operator_associativity(self):
        """Test operator associativity."""
        program = self.parse_source("x = a - b - c")
        expr = program.statements[0].expression
        # Should be (a - b) - c
        assert isinstance(expr, BinaryExpr)
        assert expr.operator == "-"
        assert isinstance(expr.left, BinaryExpr)
        assert expr.left.operator == "-"
        assert isinstance(expr.right, VariableExpr)

    def test_mixed_number_types(self):
        """Test mixing integer and float literals."""
        program = self.parse_source("x = 1 + 2.5")
        expr = program.statements[0].expression
        assert isinstance(expr, BinaryExpr)
        assert isinstance(expr.left, LiteralExpr)
        assert expr.left.value == 1
        assert isinstance(expr.right, LiteralExpr)
        assert expr.right.value == 2.5

    def test_array_operations_parser(self):
        """Test parsing array operations in expressions."""
        program = self.parse_source("x = L1(5) + L1(10)")
        assert len(program.statements) == 1
        expr = program.statements[0].expression
        assert isinstance(expr, BinaryExpr)
        # Check that left side is array access
        assert isinstance(expr.left, ListAccessExpr)

    def test_matrix_operations_parser(self):
        """Test parsing matrix operations in expressions."""
        program = self.parse_source("x = MatA(2, 3) * MatA(1, 1)")
        assert len(program.statements) == 1
        expr = program.statements[0].expression
        assert isinstance(expr, BinaryExpr)
        assert isinstance(expr.left, MatrixAccessExpr)

    def test_complex_function_calls(self):
        """Test complex function calls with multiple arguments."""
        program = self.parse_source('result = concat("Hello", " ", "World")')
        expr = program.statements[0].expression
        assert isinstance(expr, FunctionCallExpr)
        assert expr.name == "concat"
        assert len(expr.arguments) == 3

    def test_nested_expressions_deep(self):
        """Test very deeply nested expressions."""
        # Create a deeply nested expression
        expr_str = "x"
        for i in range(5):  # Limit depth to avoid stack issues
            expr_str = f"sin({expr_str})"
        program = self.parse_source(f"result = {expr_str}")
        assert isinstance(program.statements[0], AssignmentStmt)

    def test_operator_precedence_complex(self):
        """Test complex operator precedence scenarios."""
        # Test various precedence combinations
        expressions = [
            "a + b * c - d / e",
            "x ^ y * z + w",
            "not a and b or c",
            "a = b <> c < d"
        ]
        
        for expr in expressions:
            program = self.parse_source(f"result = {expr}")
            assert isinstance(program.statements[0], AssignmentStmt)

    def test_string_operations_parser(self):
        """Test parsing string operations."""
        program = self.parse_source('s1 = "hello"\ns2 = "world"\ncombined = s1 + s2\nlen = length(s1)')
        assert len(program.statements) == 4
        # Check that string concatenation and length function work

    def test_graphics_with_expressions(self):
        """Test graphics commands with complex expressions."""
        program = self.parse_source("pxlon(x + 10, y * 2, color / 2)\nline(x1, y1, x2 + 100, y2, 15)")
        assert len(program.statements) == 2
        assert isinstance(program.statements[0], PxlOnStmt)
        assert isinstance(program.statements[1], LineStmt)

    def test_sound_with_expressions(self):
        """Test sound commands with expressions."""
        program = self.parse_source("playtone(freq * 2, duration + 100, volume / 2)")
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], PlayToneStmt)

    def test_io_with_expressions(self):
        """Test I/O commands with expressions."""
        program = self.parse_source('input("Enter " + prompt, variable)\ndisp "Value: " + str(result)')
        assert len(program.statements) == 2
        assert isinstance(program.statements[0], InputStmt)
        assert isinstance(program.statements[1], DispStmt)

    def test_label_and_goto_parser(self):
        """Test label and goto parsing."""
        program = self.parse_source("start:\nx = 1\ngoto start\nend_label:")
        assert len(program.statements) == 4
        assert isinstance(program.statements[0], LabelStmt)
        assert isinstance(program.statements[2], GotoStmt)
        assert isinstance(program.statements[3], LabelStmt)

    def test_empty_control_blocks(self):
        """Test control structures with empty blocks."""
        program = self.parse_source("if true then end\nfor i = 1 to 10 next\nwhile false end")
        assert len(program.statements) == 3

    def test_minimal_programs(self):
        """Test very minimal valid programs."""
        minimal_programs = [
            "x = 1",
            "pause",
            "clrdraw",
            "goto label\nlabel:",
            "if true then end"
        ]
        
        for prog in minimal_programs:
            program = self.parse_source(prog)
            assert isinstance(program, Program)
            assert len(program.statements) >= 1

    def test_global_declaration_multiple_variables(self):
        """Test parsing GLOBAL declarations with multiple variables."""
        program = self.parse_source("global score, lives, level")
        assert len(program.statements) == 1
        stmt = program.statements[0]
        assert isinstance(stmt, VarDeclarationStmt)
        assert stmt.scope == VarScope.GLOBAL
        assert stmt.variables == ["score", "lives", "level"]

    def test_local_declaration_single_variable(self):
        """Test parsing LOCAL declaration."""
        program = self.parse_source("local temp")
        assert len(program.statements) == 1
        stmt = program.statements[0]
        assert isinstance(stmt, VarDeclarationStmt)
        assert stmt.scope == VarScope.LOCAL
        assert stmt.variables == ["temp"]

    def test_function_definition_with_default_parameter(self):
        """Test parsing function definitions with default parameters."""
        source = """
        function add(a, b = 2)
            return a + b
        end
        """
        program = self.parse_source(source)
        assert len(program.statements) == 1
        stmt = program.statements[0]
        assert isinstance(stmt, FunctionDefStmt)
        assert stmt.name == "add"
        assert len(stmt.params) == 2
        assert stmt.params[0][0] == "a"
        assert stmt.params[0][1] is None
        assert stmt.params[1][0] == "b"
        assert isinstance(stmt.params[1][1], LiteralExpr)
        assert stmt.params[1][1].value == 2
        assert len(stmt.body) == 1
        assert isinstance(stmt.body[0], ReturnStmt)

    def test_return_without_value_in_function_body(self):
        """Test parsing Return without expression inside a function."""
        source = """
        function noop()
            return
        end
        """
        program = self.parse_source(source)
        stmt = program.statements[0]
        assert isinstance(stmt, FunctionDefStmt)
        assert isinstance(stmt.body[0], ReturnStmt)
        assert stmt.body[0].value is None

    def test_struct_declaration_and_member_assignment_parse(self):
        """Test parsing struct declaration and member assignment."""
        program = self.parse_source("struct Point x y end\np.x = 1")
        assert len(program.statements) == 2

        struct_stmt = program.statements[0]
        assert isinstance(struct_stmt, StructDeclarationStmt)
        assert struct_stmt.name == "Point"
        assert struct_stmt.fields == ["x", "y"]

        assign_stmt = program.statements[1]
        assert isinstance(assign_stmt, AssignmentStmt)
        assert isinstance(assign_stmt.variable, MemberAccessExpr)
        assert isinstance(assign_stmt.variable.object, VariableExpr)
        assert assign_stmt.variable.object.name == "p"
        assert assign_stmt.variable.member == "x"

    def test_struct_declaration_rejects_more_than_ten_fields(self):
        """Struct declarations should enforce the documented 10-field max."""
        with pytest.raises(ParserError, match="maximum is 10"):
            self.parse_source("struct Big a b c d e f g h i j k end")

    def test_struct_declaration_requires_at_least_one_field(self):
        """Struct declarations should require at least one field."""
        with pytest.raises(ParserError, match="must have at least one field"):
            self.parse_source("struct Empty end")