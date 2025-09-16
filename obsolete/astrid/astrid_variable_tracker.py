#!/usr/bin/env python3
"""
Astrid Variable Tracker
Tracks variable usage, scope, and lifetime throughout Astrid programs.
"""

import argparse
import sys
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class VariableInfo:
    """Information about a variable."""
    name: str
    type: str
    scope: str
    declared_line: int
    first_use: Optional[int] = None
    last_use: Optional[int] = None
    read_count: int = 0
    write_count: int = 0
    is_parameter: bool = False
    is_unused: bool = False


@dataclass
class ScopeInfo:
    """Information about a scope."""
    name: str
    type: str  # 'function', 'block', 'loop'
    start_line: int
    end_line: Optional[int] = None
    parent: Optional[str] = None
    variables: Dict[str, VariableInfo] = None
    
    def __post_init__(self):
        if self.variables is None:
            self.variables = {}


class AstridVariableTracker:
    """Tracks variables and their usage in Astrid programs."""
    
    def __init__(self):
        self.scopes: Dict[str, ScopeInfo] = {}
        self.current_scope_stack: List[str] = []
        self.variables: Dict[str, VariableInfo] = {}
        self.scope_counter = 0
        
    def analyze_file(self, source_code: str, filename: str = "<stdin>") -> Dict[str, Any]:
        """
        Analyze variable usage in an Astrid source file.
        
        Args:
            source_code: The Astrid source code
            filename: Source filename
            
        Returns:
            Dictionary containing analysis results
        """
        lines = source_code.split('\n')
        
        # Reset state
        self.scopes = {}
        self.current_scope_stack = []
        self.variables = {}
        self.scope_counter = 0
        
        # Create global scope
        global_scope = ScopeInfo("global", "global", 1)
        self.scopes["global"] = global_scope
        self.current_scope_stack.append("global")
        
        # Analyze line by line
        for line_num, line in enumerate(lines, 1):
            self._analyze_line(line, line_num)
        
        # Post-processing
        self._finalize_analysis()
        
        return {
            'filename': filename,
            'scopes': self.scopes,
            'variables': self.variables,
            'statistics': self._calculate_statistics(),
            'warnings': self._generate_warnings(),
            'unused_variables': self._find_unused_variables()
        }
    
    def _analyze_line(self, line: str, line_num: int):
        """Analyze a single line for variable-related patterns."""
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('//') or line.startswith('/*'):
            return
        
        # Function declarations
        func_match = re.match(r'(void|int8|int16)\s+(\w+)\s*\([^)]*\)\s*{?', line)
        if func_match:
            func_name = func_match.group(2)
            scope_id = f"func_{func_name}_{line_num}"
            scope = ScopeInfo(func_name, "function", line_num)
            self.scopes[scope_id] = scope
            self.current_scope_stack.append(scope_id)
            
            # Parse parameters
            param_match = re.search(r'\(([^)]*)\)', line)
            if param_match and param_match.group(1).strip():
                self._parse_parameters(param_match.group(1), line_num, scope_id)
            return
        
        # Block starts (if, for, while)
        if re.match(r'\s*(if|for|while)\s*\(', line):
            self.scope_counter += 1
            scope_id = f"block_{self.scope_counter}_{line_num}"
            block_type = re.match(r'\s*(\w+)', line).group(1)
            scope = ScopeInfo(f"{block_type}_{self.scope_counter}", block_type, line_num)
            if self.current_scope_stack:
                scope.parent = self.current_scope_stack[-1]
            self.scopes[scope_id] = scope
            self.current_scope_stack.append(scope_id)
        
        # Block ends
        if line.strip() == '}':
            if len(self.current_scope_stack) > 1:  # Don't pop global scope
                scope_id = self.current_scope_stack.pop()
                if scope_id in self.scopes:
                    self.scopes[scope_id].end_line = line_num
        
        # Variable declarations
        var_decl_patterns = [
            r'(int8|int16|char|string|pixel|color)\s+(\w+)(?:\s*=\s*[^;]+)?;?',
            r'(int8|int16|char|string|pixel|color)\s+(\w+)\s*\[.*?\](?:\s*=\s*[^;]+)?;?'
        ]
        
        for pattern in var_decl_patterns:
            for match in re.finditer(pattern, line):
                var_type = match.group(1)
                var_name = match.group(2)
                self._declare_variable(var_name, var_type, line_num, False)
        
        # Variable assignments (writes)
        assignment_patterns = [
            r'(\w+)\s*=\s*[^=]',  # Simple assignment
            r'(\w+)\s*[+\-*/]?=',  # Compound assignment
            r'(\w+)\+\+',          # Increment
            r'\+\+(\w+)',          # Pre-increment
            r'(\w+)--',            # Decrement
            r'--(\w+)'             # Pre-decrement
        ]
        
        for pattern in assignment_patterns:
            for match in re.finditer(pattern, line):
                var_name = match.group(1)
                if var_name and var_name.isidentifier():
                    self._record_variable_write(var_name, line_num)
        
        # Variable reads (usage in expressions)
        # This is more complex as we need to distinguish from assignments
        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', line)
        for word in words:
            if word not in ['int8', 'int16', 'char', 'string', 'pixel', 'color', 'void',
                          'if', 'else', 'for', 'while', 'return', 'true', 'false',
                          'set_pixel', 'set_layer', 'print_string', 'random_range', 'halt']:
                # Check if it's not being declared or assigned to
                if not re.search(rf'(int8|int16|char|string|pixel|color)\s+{re.escape(word)}', line):
                    if not re.search(rf'{re.escape(word)}\s*=\s*[^=]', line):
                        self._record_variable_read(word, line_num)
    
    def _parse_parameters(self, param_str: str, line_num: int, scope_id: str):
        """Parse function parameters."""
        params = [p.strip() for p in param_str.split(',') if p.strip()]
        for param in params:
            parts = param.split()
            if len(parts) >= 2:
                param_type = parts[0]
                param_name = parts[1]
                self._declare_variable(param_name, param_type, line_num, True)
    
    def _declare_variable(self, name: str, var_type: str, line_num: int, is_param: bool):
        """Record a variable declaration."""
        current_scope = self.current_scope_stack[-1] if self.current_scope_stack else "global"
        
        var_info = VariableInfo(
            name=name,
            type=var_type,
            scope=current_scope,
            declared_line=line_num,
            is_parameter=is_param
        )
        
        # Use qualified name to handle scope
        qualified_name = f"{current_scope}.{name}"
        self.variables[qualified_name] = var_info
        
        # Add to scope
        if current_scope in self.scopes:
            self.scopes[current_scope].variables[name] = var_info
    
    def _record_variable_write(self, name: str, line_num: int):
        """Record a variable write operation."""
        var_info = self._find_variable(name)
        if var_info:
            var_info.write_count += 1
            var_info.last_use = line_num
            if var_info.first_use is None:
                var_info.first_use = line_num
    
    def _record_variable_read(self, name: str, line_num: int):
        """Record a variable read operation."""
        var_info = self._find_variable(name)
        if var_info:
            var_info.read_count += 1
            var_info.last_use = line_num
            if var_info.first_use is None:
                var_info.first_use = line_num
    
    def _find_variable(self, name: str) -> Optional[VariableInfo]:
        """Find a variable by name, considering scope hierarchy."""
        # Check current scope first, then parent scopes
        for scope_id in reversed(self.current_scope_stack):
            qualified_name = f"{scope_id}.{name}"
            if qualified_name in self.variables:
                return self.variables[qualified_name]
        return None
    
    def _finalize_analysis(self):
        """Finalize the analysis by marking unused variables."""
        for var_info in self.variables.values():
            if var_info.read_count == 0 and var_info.write_count <= 1 and not var_info.is_parameter:
                var_info.is_unused = True
    
    def _calculate_statistics(self) -> Dict[str, Any]:
        """Calculate usage statistics."""
        stats = {
            'total_variables': len(self.variables),
            'unused_variables': sum(1 for v in self.variables.values() if v.is_unused),
            'parameters': sum(1 for v in self.variables.values() if v.is_parameter),
            'read_only_variables': sum(1 for v in self.variables.values() if v.read_count > 0 and v.write_count <= 1),
            'write_only_variables': sum(1 for v in self.variables.values() if v.write_count > 0 and v.read_count == 0),
            'scopes': len(self.scopes),
            'max_scope_depth': len(self.current_scope_stack),
            'variables_by_type': defaultdict(int),
            'variables_by_scope_type': defaultdict(int)
        }
        
        for var_info in self.variables.values():
            stats['variables_by_type'][var_info.type] += 1
            
            # Determine scope type
            scope_id = var_info.scope
            if scope_id in self.scopes:
                scope_type = self.scopes[scope_id].type
                stats['variables_by_scope_type'][scope_type] += 1
        
        return dict(stats)
    
    def _generate_warnings(self) -> List[Dict[str, Any]]:
        """Generate warnings about variable usage."""
        warnings = []
        
        for qualified_name, var_info in self.variables.items():
            # Unused variables
            if var_info.is_unused and not var_info.is_parameter:
                warnings.append({
                    'type': 'unused_variable',
                    'severity': 'warning',
                    'message': f"Variable '{var_info.name}' is declared but never used",
                    'line': var_info.declared_line,
                    'variable': var_info.name
                })
            
            # Write-only variables (excluding parameters)
            elif var_info.write_count > 0 and var_info.read_count == 0 and not var_info.is_parameter:
                warnings.append({
                    'type': 'write_only_variable',
                    'severity': 'info',
                    'message': f"Variable '{var_info.name}' is written to but never read",
                    'line': var_info.declared_line,
                    'variable': var_info.name
                })
            
            # Variables used before written (potential uninitialized use)
            elif var_info.read_count > 0 and var_info.write_count == 0 and not var_info.is_parameter:
                warnings.append({
                    'type': 'potentially_uninitialized',
                    'severity': 'warning',
                    'message': f"Variable '{var_info.name}' may be used before initialization",
                    'line': var_info.first_use or var_info.declared_line,
                    'variable': var_info.name
                })
        
        return warnings
    
    def _find_unused_variables(self) -> List[str]:
        """Find all unused variables."""
        return [var_info.name for var_info in self.variables.values() if var_info.is_unused]


def print_analysis_results(results: Dict[str, Any], verbose: bool = False):
    """Print variable analysis results."""
    print(f"=== ASTRID VARIABLE TRACKER ===")
    print(f"File: {results['filename']}")
    
    stats = results['statistics']
    print(f"\n📊 STATISTICS:")
    print(f"  Total variables: {stats['total_variables']}")
    print(f"  Unused variables: {stats['unused_variables']}")
    print(f"  Parameters: {stats['parameters']}")
    print(f"  Read-only variables: {stats['read_only_variables']}")
    print(f"  Write-only variables: {stats['write_only_variables']}")
    print(f"  Scopes: {stats['scopes']}")
    
    if verbose and stats['variables_by_type']:
        print(f"\n🔤 VARIABLES BY TYPE:")
        for var_type, count in sorted(stats['variables_by_type'].items()):
            print(f"  {var_type}: {count}")
    
    # Warnings
    warnings = results['warnings']
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for i, warning in enumerate(warnings, 1):
            severity_icon = "🔴" if warning['severity'] == 'error' else "⚠️" if warning['severity'] == 'warning' else "ℹ️"
            print(f"  {i}. {severity_icon} Line {warning['line']}: {warning['message']}")
    
    # Unused variables
    unused = results['unused_variables']
    if unused:
        print(f"\n🗑️  UNUSED VARIABLES ({len(unused)}):")
        for var_name in unused:
            print(f"  - {var_name}")
    
    if verbose:
        print(f"\n🔍 VARIABLE DETAILS:")
        for qualified_name, var_info in sorted(results['variables'].items()):
            usage = f"R:{var_info.read_count} W:{var_info.write_count}"
            lifecycle = ""
            if var_info.first_use and var_info.last_use:
                lifecycle = f" (Lines {var_info.first_use}-{var_info.last_use})"
            elif var_info.first_use:
                lifecycle = f" (Line {var_info.first_use})"
            
            param_marker = " [PARAM]" if var_info.is_parameter else ""
            unused_marker = " [UNUSED]" if var_info.is_unused else ""
            
            print(f"  {var_info.name}: {var_info.type} | {usage}{lifecycle}{param_marker}{unused_marker}")


def main():
    parser = argparse.ArgumentParser(description="Astrid Variable Tracker")
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
    
    tracker = AstridVariableTracker()
    results = tracker.analyze_file(source_code, args.source)
    
    if args.json:
        import json
        # Make results JSON-serializable
        json_results = {}
        for key, value in results.items():
            if key in ['scopes', 'variables']:
                # Convert complex objects to dictionaries
                json_results[key] = {k: v.__dict__ if hasattr(v, '__dict__') else v 
                                   for k, v in value.items()}
            elif isinstance(value, defaultdict):
                json_results[key] = dict(value)
            else:
                json_results[key] = value
        print(json.dumps(json_results, indent=2))
    else:
        print_analysis_results(results, args.verbose)


if __name__ == "__main__":
    main()
