#!/usr/bin/env python3
"""
Test the improved register allocation with multiple scenarios
"""

import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from astrid2.main import AstridCompiler

def test_register_allocation_scenarios():
    """Test various scenarios to verify register allocation improvements"""
    
    scenarios = [
        {
            "name": "Simple function with parameters",
            "code": """
int8 add(int8 x, int8 y) {
    int8 temp = x + y;
    return temp;
}

void main() {
    int8 a = 10;
    int8 b = 20;
    int8 result = add(a, b);
    halt();
}
""",
            "expected_improvements": [
                "Parameters x, y should be in R2, R3",
                "Local var temp should avoid R2, R3",
                "Main function vars should be allocated efficiently"
            ]
        },
        {
            "name": "Multiple function calls",
            "code": """
int8 multiply(int8 x, int8 y) {
    int8 result = 0;
    return result;
}

int8 add(int8 x, int8 y) {
    return x + y;
}

void main() {
    int8 a = 5;
    int8 b = 3;
    int8 sum = add(a, b);
    int8 product = multiply(a, b);
    halt();
}
""",
            "expected_improvements": [
                "Both functions should use R2, R3 for parameters",
                "Local variables should avoid parameter registers",
                "Main should handle multiple calls correctly"
            ]
        },
        {
            "name": "Nested calls",
            "code": """
int8 double_value(int8 x) {
    return x + x;
}

int8 add_and_double(int8 a, int8 b) {
    int8 sum = a + b;
    return double_value(sum);
}

void main() {
    int8 result = add_and_double(5, 3);
    halt();
}
""",
            "expected_improvements": [
                "Parameter registers properly managed across nested calls",
                "No conflicts between caller and callee variables"
            ]
        }
    ]
    
    compiler = AstridCompiler()
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"=== SCENARIO {i}: {scenario['name']} ===")
        print("Code:")
        print(scenario["code"])
        print()
        
        try:
            assembly_code = compiler.compile(scenario["code"], f"test_scenario_{i}.ast")
            print("Generated Assembly:")
            print(assembly_code)
            print()
            
            # Analyze register usage
            lines = assembly_code.split('\n')
            
            # Find function definitions and their register usage
            functions = {}
            current_function = None
            
            for line in lines:
                line = line.strip()
                if line.endswith(':') and not line.startswith(';') and line not in ['entry:', 'STI']:
                    current_function = line[:-1]
                    functions[current_function] = []
                elif current_function and any(reg in line for reg in ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']):
                    functions[current_function].append(line)
            
            print("Function Register Analysis:")
            for func_name, instructions in functions.items():
                if func_name in ['main', 'add', 'multiply', 'double_value', 'add_and_double']:
                    print(f"\n{func_name}:")
                    # Look for parameter usage patterns
                    param_usage = []
                    local_usage = []
                    
                    for instr in instructions:
                        if 'R2' in instr or 'R3' in instr:
                            param_usage.append(instr)
                        elif any(reg in instr for reg in ['R0', 'R1', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']):
                            local_usage.append(instr)
                    
                    if param_usage:
                        print(f"  Parameter registers (R2, R3): {len(param_usage)} uses")
                        for instr in param_usage[:3]:
                            print(f"    {instr}")
                    
                    if local_usage:
                        print(f"  Other registers: {len(local_usage)} uses")
                        for instr in local_usage[:3]:
                            print(f"    {instr}")
            
            print("\nExpected improvements:")
            for improvement in scenario["expected_improvements"]:
                print(f"  - {improvement}")
                
        except Exception as e:
            print(f"Compilation failed: {e}")
        
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    test_register_allocation_scenarios()
