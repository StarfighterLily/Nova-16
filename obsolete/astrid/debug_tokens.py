#!/usr/bin/env python3
"""
Debug function call tokenization
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from astrid2.lexer.lexer import Lexer

def debug_tokenization(source_code):
    lexer = Lexer()
    tokens = lexer.tokenize(source_code, "test.ast")
    
    print("All tokens:")
    for i, token in enumerate(tokens):
        print(f"  {i:3d}: {token.type.name:15s} '{token.value}' at line {token.line}")
    
    print("\nLooking for function call patterns:")
    for i, token in enumerate(tokens):
        if token.type.name == 'IDENTIFIER' and i + 1 < len(tokens):
            next_token = tokens[i + 1]
            print(f"  {token.value} followed by {next_token.type.name} '{next_token.value}'")
            if next_token.type.name == 'LPAREN':
                print(f"    *** FUNCTION CALL FOUND: {token.value}()")

# Test simple function calls
test_code = """
void main() {
    draw_layer1();
    draw_layer2();
}
"""

debug_tokenization(test_code)
