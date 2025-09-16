#!/usr/bin/env python3
"""
Astrid Test Generator
Automatically generates test cases for Astrid programs to help identify bugs and edge cases.
"""

import argparse
import sys
import os
import random
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class TestCase:
    """Represents a generated test case."""
    name: str
    description: str
    source_code: str
    expected_behavior: str
    test_category: str
    difficulty: str  # 'basic', 'intermediate', 'advanced'


class AstridTestGenerator:
    """Generates comprehensive test cases for Astrid programs."""
    
    def __init__(self):
        self.nova_dir = Path(__file__).parent
        
        # Astrid language features for test generation
        self.data_types = ['int8', 'int16', 'char', 'string']
        self.operators = ['+', '-', '*', '/', '=', '==', '!=', '<', '>', '<=', '>=']
        self.control_structures = ['if', 'for', 'while']
        self.builtin_functions = [
            'set_pixel', 'set_layer', 'print_string', 'random_range',
            'roll_screen_x', 'roll_screen_y', 'halt'
        ]
        
        # Value ranges for different types
        self.value_ranges = {
            'int8': (0, 255),
            'int16': (0, 65535),
            'char': (32, 126),  # Printable ASCII
            'pixel': (0, 255)
        }
    
    def generate_test_suite(self, test_types: List[str], count_per_type: int = 5) -> List[TestCase]:
        """
        Generate a comprehensive test suite.
        
        Args:
            test_types: Types of tests to generate
            count_per_type: Number of tests per type
            
        Returns:
            List of generated test cases
        """
        test_cases = []
        
        for test_type in test_types:
            for i in range(count_per_type):
                if test_type == 'basic_syntax':
                    test_cases.extend(self._generate_basic_syntax_tests())
                elif test_type == 'variable_operations':
                    test_cases.extend(self._generate_variable_tests())
                elif test_type == 'control_flow':
                    test_cases.extend(self._generate_control_flow_tests())
                elif test_type == 'function_calls':
                    test_cases.extend(self._generate_function_call_tests())
                elif test_type == 'graphics':
                    test_cases.extend(self._generate_graphics_tests())
                elif test_type == 'edge_cases':
                    test_cases.extend(self._generate_edge_case_tests())
                elif test_type == 'performance':
                    test_cases.extend(self._generate_performance_tests())
                elif test_type == 'stress':
                    test_cases.extend(self._generate_stress_tests())
        
        return test_cases
    
    def _generate_basic_syntax_tests(self) -> List[TestCase]:
        """Generate basic syntax validation tests."""
        tests = []
        
        # Simple variable declaration and assignment
        tests.append(TestCase(
            name="basic_variable_declaration",
            description="Test basic variable declaration and assignment",
            source_code="""
void main() {
    int8 x = 42;
    int16 y = 1000;
    char c = 'A';
}
""",
            expected_behavior="Should compile without errors",
            test_category="basic_syntax",
            difficulty="basic"
        ))
        
        # Simple arithmetic
        tests.append(TestCase(
            name="basic_arithmetic",
            description="Test basic arithmetic operations",
            source_code="""
void main() {
    int8 a = 10;
    int8 b = 5;
    int8 sum = a + b;
    int8 diff = a - b;
    int8 prod = a * b;
    int8 quot = a / b;
}
""",
            expected_behavior="Should perform arithmetic correctly",
            test_category="basic_syntax",
            difficulty="basic"
        ))
        
        # Function definition
        tests.append(TestCase(
            name="basic_function",
            description="Test basic function definition",
            source_code="""
int8 add_numbers(int8 a, int8 b) {
    return a + b;
}

void main() {
    int8 result = add_numbers(3, 4);
}
""",
            expected_behavior="Should define and call function correctly",
            test_category="basic_syntax",
            difficulty="basic"
        ))
        
        return tests
    
    def _generate_variable_tests(self) -> List[TestCase]:
        """Generate variable operation tests."""
        tests = []
        
        # Variable scope test
        tests.append(TestCase(
            name="variable_scope",
            description="Test variable scope rules",
            source_code="""
int8 global_var = 100;

void test_function() {
    int8 local_var = 50;
    global_var = local_var + 10;
}

void main() {
    test_function();
}
""",
            expected_behavior="Global and local variables should be handled correctly",
            test_category="variable_operations",
            difficulty="intermediate"
        ))
        
        # Type conversion test
        tests.append(TestCase(
            name="type_conversion",
            description="Test implicit type conversions",
            source_code="""
void main() {
    int8 small = 200;
    int16 big = small;
    int8 converted_back = big;
}
""",
            expected_behavior="Type conversions should work as expected",
            test_category="variable_operations",
            difficulty="intermediate"
        ))
        
        # Array-like operations (if supported)
        tests.append(TestCase(
            name="sequential_assignments",
            description="Test sequential variable assignments",
            source_code="""
void main() {
    int8 arr0 = 1;
    int8 arr1 = 2;
    int8 arr2 = 3;
    int8 arr3 = 4;
    int8 arr4 = 5;
    
    // Simulate array-like access
    int8 sum = arr0 + arr1 + arr2 + arr3 + arr4;
}
""",
            expected_behavior="Sequential assignments should work correctly",
            test_category="variable_operations",
            difficulty="basic"
        ))
        
        return tests
    
    def _generate_control_flow_tests(self) -> List[TestCase]:
        """Generate control flow tests."""
        tests = []
        
        # If-else test
        tests.append(TestCase(
            name="if_else_basic",
            description="Test basic if-else statements",
            source_code="""
void main() {
    int8 x = 10;
    int8 result = 0;
    
    if (x > 5) {
        result = 1;
    } else {
        result = 0;
    }
}
""",
            expected_behavior="If-else should execute correct branch",
            test_category="control_flow",
            difficulty="basic"
        ))
        
        # For loop test
        tests.append(TestCase(
            name="for_loop_basic",
            description="Test basic for loop",
            source_code="""
void main() {
    int8 sum = 0;
    int8 i = 0;
    
    for (i = 0; i < 10; i++) {
        sum = sum + i;
    }
}
""",
            expected_behavior="For loop should iterate correctly",
            test_category="control_flow",
            difficulty="basic"
        ))
        
        # Nested loops test
        tests.append(TestCase(
            name="nested_loops",
            description="Test nested loop structures",
            source_code="""
void main() {
    int8 i = 0;
    int8 j = 0;
    int8 count = 0;
    
    for (i = 0; i < 5; i++) {
        for (j = 0; j < 3; j++) {
            count++;
        }
    }
}
""",
            expected_behavior="Nested loops should execute correctly",
            test_category="control_flow",
            difficulty="intermediate"
        ))
        
        # While loop test
        tests.append(TestCase(
            name="while_loop_basic",
            description="Test basic while loop",
            source_code="""
void main() {
    int8 counter = 0;
    int8 limit = 5;
    
    while (counter < limit) {
        counter++;
    }
}
""",
            expected_behavior="While loop should terminate correctly",
            test_category="control_flow",
            difficulty="basic"
        ))
        
        return tests
    
    def _generate_function_call_tests(self) -> List[TestCase]:
        """Generate function call tests."""
        tests = []
        
        # Recursive function test
        tests.append(TestCase(
            name="recursive_function",
            description="Test recursive function calls",
            source_code="""
int8 factorial(int8 n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

void main() {
    int8 result = factorial(5);
}
""",
            expected_behavior="Recursive function should compute factorial correctly",
            test_category="function_calls",
            difficulty="advanced"
        ))
        
        # Multiple parameter function
        tests.append(TestCase(
            name="multi_parameter_function",
            description="Test function with multiple parameters",
            source_code="""
int16 calculate(int8 a, int8 b, int8 c, int8 d) {
    return a + b * c - d;
}

void main() {
    int16 result = calculate(10, 5, 3, 2);
}
""",
            expected_behavior="Function with multiple parameters should work correctly",
            test_category="function_calls",
            difficulty="intermediate"
        ))
        
        # Function call chain
        tests.append(TestCase(
            name="function_call_chain",
            description="Test chained function calls",
            source_code="""
int8 double_value(int8 x) {
    return x * 2;
}

int8 add_ten(int8 x) {
    return x + 10;
}

void main() {
    int8 result = add_ten(double_value(5));
}
""",
            expected_behavior="Chained function calls should execute in correct order",
            test_category="function_calls",
            difficulty="intermediate"
        ))
        
        return tests
    
    def _generate_graphics_tests(self) -> List[TestCase]:
        """Generate graphics-related tests."""
        tests = []
        
        # Basic pixel setting
        tests.append(TestCase(
            name="basic_pixel_operations",
            description="Test basic pixel setting operations",
            source_code="""
void main() {
    set_layer(1);
    set_pixel(100, 100, 0x1F);
    set_pixel(101, 100, 0x0F);
    set_pixel(102, 100, 0x07);
}
""",
            expected_behavior="Should set pixels on specified layer",
            test_category="graphics",
            difficulty="basic"
        ))
        
        # Graphics loop
        tests.append(TestCase(
            name="graphics_loop",
            description="Test graphics operations in a loop",
            source_code="""
void main() {
    int8 x = 0;
    int8 y = 50;
    
    set_layer(1);
    for (x = 0; x < 100; x++) {
        set_pixel(x, y, x);
    }
}
""",
            expected_behavior="Should draw a horizontal line with gradient colors",
            test_category="graphics",
            difficulty="intermediate"
        ))
        
        # Multiple layers
        tests.append(TestCase(
            name="multiple_layers",
            description="Test operations on multiple graphics layers",
            source_code="""
void main() {
    int8 i = 0;
    
    for (i = 1; i <= 3; i++) {
        set_layer(i);
        set_pixel(50 + i * 10, 50 + i * 10, 0x1F);
    }
}
""",
            expected_behavior="Should set pixels on different layers",
            test_category="graphics",
            difficulty="intermediate"
        ))
        
        return tests
    
    def _generate_edge_case_tests(self) -> List[TestCase]:
        """Generate edge case tests."""
        tests = []
        
        # Boundary value test
        tests.append(TestCase(
            name="boundary_values",
            description="Test boundary values for different types",
            source_code="""
void main() {
    int8 max_int8 = 255;
    int8 min_int8 = 0;
    int16 max_int16 = 65535;
    int16 min_int16 = 0;
    
    int8 overflow_test = max_int8 + 1;
    int8 underflow_test = min_int8 - 1;
}
""",
            expected_behavior="Should handle boundary values correctly",
            test_category="edge_cases",
            difficulty="advanced"
        ))
        
        # Division by zero (should be caught)
        tests.append(TestCase(
            name="division_by_zero",
            description="Test division by zero handling",
            source_code="""
void main() {
    int8 numerator = 10;
    int8 denominator = 0;
    int8 result = numerator / denominator;
}
""",
            expected_behavior="Should handle division by zero gracefully",
            test_category="edge_cases",
            difficulty="advanced"
        ))
        
        # Large loop test
        tests.append(TestCase(
            name="large_loop",
            description="Test loop with large iteration count",
            source_code="""
void main() {
    int16 i = 0;
    int16 sum = 0;
    
    for (i = 0; i < 1000; i++) {
        sum = sum + 1;
    }
}
""",
            expected_behavior="Should handle large loop correctly",
            test_category="edge_cases",
            difficulty="intermediate"
        ))
        
        return tests
    
    def _generate_performance_tests(self) -> List[TestCase]:
        """Generate performance-focused tests."""
        tests = []
        
        # Computational intensive test
        tests.append(TestCase(
            name="computation_intensive",
            description="Test computationally intensive operations",
            source_code="""
int16 fibonacci(int8 n) {
    if (n <= 1) {
        return n;
    }
    return fibonacci(n - 1) + fibonacci(n - 2);
}

void main() {
    int16 result = fibonacci(10);
}
""",
            expected_behavior="Should compute Fibonacci number efficiently",
            test_category="performance",
            difficulty="advanced"
        ))
        
        # Memory intensive test
        tests.append(TestCase(
            name="memory_intensive",
            description="Test memory-intensive operations",
            source_code="""
void main() {
    int8 var1 = 1, var2 = 2, var3 = 3, var4 = 4, var5 = 5;
    int8 var6 = 6, var7 = 7, var8 = 8, var9 = 9, var10 = 10;
    
    int8 sum = var1 + var2 + var3 + var4 + var5 + var6 + var7 + var8 + var9 + var10;
}
""",
            expected_behavior="Should handle multiple variables efficiently",
            test_category="performance",
            difficulty="intermediate"
        ))
        
        return tests
    
    def _generate_stress_tests(self) -> List[TestCase]:
        """Generate stress tests."""
        tests = []
        
        # Deep nesting test
        tests.append(TestCase(
            name="deep_nesting",
            description="Test deeply nested control structures",
            source_code="""
void main() {
    int8 result = 0;
    int8 i = 0, j = 0, k = 0;
    
    for (i = 0; i < 3; i++) {
        for (j = 0; j < 3; j++) {
            for (k = 0; k < 3; k++) {
                if (i == j) {
                    if (j == k) {
                        result = i + j + k;
                    }
                }
            }
        }
    }
}
""",
            expected_behavior="Should handle deep nesting correctly",
            test_category="stress",
            difficulty="advanced"
        ))
        
        # Many function calls
        tests.append(TestCase(
            name="many_function_calls",
            description="Test many function calls",
            source_code="""
int8 increment(int8 x) {
    return x + 1;
}

void main() {
    int8 value = 0;
    value = increment(value);
    value = increment(value);
    value = increment(value);
    value = increment(value);
    value = increment(value);
    value = increment(value);
    value = increment(value);
    value = increment(value);
    value = increment(value);
    value = increment(value);
}
""",
            expected_behavior="Should handle many function calls efficiently",
            test_category="stress",
            difficulty="intermediate"
        ))
        
        return tests
    
    def run_test_case(self, test_case: TestCase) -> Dict[str, Any]:
        """
        Run a single test case and return results.
        
        Args:
            test_case: The test case to run
            
        Returns:
            Dictionary containing test results
        """
        result = {
            'test_name': test_case.name,
            'passed': False,
            'compilation': {},
            'execution': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # Create temporary test file in astrid directory
            astrid_dir = self.nova_dir / "astrid"
            test_file = astrid_dir / f"temp_test_{test_case.name}.ast"
            with open(test_file, 'w') as f:
                f.write(test_case.source_code)
            
            # Compile the test
            cmd = ["python", "run_astrid.py", test_file.name]
            compile_result = subprocess.run(cmd, cwd=astrid_dir, capture_output=True, text=True)
            
            result['compilation'] = {
                'success': compile_result.returncode == 0,
                'output': compile_result.stdout,
                'errors': compile_result.stderr,
                'return_code': compile_result.returncode
            }
            
            if compile_result.returncode == 0:
                # Try to assemble and run
                asm_file = astrid_dir / f"temp_test_{test_case.name}.asm"
                if asm_file.exists():
                    # Assemble
                    cmd = ["python", "nova_assembler.py", str(asm_file)]
                    asm_result = subprocess.run(cmd, cwd=self.nova_dir, capture_output=True, text=True)
                    
                    if asm_result.returncode == 0:
                        # Execute
                        bin_file = astrid_dir / f"temp_test_{test_case.name}.bin"
                        cmd = ["python", "nova.py", "--headless", str(bin_file), "--cycles", "1000"]
                        exec_result = subprocess.run(cmd, cwd=self.nova_dir, capture_output=True, text=True)
                        
                        result['execution'] = {
                            'success': exec_result.returncode == 0,
                            'output': exec_result.stdout,
                            'errors': exec_result.stderr,
                            'return_code': exec_result.returncode
                        }
                        
                        result['passed'] = exec_result.returncode == 0
                    else:
                        result['errors'].append(f"Assembly failed: {asm_result.stderr}")
                else:
                    result['errors'].append("Assembly file not generated")
            else:
                result['errors'].append(f"Compilation failed: {compile_result.stderr}")
            
            # Cleanup
            for ext in ['.ast', '.asm', '.bin']:
                temp_file = astrid_dir / f"temp_test_{test_case.name}{ext}"
                if temp_file.exists():
                    temp_file.unlink()
            
        except Exception as e:
            result['errors'].append(f"Test execution error: {str(e)}")
        
        return result
    
    def run_test_suite(self, test_cases: List[TestCase]) -> Dict[str, Any]:
        """Run a complete test suite."""
        results = {
            'total_tests': len(test_cases),
            'passed': 0,
            'failed': 0,
            'test_results': [],
            'summary_by_category': defaultdict(lambda: {'passed': 0, 'failed': 0}),
            'summary_by_difficulty': defaultdict(lambda: {'passed': 0, 'failed': 0})
        }
        
        for test_case in test_cases:
            print(f"Running test: {test_case.name}...")
            test_result = self.run_test_case(test_case)
            results['test_results'].append(test_result)
            
            if test_result['passed']:
                results['passed'] += 1
                results['summary_by_category'][test_case.test_category]['passed'] += 1
                results['summary_by_difficulty'][test_case.difficulty]['passed'] += 1
            else:
                results['failed'] += 1
                results['summary_by_category'][test_case.test_category]['failed'] += 1
                results['summary_by_difficulty'][test_case.difficulty]['failed'] += 1
        
        return results


def print_test_results(results: Dict[str, Any]):
    """Print test suite results."""
    print(f"\n=== ASTRID TEST GENERATOR RESULTS ===")
    print(f"Total tests: {results['total_tests']}")
    print(f"Passed: {results['passed']} ✅")
    print(f"Failed: {results['failed']} ❌")
    print(f"Success rate: {(results['passed'] / results['total_tests']) * 100:.1f}%")
    
    # Summary by category
    print(f"\n📊 RESULTS BY CATEGORY:")
    for category, stats in results['summary_by_category'].items():
        total = stats['passed'] + stats['failed']
        success_rate = (stats['passed'] / total) * 100 if total > 0 else 0
        print(f"  {category}: {stats['passed']}/{total} ({success_rate:.1f}%)")
    
    # Summary by difficulty
    print(f"\n🎯 RESULTS BY DIFFICULTY:")
    for difficulty, stats in results['summary_by_difficulty'].items():
        total = stats['passed'] + stats['failed']
        success_rate = (stats['passed'] / total) * 100 if total > 0 else 0
        print(f"  {difficulty}: {stats['passed']}/{total} ({success_rate:.1f}%)")
    
    # Failed tests
    failed_tests = [r for r in results['test_results'] if not r['passed']]
    if failed_tests:
        print(f"\n❌ FAILED TESTS:")
        for test in failed_tests:
            print(f"  - {test['test_name']}")
            for error in test['errors']:
                print(f"    Error: {error}")


def main():
    parser = argparse.ArgumentParser(description="Astrid Test Generator")
    parser.add_argument("--types", nargs="+", 
                       choices=['basic_syntax', 'variable_operations', 'control_flow', 
                               'function_calls', 'graphics', 'edge_cases', 'performance', 'stress'],
                       default=['basic_syntax', 'variable_operations', 'control_flow'],
                       help="Types of tests to generate")
    parser.add_argument("--count", type=int, default=1, help="Number of tests per type")
    parser.add_argument("--run", action="store_true", help="Run the generated tests")
    parser.add_argument("--output", help="Output file for generated tests")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    
    args = parser.parse_args()
    
    generator = AstridTestGenerator()
    
    print(f"Generating tests for: {', '.join(args.types)}")
    test_cases = generator.generate_test_suite(args.types, args.count)
    
    print(f"Generated {len(test_cases)} test cases")
    
    if args.output:
        # Save test cases to file
        with open(args.output, 'w') as f:
            for test_case in test_cases:
                f.write(f"// Test: {test_case.name}\n")
                f.write(f"// Category: {test_case.test_category}\n")
                f.write(f"// Difficulty: {test_case.difficulty}\n")
                f.write(f"// Description: {test_case.description}\n")
                f.write(f"// Expected: {test_case.expected_behavior}\n")
                f.write(test_case.source_code)
                f.write("\n" + "="*50 + "\n\n")
        print(f"Test cases saved to {args.output}")
    
    if args.run:
        print("Running test suite...")
        results = generator.run_test_suite(test_cases)
        
        if args.json:
            import json
            print(json.dumps(results, indent=2))
        else:
            print_test_results(results)


if __name__ == "__main__":
    main()
