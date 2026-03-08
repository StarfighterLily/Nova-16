"""
Unit tests for the NoBASIC semantic analyzer component.
"""

import pytest
from compiler.semantic.analyzer import SemanticAnalyzer, SymbolTable
from compiler.parser.ast import (
    Program, AssignmentStmt, LiteralExpr, VariableExpr, BinaryExpr,
    IfStmt, ForStmt, RepeatStmt, ListAccessExpr, MatrixAccessExpr, DataType
)
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.utils.error import SemanticError


class TestSemanticAnalyzer:
    """Test cases for the NoBASIC semantic analyzer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.lexer = Lexer()
        self.parser = Parser()
        self.analyzer = SemanticAnalyzer()

    def parse_and_analyze(self, source: str) -> Program:
        """Helper to parse and analyze source code."""
        tokens = self.lexer.tokenize(source)
        program = self.parser.parse(tokens)
        self.analyzer.analyze(program)
        return program

    def test_variable_definition(self):
        """Test that variables are defined on assignment."""
        program = self.parse_and_analyze("x = 42")
        assert "x" in self.analyzer.symbol_table.variables
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

    def test_string_variable_definition(self):
        """Test string variable definition."""
        program = self.parse_and_analyze('s = "hello"')
        assert "s" in self.analyzer.symbol_table.variables
        assert self.analyzer.symbol_table.get_variable_type("s") == DataType.STRING

    def test_variable_reassignment(self):
        """Test variable reassignment changes type."""
        program = self.parse_and_analyze("x = 42\nx = \"hello\"")
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.STRING

    def test_undefined_variable_usage(self):
        """Test using undefined variable defaults to NUMBER."""
        program = self.parse_and_analyze("y = x + 1")
        # x is undefined, should default to NUMBER
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("y") == DataType.NUMBER

    def test_builtin_lists(self):
        """Test that built-in lists L1-L6 are recognized."""
        # This should not raise an error
        program = self.parse_and_analyze("x = L1(1)")
        assert self.analyzer.symbol_table.is_list("L1")

    def test_builtin_matrices(self):
        """Test that built-in matrices are recognized."""
        program = self.parse_and_analyze("x = MatA(1, 1)")
        assert self.analyzer.symbol_table.is_matrix("MatA")

    def test_undefined_list_access(self):
        """Test error for accessing undefined list."""
        with pytest.raises(SemanticError, match="Undefined list"):
            self.parse_and_analyze("x = L99(1)")

    def test_undefined_matrix_access(self):
        """Test error for accessing undefined matrix."""
        with pytest.raises(SemanticError, match="Undefined matrix"):
            self.parse_and_analyze("x = MatZ(1, 1)")

    def test_arithmetic_type_checking(self):
        """Test that arithmetic operations check types."""
        # This should work
        program = self.parse_and_analyze("x = 1 + 2")
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

    def test_string_arithmetic_error(self):
        """Test that string + number is allowed (TI-BASIC concatenation)."""
        program = self.parse_and_analyze('x = "hello" + 1')
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.STRING

    def test_if_statement_analysis(self):
        """Test semantic analysis of if statements."""
        program = self.parse_and_analyze("if x = 1 then y = 2 end")
        # x is used but not defined, y is defined
        assert "y" in self.analyzer.symbol_table.variables
        assert self.analyzer.symbol_table.get_variable_type("y") == DataType.NUMBER

    def test_for_statement_analysis(self):
        """Test semantic analysis of for statements."""
        program = self.parse_and_analyze("for i = 1 to 10 next")
        assert self.analyzer.symbol_table.get_variable_type("i") == DataType.NUMBER

    def test_for_with_body(self):
        """Test for loop with body analysis."""
        program = self.parse_and_analyze("for i = 1 to 10\nx = i + 1\nnext")
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

    def test_while_statement_analysis(self):
        """Test semantic analysis of while statements."""
        program = self.parse_and_analyze("while x < 10\nx = x + 1\nend")
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

    def test_graphics_statements(self):
        """Test semantic analysis of graphics statements."""
        program = self.parse_and_analyze("pxlon(x, y, 31)")
        # Should not raise errors, variables default to NUMBER

    def test_complex_program(self):
        """Test semantic analysis of a complex program."""
        source = """
        clrdraw
        x = 128
        y = 128
        for i = 0 to 255
            pxlon(i, i, 31)
        next
        pause
        """
        program = self.parse_and_analyze(source)
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("y") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("i") == DataType.NUMBER

    def test_expression_types(self):
        """Test various expression type analysis."""
        # Binary expressions
        program = self.parse_and_analyze("x = 1 + 2 * 3")
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

        # Comparison
        program = self.parse_and_analyze("x = a = b")
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

        # Logical
        program = self.parse_and_analyze("x = (a = 1) and (b = 2)")
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

    def test_list_access_type(self):
        """Test that list access returns NUMBER type."""
        program = self.parse_and_analyze("x = L1(5)")
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

    def test_matrix_access_type(self):
        """Test that matrix access returns NUMBER type."""
        program = self.parse_and_analyze("x = MatA(1, 2)")
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

    def test_variable_in_expression(self):
        """Test variable usage in expressions."""
        program = self.parse_and_analyze("x = 10\ny = x + 5")
        assert self.analyzer.symbol_table.get_variable_type("y") == DataType.NUMBER

    def test_repeat_statement_analysis(self):
        """Test semantic analysis of repeat statements."""
        program = self.parse_and_analyze("repeat\nx = x + 1\nuntil x = 10")
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

    def test_function_call_type_inference(self):
        """Test type inference for built-in function calls."""
        # Test math functions return NUMBER
        program = self.parse_and_analyze("x = sin(30) + cos(45)")
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

        # Test string functions
        program = self.parse_and_analyze('s = length("hello")')
        assert self.analyzer.symbol_table.get_variable_type("s") == DataType.NUMBER

    def test_complex_type_inference(self):
        """Test complex type inference scenarios."""
        # Mixed operations
        program = self.parse_and_analyze("x = 1 + length(\"test\") * 2")
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

        # Logical operations
        program = self.parse_and_analyze("flag = (x > 0) and (y < 10)")
        assert self.analyzer.symbol_table.get_variable_type("flag") == DataType.NUMBER

    def test_undefined_function_error(self):
        """Test error for calling undefined functions."""
        with pytest.raises(SemanticError, match="Undefined function"):
            self.parse_and_analyze("x = unknown_func(1)")

    def test_wrong_argument_count(self):
        """Test error for wrong number of arguments to functions."""
        with pytest.raises(SemanticError, match="Wrong number of arguments"):
            self.parse_and_analyze("x = sin()")  # sin takes 1 argument

    def test_invalid_list_index_type(self):
        """Test error for non-numeric list indices."""
        with pytest.raises(SemanticError, match="List index must be numeric"):
            self.parse_and_analyze('x = L1("invalid")')

    def test_invalid_matrix_index_type(self):
        """Test error for non-numeric matrix indices."""
        with pytest.raises(SemanticError, match="Matrix indices must be numeric"):
            self.parse_and_analyze('x = MatA("invalid", 1)')

    def test_variable_scope_in_loops(self):
        """Test variable scoping in different loop types."""
        # For loop
        program = self.parse_and_analyze("for i = 1 to 10\nx = i + 1\nnext")
        assert self.analyzer.symbol_table.get_variable_type("i") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

        # While loop
        program = self.parse_and_analyze("while x < 10\ny = x + 1\nend")
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("y") == DataType.NUMBER

        # Repeat loop
        program = self.parse_and_analyze("repeat\nz = z + 1\nuntil z = 5")
        assert self.analyzer.symbol_table.get_variable_type("z") == DataType.NUMBER

    def test_graphics_statement_validation(self):
        """Test semantic validation of graphics statements."""
        # Valid graphics statements should not raise errors
        program = self.parse_and_analyze("pxlon(10, 20, 31)\npxloff(5, 5)\nsetlayer(2)")
        # Should complete without errors

    def test_sound_statement_validation(self):
        """Test semantic validation of sound statements."""
        program = self.parse_and_analyze("playtone(440, 1000, 128)\nplaywave(1, 220, 64)\nstopsound")
        # Should complete without errors

    def test_io_statement_validation(self):
        """Test semantic validation of I/O statements."""
        program = self.parse_and_analyze('getkey\ninput("Enter:", x)\ndisp "Value:"\npause')
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

    def test_goto_label_validation(self):
        """Test validation of goto and labels."""
        # Valid goto/label should work
        program = self.parse_and_analyze("label1:\nx = 1\ngoto label1")
        assert self.analyzer.symbol_table.is_label_defined("label1")
        
        # Undefined label should raise error
        with pytest.raises(SemanticError, match="Undefined label 'label2'"):
            self.parse_and_analyze("goto label2")

    def test_circular_reference_detection(self):
        """Test detection of circular variable references."""
        # This should work (no circular reference)
        program = self.parse_and_analyze("x = y\ny = z\nz = 1")
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

    def test_max_nesting_depth(self):
        """Test handling of deeply nested structures."""
        # Create deeply nested if statements
        nested_source = "if true then\n" * 10 + "x = 1\n" + "end\n" * 10
        program = self.parse_and_analyze(nested_source)
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

    def test_large_symbol_table(self):
        """Test handling of many variables."""
        # Create many variables
        source = "\n".join([f"var{i} = {i}" for i in range(100)])
        program = self.parse_and_analyze(source)
        for i in range(100):
            assert self.analyzer.symbol_table.get_variable_type(f"var{i}") == DataType.NUMBER

    def test_type_consistency_in_expressions(self):
        """Test type consistency checking in complex expressions."""
        # Valid mixed expression
        program = self.parse_and_analyze("result = (a + b) * c - d / e")
        assert self.analyzer.symbol_table.get_variable_type("result") == DataType.NUMBER

        # String concatenation (TI-BASIC style)
        program = self.parse_and_analyze('result = "text" + 1')
        assert self.analyzer.symbol_table.get_variable_type("result") == DataType.STRING

    def test_analyzer_reuse_allows_same_function_name_in_new_program(self):
        """Reusing one analyzer should not leak function definitions across programs."""
        first = self.parser.parse(self.lexer.tokenize("""
        function foo()
            return 1
        end
        x = foo()
        """))
        second = self.parser.parse(self.lexer.tokenize("""
        function foo()
            return 2
        end
        y = foo()
        """))

        self.analyzer.analyze(first)
        self.analyzer.analyze(second)
        assert self.analyzer.symbol_table.get_variable_type("y") == DataType.NUMBER

    def test_analyzer_reuse_clears_pending_gotos_after_failure(self):
        """A failed analysis with unresolved goto must not poison the next analysis."""
        with pytest.raises(SemanticError, match="Undefined label 'missing'"):
            bad_program = self.parser.parse(self.lexer.tokenize("goto missing"))
            self.analyzer.analyze(bad_program)

        good_program = self.parser.parse(self.lexer.tokenize("""
        ok:
        value = 1
        goto ok
        """))
        self.analyzer.analyze(good_program)
        assert self.analyzer.symbol_table.get_variable_type("value") == DataType.NUMBER

    def test_analyzer_reuse_allows_same_struct_name_in_new_program(self):
        """Reusing one analyzer should not leak struct definitions across programs."""
        first = self.parser.parse(self.lexer.tokenize("""
        struct Point x y end
        p.x = 1
        """))
        second = self.parser.parse(self.lexer.tokenize("""
        struct Point x y end
        q.y = 2
        """))

        self.analyzer.analyze(first)
        self.analyzer.analyze(second)
        assert self.analyzer.symbol_table.is_struct("Point")

    def test_local_declaration_in_global_scope_errors(self):
        """LOCAL declarations are invalid at global scope."""
        with pytest.raises(SemanticError, match="Cannot declare LOCAL variable"):
            self.parse_and_analyze("local temp")

    def test_local_declaration_inside_function_is_scoped(self):
        """LOCAL declarations inside functions should be allowed and scoped."""
        self.parse_and_analyze("""
        function bump(x)
            local temp
            temp = x + 1
            return temp
        end
        y = bump(5)
        """)
        assert self.analyzer.symbol_table.get_variable_type("y") == DataType.NUMBER

    def test_duplicate_explicit_global_declaration_errors(self):
        """Duplicate explicit GLOBAL declarations should fail."""
        with pytest.raises(SemanticError, match="already declared as global"):
            self.parse_and_analyze("""
            global score
            global score
            """)

    def test_return_outside_function_errors(self):
        """Return outside of a function should fail semantic analysis."""
        with pytest.raises(SemanticError, match="Return outside of function"):
            self.parse_and_analyze("return 1")

    def test_user_function_default_args_semantics(self):
        """User-defined function calls should honor required and default params."""
        self.parse_and_analyze("""
        function add(a, b = 2)
            return a + b
        end
        x = add(3)
        y = add(3, 4)
        """)
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("y") == DataType.NUMBER

    def test_user_function_default_args_too_few_arguments(self):
        """Calling a user-defined function with too few args should fail."""
        with pytest.raises(SemanticError, match="Wrong number of arguments for function 'add'"):
            self.parse_and_analyze("""
            function add(a, b = 2)
                return a + b
            end
            x = add()
            """)

    def test_function_implicit_assignment_remains_global(self):
        """Implicit assignments in functions should define/update globals by default."""
        self.parse_and_analyze("""
        function setscore(v)
            score = v
            return score
        end
        x = setscore(7)
        y = score + 1
        """)

        assert "score" in self.analyzer.symbol_table.variables
        assert self.analyzer.symbol_table.get_variable_type("score") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("y") == DataType.NUMBER


class TestSymbolTable:
    """Test cases for the SymbolTable class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.lexer = Lexer()
        self.parser = Parser()
        self.analyzer = SemanticAnalyzer()

    def parse_and_analyze(self, source: str) -> Program:
        """Helper to parse and analyze source code."""
        tokens = self.lexer.tokenize(source)
        program = self.parser.parse(tokens)
        self.analyzer.analyze(program)
        return program

    def test_variable_operations(self):
        """Test basic variable operations."""
        table = SymbolTable()
        table.define_variable("x", DataType.NUMBER)
        assert table.get_variable_type("x") == DataType.NUMBER
        assert table.get_variable_type("undefined") == DataType.NUMBER  # Default

    def test_list_operations(self):
        """Test list operations."""
        table = SymbolTable()
        table.lists.add("L1")
        assert table.is_list("L1")
        assert not table.is_list("L2")

    def test_matrix_operations(self):
        """Test matrix operations."""
        table = SymbolTable()
        table.matrices.add("MatA")
        assert table.is_matrix("MatA")
        assert not table.is_matrix("MatB")

    def test_function_call_type_checking(self):
        """Test type checking for function calls."""
        # Valid function calls
        program = self.parse_and_analyze("x = sin(30)\ny = abs(-5)")
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("y") == DataType.NUMBER

    def test_invalid_function_arguments(self):
        """Test error for invalid function arguments."""
        with pytest.raises(SemanticError):
            self.parse_and_analyze('x = sin("text")')  # sin expects number

    def test_string_operations_semantic(self):
        """Test semantic analysis of string operations."""
        program = self.parse_and_analyze('s1 = "hello"\ns2 = "world"\ncombined = s1 + s2')
        assert self.analyzer.symbol_table.get_variable_type("s1") == DataType.STRING
        assert self.analyzer.symbol_table.get_variable_type("combined") == DataType.STRING

    def test_string_length_function(self):
        """Test length function on strings."""
        program = self.parse_and_analyze('s = "hello"\nlen = length(s)')
        assert self.analyzer.symbol_table.get_variable_type("len") == DataType.NUMBER

    def test_invalid_string_length(self):
        """Test length function allows numbers (TI-BASIC style coercion)."""
        program = self.parse_and_analyze("len = length(123)")  # Should work with coercion
        assert self.analyzer.symbol_table.get_variable_type("len") == DataType.NUMBER

    def test_comparison_operations(self):
        """Test semantic analysis of comparison operations."""
        program = self.parse_and_analyze("result = (x = y) and (a < b)")
        assert self.analyzer.symbol_table.get_variable_type("result") == DataType.NUMBER  # Boolean result

    def test_logical_operations(self):
        """Test logical operations."""
        program = self.parse_and_analyze("result = (x > 0) and (y < 10) or not flag")
        assert self.analyzer.symbol_table.get_variable_type("result") == DataType.NUMBER

    def test_array_operations_semantic(self):
        """Test semantic analysis of array operations."""
        program = self.parse_and_analyze("L1(1) = 42\nx = L1(2)")
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

    def test_matrix_operations_semantic(self):
        """Test semantic analysis of matrix operations."""
        program = self.parse_and_analyze("MatA(1, 1) = 3.14\nx = MatA(2, 3)")
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

    def test_goto_label_analysis(self):
        """Test goto and label analysis."""
        program = self.parse_and_analyze("goto label\nlabel:\nx = 1")
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

    def test_undefined_label_error(self):
        """Test error for undefined label."""
        with pytest.raises(SemanticError, match="Undefined label"):
            self.parse_and_analyze("goto nonexistent")

    def test_duplicate_label_error(self):
        """Test error for duplicate labels."""
        with pytest.raises(SemanticError, match="Label already defined"):
            self.parse_and_analyze("label:\nlabel:\nx = 1")

    def test_graphics_function_semantic(self):
        """Test semantic analysis of graphics functions."""
        program = self.parse_and_analyze("pxlon(10, 20, 31)\nline(0, 0, 100, 100, 15)")
        # Should not raise errors for valid graphics calls

    def test_sound_function_semantic(self):
        """Test semantic analysis of sound functions."""
        program = self.parse_and_analyze("playtone(440, 1000, 128)\nplaywave(1, 220, 64)")
        # Should not raise errors for valid sound calls

    def test_io_function_semantic(self):
        """Test semantic analysis of I/O functions."""
        program = self.parse_and_analyze('input("Enter:", x)\ndisp "Result:"')
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

    def test_type_inference_complex(self):
        """Test complex type inference."""
        program = self.parse_and_analyze("""
        a = 1
        b = 2.5
        c = a + b  // Should be NUMBER
        s = "text"
        t = s + "more"  // Should be STRING
        """)
        assert self.analyzer.symbol_table.get_variable_type("c") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("t") == DataType.STRING

    def test_scope_analysis_simple(self):
        """Test basic scope analysis."""
        program = self.parse_and_analyze("""
        x = 1
        if x > 0 then
            y = 2
        end
        z = x + y
        """)
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("y") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("z") == DataType.NUMBER

    def test_loop_variable_analysis(self):
        """Test analysis of loop variables."""
        program = self.parse_and_analyze("""
        for i = 1 to 10
            sum = sum + i
        next
        while j < 100
            j = j + 1
        end
        """)
        assert self.analyzer.symbol_table.get_variable_type("i") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("sum") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("j") == DataType.NUMBER

    def test_function_call_in_expressions(self):
        """Test function calls within expressions."""
        program = self.parse_and_analyze("result = sin(x) + cos(y) * abs(z)")
        assert self.analyzer.symbol_table.get_variable_type("result") == DataType.NUMBER

    def test_builtin_function_return_types(self):
        """Test return types of built-in functions."""
        program = self.parse_and_analyze("""
        num = rand()
        angle = sin(30)
        dist = sqrt(16)
        text_len = length("hello")
        """)
        assert self.analyzer.symbol_table.get_variable_type("num") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("angle") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("dist") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("text_len") == DataType.NUMBER

    def test_type_mismatch_in_assignment(self):
        """Test type checking in assignments."""
        # This should work - dynamic typing
        program = self.parse_and_analyze('x = 1\nx = "text"')
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.STRING

    def test_complex_conditional_expressions(self):
        """Test complex conditional expressions."""
        program = self.parse_and_analyze("""
        result = (x > 0 and y < 10) or (z = 5)
        if result then
            flag = 1
        else
            flag = 0
        end
        """)
        assert self.analyzer.symbol_table.get_variable_type("result") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("flag") == DataType.NUMBER

    def test_error_undefined_function(self):
        """Test error for undefined functions."""
        with pytest.raises(SemanticError, match="Undefined function"):
            self.parse_and_analyze("x = nonexistent(1)")

    def test_error_wrong_argument_count(self):
        """Test error for wrong number of arguments."""
        with pytest.raises(SemanticError, match="Wrong number of arguments"):
            self.parse_and_analyze("x = sin(1, 2, 3)")  # sin takes 1 arg

    def test_nested_function_calls_semantic(self):
        """Test semantic analysis of nested function calls."""
        program = self.parse_and_analyze("result = sin(cos(tan(45)))")
        assert self.analyzer.symbol_table.get_variable_type("result") == DataType.NUMBER

    def test_array_index_bounds_checking(self):
        """Test array index bounds checking (if implemented)."""
        # For now, just check it doesn't crash
        program = self.parse_and_analyze("x = L1(1000)")  # Large index
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

    def test_matrix_bounds_checking(self):
        """Test matrix bounds checking (if implemented)."""
        program = self.parse_and_analyze("x = MatA(100, 200)")  # Large indices
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

    def test_semantic_analysis_performance(self):
        """Test performance of semantic analysis on large programs."""
        # Create a large program
        statements = []
        for i in range(100):
            statements.append(f"var{i} = {i}")
            statements.append(f"result{i} = sin(var{i}) + cos(var{i})")
        source = "\n".join(statements)
        program = self.parse_and_analyze(source)
        # Just check it completes without error
        assert len(program.statements) == 200

    def test_array_semantic_analysis(self):
        """Test semantic analysis of array operations."""
        program = self.parse_and_analyze("L1(5) = 42\nx = L1(10)\nL2(1) = x + 1")
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER

    def test_matrix_semantic_analysis(self):
        """Test semantic analysis of matrix operations."""
        program = self.parse_and_analyze("MatA(1, 2) = 3.14\nval = MatA(2, 1)")
        assert self.analyzer.symbol_table.get_variable_type("val") == DataType.NUMBER

    def test_function_call_semantic_complex(self):
        """Test semantic analysis of complex function calls."""
        program = self.parse_and_analyze("result = sin(cos(30)) + sqrt(abs(-4))")
        assert self.analyzer.symbol_table.get_variable_type("result") == DataType.NUMBER

    def test_string_semantic_analysis(self):
        """Test semantic analysis of string operations."""
        program = self.parse_and_analyze('s = "hello"\nlen = length(s)\nupper = strupr(s)')
        assert self.analyzer.symbol_table.get_variable_type("s") == DataType.STRING
        assert self.analyzer.symbol_table.get_variable_type("len") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("upper") == DataType.STRING

    def test_mixed_type_expressions(self):
        """Test semantic analysis of mixed type expressions."""
        # This should work with dynamic typing
        program = self.parse_and_analyze('x = 1\nx = "text"\ny = x + "more"')
        # x changes type, y should be string
        assert self.analyzer.symbol_table.get_variable_type("y") == DataType.STRING

    def test_graphics_semantic_analysis(self):
        """Test semantic analysis of graphics operations."""
        program = self.parse_and_analyze("clrdraw\npxlon(10, 20, 31)\nsetlayer(1)")
        # Should not raise errors

    def test_sound_semantic_analysis(self):
        """Test semantic analysis of sound operations."""
        program = self.parse_and_analyze("playtone(440, 1000, 128)\nstopsound")
        # Should not raise errors

    def test_io_semantic_analysis(self):
        """Test semantic analysis of I/O operations."""
        program = self.parse_and_analyze("getkey\npause")
        # Should not raise errors

    def test_control_flow_semantic(self):
        """Test semantic analysis of control flow."""
        program = self.parse_and_analyze("""
        if x > 0 then
            positive = 1
        else
            positive = 0
        end
        
        for i = 1 to 10
            sum = sum + i
        next
        """)
        assert self.analyzer.symbol_table.get_variable_type("positive") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("sum") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("i") == DataType.NUMBER

    def test_scope_isolation(self):
        """Test that different scopes don't interfere."""
        program = self.parse_and_analyze("""
        x = 1
        if true then
            x = 2  // This should be the same x
            y = 3  // New variable
        end
        z = x + y  // Should work
        """)
        assert self.analyzer.symbol_table.get_variable_type("z") == DataType.NUMBER

    def test_undefined_variable_in_expression(self):
        """Test handling of undefined variables in expressions."""
        program = self.parse_and_analyze("result = undefined_var + 1")
        # Should default to NUMBER type
        assert self.analyzer.symbol_table.get_variable_type("result") == DataType.NUMBER

    def test_function_return_types(self):
        """Test that function calls have correct return types."""
        functions_and_types = [
            ("sin(30)", DataType.NUMBER),
            ("cos(45)", DataType.NUMBER),
            ("length(\"test\")", DataType.NUMBER),
            ("rand()", DataType.NUMBER),
        ]
        
        for func_call, expected_type in functions_and_types:
            program = self.parse_and_analyze(f"result = {func_call}")
            assert self.analyzer.symbol_table.get_variable_type("result") == expected_type

    def test_complex_expression_types(self):
        """Test type inference in complex expressions."""
        program = self.parse_and_analyze("result = (a + b) * sin(c) / 2")
        assert self.analyzer.symbol_table.get_variable_type("result") == DataType.NUMBER

    def test_array_bounds_semantic(self):
        """Test semantic checking of array bounds (if implemented)."""
        # For now, just check it doesn't crash
        program = self.parse_and_analyze("x = L1(1000)\ny = MatA(100, 200)")
        assert self.analyzer.symbol_table.get_variable_type("x") == DataType.NUMBER
        assert self.analyzer.symbol_table.get_variable_type("y") == DataType.NUMBER

    def test_struct_member_assignment_auto_infers_single_struct(self):
        """Single declared struct should be inferred for member assignments."""
        self.parse_and_analyze("""
        struct Point x y end
        p.x = 5
        q = p.y
        """)

        assert self.analyzer.symbol_table.get_struct_instance_type("p") == "Point"
        assert self.analyzer.symbol_table.get_variable_type("q") == DataType.NUMBER

    def test_struct_member_access_unknown_field_errors(self):
        """Reading an unknown struct field should fail semantic analysis."""
        with pytest.raises(SemanticError, match="has no field"):
            self.parse_and_analyze("""
            struct Point x y end
            p.z = 1
            """)

    def test_struct_member_assignment_requires_numeric_value(self):
        """Struct fields are numeric-only according to language constraints."""
        with pytest.raises(SemanticError, match="Struct fields can only hold numeric values"):
            self.parse_and_analyze("""
            struct Point x y end
            p.x = "hello"
            """)

    def test_struct_member_access_requires_known_instance_when_ambiguous(self):
        """Multiple structs prevent implicit instance inference for member access."""
        with pytest.raises(SemanticError, match="is not a struct instance"):
            self.parse_and_analyze("""
            struct Point x y end
            struct Size w h end
            p.x = 1
            """)

    def test_struct_member_access_is_case_insensitive(self):
        """Struct names and fields should be handled case-insensitively."""
        self.parse_and_analyze("""
        struct Point X Y end
        p.x = 5
        q = P.Y
        """)

        assert self.analyzer.symbol_table.get_struct_instance_type("P") == "Point"
        assert self.analyzer.symbol_table.get_variable_type("q") == DataType.NUMBER

    def test_struct_declaration_rejects_duplicate_fields_case_insensitive(self):
        """Duplicate fields should be rejected even when case differs."""
        with pytest.raises(SemanticError, match="Duplicate field"):
            self.parse_and_analyze("""
            struct Point X x end
            """)

    def test_struct_member_read_auto_infers_single_struct(self):
        """Single declared struct should be inferred for member reads too."""
        self.parse_and_analyze("""
        struct Point x y end
        q = p.x
        """)

        assert self.analyzer.symbol_table.get_struct_instance_type("p") == "Point"
        assert self.analyzer.symbol_table.get_variable_type("q") == DataType.NUMBER

    def test_struct_member_read_requires_known_instance_when_no_struct_defined(self):
        """Member access should fail when no structs exist to infer from."""
        with pytest.raises(SemanticError, match="is not a struct instance"):
            self.parse_and_analyze("q = p.x")

    def test_struct_member_read_unknown_field_errors(self):
        """Reading unknown fields from inferred struct instances should fail."""
        with pytest.raises(SemanticError, match="has no field"):
            self.parse_and_analyze("""
            struct Point x y end
            q = p.z
            """)