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


def compile_nobasic(source_file: str, output_file: str = None, verbose: bool = False):
    """
    Compile a NoBASIC source file to Nova-16 assembly and binary.

    Args:
        source_file: Path to the .nobasic source file
        output_file: Path to the output .asm file (optional)
        verbose: Enable verbose output
    """
    try:
        # Read source
        with open(source_file, 'r') as f:
            source = f.read()

        if verbose:
            print(f"Compiling {source_file}...")

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

        # Code generation
        generator = CodeGenerator()
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
        print(f"Unexpected error: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python nobasic_compiler.py <source.nobasic> [output.asm] [--verbose]")
        sys.exit(1)

    source_file = sys.argv[1]
    output_file = None
    verbose = False

    for arg in sys.argv[2:]:
        if arg == "--verbose":
            verbose = True
        elif arg.endswith('.asm'):
            output_file = arg

    compile_nobasic(source_file, output_file, verbose)


if __name__ == "__main__":
    main()