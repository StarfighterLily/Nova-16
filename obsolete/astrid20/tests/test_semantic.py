#!/usr/bin/env python3
"""Test suite for Astrid 2.0 semantic analyzer."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from astrid2.lexer.lexer import Lexer
from astrid2.parser.parser import Parser
from astrid2.semantic.analyzer import SemanticAnalyzer, Scope
from astrid2.parser.ast import *

def test_basic_variable_declaration():
    """Test basic variable declaration and type inference."""
    code = "void main() {\n    int8 x = 42;\n    int16 y = 1000;\n}"

    lexer = Lexer()
    tokens = lexer.tokenize(code)

    parser = Parser()
    ast = parser.parse(tokens)

    analyzer = SemanticAnalyzer()
    analyzer.analyze(ast)

    # Check that no errors occurred
    assert len(analyzer.errors) == 0, f"Semantic errors: {analyzer.errors}"

    # Check that main function was added to global scope
    assert 'main' in analyzer.global_scope.symbols
    main_symbol = analyzer.global_scope.symbols['main']
    assert main_symbol.kind == 'function'

    print("PASS: Basic variable declaration test passed")

def test_builtin_function_calls():
    """Test built-in function calls return correct types."""
    code = "void main() {\n    layer l = layer(0);\n    sprite s = sprite(0);\n    sound c = channel(0);\n}"

    lexer = Lexer()
    tokens = lexer.tokenize(code)

    parser = Parser()
    ast = parser.parse(tokens)

    analyzer = SemanticAnalyzer()
    analyzer.analyze(ast)

    # Check that no errors occurred
    assert len(analyzer.errors) == 0, f"Semantic errors: {analyzer.errors}"

    print("PASS: Built-in function calls test passed")

def test_assignment():
    """Test assignment type checking."""
    code = "void main() {\n    int8 x = 42;\n    x = 100;\n}"

    lexer = Lexer()
    tokens = lexer.tokenize(code)

    parser = Parser()
    ast = parser.parse(tokens)

    analyzer = SemanticAnalyzer()
    analyzer.analyze(ast)

    # Check that no errors occurred
    assert len(analyzer.errors) == 0, f"Semantic errors: {analyzer.errors}"

    print("PASS: Assignment test passed")

if __name__ == "__main__":
    test_basic_variable_declaration()
    test_builtin_function_calls()
    test_assignment()
    print("All tests passed!")
