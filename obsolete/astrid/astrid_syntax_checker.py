#!/usr/bin/env python3
"""
Astrid Syntax Checker
Provides comprehensive syntax validation and error reporting for Astrid programs.
"""

import argparse
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add astrid src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'astrid', 'src'))

try:
    from astrid2.lexer.lexer import Lexer
    from astrid2.parser.parser import Parser
    from astrid2.semantic.analyzer import SemanticAnalyzer
    from astrid2.utils.error import CompilerError, LexerError, ParserError
    from astrid2.lexer.tokens import TokenType
except ImportError as e:
    print(f"Error importing Astrid modules: {e}")
    print("Please ensure you're running from the Nova directory")
    sys.exit(1)


class AstridSyntaxChecker:
    """Comprehensive syntax checker for Astrid programs."""
    
    def __init__(self):
        self.lexer = Lexer()
        self.parser = Parser()
        self.semantic_analyzer = SemanticAnalyzer()
        
    def check_syntax(self, source_code: str, filename: str = "<stdin>") -> Dict[str, Any]:
        """
        Perform comprehensive syntax checking on Astrid source code.
        
        Args:
            source_code: The Astrid source code to check
            filename: Source filename for error reporting
            
        Returns:
            Dictionary containing analysis results
        """
        result = {
            'filename': filename,
            'valid': True,
            'errors': [],
            'warnings': [],
            'stats': {},
            'tokens': None,
            'ast': None,
            'semantic_info': {}
        }
        
        # Phase 1: Lexical Analysis
        try:
            tokens = self.lexer.tokenize(source_code, filename)
            result['tokens'] = tokens
            result['stats']['token_count'] = len(tokens)
            result['stats']['lines_of_code'] = source_code.count('\n') + 1
            
            # Analyze token statistics
            token_stats = self._analyze_tokens(tokens)
            result['stats'].update(token_stats)
            
        except LexerError as e:
            result['valid'] = False
            result['errors'].append({
                'phase': 'lexer',
                'type': 'LexerError',
                'message': str(e),
                'line': getattr(e, 'line', None),
                'column': getattr(e, 'column', None)
            })
            return result
        except Exception as e:
            result['valid'] = False
            result['errors'].append({
                'phase': 'lexer',
                'type': 'UnexpectedError',
                'message': f"Unexpected lexer error: {e}"
            })
            return result
        
        # Phase 2: Syntax Analysis
        try:
            ast = self.parser.parse(tokens, filename)
            result['ast'] = ast
            result['stats']['function_count'] = len(ast.functions)
            
            # Analyze AST structure
            ast_stats = self._analyze_ast(ast)
            result['stats'].update(ast_stats)
            
        except ParserError as e:
            result['valid'] = False
            result['errors'].append({
                'phase': 'parser',
                'type': 'ParserError',
                'message': str(e),
                'line': getattr(e, 'line', None),
                'column': getattr(e, 'column', None)
            })
            return result
        except Exception as e:
            result['valid'] = False
            result['errors'].append({
                'phase': 'parser',
                'type': 'UnexpectedError',
                'message': f"Unexpected parser error: {e}"
            })
            return result
        
        # Phase 3: Semantic Analysis
        try:
            # Reset analyzer state
            if hasattr(self.semantic_analyzer, 'reset_state'):
                self.semantic_analyzer.reset_state()
            
            self.semantic_analyzer.analyze(ast)
            
            if self.semantic_analyzer.errors:
                result['valid'] = False
                for error in self.semantic_analyzer.errors:
                    result['errors'].append({
                        'phase': 'semantic',
                        'type': 'SemanticError',
                        'message': str(error)
                    })
            
            # Collect semantic information
            result['semantic_info'] = self._analyze_semantics(self.semantic_analyzer)
            
        except Exception as e:
            result['errors'].append({
                'phase': 'semantic',
                'type': 'UnexpectedError',
                'message': f"Unexpected semantic analysis error: {e}"
            })
        
        return result
    
    def _analyze_tokens(self, tokens: List) -> Dict[str, Any]:
        """Analyze token statistics."""
        stats = {
            'keywords': 0,
            'identifiers': 0,
            'literals': 0,
            'operators': 0,
            'comments_lines': 0
        }
        
        keyword_counts = {}
        operator_counts = {}
        
        for token in tokens:
            if token.type == TokenType.EOF:
                continue
                
            # Count by category
            if token.type.value in ['void', 'int8', 'int16', 'if', 'else', 'while', 'for', 'return']:
                stats['keywords'] += 1
                keyword_counts[token.type.value] = keyword_counts.get(token.type.value, 0) + 1
            elif token.type == TokenType.IDENTIFIER:
                stats['identifiers'] += 1
            elif token.type in [TokenType.NUMBER, TokenType.STRING_LITERAL]:
                stats['literals'] += 1
            elif token.type.value in ['+', '-', '*', '/', '=', '==', '!=', '<', '>', '<=', '>=']:
                stats['operators'] += 1
                operator_counts[token.type.value] = operator_counts.get(token.type.value, 0) + 1
        
        stats['keyword_frequency'] = keyword_counts
        stats['operator_frequency'] = operator_counts
        
        return stats
    
    def _analyze_ast(self, ast) -> Dict[str, Any]:
        """Analyze AST structure."""
        stats = {
            'variable_declarations': 0,
            'function_calls': 0,
            'control_structures': 0,
            'max_nesting_depth': 0,
            'function_names': []
        }
        
        # Analyze functions
        for func in ast.functions:
            stats['function_names'].append(func.name)
            
            # Count statements recursively
            func_stats = self._analyze_statements(func.body, 0)
            for key in ['variable_declarations', 'function_calls', 'control_structures']:
                stats[key] += func_stats.get(key, 0)
            stats['max_nesting_depth'] = max(stats['max_nesting_depth'], 
                                           func_stats.get('max_depth', 0))
        
        return stats
    
    def _analyze_statements(self, statements: List, depth: int = 0) -> Dict[str, Any]:
        """Recursively analyze statements."""
        stats = {
            'variable_declarations': 0,
            'function_calls': 0,
            'control_structures': 0,
            'max_depth': depth
        }
        
        for stmt in statements:
            # This would need to be expanded based on actual AST node types
            stmt_type = type(stmt).__name__
            
            if 'Declaration' in stmt_type:
                stats['variable_declarations'] += 1
            elif 'Call' in stmt_type:
                stats['function_calls'] += 1
            elif stmt_type in ['IfStatement', 'WhileStatement', 'ForStatement']:
                stats['control_structures'] += 1
                # Recursively analyze nested statements
                if hasattr(stmt, 'body'):
                    nested_stats = self._analyze_statements(stmt.body, depth + 1)
                    for key in ['variable_declarations', 'function_calls', 'control_structures']:
                        stats[key] += nested_stats.get(key, 0)
                    stats['max_depth'] = max(stats['max_depth'], nested_stats['max_depth'])
        
        return stats
    
    def _analyze_semantics(self, analyzer) -> Dict[str, Any]:
        """Analyze semantic information."""
        info = {
            'symbol_count': 0,
            'type_errors': 0,
            'scope_depth': 0
        }
        
        # This would need to be expanded based on semantic analyzer structure
        if hasattr(analyzer, 'symbol_table'):
            info['symbol_count'] = len(getattr(analyzer.symbol_table, 'symbols', {}))
        
        return info


def print_results(result: Dict[str, Any], verbose: bool = False):
    """Print syntax checking results in a formatted way."""
    print(f"=== ASTRID SYNTAX CHECKER ===")
    print(f"File: {result['filename']}")
    print(f"Status: {'✅ VALID' if result['valid'] else '❌ INVALID'}")
    
    if result['errors']:
        print(f"\n❌ ERRORS ({len(result['errors'])}):")
        for i, error in enumerate(result['errors'], 1):
            print(f"  {i}. [{error['phase'].upper()}] {error['type']}: {error['message']}")
            if 'line' in error and error['line']:
                print(f"     Line {error['line']}, Column {error.get('column', '?')}")
    
    if result['warnings']:
        print(f"\n⚠️  WARNINGS ({len(result['warnings'])}):")
        for i, warning in enumerate(result['warnings'], 1):
            print(f"  {i}. {warning}")
    
    # Statistics
    stats = result['stats']
    print(f"\n📊 STATISTICS:")
    print(f"  Lines of code: {stats.get('lines_of_code', 0)}")
    print(f"  Total tokens: {stats.get('token_count', 0)}")
    print(f"  Functions: {stats.get('function_count', 0)}")
    print(f"  Variables: {stats.get('variable_declarations', 0)}")
    print(f"  Function calls: {stats.get('function_calls', 0)}")
    print(f"  Control structures: {stats.get('control_structures', 0)}")
    print(f"  Max nesting depth: {stats.get('max_nesting_depth', 0)}")
    
    if verbose and 'function_names' in stats:
        print(f"\n🔧 FUNCTIONS:")
        for func_name in stats['function_names']:
            print(f"  - {func_name}")
    
    if verbose and 'keyword_frequency' in stats:
        print(f"\n🔤 KEYWORD FREQUENCY:")
        for keyword, count in sorted(stats['keyword_frequency'].items()):
            print(f"  {keyword}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Astrid Syntax Checker")
    parser.add_argument("source", help="Astrid source file (.ast)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.source):
        print(f"Error: Source file '{args.source}' not found")
        sys.exit(1)
    
    try:
        with open(args.source, 'r', encoding='utf-8') as f:
            source_code = f.read()
    except Exception as e:
        print(f"Error reading source file: {e}")
        sys.exit(1)
    
    checker = AstridSyntaxChecker()
    result = checker.check_syntax(source_code, args.source)
    
    if args.json:
        import json
        # Make result JSON-serializable
        json_result = {k: v for k, v in result.items() if k not in ['tokens', 'ast']}
        print(json.dumps(json_result, indent=2))
    else:
        print_results(result, args.verbose)
    
    sys.exit(0 if result['valid'] else 1)


if __name__ == "__main__":
    main()
