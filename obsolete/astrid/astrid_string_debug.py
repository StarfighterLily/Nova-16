#!/usr/bin/env python3
"""
String Handling Debug Tool for Astrid Language

This tool thoroughly tests string handling throughout the Astrid pipeline:
- Lexing of string literals with escape sequences
- Parsing of string types and assignments
- Semantic analysis of string operations
- IR generation for string operations
- Code generation for string constants and print functions
- Assembly generation and execution
"""

import sys
import os
import subprocess
import tempfile
from typing import List, Dict, Any

def test_string_lexing():
    """Test string lexical analysis."""
    print("=== TESTING STRING LEXING ===")
    
    # Test cases for string lexing
    test_cases = [
        '"simple string"',
        '"string with spaces"',
        '"string\\nwith\\tescapes"',
        '""',  # empty string
        '"string with \\"quotes\\""',
        '"special chars !@#$%^&*()"',
    ]
    
    try:
        sys.path.insert(0, 'src')
        from astrid2.lexer.lexer import Lexer
        
        lexer = Lexer()
        
        for test_case in test_cases:
            print(f"Testing: {test_case}")
            try:
                tokens = lexer.tokenize(test_case, "<test>")
                string_tokens = [t for t in tokens if t.type.value == "STRING_LITERAL"]
                if string_tokens:
                    print(f"  Result: '{string_tokens[0].value}'")
                    # Check if escape sequences were properly processed
                    if '\\n' in test_case and '\n' in string_tokens[0].value:
                        print("  ✓ Newline escape sequence processed")
                    if '\\t' in test_case and '\t' in string_tokens[0].value:
                        print("  ✓ Tab escape sequence processed")
                else:
                    print("  ✗ No string token found")
            except Exception as e:
                print(f"  ✗ Error: {e}")
            print()
    except ImportError as e:
        print(f"  ✗ Could not import lexer: {e}")
        print("  ℹ Skipping lexer tests")

def test_string_compilation(test_programs: List[str]):
    """Test compilation of string programs."""
    print("=== TESTING STRING COMPILATION ===")
    
    for i, program in enumerate(test_programs):
        print(f"Test {i+1}: {program[:50]}...")
        
        # Write test program to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False) as f:
            f.write(program)
            test_file = f.name
        
        try:
            # Compile the program
            result = subprocess.run([
                'python', 'run_astrid.py', test_file
            ], capture_output=True, text=True, cwd='.')
            
            if result.returncode == 0:
                print("  ✓ Compilation successful")
                
                # Check if assembly file was created
                asm_file = test_file.replace('.ast', '.asm')
                if os.path.exists(asm_file):
                    print("  ✓ Assembly file generated")
                    
                    # Check for string constants in assembly
                    with open(asm_file, 'r') as f:
                        asm_content = f.read()
                        if 'DEFSTR' in asm_content:
                            print("  ✓ String constants found in assembly")
                        if 'TEXT' in asm_content:
                            print("  ✓ TEXT instruction found for string output")
                    
                    # Try to assemble
                    try:
                        asm_result = subprocess.run([
                            'python', '../nova_assembler.py', asm_file
                        ], capture_output=True, text=True, cwd='.')
                        
                        if asm_result.returncode == 0:
                            print("  ✓ Assembly successful")
                        else:
                            print(f"  ✗ Assembly failed: {asm_result.stderr}")
                    except Exception as e:
                        print(f"  ✗ Assembly error: {e}")
                        
                else:
                    print("  ✗ Assembly file not found")
            else:
                print(f"  ✗ Compilation failed: {result.stderr}")
                
        except Exception as e:
            print(f"  ✗ Test error: {e}")
        finally:
            # Cleanup
            for ext in ['.ast', '.asm', '.bin', '.org']:
                cleanup_file = test_file.replace('.ast', ext)
                if os.path.exists(cleanup_file):
                    os.unlink(cleanup_file)
        
        print()

def test_string_execution():
    """Test execution of string programs."""
    print("=== TESTING STRING EXECUTION ===")
    
    # Create a comprehensive test program
    test_program = '''void main() {
    string msg = "Hello Astrid";
    print_string(msg, 10, 10, 0x1F);
    print_string("Direct string", 10, 30, 0x2F);
}'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False) as f:
        f.write(test_program)
        test_file = f.name
    
    try:
        # Compile
        result = subprocess.run([
            'python', 'run_astrid.py', test_file
        ], capture_output=True, text=True, cwd='.')
        
        if result.returncode == 0:
            asm_file = test_file.replace('.ast', '.asm')
            
            # Assemble
            asm_result = subprocess.run([
                'python', '../nova_assembler.py', asm_file
            ], capture_output=True, text=True, cwd='.')
            
            if asm_result.returncode == 0:
                bin_file = test_file.replace('.ast', '.bin')
                
                # Execute
                exec_result = subprocess.run([
                    'python', '../nova.py', '--headless', bin_file, '--cycles', '200'
                ], capture_output=True, text=True, cwd='.')
                
                if exec_result.returncode == 0:
                    print("  ✓ Execution successful")
                    
                    # Check for graphics output
                    if 'non-black pixels on screen' in exec_result.stdout:
                        print("  ✓ Graphics output detected")
                    
                    # Run graphics monitor for detailed analysis
                    monitor_result = subprocess.run([
                        'python', '../nova_graphics_monitor.py', bin_file, 
                        '--cycles', '200', '--quiet'
                    ], capture_output=True, text=True, cwd='.')
                    
                    if 'TEXT:' in monitor_result.stdout:
                        print("  ✓ TEXT instructions executed")
                    
                else:
                    print(f"  ✗ Execution failed: {exec_result.stderr}")
            else:
                print(f"  ✗ Assembly failed: {asm_result.stderr}")
        else:
            print(f"  ✗ Compilation failed: {result.stderr}")
            
    except Exception as e:
        print(f"  ✗ Execution test error: {e}")
    finally:
        # Cleanup
        for ext in ['.ast', '.asm', '.bin', '.org']:
            cleanup_file = test_file.replace('.ast', ext)
            if os.path.exists(cleanup_file):
                os.unlink(cleanup_file)

def main():
    """Main debugging function."""
    print("ASTRID STRING HANDLING DEBUG TOOL")
    print("=" * 50)
    
    # Change to astrid directory
    original_dir = os.getcwd()
    try:
        os.chdir('astrid')
        
        # Test 1: Lexical analysis
        test_string_lexing()
        
        # Test 2: Compilation
        test_programs = [
            'void main() { string s = "Hello"; print_string(s, 0, 0, 15); }',
            'void main() { print_string("Direct", 0, 0, 15); }',
            'void main() { string s = "Line1\\nLine2"; print_string(s, 0, 0, 15); }',
            'void main() { string s = ""; print_string(s, 0, 0, 15); }',
            'void main() { string a = "A"; string b = "B"; print_string(a, 0, 0, 15); print_string(b, 0, 10, 15); }',
        ]
        
        test_string_compilation(test_programs)
        
        # Test 3: Execution
        test_string_execution()
        
        print("STRING HANDLING DEBUG COMPLETE")
        print("=" * 50)
        
    finally:
        os.chdir(original_dir)

if __name__ == "__main__":
    main()
