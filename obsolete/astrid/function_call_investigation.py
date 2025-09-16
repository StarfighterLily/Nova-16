#!/usr/bin/env python3
"""
Comprehensive Function Call Investigation Tool for Astrid
Traces through lexer, parser, IR, and code generation to verify function calls work properly
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from astrid2.lexer.lexer import Lexer
from astrid2.parser.parser import Parser
from astrid2.semantic.analyzer import SemanticAnalyzer
from astrid2.ir.builder import IRBuilder
from astrid2.codegen.pure_stack_generator import PureStackCodeGenerator

def trace_function_calls(source_file):
    """Trace function calls through the entire compilation pipeline"""
    
    print("="*80)
    print("ASTRID FUNCTION CALL INVESTIGATION")
    print("="*80)
    
    # Read source file
    with open(source_file, 'r') as f:
        source_code = f.read()
    
    print(f"Source file: {source_file}")
    print("-" * 40)
    print(source_code)
    print("-" * 40)
    
    # Initialize compiler components
    lexer = Lexer()
    parser = Parser()
    semantic_analyzer = SemanticAnalyzer()
    ir_builder = IRBuilder()
    code_generator = PureStackCodeGenerator()
    
    try:
        # Phase 1: Lexical Analysis
        print("\n1. LEXICAL ANALYSIS")
        print("-" * 20)
        tokens = lexer.tokenize(source_code, source_file)
        
        # Find function calls in tokens
        call_tokens = []
        for i, token in enumerate(tokens):
            if token.type.name == 'IDENTIFIER' and i + 1 < len(tokens) and tokens[i + 1].type.name == 'LPAREN':
                call_tokens.append((token.value, token.line))
        
        print(f"Total tokens: {len(tokens)}")
        print(f"Function calls found in tokens: {call_tokens}")
        
        # Show some tokens around function calls
        print("Tokens around function calls:")
        for i, token in enumerate(tokens):
            if token.type.name == 'IDENTIFIER' and i + 1 < len(tokens) and tokens[i + 1].type.name == 'LPAREN':
                start = max(0, i-2)
                end = min(len(tokens), i+4)
                print(f"  Line {token.line}: {[f'{t.type.name}:{t.value}' for t in tokens[start:end]]}")
        
        # Phase 2: Syntax Analysis
        print("\n2. SYNTAX ANALYSIS")
        print("-" * 20)
        ast = parser.parse(tokens, source_file)
        
        # Find function calls in AST
        def find_function_calls(node, calls=None, visited=None):
            if calls is None:
                calls = []
            if visited is None:
                visited = set()
            
            # Prevent infinite recursion
            node_id = id(node)
            if node_id in visited:
                return calls
            visited.add(node_id)
            
            if hasattr(node, '__class__') and node.__class__.__name__ == 'FunctionCall':
                calls.append(node.name)
            elif hasattr(node, '__class__') and node.__class__.__name__ == 'ExpressionStatement':
                if hasattr(node, 'expression') and hasattr(node.expression, '__class__') and node.expression.__class__.__name__ == 'FunctionCall':
                    calls.append(node.expression.name)
            
            # Recursively search children - but be more careful
            if hasattr(node, '__dict__'):
                for attr_name, attr_value in node.__dict__.items():
                    if attr_name.startswith('_'):  # Skip private attributes
                        continue
                    if isinstance(attr_value, list):
                        for item in attr_value:
                            if hasattr(item, '__dict__'):
                                find_function_calls(item, calls, visited)
                    elif hasattr(attr_value, '__dict__') and not isinstance(attr_value, str):
                        find_function_calls(attr_value, calls, visited)
            
            return calls
        
        ast_calls = find_function_calls(ast)
        print(f"Function calls found in AST: {ast_calls}")
        
        # Show AST structure for main function
        main_func = None
        for func in ast.functions:
            if func.name == 'main':
                main_func = func
                break
        
        if main_func:
            print(f"Main function body has {len(main_func.body)} statements")
            for i, stmt in enumerate(main_func.body):
                print(f"  Statement {i}: {stmt.__class__.__name__}")
                if hasattr(stmt, 'name'):
                    print(f"    Function: {stmt.name}")
        
        # Phase 3: Semantic Analysis
        print("\n3. SEMANTIC ANALYSIS")
        print("-" * 20)
        semantic_analyzer.analyze(ast)
        if semantic_analyzer.errors:
            print(f"Semantic errors: {semantic_analyzer.errors}")
        else:
            print("No semantic errors")
        
        # Phase 4: IR Generation
        print("\n4. IR GENERATION")
        print("-" * 20)
        ir_module = ir_builder.build(ast, semantic_analyzer)
        
        # Find call instructions in IR
        call_instructions = []
        for func in ir_module.functions:
            print(f"Function: {func.name}")
            for block in func.blocks:
                print(f"  Block: {block.name}")
                for instr in block.instructions:
                    print(f"    {instr}")
                    if hasattr(instr, 'op') and instr.op == 'call':
                        call_instructions.append(instr.target)
        
        print(f"Call instructions found in IR: {call_instructions}")
        
        # Phase 5: Code Generation
        print("\n5. CODE GENERATION")
        print("-" * 20)
        assembly = code_generator.generate(ir_module)
        
        # Find CALL instructions in assembly
        assembly_lines = assembly.split('\n')
        call_lines = [line.strip() for line in assembly_lines if 'CALL' in line]
        print(f"CALL instructions in assembly: {call_lines}")
        
        print("\n" + "="*80)
        print("INVESTIGATION COMPLETE")
        print("="*80)
        
        return {
            'token_calls': call_tokens,
            'ast_calls': ast_calls,
            'ir_calls': call_instructions,
            'assembly_calls': call_lines,
            'assembly': assembly
        }
        
    except Exception as e:
        print(f"Error during investigation: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python function_call_investigation.py <source_file.ast>")
        sys.exit(1)
    
    trace_function_calls(sys.argv[1])
