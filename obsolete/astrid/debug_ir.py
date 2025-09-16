#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from astrid2.main import AstridCompiler

def debug_gfxtest_ir():
    """Debug the IR generation for gfxtest.ast"""
    
    # Read the source file
    with open('gfxtest.ast', 'r') as f:
        source_code = f.read()
    
    compiler = AstridCompiler()
    
    # Parse to AST
    tokens = compiler.lexer.tokenize(source_code, 'gfxtest.ast')
    ast = compiler.parser.parse(tokens)
    print("=== AST ===")
    print(ast)
    
    # Semantic analysis
    symbol_table = compiler.semantic_analyzer.analyze(ast)
    
    # Build IR
    ir_module = compiler.ir_builder.build(ast, symbol_table)
    print("\n=== IR Module ===")
    for func in ir_module.functions:
        print(f"\nFunction: {func.name}")
        for i, block in enumerate(func.blocks):
            print(f"  Block {i}: {block.name}")
            for j, instr in enumerate(block.instructions):
                print(f"    {j}: {instr}")

if __name__ == "__main__":
    debug_gfxtest_ir()
