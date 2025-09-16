#!/usr/bin/env python3
"""
Compile and test stack operations directly
"""

import os
import sys
import tempfile

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from astrid2.main import AstridCompiler

def test_stack_operations():
    """Test stack operations with Nova emulator"""
    
    source_code = """
int8 add(int8 x, int8 y) {
    return x + y;
}

void main() {
    int8 result = add(15, 25);
    halt();
}
"""
    
    print("=== STACK OPERATIONS TEST ===")
    
    # Compile to assembly
    compiler = AstridCompiler()
    try:
        asm_code = compiler.compile(source_code, "stack_test.ast")
        print("Generated assembly:")
        print(asm_code)
        print()
        
        # Write assembly to file
        with open("stack_test.asm", "w") as f:
            f.write(asm_code)
        
        # Assemble to binary
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from nova_assembler import assemble_file
        
        assembled = assemble_file("stack_test.asm")
        if assembled:
            print("Assembly successful")
            
            # Run with Nova emulator
            from nova import run_headless
            
            result = run_headless("stack_test.bin", max_cycles=50)
            if result:
                print("Execution completed successfully")
            else:
                print("Execution failed or did not complete")
        else:
            print("Assembly failed")
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_stack_operations()
