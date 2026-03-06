#!/usr/bin/env python3
"""
NoBASIC Compiler
Compiles NoBASIC source code to Nova-16 assembly and binary.
"""

import sys
import os
from pathlib import Path

# Add the compiler directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'compiler'))

from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.analyzer import SemanticAnalyzer
from compiler.codegen.generator import CodeGenerator
from compiler.utils.error import CompilerError


def compile_nobasic(source_file: str, output_file: str = None, verbose: bool = False, 
                    enable_optimizations: bool = False, debug_optimizations: bool = False,
                    enable_peephole: bool = False, enable_live_range_scheduling: bool = False):
    """
    Compile a NoBASIC source file to Nova-16 assembly and binary.

    Args:
        source_file: Path to the .nobasic source file
        output_file: Path to the output .asm file (optional)
        verbose: Enable verbose output
        enable_optimizations: Enable compiler optimizations (default: False)
        debug_optimizations: Enable optimization debug output (default: False)
        enable_peephole: Enable peephole optimizer (default: False)
        enable_live_range_scheduling: Enable live range scheduler (default: False)
    """
    try:
        # Read source
        with open(source_file, 'r') as f:
            source = f.read()

        if verbose:
            print(f"Compiling {source_file}...")
            if enable_optimizations:
                print("Optimizations: ENABLED")
                if enable_peephole:
                    print("  - Peephole optimization: ENABLED")
                if enable_live_range_scheduling:
                    print("  - Live range scheduling: ENABLED")
            else:
                print("Optimizations: DISABLED")

        # Lexical analysis
        lexer = Lexer()
        tokens = lexer.tokenize(source, source_file)

        if verbose:
            print(f"Lexical analysis complete: {len(tokens)} tokens")

        # Parsing
        parser = Parser()
        ast = parser.parse(tokens, source_file)

        if verbose:
            print("Parsing complete")

        # Semantic analysis
        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast, source_file)

        if verbose:
            print("Semantic analysis complete")

        # Code generation with optimizations configuration
        generator = CodeGenerator(
            debug_allocation=debug_optimizations,
            enable_optimizations=enable_optimizations,
            enable_peephole=enable_peephole,
            enable_live_range_scheduling=enable_live_range_scheduling
        )
        if debug_optimizations:
            generator.opt_config['debug_optimizations'] = True
        assembly = generator.generate(ast)

        if verbose:
            print("Code generation complete")

        # Determine output file
        if not output_file:
            output_file = Path(source_file).with_suffix('.asm')

        # Write assembly
        with open(output_file, 'w') as f:
            f.write(assembly)

        if verbose:
            print(f"Assembly written to {output_file}")

        # Assemble to binary using nova_assembler.py
        assembler_path = os.path.join(os.path.dirname(__file__), '..', 'nova_assembler.py')
        binary_file = Path(output_file).with_suffix('.bin')

        if verbose:
            print(f"Assembling {output_file} to {binary_file}...")

        # Run the assembler
        import subprocess
        result = subprocess.run([
            sys.executable, assembler_path, str(output_file)
        ], capture_output=True, text=True)

        # Check if binary was created (assembler may output to stdout/stderr but still succeed)
        if not binary_file.exists():
            print(f"Assembly failed: {result.stderr}")
            if result.stdout:
                print(f"Assembler output: {result.stdout}")
            sys.exit(1)

        if verbose:
            print(f"Binary written to {binary_file}")

        print(f"Compilation successful: {output_file} and {binary_file}")

    except CompilerError as e:
        print(f"Compilation error: {e}")
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"Unexpected error: {e}")
        print(traceback.format_exc())
        sys.exit(1)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python nobasic_compiler.py <source.nobasic> [options]")
        print()
        print("Options:")
        print("  --output <file.asm>        Output assembly file (default: same as source with .asm)")
        print("  --verbose                  Enable verbose output")
        print("  --enable-optimizations     Enable compiler optimizations (default: enabled)")
        print("  --disable-optimizations    Disable compiler optimizations")
        print("  --enable-peephole          Enable peephole optimizer (default: disabled)")
        print("  --disable-peephole         Disable peephole optimizer")
        print("  --enable-live-range        Enable live range scheduling (default: disabled)")
        print("  --disable-live-range       Disable live range scheduling")
        print("  --debug-optimizations      Enable optimization debug output")
        sys.exit(1)

    source_file = sys.argv[1]
    output_file = None
    verbose = False
    enable_optimizations = True
    debug_optimizations = False
    enable_peephole = False
    enable_live_range_scheduling = False

    # Parse command line arguments
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg == "--verbose":
            verbose = True
        elif arg == "--enable-optimizations":
            enable_optimizations = True
        elif arg == "--disable-optimizations":
            enable_optimizations = False
        elif arg == "--enable-peephole":
            enable_peephole = True
        elif arg == "--disable-peephole":
            enable_peephole = False
        elif arg == "--enable-live-range":
            enable_live_range_scheduling = True
        elif arg == "--disable-live-range":
            enable_live_range_scheduling = False
        elif arg == "--debug-optimizations":
            debug_optimizations = True
            enable_optimizations = True  # Debug implies optimizations enabled
        elif arg == "--output":
            if i + 1 < len(sys.argv):
                output_file = sys.argv[i + 1]
                i += 1
            else:
                print("Error: --output requires an argument")
                sys.exit(1)
        elif arg.endswith('.asm'):
            # Legacy support for positional output file
            output_file = arg
        else:
            print(f"Unknown option: {arg}")
            sys.exit(1)
        
        i += 1

    compile_nobasic(source_file, output_file, verbose, enable_optimizations, debug_optimizations,
                    enable_peephole, enable_live_range_scheduling)


if __name__ == "__main__":
    main()