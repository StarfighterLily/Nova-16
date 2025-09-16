#!/usr/bin/env python3
"""
Targeted Bug Validation Script
Tests specific issues found in the comprehensive analysis.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'astrid', 'src'))

from astrid2.lexer.lexer import Lexer
from astrid2.parser.parser import Parser  
from astrid2.semantic.analyzer import SemanticAnalyzer

def test_unsupported_tokens():
    """Test tokens that lexer generates but parser doesn't handle."""
    print("=== Testing Unsupported Tokens ===")
    
    test_cases = [
        ("import test;", "IMPORT token"),
        ("export function;", "EXPORT token"), 
        ("from module;", "FROM token"),
        ("value as alias;", "AS token"),
        ("a << b;", "SHIFT_LEFT token"),
        ("a >> b;", "SHIFT_RIGHT token"),
        ("namespace::item;", "DOUBLE_COLON token"),
        ("uint8 x;", "UINT8 token"),
        ("uint16 y;", "UINT16 token"),
        ("ptr->member;", "ARROW token")
    ]
    
    lexer = Lexer()
    parser = Parser()
    
    for code, description in test_cases:
        print(f"\nTesting {description}: {code}")
        try:
            tokens = lexer.tokenize(code, "test.ast")
            print(f"  ✓ Lexer: Generated {len(tokens)} tokens")
            
            # Try parsing
            ast = parser.parse(tokens, "test.ast")
            print(f"  ✓ Parser: Parsed successfully")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")

def test_missing_string_functions():
    """Test missing string function signatures."""
    print("\n=== Testing Missing String Functions ===")
    
    missing_functions = [
        'strlen("test")',
        'strcpy(dest, src)', 
        'strcat(str1, str2)',
        'strcmp(str1, str2)',
        'strchr("hello", "l")',
        'substr(str, 0, 5)'
    ]
    
    lexer = Lexer()
    parser = Parser()
    semantic = SemanticAnalyzer()
    
    for func_call in missing_functions:
        code = f"void main() {{ {func_call}; }}"
        print(f"\nTesting: {func_call}")
        
        try:
            tokens = lexer.tokenize(code, "test.ast")
            ast = parser.parse(tokens, "test.ast")
            
            semantic.reset_state()
            semantic.analyze(ast)
            
            if semantic.errors:
                print(f"  ✗ Semantic Error: {semantic.errors[0]}")
            else:
                print(f"  ✓ No semantic errors")
                
        except Exception as e:
            print(f"  ✗ Exception: {e}")

def test_unsigned_types():
    """Test unsigned type handling."""
    print("\n=== Testing Unsigned Types ===")
    
    test_cases = [
        "uint8 small = 255;",
        "uint16 large = 65535;", 
        "uint8 a = 10; uint16 b = a;"  # Type conversion
    ]
    
    lexer = Lexer()
    parser = Parser()
    semantic = SemanticAnalyzer()
    
    for code in test_cases:
        print(f"\nTesting: {code}")
        
        try:
            tokens = lexer.tokenize(f"void main() {{ {code} }}", "test.ast")
            ast = parser.parse(tokens, "test.ast")
            
            semantic.reset_state()
            semantic.analyze(ast)
            
            if semantic.errors:
                print(f"  ✗ Semantic Error: {semantic.errors[0]}")
            else:
                print(f"  ✓ No semantic errors")
                
        except Exception as e:
            print(f"  ✗ Exception: {e}")

def test_parser_error_handling():
    """Test parser error handling with malformed input."""
    print("\n=== Testing Parser Error Handling ===")
    
    malformed_cases = [
        "void main( {",  # Missing closing paren
        "if true) {",    # Missing opening paren  
        "int16 = 42;",   # Missing variable name
        "function {}",   # Missing return type and name
    ]
    
    lexer = Lexer()
    parser = Parser()
    
    for code in malformed_cases:
        print(f"\nTesting malformed: {code}")
        
        try:
            tokens = lexer.tokenize(code, "test.ast")
            ast = parser.parse(tokens, "test.ast")
            print(f"  ⚠️ Unexpectedly parsed successfully")
            
        except Exception as e:
            print(f"  ✓ Correctly caught error: {type(e).__name__}")

if __name__ == "__main__":
    print("=== ASTRID TARGETED BUG VALIDATION ===")
    
    test_unsupported_tokens()
    test_missing_string_functions() 
    test_unsigned_types()
    test_parser_error_handling()
    
    print("\n=== VALIDATION COMPLETE ===")
