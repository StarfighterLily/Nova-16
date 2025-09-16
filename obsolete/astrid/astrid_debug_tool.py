#!/usr/bin/env python3
"""
Astrid Compiler Debugging Tool
Provides comprehensive analysis and debugging capabilities for Astrid programs.
"""

import argparse
import sys
import os
import subprocess
import tempfile
from pathlib import Path

def compile_astrid_file(source_file, verbose=False):
    """Compile an Astrid file and return the assembly and binary paths."""
    try:
        # Get the directory and base name
        source_path = Path(source_file)
        base_name = source_path.stem
        astrid_dir = source_path.parent
        
        # Run Astrid compiler
        cmd = ["python", "run_astrid.py", str(source_path.name)]
        if verbose:
            cmd.append("-v")
            
        result = subprocess.run(cmd, cwd=astrid_dir, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Compilation failed:")
            print(result.stderr)
            return None, None
            
        asm_file = astrid_dir / f"{base_name}.asm"
        return str(asm_file), None
        
    except Exception as e:
        print(f"Error during compilation: {e}")
        return None, None

def analyze_assembly(asm_file):
    """Analyze the generated assembly code."""
    try:
        with open(asm_file, 'r') as f:
            lines = f.readlines()
            
        print(f"\n=== ASSEMBLY ANALYSIS ===")
        print(f"File: {asm_file}")
        print(f"Lines: {len(lines)}")
        
        # Count instruction types
        instruction_counts = {}
        graphics_instructions = []
        memory_operations = []
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith(';') or line.endswith(':'):
                continue
                
            # Extract instruction
            parts = line.split()
            if parts:
                instr = parts[0]
                instruction_counts[instr] = instruction_counts.get(instr, 0) + 1
                
                # Track special instruction types
                if instr in ['SWRITE', 'SREAD', 'VWRITE', 'VREAD', 'SROLX', 'SROLY']:
                    graphics_instructions.append((i, line))
                elif instr in ['MOV', 'PUSH', 'POP']:
                    memory_operations.append((i, line))
        
        print(f"\nInstruction frequency:")
        for instr, count in sorted(instruction_counts.items()):
            print(f"  {instr}: {count}")
            
        if graphics_instructions:
            print(f"\nGraphics instructions found: {len(graphics_instructions)}")
            for line_num, instruction in graphics_instructions[:10]:  # Show first 10
                print(f"  Line {line_num}: {instruction}")
            if len(graphics_instructions) > 10:
                print(f"  ... and {len(graphics_instructions) - 10} more")
                
        print(f"\nMemory operations: {len(memory_operations)}")
        
    except Exception as e:
        print(f"Error analyzing assembly: {e}")

def assemble_and_test(asm_file, cycles=1000):
    """Assemble the code and test it."""
    try:
        # Get paths
        asm_path = Path(asm_file)
        base_name = asm_path.stem
        main_dir = asm_path.parent.parent if asm_path.parent.name == "astrid" else asm_path.parent
        
        # Assemble
        print(f"\n=== ASSEMBLY PROCESS ===")
        cmd = ["python", os.path.join("..", "nova_assembler.py"), str(asm_file)]
        result = subprocess.run(cmd, cwd=main_dir, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Assembly failed:")
            print(result.stderr)
            return None
            
        print("Assembly successful!")
        print(result.stdout.split('\n')[-2])  # Show assembly complete line
        
        # Test execution
        bin_file = asm_path.parent / f"{base_name}.bin"
        print(f"\n=== EXECUTION TEST ===")
        cmd = ["python", os.path.join("..", "nova.py"), "--headless", str(bin_file), "--cycles", str(cycles)]
        result = subprocess.run(cmd, cwd=main_dir, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Execution failed:")
            print(result.stderr)
            return None
            
        # Parse execution results
        output_lines = result.stdout.split('\n')
        for line in output_lines:
            if "Execution finished" in line or "Final PC:" in line or "Graphics:" in line:
                print(line)
                
        return str(bin_file)
        
    except Exception as e:
        print(f"Error during assembly/test: {e}")
        return None

def graphics_analysis(bin_file, cycles=5000):
    """Analyze graphics output."""
    try:
        bin_path = Path(bin_file)
        main_dir = bin_path.parent.parent if bin_path.parent.name == "astrid" else bin_path.parent
        
        print(f"\n=== GRAPHICS ANALYSIS ===")
        cmd = ["python", os.path.join("..", "nova_graphics_monitor.py"), str(bin_file), "--cycles", str(cycles), "--quiet"]
        result = subprocess.run(cmd, cwd=main_dir, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Graphics analysis failed:")
            print(result.stderr)
            return
            
        # Parse graphics output
        output_lines = result.stdout.split('\n')
        in_analysis = False
        
        for line in output_lines:
            if "FINAL ANALYSIS" in line:
                in_analysis = True
            elif in_analysis and (
                "Total pixel writes:" in line or
                "Layers used:" in line or
                "Colors used:" in line or
                "Drawing bounds:" in line or
                "non-black pixels:" in line
            ):
                print(line.strip())
                
    except Exception as e:
        print(f"Error during graphics analysis: {e}")

def main():
    parser = argparse.ArgumentParser(description="Astrid Compiler Debugging Tool")
    parser.add_argument("source", help="Astrid source file (.ast)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose compilation")
    parser.add_argument("-c", "--cycles", type=int, default=5000, help="Execution cycles for testing")
    parser.add_argument("--no-test", action="store_true", help="Skip execution testing")
    parser.add_argument("--no-graphics", action="store_true", help="Skip graphics analysis")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.source):
        print(f"Error: Source file '{args.source}' not found")
        sys.exit(1)
        
    print(f"=== ASTRID DEBUGGING TOOL ===")
    print(f"Source: {args.source}")
    print(f"Cycles: {args.cycles}")
    
    # Step 1: Compile
    print(f"\n=== COMPILATION ===")
    asm_file, _ = compile_astrid_file(args.source, args.verbose)
    if not asm_file:
        print("Compilation failed!")
        sys.exit(1)
    print(f"Generated: {asm_file}")
    
    # Step 2: Analyze assembly
    analyze_assembly(asm_file)
    
    # Step 3: Assemble and test
    if not args.no_test:
        bin_file = assemble_and_test(asm_file, args.cycles)
        if not bin_file:
            print("Assembly/testing failed!")
            sys.exit(1)
            
        # Step 4: Graphics analysis
        if not args.no_graphics:
            graphics_analysis(bin_file, args.cycles)
    
    print(f"\n=== DEBUGGING COMPLETE ===")

if __name__ == "__main__":
    main()
