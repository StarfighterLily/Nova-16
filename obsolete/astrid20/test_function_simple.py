#!/usr/bin/env python3
"""
Simple test for function calls without Unicode symbols
"""

import os
import sys
import tempfile

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from astrid2.main import AstridCompiler
import tempfile
import subprocess

def test_function_call():
    """Test if function calls work now"""
    
    source_code = """
int8 add(int8 x, int8 y) {
    return x + y;
}

void main() {
    int8 result = add(15, 25);
    halt();
}
"""
    
    print("Testing function calls with fixed stack...")
    
    try:
        # Compile
        compiler = AstridCompiler()
        asm_code = compiler.compile(source_code, "function_test.ast")
        
        # Write to temp file and assemble
        with tempfile.NamedTemporaryFile(mode='w', suffix='.asm', delete=False) as asm_file:
            asm_file.write(asm_code)
            asm_filename = asm_file.name
        
        # Assemble 
        bin_filename = asm_filename.replace('.asm', '.bin')
        result = subprocess.run([
            'python', os.path.join('..', 'nova_assembler.py'), asm_filename
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if result.returncode == 0:
            print("Assembly successful")
            
            # Run with Nova
            result = subprocess.run([
                'python', os.path.join('..', 'nova.py'), '--headless', bin_filename, '--cycles', '100'
            ], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
            
            if "Stack underflow" in result.stderr or "Stack underflow" in result.stdout:
                print("FAILED: Still getting stack underflow")
                return False
            elif "Error at cycle" in result.stderr or "Error at cycle" in result.stdout:
                print("FAILED: Runtime error occurred")
                print("Error output:", result.stderr)
                return False
            else:
                print("SUCCESS: Function call executed without stack underflow!")
                return True
        else:
            print("Assembly failed:", result.stderr)
            return False
            
    except Exception as e:
        print(f"Test failed: {e}")
        return False
    finally:
        # Cleanup
        try:
            os.unlink(asm_filename)
            os.unlink(bin_filename)
        except:
            pass

if __name__ == "__main__":
    success = test_function_call()
    sys.exit(0 if success else 1)
