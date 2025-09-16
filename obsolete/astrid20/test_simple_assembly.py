#!/usr/bin/env python3
"""
Test simple assembly without frame pointer operations
"""

import os
import sys
import tempfile
import subprocess

def test_simple_assembly():
    """Test manually written assembly to isolate the stack issue"""
    
    simple_asm = """
; Simple test without frame pointers
ORG 0x1000
STI

; Initialize stack pointer  
MOV P8, 0xFFFF

main:
    ; Call function without frame setup
    CALL simple_func
    HLT

simple_func:
    ; Simple function - just return 42 in R0
    MOV R0, 42
    RET
"""
    
    print("Testing simple assembly without frame pointers...")
    
    try:
        # Write assembly to file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.asm', delete=False) as asm_file:
            asm_file.write(simple_asm)
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
                'python', os.path.join('..', 'nova.py'), '--headless', bin_filename, '--cycles', '50'
            ], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
            
            print("Nova output:")
            print(result.stdout)
            if result.stderr:
                print("Nova errors:")
                print(result.stderr)
            
            if "Stack underflow" in result.stderr or "Stack underflow" in result.stdout:
                print("FAILED: Getting stack underflow even with simple assembly")
                return False
            elif "Error at cycle" in result.stderr or "Error at cycle" in result.stdout:
                print("FAILED: Runtime error occurred")
                return False
            else:
                print("SUCCESS: Simple assembly executed without errors!")
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
    success = test_simple_assembly()
    sys.exit(0 if success else 1)
