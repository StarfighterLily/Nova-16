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
        self.compiler = self.test_dir / "nobasic_compiler.py"
        
        # Source mapping data
        self.source_lines: List[str] = []
        self.address_to_line: Dict[int, int] = {}  # Assembly address -> NoBASIC line number
        self.line_to_addresses: Dict[int, List[int]] = {}  # NoBASIC line -> list of assembly addresses

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
            print(f"   Execution time: {time:.2f} seconds")
            print(f"   Instructions/second: {ips:.0f}")

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
                'End': 0,
                'Goto': 0,
                'Lbl': 0,
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
                elif upper_line.startswith('END'):
                    statements['End'] += 1
                elif upper_line.startswith('GOTO'):
                    statements['Goto'] += 1
                elif 'LBL' in upper_line:
                    statements['Lbl'] += 1
                elif '=' in line and not any(keyword in upper_line for keyword in ['FOR', 'IF', 'DISP']):
                    statements['assignments'] += 1

            print("   Statement breakdown:")
            for stmt, count in statements.items():
                if count > 0:
                    print(f"     {stmt}: {count}")

        except Exception as e:
            print(f"❌ NoBASIC analysis failed: {e}")

        # 5. Source-level debugging
        print("\n5. 📝 Source-Level Analysis:")
        self.debug_source_level(nob_file)

        print("\n" + "=" * 60)
        print("🔍 Debugging complete")

    def build_source_mapping(self, nob_file: Path) -> bool:
        """Build mapping between NoBASIC source lines and assembly addresses"""
        try:
            # Read NoBASIC source
            with open(nob_file, 'r') as f:
                self.source_lines = [line.rstrip() for line in f.readlines()]
            
            # Compile to assembly to get the mapping
            asm_file = nob_file.with_suffix('.asm')
            cmd = [sys.executable, str(self.compiler), str(nob_file), str(asm_file)]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)
            
            if result.returncode != 0:
                print(f"Failed to compile {nob_file}: {result.stderr}")
                return False
            
            # Parse assembly to build address mapping
            current_line = 0
            current_address = 0x1000  # Program start address
            
            with open(asm_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith(';'):
                        continue
                    
                    # Check for NoBASIC source comments
                    if line.startswith('; ') and not line.startswith('; NoBASIC') and not line.startswith('; Generated'):
                        # Extract the NoBASIC statement
                        nobasic_stmt = line[2:].strip()
                        # Find which source line this corresponds to
                        for i, source_line in enumerate(self.source_lines):
                            if source_line.strip() == nobasic_stmt:
                                current_line = i
                                break
                    
                    # Track addresses for each instruction
                    if ':' in line and not line.startswith('ORG'):
                        # Label
                        label_name = line[:-1]  # Remove colon
                        self.address_to_line[current_address] = current_line
                        if current_line not in self.line_to_addresses:
                            self.line_to_addresses[current_line] = []
                        self.line_to_addresses[current_line].append(current_address)
                    elif not line.startswith('ORG') and not line.startswith('DW') and not line.startswith('DB'):
                        # Instruction - estimate 2 bytes per instruction
                        self.address_to_line[current_address] = current_line
                        if current_line not in self.line_to_addresses:
                            self.line_to_addresses[current_line] = []
                        self.line_to_addresses[current_line].append(current_address)
                        current_address += 2
            
            return True
            
        except Exception as e:
            print(f"Error building source mapping: {e}")
            return False

    def get_current_nobasic_line(self, pc: int) -> Optional[int]:
        """Get the NoBASIC source line number for a given PC address"""
        # Find the closest address <= pc
        closest_addr = max((addr for addr in self.address_to_line.keys() if addr <= pc), default=None)
        if closest_addr is not None:
            return self.address_to_line[closest_addr]
        return None

    def get_nobasic_source_line(self, line_num: int) -> str:
        """Get the NoBASIC source line for a given line number"""
        if 0 <= line_num < len(self.source_lines):
            return self.source_lines[line_num]
        return ""

    def debug_source_level(self, nob_file: Path):
        """Interactive source-level debugging"""
        print(f"🔍 Source-Level NoBASIC Debugger")
        print(f"Program: {nob_file.name}")
        print("=" * 60)
        
        if not self.build_source_mapping(nob_file):
            print("Failed to build source mapping")
            return
        
        # Show source
        print("NoBASIC Source:")
        for i, line in enumerate(self.source_lines):
            marker = "->" if i == 0 else "  "
            print(f"{marker} {i+1:2d}: {line}")
        
        print("\nSource mapping built successfully!")
        print(f"Lines mapped: {len(self.line_to_addresses)}")
        print(f"Addresses mapped: {len(self.address_to_line)}")
        
        # Could extend this to interactive debugging with breakpoints, etc.

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