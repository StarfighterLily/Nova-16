#!/usr/bin/env python3
"""
NoBASIC Profiler
Performance profiling tool for NoBASIC programs.
"""

import sys
import os
import time
import cProfile
import pstats
from pathlib import Path
from typing import Dict, Iterable, List, Any
import io

# Add the compiler directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'compiler'))

from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.analyzer import SemanticAnalyzer
from compiler.codegen.generator import CodeGenerator
from compiler.parser.ast import DataType
from compiler.utils.error import CompilerError
from nobasic_compiler import (
    generate_with_error_remapping,
    remap_compiler_error,
    resolve_source_file_path,
    run_frontend_pipeline,
)


class NoBASICProfiler:
    """Performance profiler for NoBASIC programs."""

    def __init__(self, source_file: str):
        self.source_file = source_file
        self.lexer = Lexer()
        self.parser = Parser()
        self.analyzer = SemanticAnalyzer()
        self.generator = CodeGenerator()

        # Profiling data
        self.parsing_time = 0
        self.semantic_time = 0
        self.codegen_time = 0
        self.total_time = 0

        # Analysis results
        self.ast = None
        self.symbols = {}
        self.assembly_code = ""

    def profile_compilation(self) -> Dict[str, Any]:
        """Profile the compilation process."""
        print(f"Profiling compilation of {self.source_file}...")

        start_total = time.time()
        tokens: List[Any] = []
        line_map = []
        resolved_source_file = None

        try:
            # Profile parsing
            start_parse = time.time()
            pipeline = run_frontend_pipeline(
                self.source_file,
                lexer_factory=Lexer,
                parser_factory=Parser,
                analyzer_factory=SemanticAnalyzer,
            )
            resolved_source_file = pipeline.resolved_source_file
            line_map = pipeline.line_map
            tokens = pipeline.tokens
            self.ast = pipeline.ast
            self.analyzer = pipeline.analyzer
            self.parsing_time = time.time() - start_parse

            # Profile semantic analysis
            start_semantic = time.time()
            self.symbols = self.analyzer.symbol_table.variables.copy()
            self.semantic_time = time.time() - start_semantic

            # Profile code generation
            start_codegen = time.time()
            self.assembly_code = generate_with_error_remapping(
                self.generator,
                self.ast,
                str(resolved_source_file),
                line_map,
            )
            self.codegen_time = time.time() - start_codegen

            self.total_time = time.time() - start_total
        except CompilerError as error:
            main_source_for_remap = str(resolved_source_file) if resolved_source_file is not None else self.source_file
            raise remap_compiler_error(error, main_source_for_remap, line_map) from error

        return {
            'parsing_time': self.parsing_time,
            'semantic_time': self.semantic_time,
            'codegen_time': self.codegen_time,
            'total_time': self.total_time,
            'token_count': len(tokens),
            'symbol_count': len(self.symbols),
            'assembly_lines': len(self.assembly_code.split('\n'))
        }

    def _symbol_matches_type(self, symbol_info: Any, expected_type: DataType) -> bool:
        """Return True when a stored symbol entry represents the requested type."""
        if isinstance(symbol_info, dict):
            symbol_info = symbol_info.get('type')
        if isinstance(symbol_info, DataType):
            return symbol_info == expected_type
        if symbol_info is None:
            return False
        normalized = str(symbol_info).strip().lower()
        return normalized in {expected_type.value, f"datatype.{expected_type.name.lower()}"}

    def analyze_code_complexity(self) -> Dict[str, Any]:
        """Analyze code complexity metrics."""
        if self.ast is None:
            print("No AST available. Run profile_compilation() first.")
            return {}

        complexity = self._analyze_ast_complexity(self.ast)

        return {
            'cyclomatic_complexity': complexity['complexity'],
            'statement_count': complexity['statements'],
            'function_count': complexity['functions'],
            'loop_count': complexity['loops'],
            'conditional_count': complexity['conditionals'],
            'max_nesting_depth': complexity['max_depth']
        }

    def _analyze_ast_complexity(self, node, depth=0, complexity=None):
        """Analyze AST for complexity metrics."""
        if complexity is None:
            complexity = {
                'complexity': 1,  # Base complexity
                'statements': 0,
                'functions': 0,
                'loops': 0,
                'conditionals': 0,
                'max_depth': 0
            }

        if node is None:
            return complexity

        complexity['statements'] += 1
        complexity['max_depth'] = max(complexity['max_depth'], depth)

        node_type = type(node).__name__

        # Increment complexity for decision points
        if node_type in ['IfStmt', 'WhileStmt', 'RepeatStmt', 'ForStmt']:
            complexity['complexity'] += 1
            if node_type in ['WhileStmt', 'RepeatStmt', 'ForStmt']:
                complexity['loops'] += 1
            if node_type == 'IfStmt':
                complexity['conditionals'] += 1

        if node_type == 'FunctionCallExpr':
            complexity['functions'] += 1

        # Recursively analyze all child containers instead of stopping at the
        # first matching attribute. Expression nodes frequently contain more
        # than one child branch.
        for branch_name in ('statements', 'then_branch', 'else_branch', 'body', 'arguments'):
            for child in self._iter_child_sequence(node, branch_name):
                child_depth = depth + 1 if branch_name != 'arguments' else depth
                self._analyze_ast_complexity(child, child_depth, complexity)

        for child_name in ('left', 'right', 'expression', 'condition', 'value', 'target', 'start', 'end', 'step'):
            child = getattr(node, child_name, None)
            if self._is_ast_node(child):
                self._analyze_ast_complexity(child, depth, complexity)

        return complexity

    def _iter_child_sequence(self, node, attribute_name: str) -> Iterable[Any]:
        """Yield AST child nodes from a list-valued attribute when present."""
        children = getattr(node, attribute_name, None)
        if not children:
            return ()
        return tuple(child for child in children if self._is_ast_node(child))

    def _is_ast_node(self, value: Any) -> bool:
        """Return True for objects that look like AST nodes rather than primitives."""
        return value is not None and hasattr(value, '__dict__')

    def analyze_memory_usage(self) -> Dict[str, Any]:
        """Analyze memory usage patterns."""
        if not self.symbols:
            print("No symbols available. Run profile_compilation() first.")
            return {}

        memory_info = {
            'total_variables': len(self.symbols),
            'number_variables': sum(1 for info in self.symbols.values() if self._symbol_matches_type(info, DataType.NUMBER)),
            'string_variables': sum(1 for info in self.symbols.values() if self._symbol_matches_type(info, DataType.STRING)),
            'estimated_memory_bytes': len(self.symbols) * 2  # 16-bit variables
        }

        return memory_info

    def generate_report(self) -> str:
        """Generate a comprehensive profiling report."""
        if self.total_time == 0:
            self.profile_compilation()

        report = []
        report.append("=" * 60)
        report.append("NoBASIC PROFILING REPORT")
        report.append("=" * 60)
        report.append(f"Source File: {self.source_file}")
        report.append("")

        # Performance metrics
        report.append("PERFORMANCE METRICS:")
        report.append("-" * 30)
        report.append(f"Parsing Time: {self.parsing_time:.4f}s")
        report.append(f"Semantic Analysis Time: {self.semantic_time:.4f}s")
        report.append(f"Code Generation Time: {self.codegen_time:.4f}s")
        report.append(f"Total Time: {self.total_time:.4f}s")
        report.append("")

        # Code metrics
        complexity = self.analyze_code_complexity()
        report.append("CODE COMPLEXITY:")
        report.append("-" * 30)
        report.append(f"Cyclomatic Complexity: {complexity.get('cyclomatic_complexity', 'N/A')}")
        report.append(f"Total Statements: {complexity.get('statement_count', 'N/A')}")
        report.append(f"Function Calls: {complexity.get('function_count', 'N/A')}")
        report.append(f"Loop Constructs: {complexity.get('loop_count', 'N/A')}")
        report.append(f"Conditional Statements: {complexity.get('conditional_count', 'N/A')}")
        report.append(f"Maximum Nesting Depth: {complexity.get('max_nesting_depth', 'N/A')}")
        report.append("")

        # Memory analysis
        memory = self.analyze_memory_usage()
        report.append("MEMORY ANALYSIS:")
        report.append("-" * 30)
        report.append(f"Total Variables: {memory.get('total_variables', 'N/A')}")
        report.append(f"Number Variables: {memory.get('number_variables', 'N/A')}")
        report.append(f"String Variables: {memory.get('string_variables', 'N/A')}")
        report.append(f"Estimated Memory: {memory.get('estimated_memory_bytes', 'N/A')} bytes")
        report.append("")

        # Assembly analysis
        if self.assembly_code:
            lines = self.assembly_code.split('\n')
            report.append("ASSEMBLY ANALYSIS:")
            report.append("-" * 30)
            report.append(f"Assembly Lines: {len(lines)}")
            report.append(f"Instructions: {len([l for l in lines if l.strip() and not l.strip().startswith(';')])}")
            report.append("")

        # Recommendations
        report.append("RECOMMENDATIONS:")
        report.append("-" * 30)

        if complexity.get('cyclomatic_complexity', 1) > 10:
            report.append("• Consider breaking down complex functions")
        if complexity.get('max_nesting_depth', 0) > 5:
            report.append("• Reduce nesting depth for better readability")
        if self.codegen_time > 1.0:
            report.append("• Code generation is slow - consider optimizing the compiler")
        if memory.get('estimated_memory_bytes', 0) > 1000:
            report.append("• High memory usage - consider optimizing variable usage")

        if not any("•" in line for line in report[-5:]):
            report.append("• Code looks good!")

        report.append("=" * 60)

        return "\n".join(report)

    def profile_with_cprofile(self):
        """Profile using Python's cProfile."""
        print("Running detailed profiling with cProfile...")

        pr = cProfile.Profile()
        pr.enable()

        # Run the compilation
        self.profile_compilation()

        pr.disable()

        # Print results
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats()
        print(s.getvalue())


def main():
    """Main entry point."""
    if len(sys.argv) not in {2, 3}:
        print("Usage: python nobasic_profiler.py <file.nobasic> [--detailed]")
        return 1

    source_file = sys.argv[1]
    detailed = len(sys.argv) == 3 and sys.argv[2] == '--detailed'
    if len(sys.argv) == 3 and not detailed:
        print(f"Unknown option: {sys.argv[2]}")
        return 1

    try:
        resolved_source_file = resolve_source_file_path(source_file)
    except CompilerError:
        print(f"File not found: {source_file}")
        return 1

    profiler = NoBASICProfiler(str(resolved_source_file))

    # Run profiling
    try:
        profiler.profile_compilation()
    except CompilerError as error:
        print(f"Profiling error: {error}")
        return 1

    # Generate and print report
    report = profiler.generate_report()
    print(report)

    # Option for detailed profiling
    if detailed:
        profiler.profile_with_cprofile()

    return 0


if __name__ == "__main__":
    sys.exit(main())