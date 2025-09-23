#!/usr/bin/env python3
"""
NoBASIC Debugger
Specialized debugging tools for NoBASIC programs on Nova-16.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional

class NoBasicDebugger:
    """Debugging tools for NoBASIC programs"""

    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.disassembler = self.test_dir / "nova_disassembler.py"
        self.memory_profiler = self.test_dir / "nova_memory_profiler.py"
        self.cpu_profiler = self.test_dir / "nova_profiler.py"

    def disassemble_program(self, bin_file: Path) -> Optional[str]:
        """Disassemble a binary program back to assembly"""
        cmd = [sys.executable, str(self.disassembler), str(bin_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)
        if result.returncode == 0:
            return result.stdout
        return None

    def analyze_memory_usage(self, bin_file: Path) -> Optional[Dict]:
        """Analyze memory usage patterns"""
        # Run program and capture memory profile
        profile_file = bin_file.with_suffix('.memory_profile.json')
        cmd = [sys.executable, str(self.memory_profiler), "run", str(bin_file),
               "--profile", str(profile_file), "--cycles", "10000"]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)

        if result.returncode == 0 and profile_file.exists():
            with open(profile_file, 'r') as f:
                return json.load(f)
        return None

    def analyze_performance(self, bin_file: Path) -> Optional[Dict]:
        """Analyze program performance"""
        profile_file = bin_file.with_suffix('.cpu_profile.json')
        cmd = [sys.executable, str(self.cpu_profiler), "run", str(bin_file),
               "--cpu-profile", "--cycles", "10000", "--export-json", str(profile_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)

        if result.returncode == 0 and profile_file.exists():
            with open(profile_file, 'r') as f:
                return json.load(f)
        return None

    def debug_nobasic_program(self, nob_file: Path):
        """Comprehensive debugging of a NoBASIC program"""
        print(f"🔍 Debugging NoBASIC program: {nob_file.name}")
        print("=" * 60)

        # Check if compiled files exist
        asm_file = nob_file.with_suffix('.asm')
        bin_file = nob_file.with_suffix('.bin')
        org_file = nob_file.with_suffix('.org')

        if not bin_file.exists():
            print("❌ Binary file not found. Please compile the program first.")
            return

        # 1. Disassemble and analyze the generated code
        print("\n1. 📋 Code Analysis:")
        disassembly = self.disassemble_program(bin_file)
        if disassembly:
            print("✅ Disassembly successful")
            # Count instructions
            lines = disassembly.split('\n')
            code_lines = [line for line in lines if line.strip() and not line.startswith(';')]
            print(f"   Instructions: {len(code_lines)}")
        else:
            print("❌ Disassembly failed")

        # 2. Memory usage analysis
        print("\n2. 🧠 Memory Analysis:")
        memory_profile = self.analyze_memory_usage(bin_file)
        if memory_profile:
            print("✅ Memory profiling successful")
            # Analyze memory regions
            if 'memory_regions' in memory_profile:
                regions = memory_profile['memory_regions']
                print(f"   Memory regions accessed: {len(regions)}")
                for region, accesses in regions.items():
                    print(f"   {region}: {accesses} accesses")
        else:
            print("❌ Memory profiling failed")

        # 3. Performance analysis
        print("\n3. ⚡ Performance Analysis:")
        perf_profile = self.analyze_performance(bin_file)
        if perf_profile:
            print("✅ Performance profiling successful")
            cycles = perf_profile.get('cycles_executed', 0)
            time = perf_profile.get('execution_time', 0)
            ips = perf_profile.get('instructions_per_second', 0)
            print(f"   Cycles executed: {cycles}")
            print(".2f")
            print(".0f")

            # Instruction frequency analysis
            if 'cpu_profile' in perf_profile:
                opcode_counts = perf_profile['cpu_profile'].get('opcode_counts', {})
                if opcode_counts:
                    print("   Top instructions:")
                    sorted_opcodes = sorted(opcode_counts.items(), key=lambda x: x[1], reverse=True)
                    for opcode, count in sorted_opcodes[:5]:
                        print(f"     {opcode}: {count} times")
        else:
            print("❌ Performance profiling failed")

        # 4. NoBASIC specific analysis
        print("\n4. 📊 NoBASIC Analysis:")
        try:
            with open(nob_file, 'r') as f:
                nobasic_code = f.read()

            lines = [line.strip() for line in nobasic_code.split('\n') if line.strip()]
            print(f"   NoBASIC lines: {len(lines)}")

            # Analyze statement types
            statements = {
                'ClrHome': 0,
                'Disp': 0,
                'For': 0,
                'If': 0,
                'Input': 0,
                'Prompt': 0,
                'Pause': 0,
                'assignments': 0
            }

            for line in lines:
                upper_line = line.upper()
                if 'CLRHOME' in upper_line:
                    statements['ClrHome'] += 1
                elif upper_line.startswith('DISP'):
                    statements['Disp'] += 1
                elif upper_line.startswith('FOR'):
                    statements['For'] += 1
                elif upper_line.startswith('IF'):
                    statements['If'] += 1
                elif upper_line.startswith('INPUT'):
                    statements['Input'] += 1
                elif upper_line.startswith('PROMPT'):
                    statements['Prompt'] += 1
                elif upper_line.startswith('PAUSE'):
                    statements['Pause'] += 1
                elif '=' in line and not any(keyword in upper_line for keyword in ['FOR', 'IF', 'DISP']):
                    statements['assignments'] += 1

            print("   Statement breakdown:")
            for stmt, count in statements.items():
                if count > 0:
                    print(f"     {stmt}: {count}")

        except Exception as e:
            print(f"❌ NoBASIC analysis failed: {e}")

        print("\n" + "=" * 60)
        print("🔍 Debugging complete")


def main():
    if len(sys.argv) != 2:
        print("Usage: python nobasic_debugger.py <program.nob>")
        sys.exit(1)

    nob_file = Path(sys.argv[1])
    if not nob_file.exists():
        print(f"Error: File {nob_file} not found")
        sys.exit(1)

    debugger = NoBasicDebugger()
    debugger.debug_nobasic_program(nob_file)


if __name__ == "__main__":
    main()