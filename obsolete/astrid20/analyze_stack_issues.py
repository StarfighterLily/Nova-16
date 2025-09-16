#!/usr/bin/env python3
"""
Analyze and fix stack underflow issues in function calls
"""

import os
import sys
import tempfile

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from astrid2.main import AstridCompiler

def analyze_stack_issues():
    """Analyze the stack management in function calls"""
    
    function_test = """
int8 add(int8 x, int8 y) {
    return x + y;
}

void main() {
    int8 result = add(15, 25);
    halt();
}
"""
    
    print("=== STACK MANAGEMENT ANALYSIS ===")
    print("Function test code:")
    print(function_test)
    print()
    
    # Compile to assembly
    compiler = AstridCompiler()
    
    try:
        assembly_code = compiler.compile(function_test, "test_stack_analysis.ast")
        print("Generated Assembly:")
        print(assembly_code)
        print()
        
        # Analyze stack operations line by line
        lines = assembly_code.split('\n')
        
        print("Stack Operation Analysis:")
        stack_depth = 0
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith(';'):
                continue
                
            if 'PUSH' in line:
                stack_depth += 1
                print(f"Line {i}: {line} -> Stack depth: +{stack_depth}")
            elif 'POP' in line:
                stack_depth -= 1
                print(f"Line {i}: {line} -> Stack depth: -{stack_depth}")
            elif 'CALL' in line:
                print(f"Line {i}: {line} -> Function call (should push return address)")
            elif 'RET' in line:
                print(f"Line {i}: {line} -> Return (should pop return address)")
            elif line.endswith(':') and 'main' in line:
                print(f"Line {i}: {line} -> Main function start")
            elif line.endswith(':') and 'add' in line:
                print(f"Line {i}: {line} -> Add function start")
        
        print(f"\nFinal theoretical stack depth: {stack_depth}")
        
        # Look for stack pointer initialization
        print("\nStack Pointer Analysis:")
        for i, line in enumerate(lines):
            if 'P8' in line or 'SP' in line or 'FP' in line:
                print(f"Line {i}: {line}")
        
        # Check for frame pointer setup
        print("\nFrame Pointer Setup:")
        for i, line in enumerate(lines):
            if 'FP' in line:
                print(f"Line {i}: {line}")
                
    except Exception as e:
        print(f"Compilation failed: {e}")

def analyze_simple_stack_test():
    """Test even simpler stack operations"""
    
    simple_test = """
void test_func() {
    return;
}

void main() {
    test_func();
    halt();
}
"""
    
    print("\n=== SIMPLE STACK TEST ===")
    print("Simple test code:")
    print(simple_test)
    print()
    
    compiler = AstridCompiler()
    
    try:
        assembly_code = compiler.compile(simple_test, "test_simple_stack.ast")
        print("Generated Assembly:")
        print(assembly_code)
        print()
        
    except Exception as e:
        print(f"Simple test compilation failed: {e}")

if __name__ == "__main__":
    analyze_stack_issues()
    analyze_simple_stack_test()
