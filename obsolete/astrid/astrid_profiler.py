#!/usr/bin/env python3
"""
Astrid Performance Profiler
Analyzes Astrid programs for performance characteristics and optimization opportunities.
"""

import argparse
import sys
import os
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict


class AstridProfiler:
    """Performance profiler for Astrid programs."""
    
    def __init__(self):
        self.nova_dir = Path(__file__).parent
        
    def profile_program(self, ast_file: str, cycles: int = 10000) -> Dict[str, Any]:
        """
        Profile an Astrid program comprehensively.
        
        Args:
            ast_file: Path to the Astrid source file
            cycles: Number of execution cycles to profile
            
        Returns:
            Dictionary containing profiling results
        """
        results = {
            'source_file': ast_file,
            'compilation': {},
            'assembly_analysis': {},
            'execution_profile': {},
            'performance_metrics': {},
            'optimization_suggestions': []
        }
        
        # Step 1: Compile the program
        print("🔄 Compiling Astrid program...")
        compile_result = self._compile_astrid(ast_file)
        results['compilation'] = compile_result
        
        if not compile_result.get('success'):
            return results
        
        asm_file = compile_result['assembly_file']
        
        # Step 2: Analyze assembly code
        print("🔍 Analyzing generated assembly...")
        asm_analysis = self._analyze_assembly(asm_file)
        results['assembly_analysis'] = asm_analysis
        
        # Step 3: Assemble and profile execution
        print("⚡ Profiling execution...")
        exec_profile = self._profile_execution(asm_file, cycles)
        results['execution_profile'] = exec_profile
        
        # Step 4: Calculate performance metrics
        print("📊 Calculating performance metrics...")
        metrics = self._calculate_metrics(asm_analysis, exec_profile)
        results['performance_metrics'] = metrics
        
        # Step 5: Generate optimization suggestions
        print("💡 Generating optimization suggestions...")
        suggestions = self._generate_suggestions(asm_analysis, metrics)
        results['optimization_suggestions'] = suggestions
        
        return results
    
    def _compile_astrid(self, ast_file: str) -> Dict[str, Any]:
        """Compile Astrid source to assembly."""
        try:
            ast_path = Path(ast_file)
            astrid_dir = self.nova_dir / "astrid"
            
            # Run Astrid compiler
            cmd = ["python", "run_astrid.py", str(ast_path.name)]
            result = subprocess.run(cmd, cwd=astrid_dir, capture_output=True, text=True)
            
            asm_file = astrid_dir / f"{ast_path.stem}.asm"
            
            return {
                'success': result.returncode == 0,
                'assembly_file': str(asm_file) if result.returncode == 0 else None,
                'compilation_output': result.stdout,
                'compilation_errors': result.stderr,
                'return_code': result.returncode
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _analyze_assembly(self, asm_file: str) -> Dict[str, Any]:
        """Analyze assembly code for performance characteristics."""
        try:
            with open(asm_file, 'r') as f:
                lines = f.readlines()
            
            analysis = {
                'total_lines': len(lines),
                'instruction_count': 0,
                'instruction_frequency': defaultdict(int),
                'register_usage': defaultdict(int),
                'memory_operations': 0,
                'graphics_operations': 0,
                'sound_operations': 0,
                'control_flow_instructions': 0,
                'optimization_opportunities': [],
                'hotspots': []
            }
            
            # Performance categories
            expensive_instructions = {'MUL', 'DIV', 'CALL', 'RET'}
            graphics_instructions = {'SWRITE', 'SREAD', 'VWRITE', 'VREAD', 'SROLX', 'SROLY'}
            sound_instructions = {'SPLAY', 'SSTOP'}
            memory_instructions = {'MOV', 'PUSH', 'POP', 'LOAD', 'STORE'}
            control_flow = {'JMP', 'JZ', 'JNZ', 'JC', 'JNC', 'CALL', 'RET'}
            
            consecutive_moves = 0
            last_instruction = None
            
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith(';') or line.endswith(':'):
                    continue
                
                parts = line.split()
                if not parts:
                    continue
                
                instruction = parts[0]
                analysis['instruction_count'] += 1
                analysis['instruction_frequency'][instruction] += 1
                
                # Count operation types
                if instruction in expensive_instructions:
                    analysis['hotspots'].append((i, line, 'expensive'))
                
                if instruction in graphics_instructions:
                    analysis['graphics_operations'] += 1
                
                if instruction in sound_instructions:
                    analysis['sound_operations'] += 1
                
                if instruction in memory_instructions:
                    analysis['memory_operations'] += 1
                
                if instruction in control_flow:
                    analysis['control_flow_instructions'] += 1
                
                # Track register usage
                for part in parts[1:]:
                    if re.match(r'^[RP]\d+$', part.strip(',')):
                        analysis['register_usage'][part.strip(',')] += 1
                
                # Detect optimization opportunities
                if instruction == 'MOV' and last_instruction == 'MOV':
                    consecutive_moves += 1
                else:
                    if consecutive_moves > 2:
                        analysis['optimization_opportunities'].append({
                            'type': 'consecutive_moves',
                            'line': i - consecutive_moves,
                            'count': consecutive_moves,
                            'suggestion': 'Consider batching memory operations'
                        })
                    consecutive_moves = 0
                
                last_instruction = instruction
            
            # Calculate percentages
            total = analysis['instruction_count']
            if total > 0:
                analysis['memory_percentage'] = (analysis['memory_operations'] / total) * 100
                analysis['graphics_percentage'] = (analysis['graphics_operations'] / total) * 100
                analysis['control_flow_percentage'] = (analysis['control_flow_instructions'] / total) * 100
            
            return analysis
            
        except Exception as e:
            return {'error': str(e)}
    
    def _profile_execution(self, asm_file: str, cycles: int) -> Dict[str, Any]:
        """Profile program execution."""
        try:
            asm_path = Path(asm_file)
            bin_file = asm_path.parent / f"{asm_path.stem}.bin"
            
            # Assemble first
            cmd = ["python", "nova_assembler.py", str(asm_file)]
            result = subprocess.run(cmd, cwd=self.nova_dir, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {'assembly_failed': True, 'error': result.stderr}
            
            # Run with profiling
            cmd = ["python", "nova.py", "--headless", str(bin_file), "--cycles", str(cycles)]
            result = subprocess.run(cmd, cwd=self.nova_dir, capture_output=True, text=True)
            
            # Parse execution output
            output_lines = result.stdout.split('\n')
            execution_data = {
                'cycles_executed': 0,
                'final_pc': None,
                'graphics_pixels': 0,
                'execution_time': None,
                'output': result.stdout
            }
            
            for line in output_lines:
                if "Execution finished" in line:
                    match = re.search(r'(\d+) cycles', line)
                    if match:
                        execution_data['cycles_executed'] = int(match.group(1))
                
                elif "Final PC:" in line:
                    match = re.search(r'0x([0-9A-Fa-f]+)', line)
                    if match:
                        execution_data['final_pc'] = match.group(1)
                
                elif "Graphics:" in line and "non-black pixels" in line:
                    match = re.search(r'(\d+) non-black pixels', line)
                    if match:
                        execution_data['graphics_pixels'] = int(match.group(1))
            
            return execution_data
            
        except Exception as e:
            return {'error': str(e)}
    
    def _calculate_metrics(self, asm_analysis: Dict, exec_profile: Dict) -> Dict[str, Any]:
        """Calculate performance metrics."""
        metrics = {}
        
        if 'instruction_count' in asm_analysis and 'cycles_executed' in exec_profile:
            code_size = asm_analysis['instruction_count']
            cycles = exec_profile['cycles_executed']
            
            if cycles > 0:
                metrics['instructions_per_cycle'] = code_size / cycles
                metrics['code_efficiency'] = min(1.0, code_size / cycles)
            
            # Performance rating
            if cycles < 1000:
                metrics['performance_rating'] = 'Excellent'
            elif cycles < 5000:
                metrics['performance_rating'] = 'Good'
            elif cycles < 10000:
                metrics['performance_rating'] = 'Average'
            else:
                metrics['performance_rating'] = 'Poor'
        
        # Memory efficiency
        if 'memory_percentage' in asm_analysis:
            mem_pct = asm_analysis['memory_percentage']
            if mem_pct < 30:
                metrics['memory_efficiency'] = 'Good'
            elif mem_pct < 50:
                metrics['memory_efficiency'] = 'Average'
            else:
                metrics['memory_efficiency'] = 'Poor'
        
        # Register usage efficiency
        if 'register_usage' in asm_analysis:
            reg_usage = asm_analysis['register_usage']
            unique_registers = len(reg_usage)
            total_usage = sum(reg_usage.values())
            
            if total_usage > 0:
                metrics['register_utilization'] = unique_registers / 20  # Assuming 20 total registers
                metrics['register_reuse'] = total_usage / unique_registers if unique_registers > 0 else 0
        
        return metrics
    
    def _generate_suggestions(self, asm_analysis: Dict, metrics: Dict) -> List[Dict[str, str]]:
        """Generate optimization suggestions."""
        suggestions = []
        
        # Memory operation suggestions
        if asm_analysis.get('memory_percentage', 0) > 50:
            suggestions.append({
                'category': 'Memory',
                'priority': 'High',
                'issue': 'High memory operation percentage',
                'suggestion': 'Consider using more register-based operations and reducing memory accesses',
                'impact': 'Significant performance improvement'
            })
        
        # Graphics operation suggestions
        if asm_analysis.get('graphics_percentage', 0) > 30:
            suggestions.append({
                'category': 'Graphics',
                'priority': 'Medium',
                'issue': 'High graphics operation percentage',
                'suggestion': 'Consider batching graphics operations or using sprites for repeated elements',
                'impact': 'Moderate performance improvement'
            })
        
        # Register usage suggestions
        if metrics.get('register_utilization', 0) < 0.3:
            suggestions.append({
                'category': 'Registers',
                'priority': 'Low',
                'issue': 'Low register utilization',
                'suggestion': 'Consider using more registers to reduce memory operations',
                'impact': 'Minor performance improvement'
            })
        
        # Code size suggestions
        if asm_analysis.get('instruction_count', 0) > 1000:
            suggestions.append({
                'category': 'Code Size',
                'priority': 'Medium',
                'issue': 'Large code size',
                'suggestion': 'Consider breaking into smaller functions or using loops to reduce code duplication',
                'impact': 'Better maintainability and potential performance improvement'
            })
        
        # Add specific optimization opportunities from assembly analysis
        for opp in asm_analysis.get('optimization_opportunities', []):
            suggestions.append({
                'category': 'Assembly',
                'priority': 'Low',
                'issue': opp['type'],
                'suggestion': opp['suggestion'],
                'impact': 'Minor optimization'
            })
        
        return suggestions


def print_profile_results(results: Dict[str, Any]):
    """Print profiling results in a formatted way."""
    print(f"\n=== ASTRID PERFORMANCE PROFILER ===")
    print(f"Source: {results['source_file']}")
    
    # Compilation results
    comp = results['compilation']
    if comp.get('success'):
        print(f"✅ Compilation: SUCCESS")
    else:
        print(f"❌ Compilation: FAILED")
        if 'error' in comp:
            print(f"   Error: {comp['error']}")
        return
    
    # Assembly analysis
    asm = results['assembly_analysis']
    if 'error' not in asm:
        print(f"\n📊 ASSEMBLY ANALYSIS:")
        print(f"   Instructions: {asm.get('instruction_count', 0)}")
        print(f"   Memory ops: {asm.get('memory_operations', 0)} ({asm.get('memory_percentage', 0):.1f}%)")
        print(f"   Graphics ops: {asm.get('graphics_operations', 0)} ({asm.get('graphics_percentage', 0):.1f}%)")
        print(f"   Control flow: {asm.get('control_flow_instructions', 0)} ({asm.get('control_flow_percentage', 0):.1f}%)")
        
        # Top instructions
        if 'instruction_frequency' in asm:
            top_instructions = sorted(asm['instruction_frequency'].items(), 
                                    key=lambda x: x[1], reverse=True)[:5]
            print(f"   Top instructions: {', '.join([f'{op}({count})' for op, count in top_instructions])}")
    
    # Execution profile
    exec_prof = results['execution_profile']
    if 'error' not in exec_prof:
        print(f"\n⚡ EXECUTION PROFILE:")
        print(f"   Cycles executed: {exec_prof.get('cycles_executed', 0)}")
        print(f"   Final PC: 0x{exec_prof.get('final_pc', '0000')}")
        print(f"   Graphics pixels: {exec_prof.get('graphics_pixels', 0)}")
    
    # Performance metrics
    metrics = results['performance_metrics']
    if metrics:
        print(f"\n🎯 PERFORMANCE METRICS:")
        print(f"   Performance rating: {metrics.get('performance_rating', 'Unknown')}")
        print(f"   Memory efficiency: {metrics.get('memory_efficiency', 'Unknown')}")
        if 'register_utilization' in metrics:
            print(f"   Register utilization: {metrics['register_utilization']:.1%}")
    
    # Optimization suggestions
    suggestions = results['optimization_suggestions']
    if suggestions:
        print(f"\n💡 OPTIMIZATION SUGGESTIONS:")
        for i, sugg in enumerate(suggestions, 1):
            priority_icon = "🔴" if sugg['priority'] == 'High' else "🟡" if sugg['priority'] == 'Medium' else "🟢"
            print(f"   {i}. {priority_icon} [{sugg['category']}] {sugg['issue']}")
            print(f"      → {sugg['suggestion']}")
            print(f"      Impact: {sugg['impact']}")


def main():
    parser = argparse.ArgumentParser(description="Astrid Performance Profiler")
    parser.add_argument("source", help="Astrid source file (.ast)")
    parser.add_argument("-c", "--cycles", type=int, default=10000, help="Execution cycles for profiling")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.source):
        print(f"Error: Source file '{args.source}' not found")
        sys.exit(1)
    
    profiler = AstridProfiler()
    results = profiler.profile_program(args.source, args.cycles)
    
    if args.json:
        import json
        # Make results JSON-serializable
        json_results = {}
        for key, value in results.items():
            if isinstance(value, defaultdict):
                json_results[key] = dict(value)
            else:
                json_results[key] = value
        print(json.dumps(json_results, indent=2))
    else:
        print_profile_results(results)


if __name__ == "__main__":
    main()
