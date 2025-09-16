#!/usr/bin/env python3
"""
Astrid Debug Toolkit
A unified interface for all Astrid debugging and diagnostic tools.
"""

import argparse
import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional


class AstridDebugToolkit:
    """Unified interface for Astrid debugging tools."""
    
    def __init__(self):
        self.nova_dir = Path(__file__).parent
        
        # Available tools
        self.tools = {
            'syntax': {
                'script': 'astrid_syntax_checker.py',
                'description': 'Check syntax and validate Astrid source code',
                'args': ['source', '--verbose', '--json']
            },
            'profile': {
                'script': 'astrid_profiler.py',
                'description': 'Profile performance and analyze bottlenecks',
                'args': ['source', '--cycles', '--json']
            },
            'variables': {
                'script': 'astrid_variable_tracker.py',
                'description': 'Track variable usage and scope',
                'args': ['source', '--verbose', '--json']
            },
            'assembly': {
                'script': 'astrid_assembly_inspector.py',
                'description': 'Inspect generated assembly code',
                'args': ['source', '--verbose', '--json']
            },
            'test': {
                'script': 'astrid_test_generator.py',
                'description': 'Generate and run test cases',
                'args': ['--types', '--count', '--run', '--output', '--json']
            },
            'debug': {
                'script': 'astrid/astrid_debug_tool.py',
                'description': 'Comprehensive debugging (existing tool)',
                'args': ['source', '--verbose', '--cycles', '--no-test', '--no-graphics']
            }
        }
    
    def run_tool(self, tool_name: str, args: List[str]) -> Dict[str, Any]:
        """Run a specific debugging tool."""
        if tool_name not in self.tools:
            return {'error': f"Unknown tool: {tool_name}"}
        
        tool_info = self.tools[tool_name]
        script_path = self.nova_dir / tool_info['script']
        
        if not script_path.exists():
            return {'error': f"Tool script not found: {script_path}"}
        
        try:
            cmd = ['python', str(script_path)] + args
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.nova_dir)
            
            return {
                'tool': tool_name,
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode
            }
        except Exception as e:
            return {'error': f"Failed to run tool: {e}"}
    
    def run_comprehensive_analysis(self, source_file: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run comprehensive analysis using multiple tools."""
        if options is None:
            options = {}
        
        if not os.path.exists(source_file):
            return {'error': f"Source file not found: {source_file}"}
        
        results = {
            'source_file': source_file,
            'tools_run': [],
            'summary': {},
            'recommendations': []
        }
        
        # Define analysis pipeline
        pipeline = [
            ('syntax', [source_file, '--json']),
            ('variables', [source_file, '--json']),
            ('assembly', [source_file, '--json']),
            ('profile', [source_file, '--cycles', str(options.get('cycles', 5000)), '--json'])
        ]
        
        print(f"Running comprehensive analysis on {source_file}")
        
        for tool_name, tool_args in pipeline:
            print(f"  Running {tool_name} analysis...")
            
            tool_result = self.run_tool(tool_name, tool_args)
            results['tools_run'].append(tool_name)
            
            if tool_result.get('success'):
                # Parse JSON output if available
                try:
                    import json
                    if tool_result['stdout'].strip():
                        parsed_output = json.loads(tool_result['stdout'])
                        results[f'{tool_name}_results'] = parsed_output
                except json.JSONDecodeError:
                    results[f'{tool_name}_results'] = {'raw_output': tool_result['stdout']}
            else:
                results[f'{tool_name}_error'] = tool_result.get('stderr', 'Unknown error')
        
        # Generate summary and recommendations
        results['summary'] = self._generate_summary(results)
        results['recommendations'] = self._generate_recommendations(results)
        
        return results
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of all analysis results."""
        summary = {
            'overall_status': 'unknown',
            'key_metrics': {},
            'issues_found': 0,
            'performance_rating': 'unknown'
        }
        
        # Check syntax results
        if 'syntax_results' in results:
            syntax = results['syntax_results']
            summary['overall_status'] = 'valid' if syntax.get('valid', False) else 'invalid'
            summary['issues_found'] += len(syntax.get('errors', []))
            
            if 'stats' in syntax:
                summary['key_metrics']['lines_of_code'] = syntax['stats'].get('lines_of_code', 0)
                summary['key_metrics']['functions'] = syntax['stats'].get('function_count', 0)
        
        # Check variable results
        if 'variables_results' in results:
            variables = results['variables_results']
            if 'statistics' in variables:
                stats = variables['statistics']
                summary['key_metrics']['total_variables'] = stats.get('total_variables', 0)
                summary['key_metrics']['unused_variables'] = stats.get('unused_variables', 0)
                summary['issues_found'] += len(variables.get('warnings', []))
        
        # Check performance results
        if 'profile_results' in results:
            profile = results['profile_results']
            if 'performance_metrics' in profile:
                metrics = profile['performance_metrics']
                summary['performance_rating'] = metrics.get('performance_rating', 'unknown')
        
        return summary
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis results."""
        recommendations = []
        
        # Syntax-based recommendations
        if 'syntax_results' in results:
            syntax = results['syntax_results']
            if not syntax.get('valid', True):
                recommendations.append("🔴 Fix syntax errors before proceeding with optimization")
            
            stats = syntax.get('stats', {})
            if stats.get('max_nesting_depth', 0) > 5:
                recommendations.append("🟡 Consider reducing nesting depth for better readability")
        
        # Variable-based recommendations
        if 'variables_results' in results:
            variables = results['variables_results']
            stats = variables.get('statistics', {})
            
            unused_vars = stats.get('unused_variables', 0)
            if unused_vars > 0:
                recommendations.append(f"🟡 Remove {unused_vars} unused variable(s) to clean up code")
            
            if len(variables.get('warnings', [])) > 0:
                recommendations.append("🟡 Review variable warnings for potential issues")
        
        # Performance-based recommendations
        if 'profile_results' in results:
            profile = results['profile_results']
            suggestions = profile.get('optimization_suggestions', [])
            
            high_priority = [s for s in suggestions if s.get('priority') == 'High']
            if high_priority:
                recommendations.append(f"🔴 Address {len(high_priority)} high-priority performance issue(s)")
            
            medium_priority = [s for s in suggestions if s.get('priority') == 'Medium']
            if medium_priority:
                recommendations.append(f"🟡 Consider {len(medium_priority)} medium-priority optimization(s)")
        
        # Assembly-based recommendations
        if 'assembly_results' in results:
            assembly = results['assembly_results']
            opt_analysis = assembly.get('optimization_analysis', {})
            
            opt_score = opt_analysis.get('optimization_score', 100)
            if opt_score < 80:
                recommendations.append(f"🟡 Assembly optimization score is {opt_score}/100 - review generated code")
        
        # General recommendations
        if not recommendations:
            recommendations.append("✅ Code analysis looks good! No major issues found.")
        
        return recommendations
    
    def interactive_mode(self):
        """Run in interactive mode for debugging."""
        print("=== ASTRID DEBUG TOOLKIT - INTERACTIVE MODE ===")
        print("Available tools:")
        for name, info in self.tools.items():
            print(f"  {name}: {info['description']}")
        print("\nCommands:")
        print("  analyze <file>     - Run comprehensive analysis")
        print("  run <tool> <args>  - Run specific tool")
        print("  help              - Show this help")
        print("  quit              - Exit")
        
        while True:
            try:
                command = input("\n> ").strip()
                
                if not command:
                    continue
                elif command == 'quit':
                    break
                elif command == 'help':
                    self.interactive_mode()
                    return
                
                parts = command.split()
                cmd = parts[0]
                
                if cmd == 'analyze' and len(parts) >= 2:
                    source_file = parts[1]
                    results = self.run_comprehensive_analysis(source_file)
                    self._print_comprehensive_results(results)
                    
                elif cmd == 'run' and len(parts) >= 2:
                    tool_name = parts[1]
                    tool_args = parts[2:] if len(parts) > 2 else []
                    result = self.run_tool(tool_name, tool_args)
                    print(result.get('stdout', result.get('error', 'No output')))
                    
                else:
                    print("Unknown command. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    def _print_comprehensive_results(self, results: Dict[str, Any]):
        """Print comprehensive analysis results."""
        print(f"\n=== COMPREHENSIVE ANALYSIS RESULTS ===")
        print(f"Source: {results['source_file']}")
        
        summary = results.get('summary', {})
        print(f"\n📊 SUMMARY:")
        print(f"  Status: {summary.get('overall_status', 'unknown')}")
        print(f"  Performance: {summary.get('performance_rating', 'unknown')}")
        print(f"  Issues found: {summary.get('issues_found', 0)}")
        
        metrics = summary.get('key_metrics', {})
        if metrics:
            print(f"  Key metrics:")
            for metric, value in metrics.items():
                print(f"    {metric}: {value}")
        
        recommendations = results.get('recommendations', [])
        if recommendations:
            print(f"\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        
        print(f"\n🔧 TOOLS RUN: {', '.join(results.get('tools_run', []))}")


def main():
    parser = argparse.ArgumentParser(description="Astrid Debug Toolkit")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    parser.add_argument("--analyze", help="Run comprehensive analysis on source file")
    parser.add_argument("--tool", help="Run specific tool")
    parser.add_argument("--cycles", type=int, default=5000, help="Cycles for profiling")
    parser.add_argument("args", nargs="*", help="Arguments for the tool")
    
    args = parser.parse_args()
    
    toolkit = AstridDebugToolkit()
    
    if args.interactive:
        toolkit.interactive_mode()
    elif args.analyze:
        options = {'cycles': args.cycles}
        results = toolkit.run_comprehensive_analysis(args.analyze, options)
        toolkit._print_comprehensive_results(results)
    elif args.tool:
        result = toolkit.run_tool(args.tool, args.args)
        if result.get('success'):
            print(result['stdout'])
        else:
            print(f"Error: {result.get('stderr', result.get('error', 'Unknown error'))}")
    else:
        print("Astrid Debug Toolkit")
        print("\nAvailable tools:")
        for name, info in toolkit.tools.items():
            print(f"  {name}: {info['description']}")
        print(f"\nUsage:")
        print(f"  {sys.argv[0]} --analyze <file>           # Comprehensive analysis")
        print(f"  {sys.argv[0]} --tool <tool> [args]       # Run specific tool")
        print(f"  {sys.argv[0]} --interactive              # Interactive mode")


if __name__ == "__main__":
    main()
