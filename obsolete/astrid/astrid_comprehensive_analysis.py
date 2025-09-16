#!/usr/bin/env python3
"""
Comprehensive Astrid Language Pipeline Analysis Tool
Performs thorough static analysis of the Astrid compiler for bugs, flaws, and inconsistencies.
"""

import sys
import os
import re
import inspect
from typing import Dict, List, Set, Tuple, Any
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'astrid', 'src'))

from astrid2.lexer.lexer import Lexer
from astrid2.lexer.tokens import TokenType, KEYWORDS, SINGLE_CHAR_TOKENS, MULTI_CHAR_OPERATORS
from astrid2.parser.parser import Parser
from astrid2.parser.ast import Type
from astrid2.semantic.analyzer import SemanticAnalyzer
from astrid2.ir.builder import IRBuilder
from astrid2.codegen.pure_stack_generator import PureStackCodeGenerator

class AstridAnalyzer:
    """Comprehensive analyzer for the Astrid language pipeline."""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.lexer = Lexer()
        self.parser = Parser()
        self.semantic_analyzer = SemanticAnalyzer()
        self.ir_builder = IRBuilder()
        self.code_generator = PureStackCodeGenerator()
        
    def log_issue(self, category: str, severity: str, component: str, description: str, location: str = ""):
        """Log a discovered issue."""
        self.issues.append({
            'category': category,
            'severity': severity,
            'component': component,
            'description': description,
            'location': location
        })
        
    def log_warning(self, category: str, component: str, description: str, location: str = ""):
        """Log a discovered warning."""
        self.warnings.append({
            'category': category,
            'component': component,
            'description': description,
            'location': location
        })

    def analyze_lexer_consistency(self):
        """Analyze lexer for consistency issues."""
        print("Analyzing Lexer Consistency...")
        
        # Check token type consistency
        token_values = set()
        for token_type in TokenType:
            if token_type.value in token_values:
                self.log_issue("Consistency", "CRITICAL", "Lexer", 
                    f"Duplicate token value: {token_type.value}")
            token_values.add(token_type.value)
            
        # Check keyword mapping consistency
        missing_keywords = []
        for keyword, token_type in KEYWORDS.items():
            if not hasattr(TokenType, token_type.name):
                missing_keywords.append(keyword)
                
        if missing_keywords:
            self.log_issue("Consistency", "HIGH", "Lexer",
                f"Keywords mapped to non-existent token types: {missing_keywords}")
                
        # Check operator consistency
        for char, token_type in SINGLE_CHAR_TOKENS.items():
            if char in MULTI_CHAR_OPERATORS:
                self.log_warning("Consistency", "Lexer",
                    f"Character '{char}' appears in both single and multi-char operators")
                    
        # Check escape sequence handling
        lexer_source = inspect.getsource(self.lexer._scan_string)
        escape_sequences = re.findall(r'escape_char == "([^"]*)"', lexer_source)
        standard_escapes = ["n", "t", "r", "\\", '"']
        
        for seq in escape_sequences:
            if seq not in standard_escapes:
                self.log_warning("Standards", "Lexer",
                    f"Non-standard escape sequence: \\{seq}")

    def analyze_parser_completeness(self):
        """Analyze parser for completeness and consistency."""
        print("Analyzing Parser Completeness...")
        
        # Check if all token types are handled
        parser_source = inspect.getsource(Parser)
        
        # Find all TokenType references in parser
        token_refs = re.findall(r'TokenType\.([A-Z_]+)', parser_source)
        referenced_tokens = set(token_refs)
        
        all_tokens = set(token.name for token in TokenType)
        unreferenced_tokens = all_tokens - referenced_tokens
        
        # Filter out tokens that might be legitimately unreferenced
        problematic_tokens = []
        for token in unreferenced_tokens:
            if token not in ['EOF', 'COMMENT', 'WHITESPACE']:
                problematic_tokens.append(token)
                
        if problematic_tokens:
            self.log_warning("Completeness", "Parser",
                f"Tokens not referenced in parser: {problematic_tokens}")
                
        # Check for missing AST node types
        try:
            from astrid2.parser.ast import (
                BinaryOp, UnaryOp, TernaryOp, Assignment, IfStatement, 
                WhileStatement, ForStatement, SwitchStatement
            )
        except ImportError as e:
            self.log_issue("Completeness", "HIGH", "Parser",
                f"Missing AST node import: {e}")

    def analyze_semantic_type_system(self):
        """Analyze semantic analyzer type system for consistency."""
        print("Analyzing Semantic Type System...")
        
        # Check builtin function consistency
        builtin_functions = self.semantic_analyzer.builtin_functions
        builtin_signatures = self.semantic_analyzer.builtin_signatures
        
        # Find functions without signatures
        missing_signatures = []
        for func_name in builtin_functions:
            if func_name not in builtin_signatures:
                missing_signatures.append(func_name)
                
        if missing_signatures:
            self.log_warning("Completeness", "Semantic",
                f"Builtin functions without signatures: {missing_signatures}")
                
        # Find signatures without functions
        extra_signatures = []
        for func_name in builtin_signatures:
            if func_name not in builtin_functions:
                extra_signatures.append(func_name)
                
        if extra_signatures:
            self.log_warning("Consistency", "Semantic",
                f"Signatures without corresponding functions: {extra_signatures}")
                
        # Check type compatibility logic
        analyzer_source = inspect.getsource(self.semantic_analyzer._type_compatible)
        
        # Look for hardcoded type checks that might be incomplete
        hardcoded_types = re.findall(r'Type\.([A-Z_0-9]+)', analyzer_source)
        available_types = set(t.name for t in Type)
        
        missing_type_checks = available_types - set(hardcoded_types)
        if missing_type_checks:
            self.log_warning("Completeness", "Semantic",
                f"Types not handled in compatibility checks: {missing_type_checks}")

    def analyze_ir_generation(self):
        """Analyze IR generation for consistency."""
        print("Analyzing IR Generation...")
        
        # Check for proper visitor pattern implementation
        ir_source = inspect.getsource(IRBuilder)
        
        # Find all visit methods
        visit_methods = re.findall(r'def (visit_[a-z_]+)\(', ir_source)
        
        # Check if all AST node types have corresponding visit methods
        from astrid2.parser import ast
        ast_classes = []
        for name in dir(ast):
            obj = getattr(ast, name)
            if (inspect.isclass(obj) and 
                hasattr(obj, 'accept') and 
                name not in ['ASTNode', 'ASTVisitor']):
                ast_classes.append(name.lower())
                
        missing_visitors = []
        for ast_class in ast_classes:
            visitor_name = f"visit_{ast_class}"
            if visitor_name not in visit_methods:
                missing_visitors.append(visitor_name)
                
        if missing_visitors:
            self.log_warning("Completeness", "IR",
                f"Missing visitor methods: {missing_visitors}")

    def analyze_code_generation_patterns(self):
        """Analyze code generation for common patterns and issues."""
        print("Analyzing Code Generation Patterns...")
        
        codegen_source = inspect.getsource(PureStackCodeGenerator)
        
        # Check for hardcoded register usage
        register_refs = re.findall(r'["\']([RP][0-9])["\']', codegen_source)
        register_usage = {}
        for reg in register_refs:
            register_usage[reg] = register_usage.get(reg, 0) + 1
            
        # Check if register usage follows stack-centric principles
        excessive_register_usage = []
        for reg, count in register_usage.items():
            if count > 20:  # Arbitrary threshold
                excessive_register_usage.append((reg, count))
                
        if excessive_register_usage:
            self.log_warning("Design", "CodeGen",
                f"Potentially excessive register usage: {excessive_register_usage}")
                
        # Check for proper FP-relative addressing
        fp_refs = len(re.findall(r'FP[+-]', codegen_source))
        absolute_refs = len(re.findall(r'0x[0-9A-Fa-f]+', codegen_source))
        
        if absolute_refs > fp_refs * 2:  # Allow some absolute refs for constants
            self.log_warning("Design", "CodeGen",
                f"More absolute references ({absolute_refs}) than FP-relative ({fp_refs})")

    def test_basic_compilation_pipeline(self):
        """Test basic compilation pipeline with various inputs."""
        print("Testing Basic Compilation Pipeline...")
        
        test_cases = [
            # Basic variable declaration
            "void main() { int16 x = 42; }",
            
            # Function call
            "void main() { set_pixel(100, 100, 15); }",
            
            # Arithmetic expression
            "void main() { int16 result = 10 + 20 * 3; }",
            
            # Control flow
            "void main() { if (true) { int16 x = 1; } }",
            
            # Loop
            "void main() { for (int8 i = 0; i < 10; i++) { } }",
            
            # String handling
            'void main() { string msg = "Hello"; }',
            
            # Hardware access
            "void main() { int16 x = random(); }",
        ]
        
        for i, test_code in enumerate(test_cases):
            try:
                # Reset state
                self.semantic_analyzer.reset_state()
                
                # Lexing
                tokens = self.lexer.tokenize(test_code, f"test_{i}.ast")
                
                # Parsing
                ast = self.parser.parse(tokens, f"test_{i}.ast")
                
                # Semantic analysis
                self.semantic_analyzer.analyze(ast)
                if self.semantic_analyzer.errors:
                    self.log_issue("Pipeline", "MEDIUM", "Integration",
                        f"Test case {i} failed semantic analysis: {self.semantic_analyzer.errors[0]}")
                    continue
                    
                # IR generation
                ir_module = self.ir_builder.build(ast, self.semantic_analyzer)
                
                # Code generation
                assembly = self.code_generator.generate(ir_module)
                
                if not assembly or len(assembly.strip()) == 0:
                    self.log_issue("Pipeline", "HIGH", "Integration",
                        f"Test case {i} produced empty assembly")
                        
            except Exception as e:
                self.log_issue("Pipeline", "HIGH", "Integration",
                    f"Test case {i} failed with exception: {e}")

    def analyze_builtin_function_consistency(self):
        """Analyze builtin function implementations for consistency."""
        print("Analyzing Builtin Function Consistency...")
        
        # Check graphics builtins
        try:
            from astrid2.builtin.graphics import GraphicsBuiltins
            graphics = GraphicsBuiltins()
            
            # Check if all graphics functions return valid assembly
            for func_name, func in graphics.functions.items():
                try:
                    if callable(func):
                        # Try calling with dummy parameters
                        result = func()
                        if not isinstance(result, str):
                            self.log_issue("Implementation", "MEDIUM", "Builtins",
                                f"Graphics function {func_name} doesn't return string")
                except Exception as e:
                    self.log_warning("Implementation", "Builtins",
                        f"Graphics function {func_name} failed test call: {e}")
                        
        except ImportError:
            self.log_issue("Structure", "HIGH", "Builtins",
                "Graphics builtins module not found")

    def check_error_handling_completeness(self):
        """Check error handling throughout the pipeline."""
        print("Checking Error Handling...")
        
        # Check if all components properly use error classes
        components = [
            ('Lexer', self.lexer),
            ('Parser', self.parser),
            ('Semantic', self.semantic_analyzer),
            ('IR', self.ir_builder),
            ('CodeGen', self.code_generator)
        ]
        
        for name, component in components:
            source = inspect.getsource(component.__class__)
            
            # Check for bare exceptions
            bare_excepts = len(re.findall(r'except:', source))
            if bare_excepts > 0:
                self.log_warning("ErrorHandling", name,
                    f"Found {bare_excepts} bare except clauses")
                    
            # Check for proper error message formatting
            error_messages = re.findall(r'raise.*Error\((.*?)\)', source, re.DOTALL)
            for msg in error_messages:
                if 'f"' not in msg and '{' not in msg:
                    self.log_warning("ErrorHandling", name,
                        "Error message might not include context information")

    def run_comprehensive_analysis(self):
        """Run all analysis modules."""
        print("=== ASTRID COMPREHENSIVE PIPELINE ANALYSIS ===")
        print()
        
        # Run all analysis modules
        self.analyze_lexer_consistency()
        self.analyze_parser_completeness()
        self.analyze_semantic_type_system()
        self.analyze_ir_generation()
        self.analyze_code_generation_patterns()
        self.test_basic_compilation_pipeline()
        self.analyze_builtin_function_consistency()
        self.check_error_handling_completeness()
        
        # Report results
        print("\n=== ANALYSIS RESULTS ===")
        
        if self.issues:
            print(f"\n🔴 ISSUES FOUND: {len(self.issues)}")
            for issue in self.issues:
                severity_icon = {"CRITICAL": "🚨", "HIGH": "🔥", "MEDIUM": "⚠️", "LOW": "ℹ️"}
                icon = severity_icon.get(issue['severity'], "❓")
                print(f"{icon} [{issue['severity']}] {issue['component']}.{issue['category']}: {issue['description']}")
                if issue['location']:
                    print(f"    Location: {issue['location']}")
        else:
            print("✅ No critical issues found!")
            
        if self.warnings:
            print(f"\n⚠️ WARNINGS: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"⚠️ {warning['component']}.{warning['category']}: {warning['description']}")
                if warning['location']:
                    print(f"    Location: {warning['location']}")
        else:
            print("✅ No warnings!")
            
        print(f"\n📊 SUMMARY:")
        print(f"   Critical Issues: {len([i for i in self.issues if i['severity'] == 'CRITICAL'])}")
        print(f"   High Priority: {len([i for i in self.issues if i['severity'] == 'HIGH'])}")
        print(f"   Medium Priority: {len([i for i in self.issues if i['severity'] == 'MEDIUM'])}")
        print(f"   Low Priority: {len([i for i in self.issues if i['severity'] == 'LOW'])}")
        print(f"   Warnings: {len(self.warnings)}")
        print()

if __name__ == "__main__":
    analyzer = AstridAnalyzer()
    analyzer.run_comprehensive_analysis()
