#!/usr/bin/env python3

import sys
import os

# Add the astrid src directory to the path
astrid_src = os.path.join(os.path.dirname(__file__), 'astrid', 'src')
sys.path.insert(0, astrid_src)

from astrid2.ir.builder import IRBuilder
from astrid2.lexer.lexer import Lexer  
from astrid2.parser.parser import Parser

code = '''
void main() {
    int16 x = 25;
    int16 y = 50;
}
'''

lexer = Lexer()
tokens = lexer.tokenize(code)
parser = Parser()
ast = parser.parse(tokens)
ir_builder = IRBuilder()
ir = ir_builder.build(ast)

print("Functions:", ir.functions)
if ir.functions:
    for func in ir.functions:
        print(f"Function {func.name}:")
        print(f"  Blocks: {func.blocks}")
        for i, block in enumerate(func.blocks):
            print(f"  Block {i}:")
            if hasattr(block, 'instructions'):
                for j, instr in enumerate(block.instructions):
                    print(f'    {j:2d}: {instr}')
            else:
                print(f"    Block attributes: {dir(block)}")
