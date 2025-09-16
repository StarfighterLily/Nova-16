#!/usr/bin/env python3
"""
Astrid Compiler - Main Entry Point
Nova-16 Hardware-Optimized Compiler

Usage:
    python -m astrid2 source.ast -o output.asm
    python -m astrid2 --help
"""

import argparse
import sys
import os
import logging
from pathlib import Path
from typing import Optional

from .lexer.lexer import Lexer
from .parser.parser import Parser
from .semantic.analyzer import SemanticAnalyzer
from .ir.builder import IRBuilder
from .codegen.pure_stack_generator import PureStackCodeGenerator
from .utils.error import CompilerError
from .utils.logger import get_logger

logger = get_logger(__name__)


class AstridCompiler:
    """Main Astrid compiler class."""

    def __init__(self):
        self.lexer = Lexer()
        self.parser = Parser()
        self.semantic_analyzer = SemanticAnalyzer()
        self.ir_builder = IRBuilder()
        self.code_generator = PureStackCodeGenerator()

    def compile(self, source_code: str, filename: str = "<stdin>", verbose: bool = False) -> str:
        """
        Compile Astrid source code to Nova-16 assembly.

        Args:
            source_code: The Astrid source code
            filename: Source filename for error reporting

        Returns:
            Generated assembly code as a string

        Raises:
            CompilerError: If compilation fails
        """
        try:
            # Reset semantic analyzer state for new compilation
            self.semantic_analyzer.reset_state()
            
            # Phase 1: Lexical Analysis
            logger.info(f"Starting compilation of {filename}")
            tokens = self.lexer.tokenize(source_code, filename)
            logger.info(f"OK: Lexer: Generated {len(tokens)} tokens")

            # Phase 2: Syntax Analysis
            ast = self.parser.parse(tokens, filename)
            logger.info(f"OK: Parser: Generated AST with {len(ast.functions)} functions")

            # Phase 3: Semantic Analysis
            self.semantic_analyzer.analyze(ast)
            if self.semantic_analyzer.errors:
                error_msg = f"Semantic analysis found {len(self.semantic_analyzer.errors)} errors:\n"
                for error in self.semantic_analyzer.errors:
                    error_msg += f"  {error}\n"
                raise CompilerError(error_msg.strip())
            logger.info("OK: Semantic Analysis: Type checking and symbol resolution complete")

            # Phase 4: IR Generation
            ir_module = self.ir_builder.build(ast, self.semantic_analyzer)
            logger.info(f"OK: IR Generation: Created IR with {len(ir_module.functions)} functions")
            if verbose:
                print("IR Module:")
                for func in ir_module.functions:
                    print(f"Function: {func.name}")
                    for block in func.blocks:
                        print(f"  Block: {block.name}")
                        for instr in block.instructions:
                            print(f"    {instr}")

            # Phase 5: Code Generation (Pure Stack approach only)
            logger.info("Using pure stack approach: Minimal register usage")
            assembly = self.code_generator.generate(ir_module)
            logger.info("OK: Pure Stack Code Generation: Generated Nova-16 assembly")

            return assembly

        except CompilerError as e:
            logger.error(f"Compilation failed: {e}")
            raise
        except Exception as e:
            import traceback
            logger.error(f"Unexpected error during compilation: {e}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            raise CompilerError(f"Internal compiler error: {e}") from e


def main():
    """Main entry point for the Astrid compiler."""
    parser = argparse.ArgumentParser(
        description="Astrid - Nova-16 Pure Stack Compiler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m astrid2 program.ast                    # Compile with pure stack approach
  python -m astrid2 program.ast -o output.asm       # Specify output file
  python -m astrid2 --verbose program.ast           # Verbose output
  python -m astrid2 --help                          # Show this help
        """
    )

    parser.add_argument(
        "source",
        nargs="?",
        help="Astrid source file (.ast)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output assembly file (.asm)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Astrid Compiler v{__import__('astrid2').__version__}"
    )

    args = parser.parse_args()

    # Set up logging
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        # Also set the astrid2 logger to DEBUG
        from .utils.logger import set_log_level
        set_log_level("DEBUG")

    # Get source code
    if args.source:
        if not os.path.exists(args.source):
            print(f"Error: Source file '{args.source}' not found", file=sys.stderr)
            sys.exit(1)

        with open(args.source, "r", encoding="utf-8") as f:
            source_code = f.read()
        filename = args.source
        output_file = args.output or os.path.splitext(args.source)[0] + ".asm"
    else:
        print("Reading Astrid source from stdin. Press Ctrl+D (Unix) or Ctrl+Z+Enter (Windows) to end input.")
        try:
            source_code = sys.stdin.read()
        except KeyboardInterrupt:
            print("\nCompilation cancelled.", file=sys.stderr)
            sys.exit(1)
        filename = "<stdin>"
        output_file = args.output or "output.asm"

    # Compile
    compiler = AstridCompiler()
    try:
        print("=== Astrid COMPILER ===")
        print("Using pure stack-centric approach (minimal registers)")
        print(f"Compiling: {filename} -> {output_file}")

        assembly = compiler.compile(source_code, filename, args.verbose)

        # Write output
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(assembly)

        print(f"OK: Compilation successful!")
        print(f"OK: Assembly saved to {output_file}")

    except CompilerError as e:
        print(f"ERROR: Compilation failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
