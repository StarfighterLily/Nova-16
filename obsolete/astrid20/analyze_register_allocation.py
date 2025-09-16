#!/usr/bin/env python3
"""
Analyze register allocation issues in Astrid compiler
"""

import os
import sys
import tempfile

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from astrid2.main import AstridCompiler

def analyze_register_allocation():
    """Analyze how registers are being allocated vs expected"""
    
    test_code = """
void main() {
    int8 a = 10;
    int8 b = 20;
    int8 c = a + b;
    halt();
}
"""
    
    print("=== REGISTER ALLOCATION ANALYSIS ===")
    print("Test code:")
    print(test_code)
    print()
    
    # Compile to assembly
    compiler = AstridCompiler()
    
    try:
        assembly_code = compiler.compile(test_code, "test_register_allocation.ast")
        print("Generated Assembly:")
        print(assembly_code)
        print()
        
        # Look for register usage patterns
        lines = assembly_code.split('\n')
        register_usage = {}
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith(';') or line.endswith(':'):
                continue
                
            # Look for register references
            for reg in ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']:
                if reg in line:
                    if reg not in register_usage:
                        register_usage[reg] = []
                    register_usage[reg].append(line)
        
        print("Register Usage Analysis:")
        for reg, lines in register_usage.items():
            print(f"{reg}: {len(lines)} uses")
            for line in lines[:3]:  # Show first 3 uses
                print(f"  {line}")
            if len(lines) > 3:
                print(f"  ... and {len(lines)-3} more")
        
        # Check for variable-to-register mapping hints in comments
        print("\nVariable Allocation Hints:")
        for line in lines:
            if ';' in line and any(var in line.lower() for var in ['var', 'variable', 'alloc']):
                print(f"  {line}")
        
    except Exception as e:
        print(f"Compilation failed: {e}")
        return
        
    # Test a function call example
    print("\n=== FUNCTION CALL ANALYSIS ===")
    function_test = """
int8 add(int8 x, int8 y) {
    return x + y;
}

void main() {
    int8 result = add(15, 25);
    halt();
}
"""
    
    print("Function test code:")
    print(function_test)
    print()
    
    try:
        assembly_code = compiler.compile(function_test, "test_function_call.ast")
        print("Generated Assembly:")
        print(assembly_code)
        print()
        
        # Look for function call patterns
        lines = assembly_code.split('\n')
        
        print("Function Call Pattern Analysis:")
        for i, line in enumerate(lines):
            line = line.strip()
            if 'CALL' in line or 'JSR' in line or any(op in line for op in ['69', '0x69']):
                print(f"Line {i}: {line}")
                # Show context
                for j in range(max(0, i-2), min(len(lines), i+3)):
                    marker = ">>>" if j == i else "   "
                    print(f"{marker} {j}: {lines[j].strip()}")
                print()
        
        print("Stack Management:")
        stack_ops = ['PUSH', 'POP', '2E', '2F', '0x2E', '0x2F']
        for i, line in enumerate(lines):
            if any(op in line for op in stack_ops):
                print(f"Line {i}: {line.strip()}")
        
    except Exception as e:
        print(f"Function compilation failed: {e}")

if __name__ == "__main__":
    analyze_register_allocation()
