#!/usr/bin/env python3
"""Debug script to analyze the IR and compilation pipeline"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from astrid2.lexer.lexer import Lexer
from astrid2.parser.parser import Parser
from astrid2.semantic.analyzer import SemanticAnalyzer
from astrid2.ir.builder import IRBuilder

def test_ir_generation():
    """Test IR generation for random function calls"""
    source = """
    void main() {
        int16 x = random_range(0, 256);
        int16 y = random_range(0, 256);
        int8 brightness = random_range(0, 15);
        set_pixel(x, y, brightness);
    }
    """
    
    print("=== IR GENERATION TEST ===")
    print(f"Source: {source}")
    
    # Lexing
    lexer = Lexer()
    tokens = lexer.tokenize(source, "test.ast")
    print(f"Tokens: {len(tokens)}")
    
    # Parsing
    parser = Parser()
    ast = parser.parse(tokens, "test.ast")
    print(f"AST declarations: {len(ast.declarations)}")
    
    # Semantic analysis
    semantic_analyzer = SemanticAnalyzer()
    semantic_analyzer.analyze(ast)
    print("Semantic analysis complete")
    
    # IR generation
    ir_builder = IRBuilder()
    ir_module = ir_builder.build(ast)
    print(f"IR module functions: {len(ir_module.functions)}")
    
    # Examine the IR
    for function in ir_module.functions:
        print(f"\nFunction: {function.name}")
        print(f"Blocks: {len(function.blocks)}")
        for block in function.blocks:
            print(f"  Block: {block.name}")
            print(f"  Instructions: {len(block.instructions)}")
            for i, instr in enumerate(block.instructions):
                print(f"    {i}: {instr.opcode} {instr.operands} -> {instr.result}")

if __name__ == "__main__":
    test_ir_generation()
