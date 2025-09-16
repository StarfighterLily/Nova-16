#!/usr/bin/env python3
"""
Targeted Bug Analysis for Astrid 2.0 Compiler Issues
Focused tests to identify specific problem areas
"""

import os
import sys
import tempfile

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from astrid2.main import AstridCompiler

def analyze_compilation_output(test_name, source_code):
    """Analyze what the compiler generates for given source."""
    print(f"\n=== Analyzing: {test_name} ===")
    
    compiler = AstridCompiler()
    try:
        asm_code = compiler.compile(source_code, f"analyze_{test_name}.ast", verbose=False)
        print("✅ Compilation successful")
        print("Generated Assembly:")
        print(asm_code)
        return True
    except Exception as e:
        print(f"❌ Compilation failed: {e}")
        return False

def main():
    """Run targeted analysis."""
    
    print("TARGETED BUG ANALYSIS FOR ASTRID 2.0")
    print("=====================================")
    
    # Test 1: Simple variable assignment - should work
    analyze_compilation_output("simple_assignment", """
void main() {
    int8 x = 42;
    halt();
}
""")
    
    # Test 2: Function with parameters - has stack issues
    analyze_compilation_output("function_params", """
int8 add_numbers(int8 a, int8 b) {
    return a + b;
}

void main() {
    int8 result = add_numbers(10, 20);
    halt();
}
""")
    
    # Test 3: Memory operations - seems broken
    analyze_compilation_output("memory_ops", """
void main() {
    memory_write(0x2000, 123);
    int8 value = memory_read(0x2000);
    halt();
}
""")
    
    # Test 4: Arrays - should fail but doesn't
    analyze_compilation_output("arrays_test", """
void main() {
    int8 arr[5];
    arr[0] = 10;
    halt();
}
""")
    
    # Test 5: Structs - should fail but doesn't  
    analyze_compilation_output("structs_test", """
struct Point {
    int8 x;
    int8 y;
};

void main() {
    Point p;
    p.x = 10;
    halt();
}
""")
    
    # Test 6: Sound operations - has assembly issues
    analyze_compilation_output("sound_ops", """
void main() {
    play_tone(440, 128, 100);
    halt();
}
""")
    
    # Test 7: Register usage analysis
    analyze_compilation_output("register_usage", """
void main() {
    int8 a = 1;
    int8 b = 2; 
    int8 c = 3;
    int16 x = 100;
    int16 y = 200;
    halt();
}
""")

if __name__ == "__main__":
    main()
