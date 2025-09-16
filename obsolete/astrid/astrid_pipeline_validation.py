#!/usr/bin/env python3
"""
Astrid Pipeline Validation Script
Tests all major components of the Astrid compiler pipeline for proper functionality.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'astrid', 'src'))

from astrid2.main import AstridCompiler
from astrid2.lexer.lexer import Lexer
from astrid2.parser.parser import Parser
from astrid2.semantic.analyzer import SemanticAnalyzer
from astrid2.ir.builder import IRBuilder
from astrid2.codegen.pure_stack_generator import PureStackCodeGenerator

def test_comprehensive_compilation():
    """Test compilation of various Astrid constructs."""
    
    test_programs = [
        # Basic variable and arithmetic
        """
        void main() {
            int16 x = 42;
            int16 y = x + 10;
            int16 result = y * 2;
        }
        """,
        
        # Control flow
        """
        void main() {
            int16 i = 0;
            for(i = 0; i < 10; i++) {
                if(i % 2 == 0) {
                    set_pixel(i, i, 15);
                }
            }
        }
        """,
        
        # Function calls and string handling
        """
        void main() {
            string msg = "Hello World";
            print_string(msg, 50, 50, 31);
            int16 len = strlen(msg);
        }
        """,
        
        # Hardware access
        """
        void main() {
            int16 rnd = random();
            play_tone(440, 128, 0);
            enable_interrupts();
        }
        """,
        
        # Complex expressions and arrays
        """
        void main() {
            int16 arr[10];
            int16 i = 0;
            for(i = 0; i < 10; i++) {
                arr[i] = i * i;
            }
            
            int16 sum = 0;
            for(i = 0; i < 10; i++) {
                sum = sum + arr[i];
            }
        }
        """
    ]
    
    compiler = AstridCompiler()
    
    for i, program in enumerate(test_programs):
        try:
            print(f"Testing program {i+1}...")
            assembly = compiler.compile(program, f"test_{i+1}.ast", verbose=False)
            
            # Verify assembly is generated
            if not assembly or len(assembly.strip()) == 0:
                print(f"ERROR: Program {i+1} produced empty assembly")
                return False
                
            # Check for essential assembly components
            if "main:" not in assembly:
                print(f"ERROR: Program {i+1} missing main function label")
                return False
                
            if "HLT" not in assembly:
                print(f"ERROR: Program {i+1} missing HLT instruction")
                return False
                
            print(f"  ✅ Program {i+1} compiled successfully")
            
        except Exception as e:
            print(f"ERROR: Program {i+1} failed: {e}")
            return False
    
    return True

def test_visitor_methods():
    """Test that all visitor methods work properly."""
    
    ir_builder = IRBuilder()
    
    # Check that all expected visitor methods exist
    expected_methods = [
        'visit_program', 'visit_function_declaration', 'visit_variable_declaration',
        'visit_assignment', 'visit_return_statement', 'visit_expression_statement',
        'visit_block_statement', 'visit_if_statement', 'visit_while_statement',
        'visit_for_statement', 'visit_function_call', 'visit_ternary_op',
        'visit_switch_statement', 'visit_break_statement', 'visit_continue_statement',
        'visit_binary_op', 'visit_unary_op', 'visit_literal', 'visit_variable',
        'visit_array_access', 'visit_member_access', 'visit_hardware_access',
        'visit_struct_declaration'
    ]
    
    missing_methods = []
    for method in expected_methods:
        if not hasattr(ir_builder, method):
            missing_methods.append(method)
    
    if missing_methods:
        print(f"ERROR: Missing IR builder methods: {missing_methods}")
        return False
    
    print("✅ All visitor methods present")
    return True

def test_semantic_analyzer():
    """Test semantic analyzer functionality."""
    
    analyzer = SemanticAnalyzer()
    
    # Test type compatibility
    from astrid2.parser.ast import Type
    
    test_cases = [
        (Type.INT8, Type.INT16, True),    # int8 to int16 promotion
        (Type.PIXEL, Type.INT8, True),    # pixel with int8
        (Type.COLOR, Type.INT8, True),    # color with int8
        (Type.UINT8, Type.INT8, True),    # uint8 with int8
        (Type.VOID, Type.INT8, True),     # void compatibility
        (Type.STRING, Type.INT8, False),  # incompatible types
    ]
    
    for left, right, expected in test_cases:
        result = analyzer._type_compatible(left, right)
        if result != expected:
            print(f"ERROR: Type compatibility {left} <-> {right} expected {expected}, got {result}")
            return False
    
    print("✅ Semantic analyzer type compatibility working")
    
    # Test builtin function signatures
    missing_signatures = []
    for func_name in ['strlen', 'strcpy', 'print_string', 'set_pixel', 'random']:
        if func_name not in analyzer.builtin_signatures:
            missing_signatures.append(func_name)
    
    if missing_signatures:
        print(f"ERROR: Missing builtin signatures: {missing_signatures}")
        return False
    
    print("✅ Builtin function signatures complete")
    return True

def test_error_handling():
    """Test error handling in all components."""
    
    compiler = AstridCompiler()
    
    # Test lexer error handling
    try:
        compiler.compile("void main() { string s = \"unterminated string; }", "test.ast")
        print("ERROR: Lexer should have failed on unterminated string")
        return False
    except Exception:
        print("✅ Lexer error handling working")
    
    # Test parser error handling
    try:
        compiler.compile("void main() { if (condition { missing paren }", "test.ast")
        print("ERROR: Parser should have failed on syntax error")
        return False
    except Exception:
        print("✅ Parser error handling working")
    
    # Test semantic error handling
    try:
        compiler.compile("void main() { undefined_function(); }", "test.ast")
        print("ERROR: Semantic analyzer should have failed on undefined function")
        return False
    except Exception:
        print("✅ Semantic analyzer error handling working")
    
    return True

def main():
    """Run all validation tests."""
    print("=== ASTRID PIPELINE VALIDATION ===")
    print()
    
    tests = [
        ("Visitor Methods", test_visitor_methods),
        ("Semantic Analyzer", test_semantic_analyzer),
        ("Error Handling", test_error_handling),
        ("Comprehensive Compilation", test_comprehensive_compilation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Running {test_name} test...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} test passed")
            else:
                print(f"❌ {test_name} test failed")
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
        print()
    
    print(f"=== RESULTS: {passed}/{total} tests passed ===")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Astrid pipeline is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
