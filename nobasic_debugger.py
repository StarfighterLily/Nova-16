#!/usr/bin/env python3
"""
NoBASIC Debugger
Specialized debugging tools for NoBASIC programs on Nova-16.
"""

import os
import sys
import subprocess
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Set
import nova_cpu as cpu
import nova_memory as ram
import nova_gfx as gpu
import nova_sound as sound
import nova_keyboard as keyboard

class NoBasicInteractiveDebugger:
    """Interactive source-level debugger for NoBASIC programs"""

    def __init__(self, nob_file: Path):
        self.nob_file = nob_file
        self.bin_file = nob_file.with_suffix('.bin')
        self.asm_file = nob_file.with_suffix('.asm')

        # Source mapping
        self.source_lines: List[str] = []
        self.address_to_line: Dict[int, int] = {}
        self.line_to_addresses: Dict[int, List[int]] = {}
        self.line_breakpoints: Set[int] = set()  # NoBASIC line numbers
        self.address_breakpoints: Set[int] = set()  # Assembly addresses

        # Variable tracking
        self.variable_addresses: Dict[str, int] = {}  # Variable name -> memory address
        self.variable_types: Dict[str, str] = {}  # Variable name -> type (real, list, string)

        # Nova-16 components
        self.memory = ram.Memory()
        self.gpu = gpu.GFX()
        self.snd = sound.NovaSound()
        self.kbd = keyboard.NovaKeyboard()
        self.cpu = cpu.CPU(self.memory, self.gpu, self.kbd, self.snd)

        # Interactive state
        self.running = True
        self.current_nobasic_line = 0

    def load_program(self) -> bool:
        """Load the NoBASIC program into the emulator"""
        try:
            if not self.bin_file.exists():
                print(f"Binary file {self.bin_file} not found. Compiling...")
                if not self.compile_program():
                    return False

            entry_point = self.memory.load(str(self.bin_file))
            self.cpu.pc = entry_point
            print(f"Program loaded at 0x{entry_point:04X}")
            return True
        except Exception as e:
            print(f"Error loading program: {e}")
            return False

    def compile_program(self) -> bool:
        """Compile NoBASIC to binary"""
        cmd = [sys.executable, "nobasic_compiler.py", str(self.nob_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent)
        if result.returncode != 0:
            print(f"Compilation failed: {result.stderr}")
            return False
        return self.bin_file.exists()

    def build_source_mapping(self) -> bool:
        """Build mapping between NoBASIC source and assembly addresses"""
        try:
            # Read NoBASIC source
            with open(self.nob_file, 'r') as f:
                self.source_lines = [line.rstrip() for line in f.readlines()]

            # Parse assembly file for mapping
            if not self.asm_file.exists():
                if not self.compile_program():
                    return False

            current_line = 0
            current_address = 0x1000  # Program start address

            with open(self.asm_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith(';'):
                        # Check for NoBASIC source comments
                        if line.startswith('; ') and not line.startswith('; NoBASIC') and not line.startswith('; Generated'):
                            nobasic_stmt = line[2:].strip()
                            # Find matching source line
                            for i, source_line in enumerate(self.source_lines):
                                if source_line.strip() == nobasic_stmt:
                                    current_line = i
                                    break
                        continue

                    # Track addresses for instructions
                    if ':' in line and not line.startswith('ORG'):
                        # Label
                        label_name = line[:-1]
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

            # Build variable mapping from assembly
            self.build_variable_mapping()

            return True

        except Exception as e:
            print(f"Error building source mapping: {e}")
            return False

    def build_variable_mapping(self):
        """Build mapping of NoBASIC variables to memory addresses"""
        # Parse assembly for variable allocations
        # Variables are typically stored in memory with labels
        try:
            with open(self.asm_file, 'r') as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                line = line.strip()
                if line.startswith('VAR_') and line.endswith(':'):
                    var_name = line[4:-1]  # Remove VAR_ prefix and :
                    # Look for the next DW instruction for the address
                    for j in range(i+1, len(lines)):
                        next_line = lines[j].strip()
                        if next_line.startswith('DW'):
                            # This is approximate - we'd need better parsing
                            # For now, assume variables start at 0x2000 and increment
                            if not self.variable_addresses:
                                base_addr = 0x2000
                            else:
                                base_addr = max(self.variable_addresses.values()) + 2
                            self.variable_addresses[var_name] = base_addr
                            self.variable_types[var_name] = 'real'  # Default type
                            break
        except Exception as e:
            print(f"Warning: Could not build variable mapping: {e}")

    def get_current_nobasic_line(self) -> Optional[int]:
        """Get current NoBASIC source line from PC"""
        pc = self.cpu.pc
        # Find closest address <= pc
        valid_addresses = [addr for addr in self.address_to_line.keys() if addr <= pc]
        if valid_addresses:
            closest_addr = max(valid_addresses)
            return self.address_to_line[closest_addr]
        return None

    def get_nobasic_source_line(self, line_num: int) -> str:
        """Get NoBASIC source line"""
        if 0 <= line_num < len(self.source_lines):
            return self.source_lines[line_num]
        return ""

    def set_line_breakpoint(self, line_num: int):
        """Set breakpoint at NoBASIC source line"""
        if line_num in self.line_to_addresses:
            addresses = self.line_to_addresses[line_num]
            if addresses:
                addr = addresses[0]  # Use first address for the line
                self.address_breakpoints.add(addr)
                self.line_breakpoints.add(line_num)
                print(f"Breakpoint set at line {line_num+1}: {self.get_nobasic_source_line(line_num)}")

    def clear_line_breakpoint(self, line_num: int):
        """Clear breakpoint at NoBASIC source line"""
        if line_num in self.line_to_addresses:
            addresses = self.line_to_addresses[line_num]
            for addr in addresses:
                self.address_breakpoints.discard(addr)
            self.line_breakpoints.discard(line_num)
            print(f"Breakpoint cleared at line {line_num+1}")

    def print_source_context(self, center_line: int, context_lines: int = 3):
        """Print source code around current line"""
        start = max(0, center_line - context_lines)
        end = min(len(self.source_lines), center_line + context_lines + 1)

        print("\nNoBASIC Source:")
        for i in range(start, end):
            marker = "->" if i == center_line else "  "
            bp_marker = "●" if i in self.line_breakpoints else " "
            print(f"{bp_marker}{marker} {i+1:2d}: {self.source_lines[i]}")

    def print_variables(self):
        """Print current variable values"""
        print("\nNoBASIC Variables:")
        if not self.variable_addresses:
            print("  No variables found or mapped")
            return

        for var_name, addr in self.variable_addresses.items():
            try:
                if addr < len(self.memory.memory):
                    # Read 2 bytes as 16-bit value
                    value = (self.memory.memory[addr] << 8) | self.memory.memory[addr + 1]
                    var_type = self.variable_types.get(var_name, 'unknown')
                    print(f"  {var_name} ({var_type}): 0x{value:04X} ({value})")
                else:
                    print(f"  {var_name}: <invalid address>")
            except Exception as e:
                print(f"  {var_name}: <error reading: {e}>")

    def step_instruction(self):
        """Step one assembly instruction"""
        try:
            self.cpu.step()
            current_line = self.get_current_nobasic_line()
            if current_line is not None and current_line != self.current_nobasic_line:
                self.current_nobasic_line = current_line
                self.print_source_context(current_line, 2)
            else:
                # Print current assembly instruction
                pc = self.cpu.pc
                if pc < len(self.memory.memory) - 1:
                    opcode = self.memory.memory[pc]
                    operand = self.memory.memory[pc + 1]
                    print(f"PC=0x{pc:04X}: {opcode:02X} {operand:02X}")
        except Exception as e:
            print(f"Error during step: {e}")

    def run_until_breakpoint(self):
        """Run until breakpoint or end"""
        print("Running until breakpoint...")
        max_steps = 10000  # Safety limit
        steps = 0

        while steps < max_steps:
            if self.cpu.pc in self.address_breakpoints:
                print(f"Breakpoint hit at PC=0x{self.cpu.pc:04X}")
                current_line = self.get_current_nobasic_line()
                if current_line is not None:
                    self.print_source_context(current_line, 2)
                break

            try:
                self.cpu.step()
                steps += 1
            except Exception as e:
                print(f"Execution error: {e}")
                break

        if steps >= max_steps:
            print("Execution stopped after maximum steps")

    def interactive_session(self):
        """Start interactive debugging session"""
        print(f"🔍 NoBASIC Interactive Debugger")
        print(f"Program: {self.nob_file.name}")
        print("=" * 60)

        if not self.load_program():
            return

        if not self.build_source_mapping():
            print("Warning: Could not build source mapping")

        # Show initial source context
        self.print_source_context(0, 5)

        print("\nCommands:")
        print("  s, step          - Step one instruction")
        print("  n, next          - Step to next NoBASIC line")
        print("  r, run           - Run until breakpoint")
        print("  b <line>         - Set breakpoint at line")
        print("  cb <line>        - Clear breakpoint at line")
        print("  bl               - List breakpoints")
        print("  v, vars          - Show variables")
        print("  src              - Show source code")
        print("  regs             - Show registers")
        print("  q, quit          - Exit debugger")
        print("  h, help          - Show this help")

        while self.running:
            try:
                cmd = input("(nobasic-debug) ").strip()
                self.handle_command(cmd)
            except (EOFError, KeyboardInterrupt):
                print("\nExiting debugger.")
                break

    def handle_command(self, cmd):
        """Handle debugger commands"""
        if not cmd:
            return

        parts = cmd.split()
        command = parts[0].lower()

        if command in ('q', 'quit', 'exit'):
            self.running = False
        elif command in ('s', 'step'):
            self.step_instruction()
        elif command in ('n', 'next'):
            # Step to next NoBASIC line
            current_line = self.get_current_nobasic_line()
            if current_line is not None:
                target_addresses = set()
                for line_num in range(current_line + 1, len(self.source_lines)):
                    if line_num in self.line_to_addresses:
                        target_addresses.update(self.line_to_addresses[line_num])

                if target_addresses:
                    print(f"Stepping to next line...")
                    steps = 0
                    while steps < 1000:  # Safety limit
                        if self.cpu.pc in target_addresses:
                            break
                        self.step_instruction()
                        steps += 1
                    current_line = self.get_current_nobasic_line()
                    if current_line is not None:
                        self.print_source_context(current_line, 2)
                else:
                    print("No more lines to step to")
        elif command in ('r', 'run'):
            self.run_until_breakpoint()
        elif command == 'b' and len(parts) == 2:
            try:
                line_num = int(parts[1]) - 1  # Convert to 0-based
                self.set_line_breakpoint(line_num)
            except ValueError:
                print("Invalid line number")
        elif command == 'cb' and len(parts) == 2:
            try:
                line_num = int(parts[1]) - 1  # Convert to 0-based
                self.clear_line_breakpoint(line_num)
            except ValueError:
                print("Invalid line number")
        elif command == 'bl':
            if self.line_breakpoints:
                print("Breakpoints:")
                for line_num in sorted(self.line_breakpoints):
                    print(f"  Line {line_num+1}: {self.get_nobasic_source_line(line_num)}")
            else:
                print("No breakpoints set")
        elif command in ('v', 'vars'):
            self.print_variables()
        elif command == 'src':
            self.print_source_context(self.current_nobasic_line, 10)
        elif command == 'regs':
            self.print_registers()
        elif command in ('h', 'help', '?'):
            self.print_help()
        else:
            print("Unknown command. Type 'help' for commands.")

    def print_registers(self):
        """Print CPU registers"""
        print("PC: 0x{:04X}".format(self.cpu.pc))
        print("R0-R9:", ' '.join("02X" for i, val in enumerate(self.cpu.Rregisters[:10])))
        print("P0-P9:", ' '.join("04X" for i, val in enumerate(self.cpu.Pregisters[:10])))
        print("VM: 0x{:04X} VX: 0x{:04X} VY: 0x{:04X} VL: 0x{:04X}".format(
            self.gpu.Vregisters[2], self.gpu.Vregisters[0], self.gpu.Vregisters[1], self.gpu.VL))
        print("SA: 0x{:04X} SF: 0x{:04X} SV: 0x{:04X} SW: 0x{:04X}".format(
            self.snd.SA, self.snd.SF, self.snd.SV, self.snd.SW))

    def print_help(self):
        """Print help information"""
        print("\nNoBASIC Debugger Commands:")
        print("  s, step          - Step one assembly instruction")
        print("  n, next          - Step to next NoBASIC source line")
        print("  r, run           - Run until breakpoint")
        print("  b <line>         - Set breakpoint at source line")
        print("  cb <line>        - Clear breakpoint at source line")
        print("  bl               - List all breakpoints")
        print("  v, vars          - Show NoBASIC variables")
        print("  src              - Show source code around current line")
        print("  regs             - Show CPU registers")
        print("  q, quit          - Exit debugger")
        print("  h, help          - Show this help")


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
    parser = argparse.ArgumentParser(description="NoBASIC Debugger")
    parser.add_argument("program", help="NoBASIC program file (.nob)")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Start interactive debugging session")
    parser.add_argument("--analyze", "-a", action="store_true",
                       help="Run static analysis only")

    args = parser.parse_args()

    nob_file = Path(args.program)
    if not nob_file.exists():
        print(f"Error: File {nob_file} not found")
        sys.exit(1)

    if args.interactive:
        # Start interactive debugging session
        debugger = NoBasicInteractiveDebugger(nob_file)
        debugger.interactive_session()
    else:
        # Run static analysis
        debugger = NoBasicDebugger()
        debugger.debug_nobasic_program(nob_file)


if __name__ == "__main__":
    main()