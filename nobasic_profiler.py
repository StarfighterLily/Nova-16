#!/usr/bin/env python3
"""
NoBASIC Profiler
Comprehensive profiling and analysis tool for NoBASIC programs.
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class NoBasicProfiler:
    """Comprehensive profiler for NoBASIC programs"""

    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.emulator = self.test_dir / "nova.py"
        self.graphics_monitor = self.test_dir / "nova_graphics_monitor.py"
        self.cpu_profiler = self.test_dir / "nova_profiler.py"
        self.memory_profiler = self.test_dir / "nova_memory_profiler.py"
        self.disassembler = self.test_dir / "nova_disassembler.py"

    def profile_program(self, bin_file: Path, cycles: int = 10000) -> Dict:
        """Run comprehensive profiling on a NoBASIC program"""
        results = {
            'program': bin_file.name,
            'timestamp': time.time(),
            'cycles_limit': cycles,
            'analyses': {}
        }

        print(f"🔬 Profiling: {bin_file.name}")

        # 1. Basic execution profiling
        print("   Running basic execution profile...")
        results['analyses']['execution'] = self._profile_execution(bin_file, cycles)

        # 2. CPU profiling
        print("   Running CPU profiling...")
        results['analyses']['cpu'] = self._profile_cpu(bin_file, cycles)

        # 3. Memory profiling
        print("   Running memory profiling...")
        results['analyses']['memory'] = self._profile_memory(bin_file, cycles)

        # 4. Graphics analysis
        print("   Running graphics analysis...")
        results['analyses']['graphics'] = self._profile_graphics(bin_file, cycles)

        # 5. Code analysis
        print("   Analyzing generated code...")
        results['analyses']['code'] = self._analyze_code(bin_file)

        return results

    def _profile_execution(self, bin_file: Path, cycles: int) -> Dict:
        """Basic execution profiling"""
        cmd = [sys.executable, str(self.emulator), "--headless", str(bin_file), "--cycles", str(cycles)]
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)
        end_time = time.time()

        analysis = {
            'success': result.returncode == 0,
            'execution_time': end_time - start_time,
            'stdout': result.stdout,
            'stderr': result.stderr
        }

        # Extract execution metrics from output
        stdout_lines = result.stdout.split('\n')
        for line in stdout_lines:
            if "Final PC:" in line:
                analysis['final_pc'] = line.split(": ")[1]
            elif "Execution finished after" in line:
                analysis['cycles_executed'] = int(line.split(" ")[3])
            elif "CPU Halted:" in line:
                analysis['cpu_halted'] = "True" in line

        return analysis

    def _profile_cpu(self, bin_file: Path, cycles: int) -> Dict:
        """CPU profiling"""
        profile_file = bin_file.with_suffix('.cpu_profile.json')
        cmd = [sys.executable, str(self.cpu_profiler), "run", str(bin_file),
               "--cpu-profile", "--cycles", str(cycles), "--export-json", str(profile_file)]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)

        analysis = {
            'success': result.returncode == 0,
            'profile_file': str(profile_file)
        }

        if result.returncode == 0 and profile_file.exists():
            try:
                with open(profile_file, 'r') as f:
                    profile_data = json.load(f)
                    analysis['data'] = profile_data
            except Exception as e:
                analysis['error'] = str(e)

        return analysis

    def _profile_memory(self, bin_file: Path, cycles: int) -> Dict:
        """Memory profiling"""
        profile_file = bin_file.with_suffix('.memory_profile.json')
        cmd = [sys.executable, str(self.memory_profiler), "run", str(bin_file),
               "--profile", str(profile_file), "--cycles", str(cycles)]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)

        analysis = {
            'success': result.returncode == 0,
            'profile_file': str(profile_file)
        }

        if result.returncode == 0 and profile_file.exists():
            try:
                with open(profile_file, 'r') as f:
                    profile_data = json.load(f)
                    analysis['data'] = profile_data
            except Exception as e:
                analysis['error'] = str(e)

        return analysis

    def _profile_graphics(self, bin_file: Path, cycles: int) -> Dict:
        """Graphics profiling"""
        export_prefix = bin_file.with_suffix('').name + "_graphics"
        cmd = [sys.executable, str(self.graphics_monitor), str(bin_file),
               "--cycles", str(cycles), "--export", export_prefix]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)

        analysis = {
            'success': result.returncode == 0,
            'export_prefix': export_prefix
        }

        # Extract graphics statistics from output
        stdout_lines = result.stdout.split('\n')
        in_final_analysis = False
        for line in stdout_lines:
            if "FINAL ANALYSIS" in line:
                in_final_analysis = True
            elif in_final_analysis:
                if "Graphics Statistics:" in line:
                    analysis['stats'] = {}
                elif "Total pixel writes:" in line:
                    analysis['stats']['pixel_writes'] = int(line.split(": ")[1])
                elif "Layers used:" in line:
                    analysis['stats']['layers_used'] = eval(line.split(": ")[1])
                elif "Colors used:" in line:
                    colors_part = line.split(": ")[1]
                    analysis['stats']['colors_used'] = len(colors_part.split()) if colors_part != "[]" else 0

        return analysis

    def _analyze_code(self, bin_file: Path) -> Dict:
        """Analyze the generated assembly code"""
        analysis = {}

        # Try to disassemble
        cmd = [sys.executable, str(self.disassembler), str(bin_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)

        if result.returncode == 0:
            disassembly = result.stdout
            lines = disassembly.split('\n')

            # Count different instruction types
            instruction_counts = {}
            total_instructions = 0

            for line in lines:
                line = line.strip()
                if line and not line.startswith(';') and not line.startswith('ORG'):
                    parts = line.split()
                    if parts:
                        mnemonic = parts[0].upper()
                        instruction_counts[mnemonic] = instruction_counts.get(mnemonic, 0) + 1
                        total_instructions += 1

            analysis['disassembly_success'] = True
            analysis['total_instructions'] = total_instructions
            analysis['instruction_counts'] = instruction_counts
            analysis['unique_instructions'] = len(instruction_counts)
        else:
            analysis['disassembly_success'] = False
            analysis['error'] = result.stderr

        return analysis

    def generate_report(self, profile_results: Dict) -> str:
        """Generate a human-readable profiling report"""
        report = []
        report.append("=" * 80)
        report.append(f"NoBASIC Program Profiling Report")
        report.append(f"Program: {profile_results['program']}")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(profile_results['timestamp']))}")
        report.append("=" * 80)

        # Execution summary
        exec_analysis = profile_results['analyses'].get('execution', {})
        if exec_analysis.get('success'):
            report.append("\nEXECUTION SUMMARY")
            report.append("-" * 40)
            report.append(f"Status: SUCCESSFUL")
            report.append(f"Execution Time: {exec_analysis.get('execution_time', 0):.4f} seconds")
            report.append(f"Cycles Executed: {exec_analysis.get('cycles_executed', 'N/A')}")
            report.append(f"Final PC: {exec_analysis.get('final_pc', 'N/A')}")
            report.append(f"CPU Halted: {exec_analysis.get('cpu_halted', 'N/A')}")
        else:
            report.append("\nEXECUTION FAILED")

        # CPU analysis
        cpu_analysis = profile_results['analyses'].get('cpu', {})
        if cpu_analysis.get('success') and 'data' in cpu_analysis:
            cpu_data = cpu_analysis['data']
            report.append("\nCPU ANALYSIS")
            report.append("-" * 40)
            report.append(f"Instructions Executed: {cpu_data.get('cpu_profile', {}).get('instructions_executed', 'N/A')}")
            report.append(f"Memory Accesses: {cpu_data.get('cpu_profile', {}).get('memory_accesses', 'N/A')}")
            report.append(".2f")
            report.append(".0f")

            # Top instructions
            opcode_counts = cpu_data.get('cpu_profile', {}).get('opcode_counts', {})
            if opcode_counts:
                report.append("\nTop Instructions:")
                sorted_opcodes = sorted(opcode_counts.items(), key=lambda x: x[1], reverse=True)
                for opcode, count in sorted_opcodes[:10]:
                    report.append(f"  {opcode}: {count}")

        # Memory analysis
        mem_analysis = profile_results['analyses'].get('memory', {})
        if mem_analysis.get('success') and 'data' in mem_analysis:
            report.append("\nMEMORY ANALYSIS")
            report.append("-" * 40)
            mem_data = mem_analysis['data']
            # Add memory-specific metrics if available

        # Graphics analysis
        gfx_analysis = profile_results['analyses'].get('graphics', {})
        if gfx_analysis.get('success'):
            report.append("\nGRAPHICS ANALYSIS")
            report.append("-" * 40)
            stats = gfx_analysis.get('stats', {})
            report.append(f"Pixel Writes: {stats.get('pixel_writes', 'N/A')}")
            report.append(f"Layers Used: {stats.get('layers_used', 'N/A')}")
            report.append(f"Colors Used: {stats.get('colors_used', 'N/A')}")

        # Code analysis
        code_analysis = profile_results['analyses'].get('code', {})
        if code_analysis.get('disassembly_success'):
            report.append("\nCODE ANALYSIS")
            report.append("-" * 40)
            report.append(f"Total Instructions: {code_analysis.get('total_instructions', 'N/A')}")
            report.append(f"Unique Instructions: {code_analysis.get('unique_instructions', 'N/A')}")

            inst_counts = code_analysis.get('instruction_counts', {})
            if inst_counts:
                report.append("\nInstruction Distribution:")
                sorted_inst = sorted(inst_counts.items(), key=lambda x: x[1], reverse=True)
                for inst, count in sorted_inst[:10]:
                    report.append(f"  {inst}: {count}")

        report.append("\n" + "=" * 80)
        return "\n".join(report)

    def save_report(self, profile_results: Dict, output_file: Path):
        """Save profiling results to JSON file"""
        with open(output_file, 'w') as f:
            json.dump(profile_results, f, indent=2)

    def save_text_report(self, profile_results: Dict, output_file: Path):
        """Save human-readable report to text file"""
        report = self.generate_report(profile_results)
        with open(output_file, 'w') as f:
            f.write(report)

    def profile_nobasic_program(self, nob_file: Path, cycles: int = 10000) -> Optional[Dict]:
        """Profile a NoBASIC program with language-specific analysis"""
        print(f"📊 Profiling NoBASIC program: {nob_file.name}")
        print("=" * 60)

        # Compile if needed
        bin_file = nob_file.with_suffix('.bin')
        if not bin_file.exists():
            print("Compiling NoBASIC program...")
            if not self._compile_nobasic(nob_file):
                print("❌ Compilation failed")
                return None

        # Run standard profiling
        profile_results = self.profile_program(bin_file, cycles)

        # Add NoBASIC-specific analysis
        print("\n📝 NoBASIC Language Analysis:")
        nobasic_analysis = self._analyze_nobasic_source(nob_file, profile_results)
        if nobasic_analysis:
            profile_results['nobasic_analysis'] = nobasic_analysis
            self._print_nobasic_analysis(nobasic_analysis)

        # Generate optimization suggestions
        print("\n💡 Optimization Suggestions:")
        suggestions = self._generate_nobasic_suggestions(profile_results)
        profile_results['optimization_suggestions'] = suggestions
        for suggestion in suggestions:
            print(f"   • {suggestion}")

        # Save NoBASIC-specific report
        nob_profile_file = nob_file.with_suffix('.nob_profile.json')
        nob_text_file = nob_file.with_suffix('.nob_profile.txt')

        self.save_report(profile_results, nob_profile_file)
        self.save_text_report(profile_results, nob_text_file)

        print(f"\n📄 NoBASIC profile saved: {nob_profile_file}")
        print(f"📄 Text report saved: {nob_text_file}")

        return profile_results

    def _compile_nobasic(self, nob_file: Path) -> bool:
        """Compile NoBASIC source to binary"""
        compiler = self.test_dir / "nobasic_compiler.py"
        cmd = [sys.executable, str(compiler), str(nob_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)
        return result.returncode == 0

    def _analyze_nobasic_source(self, nob_file: Path, profile_results: Dict) -> Optional[Dict]:
        """Analyze NoBASIC source code for language-specific metrics"""
        try:
            with open(nob_file, 'r') as f:
                source_code = f.read()

            lines = [line.strip() for line in source_code.split('\n') if line.strip()]

            analysis = {
                'total_lines': len(lines),
                'source_size': len(source_code),
                'construct_counts': self._count_nobasic_constructs(lines),
                'complexity_metrics': self._calculate_complexity_metrics(lines),
                'performance_estimates': self._estimate_performance_metrics(lines, profile_results)
            }

            return analysis

        except Exception as e:
            print(f"Error analyzing NoBASIC source: {e}")
            return None

    def _count_nobasic_constructs(self, lines: List[str]) -> Dict[str, int]:
        """Count different NoBASIC language constructs"""
        constructs = {
            'assignments': 0,
            'arithmetic_ops': 0,
            'comparisons': 0,
            'control_flow': 0,
            'loops': 0,
            'subroutines': 0,
            'graphics_ops': 0,
            'sound_ops': 0,
            'io_ops': 0,
            'comments': 0
        }

        for line in lines:
            upper_line = line.upper()

            # Comments
            if line.strip().startswith('//') or line.strip().startswith("'"):
                constructs['comments'] += 1
                continue

            # Assignments
            if '=' in line and not any(keyword in upper_line for keyword in
                ['FOR', 'IF', 'WHILE', 'DISP', 'LBL', 'LINE', 'CIRCLE', 'PLAY', 'SOUND']):
                constructs['assignments'] += 1

            # Arithmetic operations
            if any(op in line for op in ['+', '-', '*', '/']):
                constructs['arithmetic_ops'] += 1

            # Comparisons
            if any(op in line for op in ['=', '<>', '>', '<', '>=', '<=', '!=']):
                constructs['comparisons'] += 1

            # Control flow
            if any(keyword in upper_line for keyword in ['IF', 'THEN', 'ELSE', 'FOR', 'WHILE', 'GOTO', 'LBL']):
                constructs['control_flow'] += 1

            # Loops
            if 'FOR' in upper_line or 'WHILE' in upper_line:
                constructs['loops'] += 1

            # Subroutines
            if any(keyword in upper_line for keyword in ['DEFINE', 'CALL', 'RETURN']):
                constructs['subroutines'] += 1

            # Graphics operations
            if any(keyword in upper_line for keyword in
                ['LINE', 'CIRCLE', 'PTON', 'PTOFF', 'PTCHANGE', 'PXLON', 'PXLOFF', 'PXLCHANGE', 'CLRHOME']):
                constructs['graphics_ops'] += 1

            # Sound operations
            if any(keyword in upper_line for keyword in ['PLAY', 'STOP', 'SOUND']):
                constructs['sound_ops'] += 1

            # I/O operations
            if any(keyword in upper_line for keyword in ['DISP', 'INPUT', 'PROMPT', 'PAUSE']):
                constructs['io_ops'] += 1

        return constructs

    def _calculate_complexity_metrics(self, lines: List[str]) -> Dict[str, float]:
        """Calculate code complexity metrics"""
        total_lines = len(lines)
        if total_lines == 0:
            return {'cyclomatic_complexity': 0, 'nesting_depth': 0, 'halstead_volume': 0}

        # Cyclomatic complexity (simplified)
        decision_points = sum(1 for line in lines if any(keyword in line.upper()
            for keyword in ['IF', 'FOR', 'WHILE', 'GOTO']))
        cyclomatic = decision_points + 1

        # Nesting depth (simplified)
        max_nesting = 0
        current_nesting = 0
        for line in lines:
            upper_line = line.upper()
            if 'IF' in upper_line or 'FOR' in upper_line or 'WHILE' in upper_line:
                current_nesting += 1
                max_nesting = max(max_nesting, current_nesting)
            elif 'END' in upper_line or 'NEXT' in upper_line:
                current_nesting = max(0, current_nesting - 1)

        # Halstead volume (simplified)
        operators = ['+', '-', '*', '/', '=', '>', '<', '>=', '<=', '<>', '!=', 'AND', 'OR', 'NOT']
        operands = []  # Would need proper parsing for accurate count

        operator_count = sum(1 for line in lines for op in operators if op in line.upper())
        halstead_volume = operator_count  # Simplified

        return {
            'cyclomatic_complexity': cyclomatic,
            'nesting_depth': max_nesting,
            'halstead_volume': halstead_volume
        }

    def _estimate_performance_metrics(self, lines: List[str], profile_results: Dict) -> Dict[str, float]:
        """Estimate performance metrics based on source analysis"""
        total_lines = len(lines)
        if total_lines == 0:
            return {}

        # Get actual execution data
        execution_analysis = profile_results['analyses'].get('execution', {})
        cycles_executed = execution_analysis.get('cycles_executed', 10000)

        # Estimate cycles per source line
        cycles_per_line = cycles_executed / total_lines

        # Estimate based on construct types
        constructs = self._count_nobasic_constructs(lines)

        # Rough estimates for different operations
        estimated_cycles = (
            constructs['assignments'] * 10 +      # Variable assignments
            constructs['arithmetic_ops'] * 20 +   # Arithmetic operations
            constructs['comparisons'] * 15 +      # Comparisons
            constructs['control_flow'] * 25 +     # Control flow operations
            constructs['loops'] * 50 +           # Loop overhead
            constructs['graphics_ops'] * 100 +    # Graphics operations
            constructs['sound_ops'] * 50 +       # Sound operations
            constructs['io_ops'] * 200           # I/O operations
        )

        return {
            'cycles_per_source_line': cycles_per_line,
            'estimated_complexity_cycles': estimated_cycles,
            'execution_efficiency': cycles_per_line / 50.0  # Lower is better
        }

    def _print_nobasic_analysis(self, analysis: Dict):
        """Print NoBASIC-specific analysis results"""
        print(f"   Source lines: {analysis.get('total_lines', 0)}")
        print(f"   Source size: {analysis.get('source_size', 0)} characters")

        constructs = analysis.get('construct_counts', {})
        print("   Language constructs:")
        for construct, count in constructs.items():
            if count > 0:
                construct_name = construct.replace('_', ' ').title()
                percentage = (count / analysis.get('total_lines', 1)) * 100
                print(f"     - {construct_name}: {count} ({percentage:.1f}%)")

        complexity = analysis.get('complexity_metrics', {})
        if complexity:
            print("   Complexity metrics:")
            print(f"     Cyclomatic complexity: {complexity.get('cyclomatic_complexity', 0)}")
            print(f"     Maximum nesting depth: {complexity.get('nesting_depth', 0)}")
            print(f"     Halstead volume: {complexity.get('halstead_volume', 0)}")

        performance = analysis.get('performance_estimates', {})
        if performance:
            print("   Performance estimates:")
            print(f"     Cycles per source line: {performance.get('cycles_per_source_line', 0):.1f}")
            print(f"     Estimated complexity cycles: {performance.get('estimated_complexity_cycles', 0):.1f}")
            efficiency = performance.get('execution_efficiency', 1.0)
            status = ""
            if efficiency < 0.8:
                status = "Good"
            elif efficiency < 1.5:
                status = "Average"
            else:
                status = "Needs optimization"
            print(f"     Execution efficiency: {efficiency:.2f} ({status})")

    def _generate_nobasic_suggestions(self, profile_results: Dict) -> List[str]:
        """Generate optimization suggestions for NoBASIC code"""
        suggestions = []

        nobasic_analysis = profile_results.get('nobasic_analysis', {})
        constructs = nobasic_analysis.get('construct_counts', {})
        complexity = nobasic_analysis.get('complexity_metrics', {})
        performance = nobasic_analysis.get('performance_estimates', {})

        # Complexity-based suggestions
        if complexity.get('cyclomatic_complexity', 0) > 10:
            suggestions.append("High cyclomatic complexity - consider breaking down complex functions")

        if complexity.get('nesting_depth', 0) > 3:
            suggestions.append("Deep nesting detected - consider flattening control structures")

        # Performance-based suggestions
        if performance.get('execution_efficiency', 1.0) > 2.0:
            suggestions.append("Low execution efficiency - review algorithm complexity")

        # Construct-based suggestions
        if constructs.get('loops', 0) > 5:
            suggestions.append("Multiple loops detected - review loop efficiency and consider loop unrolling")

        if constructs.get('arithmetic_ops', 0) > constructs.get('assignments', 0) * 3:
            suggestions.append("High arithmetic intensity - consider optimizing mathematical expressions")

        if constructs.get('graphics_ops', 0) > 20:
            suggestions.append("Many graphics operations - consider batching draw calls or using sprites")

        if constructs.get('control_flow', 0) > constructs.get('assignments', 0) * 2:
            suggestions.append("High control flow complexity - consider simplifying conditional logic")

        # Check for inefficient patterns
        execution_analysis = profile_results['analyses'].get('execution', {})
        if not execution_analysis.get('success', False):
            suggestions.append("Program execution failed - check for runtime errors")

        if not suggestions:
            suggestions.append("No major optimization opportunities identified - program is well-optimized")

        return suggestions

def main():
    import argparse

    parser = argparse.ArgumentParser(description="NoBASIC Profiler")
    parser.add_argument("program", help="NoBASIC program file (.nob) or binary (.bin)")
    parser.add_argument("--cycles", "-c", type=int, default=10000,
                       help="Number of cycles to profile (default: 10000)")

    args = parser.parse_args()

    program_file = Path(args.program)
    if not program_file.exists():
        print(f"Error: File {program_file} not found")
        sys.exit(1)

    profiler = NoBasicProfiler()

    if program_file.suffix == '.nob':
        # Profile NoBASIC source
        results = profiler.profile_nobasic_program(program_file, args.cycles)
    else:
        # Profile binary (legacy mode)
        results = profiler.profile_program(program_file, args.cycles)

        # Save results
        json_file = program_file.with_suffix('.nob_profile.json')
        text_file = program_file.with_suffix('.nob_profile.txt')

        profiler.save_report(results, json_file)
        profiler.save_text_report(results, text_file)

        print(f"\n📄 Reports saved:")
        print(f"   JSON: {json_file}")
        print(f"   Text: {text_file}")

    # Print summary to console
    if 'results' in locals():
        print("\n" + profiler.generate_report(results))


if __name__ == "__main__":
    main()