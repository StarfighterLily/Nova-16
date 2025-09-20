#!/usr/bin/env python3
"""
Nova-16 CPU Profiler Tool

A comprehensive profiling tool for the Nova-16 CPU emulator that helps identify
performance bottlenecks and optimization opportunities.

Features:
- Built-in CPU profiling with detailed metrics
- cProfile integration for Python-level profiling
- Memory access pattern analysis
- Instruction set benchmarking
- JSON/CSV export for reports
- Visualization of profiling data
- Comparison between profiling runs
- GUI integration for interactive profiling

Usage:
    python nova_profiler.py <command> [options] [program.bin]

Commands:
    run         Run profiling on a program
    benchmark   Run built-in benchmarks
    compare     Compare two profiling runs
    visualize   Generate visualizations from profile data

Examples:
    python nova_profiler.py run --cpu-profile asm/gfxtest.bin
    python nova_profiler.py benchmark --export-json results.json
    python nova_profiler.py compare profile1.json profile2.json
    python nova_profiler.py visualize profile.json --output chart.png
"""

import sys
import time
import cProfile
import pstats
import io
import json
import csv
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

import nova_cpu as cpu
import nova_memory as mem
import nova_gfx as gpu
import nova_sound as sound
import nova_keyboard as kbd

class NovaProfiler:
    def __init__(self):
        self.cpu = None
        self.memory = None
        self.gfx = None
        self.keyboard = None
        self.sound = None
        self.profile_data = {}

    def setup_system(self, program_path: Optional[str] = None):
        """Initialize the Nova-16 system"""
        self.memory = mem.Memory()
        self.gfx = gpu.GFX()
        self.keyboard = kbd.NovaKeyboard()
        self.sound = sound.NovaSound()
        self.cpu = cpu.CPU(self.memory, self.gfx, self.keyboard, self.sound)

        if program_path:
            entry_point = self.memory.load(program_path)
            self.cpu.pc = entry_point
            print(f"Loaded {program_path}, entry point: 0x{entry_point:04X}")

    def run_profiling(self, max_cycles: int = 10000, enable_cpu_profile: bool = True,
                     use_cprofile: bool = False, export_json: Optional[str] = None,
                     export_csv: Optional[str] = None) -> Dict[str, Any]:
        """Run CPU profiling with various options"""
        print("Starting CPU profiling...")

        if enable_cpu_profile:
            self.cpu.enable_profiling()

        if use_cprofile:
            pr = cProfile.Profile()
            pr.enable()

        start_time = time.time()
        cycles = 0

        try:
            while not self.cpu.halted and cycles < max_cycles:
                self.cpu.step()
                cycles += 1

                if cycles % 1000 == 0:
                    print(f"Executed {cycles} cycles...")

        except KeyboardInterrupt:
            print("\nProfiling interrupted by user")

        end_time = time.time()
        total_time = end_time - start_time

        if use_cprofile:
            pr.disable()

        # Collect profiling data
        profile_results = {
            'execution_time': total_time,
            'cycles_executed': cycles,
            'cycles_per_second': cycles / total_time if total_time > 0 else 0,
            'timestamp': time.time(),
            'program': getattr(self.memory, 'loaded_program', None)
        }

        if enable_cpu_profile:
            cpu_report = self.cpu.get_profile_report()
            profile_results.update({
                'cpu_profile': self.cpu.profile_data.copy(),
                'cpu_report_text': cpu_report,
                'instructions_per_second': self.cpu.profile_data['instructions_executed'] / total_time if total_time > 0 else 0
            })

        if use_cprofile:
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
            ps.print_stats(20)
            profile_results['cprofile_report'] = s.getvalue()

        # Export results
        if export_json:
            with open(export_json, 'w') as f:
                json.dump(profile_results, f, indent=2, default=str)
            print(f"Profile data exported to {export_json}")

        if export_csv:
            self._export_csv(profile_results, export_csv)

        # Print summary
        print(f"\nExecution completed:")
        print(f"- Total cycles: {cycles}")
        print(f"- Total time: {total_time:.4f} seconds")
        print(f"- Average CPS: {cycles / total_time:.2f}")

        if enable_cpu_profile:
            print(f"- Instructions executed: {self.cpu.profile_data['instructions_executed']}")
            print(f"- Average IPS: {self.cpu.profile_data['instructions_executed'] / total_time:.2f}")
            print(f"- Memory accesses: {self.cpu.profile_data['memory_accesses']}")

        return profile_results

    def run_benchmark(self, benchmark_type: str = 'instruction_set',
                     export_json: Optional[str] = None) -> Dict[str, Any]:
        """Run built-in benchmarks"""
        if benchmark_type == 'instruction_set':
            return self._benchmark_instruction_set(export_json)
        elif benchmark_type == 'memory_access':
            return self._benchmark_memory_access(export_json)
        else:
            raise ValueError(f"Unknown benchmark type: {benchmark_type}")

    def _benchmark_instruction_set(self, export_json: Optional[str] = None) -> Dict[str, Any]:
        """Benchmark different instruction types"""
        print("Running instruction set benchmark...")

        # Test program with various instruction types
        benchmark_program = [
            0x06, 0x04, 0xE7, 0x00,  # MOV R0, 0     ; Load immediate
            0x06, 0x04, 0xE8, 0x01,  # MOV R1, 1     ; Load immediate
            0x08, 0x00, 0xE7, 0xE8,  # ADD R0, R1    ; Register arithmetic
            0x0A, 0x00, 0xE7, 0xE8,  # SUB R0, R1    ; Register arithmetic
            0x10, 0x00, 0xE7, 0xE8,  # AND R0, R1    ; Logical
            0x11, 0x00, 0xE7, 0xE8,  # OR R0, R1     ; Logical
            0x12, 0x00, 0xE7, 0xE8,  # XOR R0, R1    ; Logical
            0x06, 0x08, 0xF1, 0x00, 0x20,  # MOV [0x2000], R0  ; Memory write
            0x07, 0x08, 0xF1, 0x00, 0x20,  # MOV R0, [0x2000]  ; Memory read
            0x0E, 0x08, 0xF0, 0x00, 0x00,  # JMP 0x0000 (loop back)
        ]

        # Load benchmark program
        for i, byte in enumerate(benchmark_program):
            self.memory.write_byte(i, byte)

        self.cpu.pc = 0
        self.cpu.enable_profiling()

        start_time = time.time()
        cycles = 0
        max_cycles = 10000

        while not self.cpu.halted and cycles < max_cycles:
            self.cpu.step()
            cycles += 1

        end_time = time.time()
        total_time = end_time - start_time

        results = {
            'benchmark_type': 'instruction_set',
            'cycles': cycles,
            'time': total_time,
            'avg_time_per_instruction': total_time / self.cpu.profile_data['instructions_executed'] * 1000000,
            'instructions_per_second': self.cpu.profile_data['instructions_executed'] / total_time,
            'profile_data': self.cpu.profile_data.copy(),
            'timestamp': time.time()
        }

        if export_json:
            with open(export_json, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Benchmark results exported to {export_json}")

        print(f"Benchmark completed:")
        print(f"- Cycles: {cycles}")
        print(f"- Time: {total_time:.6f} seconds")
        print(f"- Avg time per instruction: {results['avg_time_per_instruction']:.2f} μs")
        print(f"- Instructions per second: {results['instructions_per_second']:.2f}")

        return results

    def _benchmark_memory_access(self, export_json: Optional[str] = None) -> Dict[str, Any]:
        """Benchmark memory access patterns"""
        print("Running memory access benchmark...")

        # Program that tests different memory access patterns
        memory_program = [
            # Sequential access in zero page (fast)
            0x06, 0x08, 0xF0, 0x00, 0x00,  # MOV R0, [0x0000]
            0x06, 0x08, 0xF0, 0x01, 0x00,  # MOV R0, [0x0001]
            0x06, 0x08, 0xF0, 0x02, 0x00,  # MOV R0, [0x0002]

            # Sequential access in general memory
            0x06, 0x08, 0xF0, 0x00, 0x20,  # MOV R0, [0x2000]
            0x06, 0x08, 0xF0, 0x01, 0x20,  # MOV R0, [0x2001]
            0x06, 0x08, 0xF0, 0x02, 0x20,  # MOV R0, [0x2002]

            # Random access
            0x06, 0x08, 0xF0, 0xFF, 0x2F,  # MOV R0, [0x2FFF]
            0x06, 0x08, 0xF0, 0x80, 0x15,  # MOV R0, [0x1580]
            0x06, 0x08, 0xF0, 0x00, 0xF0,  # MOV R0, [0xF000] (sprite area)

            # Stack operations
            0x1A,  # PUSH R0
            0x1B,  # POP R0

            0x0E, 0x08, 0xF0, 0x00, 0x00,  # JMP 0x0000 (loop)
        ]

        # Load test program
        for i, byte in enumerate(memory_program):
            self.memory.write_byte(i, byte)

        self.cpu.pc = 0
        self.cpu.enable_profiling()

        start_time = time.time()
        cycles = 0
        max_cycles = 5000

        while not self.cpu.halted and cycles < max_cycles:
            self.cpu.step()
            cycles += 1

        end_time = time.time()
        total_time = end_time - start_time

        results = {
            'benchmark_type': 'memory_access',
            'cycles': cycles,
            'time': total_time,
            'memory_accesses': self.cpu.profile_data['memory_accesses'],
            'accesses_per_second': self.cpu.profile_data['memory_accesses'] / total_time,
            'profile_data': self.cpu.profile_data.copy(),
            'timestamp': time.time()
        }

        if export_json:
            with open(export_json, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Benchmark results exported to {export_json}")

        print(f"Memory benchmark completed:")
        print(f"- Memory accesses: {results['memory_accesses']}")
        print(f"- Time: {total_time:.6f} seconds")
        print(f"- Accesses per second: {results['accesses_per_second']:.2f}")

        return results

    def compare_profiles(self, profile1_path: str, profile2_path: str,
                        output_path: Optional[str] = None) -> Dict[str, Any]:
        """Compare two profiling runs"""
        print(f"Comparing {profile1_path} vs {profile2_path}")

        with open(profile1_path, 'r') as f:
            profile1 = json.load(f)

        with open(profile2_path, 'r') as f:
            profile2 = json.load(f)

        comparison = {
            'profile1': profile1_path,
            'profile2': profile2_path,
            'timestamp': time.time(),
            'differences': {}
        }

        # Compare execution metrics
        metrics_to_compare = ['execution_time', 'cycles_executed', 'instructions_per_second', 'cycles_per_second']

        for metric in metrics_to_compare:
            if metric in profile1 and metric in profile2:
                val1 = profile1[metric]
                val2 = profile2[metric]
                diff = val2 - val1
                pct_change = (diff / val1 * 100) if val1 != 0 else 0

                comparison['differences'][metric] = {
                    'value1': val1,
                    'value2': val2,
                    'difference': diff,
                    'percent_change': pct_change
                }

        # Compare opcode frequencies if available
        if 'cpu_profile' in profile1 and 'cpu_profile' in profile2:
            opcodes1 = profile1['cpu_profile'].get('opcode_counts', {})
            opcodes2 = profile2['cpu_profile'].get('opcode_counts', {})

            opcode_comparison = {}
            all_opcodes = set(opcodes1.keys()) | set(opcodes2.keys())

            for opcode in all_opcodes:
                count1 = opcodes1.get(opcode, 0)
                count2 = opcodes2.get(opcode, 0)
                diff = count2 - count1
                pct_change = (diff / count1 * 100) if count1 != 0 else 0

                # Handle both string and int keys from JSON
                if isinstance(opcode, int):
                    key = f'0x{opcode:02X}'
                else:
                    key = opcode

                opcode_comparison[key] = {
                    'count1': count1,
                    'count2': count2,
                    'difference': diff,
                    'percent_change': pct_change
                }

            comparison['opcode_differences'] = opcode_comparison

        if output_path:
            with open(output_path, 'w') as f:
                json.dump(comparison, f, indent=2, default=str)
            print(f"Comparison results saved to {output_path}")

        # Print summary
        print("\nComparison Summary:")
        for metric, data in comparison['differences'].items():
            print(f"{metric}: {data['value1']:.4f} → {data['value2']:.4f} ({data['percent_change']:+.1f}%)")

        return comparison

    def _export_csv(self, profile_data: Dict[str, Any], csv_path: str):
        """Export profiling data to CSV format"""
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow(['Metric', 'Value'])

            # Write basic metrics
            writer.writerow(['Execution Time (s)', profile_data.get('execution_time', 0)])
            writer.writerow(['Cycles Executed', profile_data.get('cycles_executed', 0)])
            writer.writerow(['Cycles per Second', profile_data.get('cycles_per_second', 0)])
            writer.writerow(['Instructions per Second', profile_data.get('instructions_per_second', 0)])

            # Write opcode counts if available
            if 'cpu_profile' in profile_data and 'opcode_counts' in profile_data['cpu_profile']:
                writer.writerow([])
                writer.writerow(['Opcode', 'Count', 'Percentage'])
                total_instructions = profile_data['cpu_profile']['instructions_executed']

                for opcode, count in sorted(profile_data['cpu_profile']['opcode_counts'].items(),
                                          key=lambda x: x[1], reverse=True):
                    pct = (count / total_instructions * 100) if total_instructions > 0 else 0
                    writer.writerow([f'0x{opcode:02X}', count, f'{pct:.1f}%'])

        print(f"Profile data exported to {csv_path}")

def create_visualization(profile_path: str, output_path: str):
    """Generate visualizations from profile data"""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed. Install with: pip install matplotlib")
        return

    with open(profile_path, 'r') as f:
        data = json.load(f)

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle('Nova-16 CPU Profiling Results')

    # Execution time and throughput
    ax1.bar(['Execution Time', 'Cycles', 'Instructions'],
            [data.get('execution_time', 0),
             data.get('cycles_executed', 0) / 1000,  # Scale down
             data.get('cpu_profile', {}).get('instructions_executed', 0) / 1000])
    ax1.set_ylabel('Value (scaled)')
    ax1.set_title('Execution Metrics')

    # Instructions per second
    ax2.bar(['IPS'], [data.get('instructions_per_second', 0)])
    ax2.set_ylabel('Instructions/Second')
    ax2.set_title('Throughput')

    # Opcode frequency (top 10)
    if 'cpu_profile' in data and 'opcode_counts' in data['cpu_profile']:
        opcodes = data['cpu_profile']['opcode_counts']
        top_opcodes = sorted(opcodes.items(), key=lambda x: x[1], reverse=True)[:10]
        opcode_names = []
        for k, v in top_opcodes:
            if isinstance(k, int):
                opcode_names.append(f'0x{k:02X}')
            else:
                opcode_names.append(str(k))
        opcode_counts = [v for k, v in top_opcodes]

        ax3.bar(opcode_names, opcode_counts)
        ax3.set_ylabel('Count')
        ax3.set_title('Top 10 Opcodes')
        ax3.tick_params(axis='x', rotation=45)

    # Memory accesses
    ax4.bar(['Memory Accesses'], [data.get('cpu_profile', {}).get('memory_accesses', 0)])
    ax4.set_ylabel('Count')
    ax4.set_title('Memory Operations')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Visualization saved to {output_path}")
    plt.close()

def main():
    parser = argparse.ArgumentParser(description='Nova-16 CPU Profiler')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Run command
    run_parser = subparsers.add_parser('run', help='Run profiling on a program')
    run_parser.add_argument('program', nargs='?', help='Program file to profile')
    run_parser.add_argument('--cycles', type=int, default=10000, help='Maximum cycles to run')
    run_parser.add_argument('--cpu-profile', action='store_true', help='Enable CPU profiling')
    run_parser.add_argument('--cprofile', action='store_true', help='Use Python cProfile')
    run_parser.add_argument('--export-json', help='Export results to JSON file')
    run_parser.add_argument('--export-csv', help='Export results to CSV file')

    # Benchmark command
    bench_parser = subparsers.add_parser('benchmark', help='Run built-in benchmarks')
    bench_parser.add_argument('type', choices=['instruction_set', 'memory_access'],
                            default='instruction_set', help='Benchmark type')
    bench_parser.add_argument('--export-json', help='Export results to JSON file')

    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare two profiling runs')
    compare_parser.add_argument('profile1', help='First profile JSON file')
    compare_parser.add_argument('profile2', help='Second profile JSON file')
    compare_parser.add_argument('--output', help='Output comparison to JSON file')

    # Visualize command
    viz_parser = subparsers.add_parser('visualize', help='Generate visualizations')
    viz_parser.add_argument('profile', help='Profile JSON file')
    viz_parser.add_argument('--output', required=True, help='Output image file (PNG)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    profiler = NovaProfiler()

    if args.command == 'run':
        profiler.setup_system(args.program)
        profiler.run_profiling(
            max_cycles=args.cycles,
            enable_cpu_profile=args.cpu_profile,
            use_cprofile=args.cprofile,
            export_json=args.export_json,
            export_csv=args.export_csv
        )

    elif args.command == 'benchmark':
        profiler.setup_system()
        profiler.run_benchmark(
            benchmark_type=args.type,
            export_json=args.export_json
        )

    elif args.command == 'compare':
        profiler.compare_profiles(args.profile1, args.profile2, args.output)

    elif args.command == 'visualize':
        create_visualization(args.profile, args.output)

if __name__ == "__main__":
    main()