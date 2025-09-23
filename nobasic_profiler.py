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


def main():
    if len(sys.argv) != 2:
        print("Usage: python nobasic_profiler.py <program.bin>")
        print("This will profile the specified NoBASIC binary program")
        sys.exit(1)

    bin_file = Path(sys.argv[1])
    if not bin_file.exists():
        print(f"Error: File {bin_file} not found")
        sys.exit(1)

    profiler = NoBasicProfiler()
    results = profiler.profile_program(bin_file)

    # Save results
    json_file = bin_file.with_suffix('.nob_profile.json')
    text_file = bin_file.with_suffix('.nob_profile.txt')

    profiler.save_report(results, json_file)
    profiler.save_text_report(results, text_file)

    print(f"\n📄 Reports saved:")
    print(f"   JSON: {json_file}")
    print(f"   Text: {text_file}")

    # Print summary to console
    print("\n" + profiler.generate_report(results))


if __name__ == "__main__":
    main()