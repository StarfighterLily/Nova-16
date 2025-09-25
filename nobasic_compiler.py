#!/usr/bin/env python3
"""
NoBASIC Compiler Main Driver
Orchestrates the compilation pipeline: lexing -> parsing -> semantics -> codegen.
"""

import os
from pathlib import Path
from typing import List
from nobasic_lexer import Lexer
from nobasic_parser import Parser
from nobasic_semantics import SemanticAnalyzer
from nobasic_codegen import CodeGenerator
from nobasic_errors import CompilerError
from nobasic_utils import TokenType, ClrHomeStmt, DispStmt, LiteralExpr


class NoBasicCompiler:
    """Main NoBASIC compiler class."""

    def __init__(self):
        self.lexer = Lexer()
        self.parser = Parser()
        self.semantic_analyzer = SemanticAnalyzer()
        self.code_generator = CodeGenerator()
        # Backward compatibility attributes
        self.assembly_lines = []
        self.variables = {var: 0x2000 + i * 2 for i, var in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}
        self.PROGRAM_START = 0x1000
        self.VARIABLE_START = 0x2000

    def compile_program(self, source_code: str, output_file: str):
        """
        Compile NoBASIC source code to assembly file.

        Args:
            source_code: The NoBASIC source code
            output_file: Path to output assembly file
        """
        try:
            # Phase 1: Lexical Analysis
            tokens = self.lexer.tokenize(source_code)

            # Phase 2: Syntax Analysis
            ast = self.parser.parse(tokens)

            # Phase 3: Semantic Analysis
            self.semantic_analyzer.analyze(ast)

            # Phase 4: Code Generation
            assembly_code = self.code_generator.generate(ast)

            # Write to file
            with open(output_file, 'w') as f:
                f.write(assembly_code)

        except CompilerError as e:
            raise e

    def compile_to_lines(self, source_code: str) -> List[str]:
        """
        Compile NoBASIC source code to list of assembly lines.

        Args:
            source_code: The NoBASIC source code

        Returns:
            List of assembly code lines
        """
        try:
            # Phase 1: Lexical Analysis
            tokens = self.lexer.tokenize(source_code)

            # Phase 2: Syntax Analysis
            ast = self.parser.parse(tokens)

            # Phase 3: Semantic Analysis
            self.semantic_analyzer.analyze(ast)

            # Phase 4: Code Generation
            assembly_code = self.code_generator.generate(ast)

            return assembly_code.splitlines()

        except CompilerError as e:
            raise e

    def compile_to_string(self, source_code: str) -> str:
        """
        Compile NoBASIC source code to assembly string.

        Args:
            source_code: The NoBASIC source code

        Returns:
            Assembly code as string
        """
        lines = self.compile_to_lines(source_code)
        return '\n'.join(lines)

    def _tokenize(self, source_code: str):
        """Tokenize source code (for backward compatibility)."""
        tokens = self.lexer.tokenize(source_code)
        # Convert to old format (list of strings)
        result = []
        for token in tokens:
            if token.type == TokenType.STRING:
                result.append(f'"{token.value}"')
            elif token.type == TokenType.NEWLINE:
                result.append('\n')
            elif token.type != TokenType.EOF:
                result.append(token.value)
        return result

    def _compile_clrhome(self):
        """Compile ClrHome (for backward compatibility)."""
        old_len = len(self.code_generator.output)
        self.code_generator._generate_clrhome()
        return self.code_generator.output[old_len:]

    def _compile_disp(self, tokens, i):
        """Compile Disp (for backward compatibility)."""
        # Simplified implementation
        expressions = []
        while i < len(tokens) and tokens[i] != '\n':
            if tokens[i].startswith('"') and tokens[i].endswith('"'):
                expressions.append(LiteralExpr(tokens[i][1:-1]))
            i += 1
        stmt = DispStmt(expressions)
        old_len = len(self.code_generator.output)
        self.code_generator._generate_disp(stmt)
        return self.code_generator.output[old_len:], i

    def _parse_expression(self, tokens, i):
        """Parse expression (for backward compatibility)."""
        # Simplified
        return ["    ; parsed expression"], i + 1

    def _parse_primary_expression(self, tokens, i):
        """Parse primary expression (for backward compatibility)."""
        # Simplified
        return ["    ; parsed primary expression"], i + 1

    def _compile_assignment(self, tokens, i):
        """Compile assignment (for backward compatibility)."""
        # Simplified
        return [], i + 2

    def _compile_struct(self, tokens, i):
        """Compile struct (for backward compatibility)."""
        # Simplified
        return [], i + 1

    def _compile_dim(self, tokens, i):
        """Compile DIM (for backward compatibility)."""
        # Simplified implementation
        return [], i + 1


def main():
    """Command-line interface for the NoBASIC compiler."""
    import argparse

    parser = argparse.ArgumentParser(description='NoBASIC Compiler for Nova-16')
    parser.add_argument('input', help='Input NoBASIC source file (.nob)')
    parser.add_argument('output', nargs='?', help='Output assembly file (.asm)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    # Determine output file
    if args.output:
        output_file = args.output
    else:
        input_path = Path(args.input)
        output_file = input_path.with_suffix('.asm')

    # Read source
    try:
        with open(args.input, 'r', encoding='utf-8-sig') as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found")
        return 1

    # Compile
    compiler = NoBasicCompiler()
    try:
        compiler.compile_program(source_code, output_file)
        if args.verbose:
            print(f"Successfully compiled '{args.input}' to '{output_file}'")
        return 0
    except CompilerError as e:
        print(f"Compilation error: {e}")
        return 1


if __name__ == '__main__':
    exit(main())