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
        # Remove trailing newlines that the new lexer adds
        while result and result[-1] == '\n':
            result.pop()
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
        # Simple expression parser for backward compatibility
        if i >= len(tokens):
            return [], i
        
        # Parse left operand
        left_lines, i = self._parse_primary_expression(tokens, i)
        
        # Check for binary operator
        if i < len(tokens) and tokens[i] in ['+', '-', '*', '/']:
            op = tokens[i]
            i += 1  # consume operator
            
            # Parse right operand
            right_lines, i = self._parse_primary_expression(tokens, i)
            
            # Generate binary operation
            lines = left_lines + ["    PUSH P0"] + right_lines + ["    POP P1"]
            if op == '+':
                lines.append("    ADD P0,P1")
            elif op == '-':
                lines.append("    SUB P0,P1")
            elif op == '*':
                lines.append("    MUL P0,P1")
            elif op == '/':
                lines.append("    DIV P0,P1")
            
            return lines, i
        
        return left_lines, i

    def _parse_primary_expression(self, tokens, i):
        """Parse primary expression (for backward compatibility)."""
        if i >= len(tokens):
            return [], i
            
        token = tokens[i]
        
        # Handle variables
        if token in self.variables:
            var_addr = self.variables[token]
            lines = [f"    MOV P0,[{var_addr}]"]
            return lines, i + 1
        # Handle numbers
        elif token.isdigit():
            lines = [f"    MOV P0,{token}"]
            return lines, i + 1
        # Handle string literals
        elif token.startswith('"') and token.endswith('"'):
            string_val = token[1:-1]
            addr = self._get_string_literal_address(string_val)
            lines = [f"    MOV P0,{addr}"]
            return lines, i + 1
        
        # Handle function calls
        if token == 'LEN' and i + 3 < len(tokens) and tokens[i+1] == '(' and tokens[i+3] == ')':
            # LEN(string)
            string_token = tokens[i+2]
            if string_token.startswith('"') and string_token.endswith('"'):
                lines = [
                    f"    ; LEN({string_token})",
                    f"    MOV P0,{self._get_string_literal_address(string_token[1:-1])}",
                    "    STRLEN P0",
                    "    MOV P0,R0"
                ]
                return lines, i + 4
        elif token == 'UPPER' and i + 3 < len(tokens) and tokens[i+1] == '(' and tokens[i+3] == ')':
            # UPPER(string)
            string_token = tokens[i+2]
            if string_token.startswith('"') and string_token.endswith('"'):
                temp_addr = f"0x{0x4000 + self.code_generator.label_counter:04X}"
                self.code_generator.label_counter += 1
                lines = [
                    f"    ; UPPER({string_token})",
                    f"    MOV P0,{self._get_string_literal_address(string_token[1:-1])}",
                    f"    MOV P1,{temp_addr}",
                    "    STRUPR P1,P0",
                    f"    MOV P0,{temp_addr}"
                ]
                return lines, i + 4
        elif token in ['LEFT', 'RIGHT', 'MID', 'INSTR'] and i + 5 < len(tokens):
            # Function calls with multiple arguments
            func_name = token
            if func_name == 'LEFT':
                lines = [f"    ; LEFT() call", "    CALL left_substr"]
            elif func_name == 'RIGHT':
                lines = [f"    ; RIGHT() call", "    CALL right_substr"]
            elif func_name == 'MID':
                lines = [f"    ; MID() call", "    CALL mid_substr"]
            elif func_name == 'INSTR':
                lines = [f"    ; INSTR() call", "    STREXT P0,P1", "    MOV P0,R0"]
            # Skip to end of function call
            paren_count = 0
            j = i + 1
            while j < len(tokens):
                if tokens[j] == '(':
                    paren_count += 1
                elif tokens[j] == ')':
                    paren_count -= 1
                    if paren_count == 0:
                        return lines, j + 1
                j += 1
            return lines, j
        
        # For other cases, return dummy
        return ["    ; parsed primary expression"], i + 1

    def _get_string_literal_address(self, string_val):
        """Get address for string literal (for backward compatibility)."""
        if string_val not in self.code_generator.string_literals:
            addr = 0x3000 + len(self.code_generator.string_literals) * 20  # Rough estimate
            self.code_generator.string_literals[string_val] = addr
        return self.code_generator.string_literals[string_val]

    def _compile_assignment(self, tokens, i):
        """Compile assignment (for backward compatibility)."""
        if i >= len(tokens) or tokens[i] not in self.variables:
            return [], i
        
        var_name = tokens[i]
        i += 1  # consume variable
        
        if i >= len(tokens) or tokens[i] != '=':
            return [], i
        
        i += 1  # consume '='
        
        # Parse expression
        expr_lines, i = self._parse_expression(tokens, i)
        
        # Generate assignment
        var_addr = self.variables[var_name]
        lines = [f"    ; {var_name} = "] + expr_lines + [f"    MOV [0x{var_addr:04X}],P0"]
        
        return lines, i

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