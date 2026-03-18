#!/usr/bin/env python3
"""
NoBASIC Inspection Tools
Utilities for inspecting NoBASIC programs: AST, symbols, etc.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, Any

# Add the compiler directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'compiler'))

from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.analyzer import SemanticAnalyzer
from compiler.codegen.generator import CodeGenerator
from compiler.utils.error import CompilerError
from nobasic_compiler import generate_with_error_remapping, resolve_source_file_path, run_frontend_pipeline


class NoBASICInspector:
    """Tools for inspecting NoBASIC programs."""

    def __init__(self, source_file: str):
        self.source_file = str(resolve_source_file_path(source_file))
        self.lexer = Lexer()
        self.parser = Parser()
        self.analyzer = SemanticAnalyzer()
        self.generator = CodeGenerator()

    def inspect_all(self, output_dir: str = None):
        """Perform complete inspection and save results."""
        results = {}

        try:
            pipeline = run_frontend_pipeline(
                self.source_file,
                lexer_factory=Lexer,
                parser_factory=Parser,
                analyzer_factory=SemanticAnalyzer,
            )
            self.analyzer = pipeline.analyzer

            results['source'] = pipeline.source
            results['tokens'] = [str(token) for token in pipeline.tokens]
            results['ast'] = self._ast_to_dict(pipeline.ast)
            results['symbols'] = self._symbols_to_dict()

            # Code generation
            assembly = generate_with_error_remapping(
                self.generator,
                pipeline.ast,
                str(pipeline.resolved_source_file),
                pipeline.line_map,
            )
            results['assembly'] = assembly

            if output_dir:
                self._save_results(results, output_dir)
            else:
                self._print_results(results)

        except CompilerError as e:
            print(f"Inspection error: {e}")
            return False

        return True

    def _ast_to_dict(self, node, max_depth=5, current_depth=0) -> Dict[str, Any]:
        """Convert AST node to dictionary representation."""
        if current_depth > max_depth:
            return {"type": type(node).__name__, "truncated": True}

        result = {"type": type(node).__name__}

        if hasattr(node, '__dict__'):
            for key, value in node.__dict__.items():
                if key.startswith('_'):
                    continue
                elif isinstance(value, list):
                    result[key] = [self._ast_to_dict(item, max_depth, current_depth + 1) for item in value]
                elif hasattr(value, '__dict__'):
                    result[key] = self._ast_to_dict(value, max_depth, current_depth + 1)
                else:
                    result[key] = str(value)

        return result

    def _symbols_to_dict(self) -> Dict[str, Any]:
        """Convert symbol table to dictionary."""
        symbols = {}
        for name, data_type in self.analyzer.symbol_table.variables.items():
            symbols[name] = {
                'type': str(data_type),
            }
        return symbols

    def _save_results(self, results: Dict[str, Any], output_dir: str):
        """Save inspection results to files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        base_name = Path(self.source_file).stem

        # Save each component
        with open(output_path / f"{base_name}_ast.json", 'w') as f:
            json.dump(results['ast'], f, indent=2)

        with open(output_path / f"{base_name}_symbols.json", 'w') as f:
            json.dump(results['symbols'], f, indent=2)

        with open(output_path / f"{base_name}_tokens.txt", 'w') as f:
            f.write('\n'.join(results['tokens']))

        with open(output_path / f"{base_name}_assembly.asm", 'w') as f:
            f.write(results['assembly'])

        print(f"Inspection results saved to {output_path}")

    def _print_results(self, results: Dict[str, Any]):
        """Print inspection results to console."""
        print("=== NoBASIC Inspection Results ===")
        print(f"Source file: {self.source_file}")
        print()

        print("TOKENS:")
        for i, token in enumerate(results['tokens'][:20]):  # First 20 tokens
            print(f"  {i}: {token}")
        if len(results['tokens']) > 20:
            print(f"  ... and {len(results['tokens']) - 20} more")
        print()

        print("SYMBOLS:")
        for name, info in results['symbols'].items():
            print(f"  {name}: {info['type']}")
        print()

        print("AST (first level):")
        self._print_ast_level(results['ast'], 0)
        print()

        print("ASSEMBLY (first 20 lines):")
        lines = results['assembly'].split('\n')[:20]
        for line in lines:
            print(f"  {line}")
        if len(results['assembly'].split('\n')) > 20:
            print("  ... (truncated)")

    def _print_ast_level(self, ast_dict: Dict[str, Any], depth: int, max_depth=3):
        """Print AST level with indentation."""
        if depth > max_depth:
            return

        indent = "  " * depth
        node_type = ast_dict.get('type', 'unknown')

        if 'statements' in ast_dict:
            print(f"{indent}{node_type}: {len(ast_dict['statements'])} statements")
            for stmt in ast_dict['statements'][:3]:  # First 3 statements
                self._print_ast_level(stmt, depth + 1, max_depth)
            if len(ast_dict['statements']) > 3:
                print(f"{indent}  ... and {len(ast_dict['statements']) - 3} more")
        else:
            attrs = {k: v for k, v in ast_dict.items() if k != 'type' and not k.startswith('_')}
            if attrs:
                attr_str = ", ".join(f"{k}={v}" for k, v in attrs.items())
                print(f"{indent}{node_type}: {attr_str}")
            else:
                print(f"{indent}{node_type}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python nobasic_inspect.py <file.nobasic> [output_dir]")
        print("If output_dir is provided, saves results to files instead of printing.")
        return 1

    source_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        resolved_source_file = resolve_source_file_path(source_file)
    except CompilerError:
        print(f"File not found: {source_file}")
        return 1

    inspector = NoBASICInspector(str(resolved_source_file))
    success = inspector.inspect_all(output_dir)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())