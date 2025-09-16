#!/usr/bin/env python3
"""
Comprehensive Random Function Testing Tool
Tests and debugs random functions throughout the Astrid language pipeline
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from astrid2.lexer.lexer import Lexer
from astrid2.parser.parser import Parser
from astrid2.semantic.analyzer import SemanticAnalyzer
from astrid2.ir.builder import IRBuilder
from astrid2.codegen.pure_stack_generator import PureStackCodeGenerator

def test_random_pipeline():
    """Test random functions through the complete compilation pipeline."""
    
    test_cases = [
        # Test case 1: Basic random
        {
            'name': 'Basic Random',
            'code': """
            void main() {
                int16 x = random();
                set_pixel(100, 100, 15);
            }
            """
        },
        
        # Test case 2: Simple random range
        {
            'name': 'Simple Random Range',
            'code': """
            void main() {
                int16 dice = random_range(1, 6);
                int16 coord = random_range(0, 255);
                set_pixel(coord, coord, dice);
            }
            """
        },
        
        # Test case 3: Random with variables
        {
            'name': 'Random with Variables',
            'code': """
            void main() {
                int16 min_val = 10;
                int16 max_val = 50;
                int16 result = random_range(min_val, max_val);
                set_pixel(result, result, 15);
            }
            """
        },
        
        # Test case 4: Random in expressions
        {
            'name': 'Random in Expressions',
            'code': """
            void main() {
                int16 result = random_range(0, 10) + random_range(20, 30);
                set_pixel(result, result, random_range(1, 31));
            }
            """
        },
        
        # Test case 5: Random in loops
        {
            'name': 'Random in Loops',
            'code': """
            void main() {
                for (int8 i = 0; i < 3; i++) {
                    int16 x = random_range(0, 255);
                    int16 y = random_range(0, 191);
                    set_pixel(x, y, random_range(1, 31));
                }
            }
            """
        },
        
        # Test case 6: Edge cases
        {
            'name': 'Edge Cases',
            'code': """
            void main() {
                int16 edge1 = random_range(0, 255);    // 8-bit boundary
                int16 edge2 = random_range(0, 256);    // Just over 8-bit  
                int16 edge3 = random_range(254, 256);  // Cross boundary
                set_pixel(edge1, edge2 % 192, edge3 % 32);
            }
            """
        }
    ]
    
    print("=== COMPREHENSIVE RANDOM FUNCTION TESTING ===")
    print()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {test_case['name']}")
        print("-" * 50)
        
        try:
            # Lexing
            lexer = Lexer()
            tokens = lexer.tokenize(test_case['code'], f"test_{i}.ast")
            print(f"✓ Lexing successful: {len(tokens)} tokens")
            
            # Check for random tokens
            random_tokens = [t for t in tokens if 'random' in t.value.lower()]
            if random_tokens:
                print(f"  Random tokens found: {[t.value for t in random_tokens]}")
            
            # Parsing
            parser = Parser()
            ast = parser.parse(tokens, f"test_{i}.ast")
            print(f"✓ Parsing successful: {len(ast.declarations)} declarations")
            
            # Semantic analysis
            semantic_analyzer = SemanticAnalyzer()
            semantic_analyzer.analyze(ast)
            
            error_count = len(semantic_analyzer.errors)
            warning_count = len(semantic_analyzer.warnings)
            
            if error_count > 0:
                print(f"✗ Semantic analysis failed: {error_count} errors")
                for error in semantic_analyzer.errors:
                    print(f"    Error: {error}")
                continue
            else:
                print(f"✓ Semantic analysis successful")
                if warning_count > 0:
                    print(f"  Warnings: {warning_count}")
            
            # IR generation
            ir_builder = IRBuilder()
            ir_module = ir_builder.build(ast, semantic_analyzer)
            print(f"✓ IR generation successful: {len(ir_module.functions)} functions")
            
            # Check for random calls in IR
            random_calls = []
            for function in ir_module.functions:
                for block in function.blocks:
                    for instr in block.instructions:
                        if instr.opcode == 'call' and len(instr.operands) > 0:
                            func_name = instr.operands[0]
                            if 'random' in func_name.lower():
                                random_calls.append((func_name, instr.operands[1:]))
            
            if random_calls:
                print(f"  Random calls in IR:")
                for func_name, args in random_calls:
                    print(f"    {func_name}({', '.join(str(arg) for arg in args)})")
            
            # Code generation
            code_generator = PureStackCodeGenerator()
            assembly = code_generator.generate(ir_module)
            print(f"✓ Code generation successful: {len(assembly.split('\\n'))} lines")
            
            # Check for random instructions in assembly
            assembly_lines = assembly.split('\n')
            random_instructions = [line.strip() for line in assembly_lines if 'RND' in line or 'random' in line.lower()]
            
            if random_instructions:
                print(f"  Random instructions in assembly:")
                for instr in random_instructions:
                    print(f"    {instr}")
            
            print("✓ Test case passed!")
            
        except Exception as e:
            print(f"✗ Test case failed: {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    print("=== TESTING COMPLETE ===")

def test_random_instruction_variants():
    """Test different variants of random instructions generated."""
    
    print("=== RANDOM INSTRUCTION VARIANTS TEST ===")
    print()
    
    variants = [
        ('random()', 'RND P0'),
        ('random_range(1, 6)', 'RNDR P0, 1, 6'),
        ('random_range(0, 255)', 'RNDR P0, 0, 255'),
        ('random_range(0, 256)', 'RNDR P0, 0, 256'),
        ('random_range(0, 32767)', 'RNDR P0, 0, 32767'),
    ]
    
    for call, expected in variants:
        print(f"Testing: {call}")
        print(f"Expected: {expected}")
        
        code = f"""
        void main() {{
            int16 result = {call};
            set_pixel(100, 100, 15);
        }}
        """
        
        try:
            # Full compilation
            lexer = Lexer()
            tokens = lexer.tokenize(code, "variant_test.ast")
            
            parser = Parser()
            ast = parser.parse(tokens, "variant_test.ast")
            
            semantic_analyzer = SemanticAnalyzer()
            semantic_analyzer.analyze(ast)
            
            if semantic_analyzer.errors:
                print(f"✗ Compilation failed")
                continue
            
            ir_builder = IRBuilder()
            ir_module = ir_builder.build(ast, semantic_analyzer)
            
            code_generator = PureStackCodeGenerator()
            assembly = code_generator.generate(ir_module)
            
            # Check if expected instruction appears
            if expected in assembly:
                print(f"✓ Correct instruction generated")
            else:
                print(f"✗ Expected instruction not found")
                # Find what was actually generated
                assembly_lines = assembly.split('\n')
                random_lines = [line for line in assembly_lines if 'RND' in line]
                if random_lines:
                    print(f"  Actually generated: {random_lines}")
                else:
                    print(f"  No random instructions found")
        
        except Exception as e:
            print(f"✗ Test failed: {e}")
        
        print()

if __name__ == "__main__":
    test_random_pipeline()
    test_random_instruction_variants()
