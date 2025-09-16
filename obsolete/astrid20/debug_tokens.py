import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from astrid2.lexer.lexer import Lexer

with open('complex_test.ast', 'r') as f:
    source = f.read()

lexer = Lexer()
tokens = lexer.tokenize(source, 'complex_test.ast')

for i, token in enumerate(tokens):
    if token.line >= 20 and token.line <= 25:
        print(f'{i}: Line {token.line}:{token.column} {token.type} "{token.value}"')
