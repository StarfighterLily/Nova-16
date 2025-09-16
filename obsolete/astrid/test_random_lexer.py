#!/usr/bin/env python3
"""Test script to debug random function lexing and parsing"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from astrid2.lexer.lexer import Lexer
from astrid2.parser.parser import Parser

def test_lexer():
    """Test lexer with random function calls"""
    lexer = Lexer()
    source = "int16 x = random_range(0, 256);"
    
    print("=== LEXER TEST ===")
    print(f"Source: {source}")
    
    tokens = lexer.tokenize(source, "test.ast")
    
    print("\nTokens:")
    for token in tokens:
        print(f"  {token}")
    
    return tokens

def test_parser():
    """Test parser with random function calls"""
    lexer = Lexer()
    parser = Parser()
    
    source = """
    void main() {
        int16 x = random_range(0, 256);
        int16 y = random_range(0, 256);
        int8 brightness = random_range(0, 15);
        set_pixel(x, y, brightness);
    }
    """
    
    print("\n=== PARSER TEST ===")
    print(f"Source: {source}")
    
    tokens = lexer.tokenize(source, "test.ast")
    print(f"\nTokens generated: {len(tokens)}")
    
    try:
        ast = parser.parse(tokens, "test.ast")
        print("\nAST parsed successfully!")
        print(f"AST type: {type(ast)}")
        print(f"Declarations: {len(ast.declarations)}")
        
        # Try to inspect the main function
        for decl in ast.declarations:
            print(f"Declaration type: {type(decl)}")
            if hasattr(decl, 'name'):
                print(f"Declaration name: {decl.name}")
            if hasattr(decl, 'body'):
                print(f"Body type: {type(decl.body)}")
                if hasattr(decl.body, 'statements'):
                    print(f"Statements: {len(decl.body.statements)}")
                    for i, stmt in enumerate(decl.body.statements):
                        print(f"  Statement {i}: {type(stmt)}")
                        if hasattr(stmt, 'expression'):
                            print(f"    Expression: {type(stmt.expression)}")
                        
    except Exception as e:
        print(f"Parser error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_lexer()
    test_parser()
