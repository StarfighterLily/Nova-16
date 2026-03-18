#!/usr/bin/env python3
"""
NoBASIC Debugger
Interactive debugger for NoBASIC programs.
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, Set, List

# Add the compiler directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'compiler'))

from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.analyzer import SemanticAnalyzer
from compiler.codegen.generator import CodeGenerator
from compiler.utils.error import CompilerError
from compiler.parser.ast import DataType
from compiler.parser.ast import VariableExpr, LiteralExpr
from nobasic_compiler import resolve_source_file_path, run_frontend_pipeline

# Add Nova-16 emulator imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import nova_cpu as cpu
import nova_memory as ram
import nova_gfx as gpu
import nova_sound as sound
import nova_keyboard as keyboard
import nova_assembler


class NoBASICDebugger:
    """Interactive debugger for NoBASIC programs."""

    def __init__(self, source_file: str):
        self.source_file = str(resolve_source_file_path(source_file))
        self.source_lines = self._read_source()
        self.lexer = Lexer()
        self.parser = Parser()
        self.analyzer = SemanticAnalyzer()
        self.generator = CodeGenerator()

        # Parsed data
        self.tokens: list = []
        self.ast = None
        self.symbols: Dict[str, Any] = {}

        # Current state
        self.current_line = 0
        self.current_token = 0
        # Breakpoints with conditions
        self.breakpoints: Dict[int, Optional[str]] = {}
        self.watch_variables: Set[str] = set()
        self.call_stack: List[Dict[str, Any]] = []

        # Execution state (when connected to emulator)
        self.emulator_connected = False
        self.emulator_state = None
        
        # Nova-16 emulator components
        self.proc = None
        self.mem = None
        self.gfx = None
        self.kbd = None
        self.snd = None
        
        # Debug mappings
        self.variable_addresses: Dict[str, int] = {}
        self.line_to_address: Dict[int, int] = {}  # Map NoBASIC line numbers to assembly addresses
        self.address_to_line: Dict[int, int] = {}  # Map assembly addresses back to NoBASIC lines
        
        # Breakpoints with conditions
        self.breakpoints: Dict[int, Optional[str]] = {}  # line -> condition (None for unconditional)
        
        # Execution control
        self.is_running = False
        self.step_mode = False
        self.break_on_next = False

    def _read_source(self) -> list:
        """Read source file into lines."""
        with open(self.source_file, 'r') as f:
            return f.readlines()

    def _symbol_type_name(self, symbol_info: Any) -> str:
        """Return a user-facing symbol type string for analyzer/debug output."""
        if isinstance(symbol_info, dict):
            symbol_info = symbol_info.get('type')
        if isinstance(symbol_info, DataType):
            return symbol_info.value.upper()
        if symbol_info is None:
            return 'unknown'
        return str(symbol_info)

    def parse_program(self):
        """Parse the NoBASIC program."""
        try:
            pipeline = run_frontend_pipeline(
                self.source_file,
                lexer_factory=Lexer,
                parser_factory=Parser,
                analyzer_factory=SemanticAnalyzer,
            )

            print(f"Parsing {self.source_file}...")

            self.tokens = pipeline.tokens
            print(f"Lexical analysis complete: {len(self.tokens)} tokens")

            self.ast = pipeline.ast
            print("Parsing complete")

            self.analyzer = pipeline.analyzer
            self.symbols = self.analyzer.symbol_table.variables.copy()
            print("Semantic analysis complete")

        except CompilerError as e:
            print(f"Error: {e}")
            return False
        return True

    def show_source(self, start_line: int = 1, end_line: Optional[int] = None):
        """Display source code lines."""
        if end_line is None:
            end_line = len(self.source_lines)

        for i in range(start_line - 1, min(end_line, len(self.source_lines))):
            marker = "->" if i + 1 == self.current_line else "  "
            print(f"{marker} {i+1:3}: {self.source_lines[i].rstrip()}")

    def show_tokens(self, start: int = 0, count: int = 10):
        """Display tokens."""
        end = min(start + count, len(self.tokens))
        for i in range(start, end):
            token = self.tokens[i]
            marker = "->" if i == self.current_token else "  "
            print(f"{marker} {i:3}: {token}")

    def show_ast(self, node=None, indent=0):
        """Display AST structure."""
        if node is None:
            node = self.ast

        if node is None:
            print("No AST available. Run 'parse' first.")
            return

        prefix = "  " * indent
        node_type = type(node).__name__

        if hasattr(node, 'statements') and node.statements:
            print(f"{prefix}{node_type}: {len(node.statements)} statements")
            for stmt in node.statements:
                self.show_ast(stmt, indent + 1)
        elif hasattr(node, 'name'):
            print(f"{prefix}{node_type}: {node.name}")
        elif hasattr(node, 'variable'):
            print(f"{prefix}{node_type}: {node.variable}")
        elif hasattr(node, 'value'):
            print(f"{prefix}{node_type}: {node.value}")
        else:
            print(f"{prefix}{node_type}")

    def show_symbols(self):
        """Display symbol table."""
        if not self.symbols:
            print("No symbols available. Run 'parse' first.")
            return

        print("Symbol Table:")
        print("-" * 40)
        for name, info in self.symbols.items():
            var_type = self._symbol_type_name(info)
            print(f"{name}: {var_type}")

    def generate_code(self) -> str:
        """Generate assembly code."""
        if self.ast is None:
            print("No AST available. Run 'parse' first.")
            return ""

        return self.generator.generate(self.ast)

    def show_assembly(self):
        """Display generated assembly."""
        code = self.generate_code()
        if code:
            print("Generated Assembly:")
            print("-" * 40)
            print(code)

    def initialize_emulator(self):
        """Initialize the Nova-16 emulator components."""
        if self.emulator_connected:
            return True
            
        try:
            self.mem = ram.Memory()
            self.gfx = gpu.GFX()
            self.kbd = keyboard.NovaKeyboard()
            self.snd = sound.NovaSound()
            
            self.proc = cpu.CPU(self.mem, self.gfx, self.kbd, self.snd)
            
            # Ensure keyboard is properly connected
            self.kbd.cpu = self.proc
            
            # Connect graphics system to memory for sprite updates
            self.mem.gfx_system = self.gfx
            
            self.emulator_connected = True
            print("Nova-16 emulator initialized successfully")
            return True
        except Exception as e:
            print(f"Failed to initialize emulator: {e}")
            return False

    def compile_and_load_program(self) -> bool:
        """Compile the NoBASIC program and load it into the emulator."""
        if not self.initialize_emulator():
            return False
            
        if self.ast is None:
            print("No AST available. Run 'parse' first.")
            return False
            
        try:
            # Generate assembly code
            assembly_code = self.generator.generate(self.ast)
            
            # Save assembly to temporary file
            temp_asm_file = self.source_file + ".debug.asm"
            with open(temp_asm_file, 'w') as f:
                f.write(assembly_code)
            
            # Assemble to binary
            temp_bin_file = self.source_file + ".debug.bin"
            assembler = nova_assembler.Assembler()
            success = assembler.assemble(temp_asm_file)
            
            if not success:
                print("Assembly failed")
                return False
            
            # Load the binary into memory
            entry_point = self.mem.load(temp_bin_file)
            self.proc.pc = entry_point
            
            # Copy variable address mappings from generator
            self.variable_addresses = self.generator.variable_addresses.copy()
            
            # Build line-to-address mapping (simplified - would need enhancement for full mapping)
            self._build_line_mappings(assembly_code)
            
            print(f"Program compiled and loaded successfully")
            print(f"Entry point: 0x{entry_point:04X}")
            print(f"Variables allocated: {len(self.variable_addresses)}")
            
            # Clean up temporary files
            try:
                os.remove(temp_asm_file)
                os.remove(temp_bin_file)
            except:
                pass
                
            return True
            
        except Exception as e:
            print(f"Failed to compile and load program: {e}")
            return False

    def _build_line_mappings(self, assembly_code: str):
        """Build mappings between NoBASIC lines and assembly addresses."""
        # This is a simplified mapping - in a full implementation, 
        # we'd need to track source line information during code generation
        self.line_to_address = {}
        self.address_to_line = {}
        
        # For now, create a basic mapping assuming each NoBASIC statement 
        # corresponds to roughly 5-10 assembly instructions
        address = 0x0120  # Starting after interrupt vectors
        for line_num in range(1, len(self.source_lines) + 1):
            self.line_to_address[line_num] = address
            self.address_to_line[address] = line_num
            address += 10  # Rough estimate

    def run_debugger(self):
        """Run the interactive debugger."""
        print("NoBASIC Debugger")
        print("Type 'help' for commands.")

        while True:
            try:
                command = input("nobasic-debug> ").strip().lower()
                if not command:
                    continue

                if command == 'quit' or command == 'q':
                    break
                elif command == 'help' or command == 'h':
                    self._show_help()
                elif command == 'parse' or command == 'p':
                    self.parse_program()
                elif command.startswith('source') or command.startswith('s '):
                    self._handle_source_command(command)
                elif command.startswith('tokens') or command.startswith('t '):
                    self._handle_tokens_command(command)
                elif command == 'ast' or command == 'a':
                    self.show_ast()
                elif command == 'symbols' or command == 'sym':
                    self.show_symbols()
                elif command == 'assembly' or command == 'asm':
                    self.show_assembly()
                elif command == 'breakpoints' or command == 'bp':
                    self.list_breakpoints()
                elif command.startswith('break ') or command.startswith('b '):
                    self._handle_breakpoint_command(command)
                elif command.startswith('clear ') or command.startswith('cb '):
                    self._handle_clear_command(command)
                elif command.startswith('watch ') or command.startswith('w '):
                    self._handle_watch_command(command)
                elif command.startswith('unwatch ') or command.startswith('uw '):
                    self._handle_unwatch_command(command)
                elif command == 'watches' or command == 'ws':
                    self.show_watched_variables()
                elif command == 'stack' or command == 'st':
                    self.show_call_stack()
                elif command == 'context' or command == 'ctx':
                    self.show_execution_context()
                elif command == 'step' or command == 's':
                    self.step_over()
                elif command == 'stepinto' or command == 'si':
                    self.step_into()
                elif command == 'stepout' or command == 'so':
                    self.step_out()
                elif command.startswith('runto ') or command.startswith('rt '):
                    self._handle_runto_command(command)
                elif command == 'analyze' or command == 'an':
                    self.analyze_performance()
                elif command == 'issues' or command == 'iss':
                    self.find_potential_issues()
                elif command == 'load' or command == 'l':
                    self.compile_and_load_program()
                elif command == 'run' or command == 'r':
                    self.run_program()
                elif command == 'stop' or command == 'st':
                    self.stop_execution()
                elif command == 'registers' or command == 'regs':
                    self.inspect_registers()
                elif command.startswith('memory ') or command.startswith('mem '):
                    self._handle_memory_command(command)
                elif command == 'graphics' or command == 'gfx':
                    self.inspect_graphics()
                elif command == 'sound' or command == 'snd':
                    self.inspect_sound()
                elif command == 'variables' or command == 'vars':
                    self.inspect_variables()
                elif command.startswith('eval ') or command.startswith('e '):
                    self._handle_eval_command(command)
                else:
                    print(f"Unknown command: {command}")

            except KeyboardInterrupt:
                print("\nUse 'quit' to exit.")
            except EOFError:
                break

    def _show_help(self):
        """Show help information."""
        print("""
NoBASIC Debugger Commands:
  parse (p)           - Parse the source file
  load (l)            - Compile and load program into emulator
  run (r)             - Run program until completion or breakpoint
  stop (st)           - Stop program execution
  step (s)            - Step over current statement
  stepinto (si)       - Step into function calls
  stepout (so)        - Step out of current function
  registers (regs)    - Display CPU register values
  memory <addr> [count] (mem) - Inspect memory at address
  graphics (gfx)      - Display graphics system state
  sound (snd)         - Display sound system state
  variables (vars)    - Display watched variable values
  source [start [end]] (s) - Show source lines
  tokens [start [count]] (t) - Show tokens
  ast (a)             - Show AST structure
  symbols (sym)       - Show symbol table
  assembly (asm)      - Show generated assembly
  breakpoints (bp)    - List breakpoints
  break <line> [cond] (b) - Set breakpoint at line (optional condition)
  clear <line> (cb)   - Clear breakpoint at line
  watch <var> (w)     - Watch a variable
  unwatch <var> (uw)  - Stop watching a variable
  watches (ws)        - Show watched variables
  stack (st)          - Show call stack
  context (ctx)       - Show execution context
  runto <line> (rt)   - Run to specified line
  analyze (an)        - Analyze performance
  issues (iss)        - Find potential issues
  help (h)            - Show this help
  quit (q)            - Exit debugger
  eval <expr> (e)    - Evaluate a NoBASIC expression
        """)

    def _handle_source_command(self, command: str):
        """Handle source display command."""
        parts = command.split()
        start = 1
        end = None

        if len(parts) > 1:
            try:
                start = int(parts[1])
            except ValueError:
                print("Invalid start line")
                return

        if len(parts) > 2:
            try:
                end = int(parts[2])
            except ValueError:
                print("Invalid end line")
                return

        self.show_source(start, end)

    def _handle_tokens_command(self, command: str):
        """Handle tokens display command."""
        parts = command.split()
        start = 0
        count = 10

        if len(parts) > 1:
            try:
                start = int(parts[1])
            except ValueError:
                print("Invalid start index")
                return

        if len(parts) > 2:
            try:
                count = int(parts[2])
            except ValueError:
                print("Invalid count")
                return

        self.show_tokens(start, count)

    def show_call_stack(self):
        """Display the call stack."""
        if not self.call_stack:
            print("Call stack is empty.")
            return

        print("Call Stack:")
        print("-" * 40)
        for i, frame in enumerate(reversed(self.call_stack)):
            print(f"#{i}: {frame.get('function', 'main')} at line {frame.get('line', '?')}")

    def set_breakpoint(self, line_number: int, condition: Optional[str] = None):
        """Set a breakpoint at the specified line with optional condition."""
        if 1 <= line_number <= len(self.source_lines):
            self.breakpoints[line_number] = condition
            if condition:
                print(f"Conditional breakpoint set at line {line_number}: {condition}")
            else:
                print(f"Breakpoint set at line {line_number}")
        else:
            print(f"Invalid line number: {line_number}")

    def clear_breakpoint(self, line_number: int):
        """Clear a breakpoint at the specified line."""
        if line_number in self.breakpoints:
            del self.breakpoints[line_number]
            print(f"Breakpoint cleared at line {line_number}")
        else:
            print(f"No breakpoint at line {line_number}")

    def list_breakpoints(self):
        """List all breakpoints."""
        if not self.breakpoints:
            print("No breakpoints set.")
            return

        print("Breakpoints:")
        print("-" * 60)
        for bp, condition in sorted(self.breakpoints.items()):
            status = "conditional" if condition else "unconditional"
            print(f"Line {bp:3}: {status}")
            if condition:
                print(f"           Condition: {condition}")
            if bp <= len(self.source_lines):
                print(f"           {self.source_lines[bp-1].strip()}")

    def check_breakpoint_condition(self, condition: str) -> bool:
        """Check if a breakpoint condition is met."""
        if not condition:
            return True
            
        try:
            # Simple condition evaluation - for now just variable comparisons
            # Format: var == value, var != value, var > value, etc.
            if '==' in condition:
                var_name, value_str = condition.split('==')
                var_name = var_name.strip()
                value = int(value_str.strip())
                if var_name in self.variable_addresses:
                    addr = self.variable_addresses[var_name]
                    current_value = self.mem.read_word(addr)
                    return current_value == value
            elif '!=' in condition:
                var_name, value_str = condition.split('!=')
                var_name = var_name.strip()
                value = int(value_str.strip())
                if var_name in self.variable_addresses:
                    addr = self.variable_addresses[var_name]
                    current_value = self.mem.read_word(addr)
                    return current_value != value
            elif '>' in condition:
                var_name, value_str = condition.split('>')
                var_name = var_name.strip()
                value = int(value_str.strip())
                if var_name in self.variable_addresses:
                    addr = self.variable_addresses[var_name]
                    current_value = self.mem.read_word(addr)
                    return current_value > value
            elif '<' in condition:
                var_name, value_str = condition.split('<')
                var_name = var_name.strip()
                value = int(value_str.strip())
                if var_name in self.variable_addresses:
                    addr = self.variable_addresses[var_name]
                    current_value = self.mem.read_word(addr)
                    return current_value < value
                    
            return False
        except:
            return False

    def watch_variable(self, var_name: str):
        """Add a variable to the watch list."""
        self.watch_variables.add(var_name)
        print(f"Added watch for variable: {var_name}")

    def unwatch_variable(self, var_name: str):
        """Remove a variable from the watch list."""
        if var_name in self.watch_variables:
            self.watch_variables.remove(var_name)
            print(f"Removed watch for variable: {var_name}")
        else:
            print(f"Variable not in watch list: {var_name}")

    def show_watched_variables(self):
        """Display values of watched variables."""
        if not self.watch_variables:
            print("No variables being watched.")
            return

        print("Watched Variables:")
        print("-" * 40)
        for var in sorted(self.watch_variables):
            if var in self.symbols:
                var_type = self._symbol_type_name(self.symbols[var])
                print(f"{var}: {var_type}")
            else:
                print(f"{var}: <undefined>")

    def run_program(self):
        """Run the program until completion or breakpoint."""
        if not self.emulator_connected:
            print("Emulator not initialized. Run 'load' first.")
            return
            
        if self.is_running:
            print("Program is already running")
            return
            
        self.is_running = True
        self.step_mode = False
        
        print("Running program...")
        
        try:
            cycle = 0
            max_cycles = 100000  # Prevent infinite loops
            
            while cycle < max_cycles and not self.proc.halted and self.is_running:
                cycle += 1
                
                # Check for breakpoints
                if self.proc.pc in self.address_to_line:
                    line_num = self.address_to_line[self.proc.pc]
                    if line_num in self.breakpoints:
                        condition = self.breakpoints[line_num]
                        if condition is None or self.check_breakpoint_condition(condition):
                            print(f"Breakpoint hit at line {line_num}")
                            if condition:
                                print(f"Condition met: {condition}")
                            self.current_line = line_num
                            self.is_running = False
                            break
                
                # Execute one instruction
                old_pc = self.proc.pc
                self.proc.step()
                
                # Check for infinite loops
                if self.proc.pc == old_pc and not self.proc.halted:
                    print(f"Possible infinite loop detected at PC: 0x{self.proc.pc:04X}")
                    self.is_running = False
                    break
                    
                # Progress update
                if cycle % 1000 == 0:
                    print(f"Executed {cycle} cycles, PC: 0x{self.proc.pc:04X}")
                    
            if cycle >= max_cycles:
                print("Maximum cycle limit reached")
            elif self.proc.halted:
                print("Program halted")
            else:
                print(f"Program stopped after {cycle} cycles")
                
        except Exception as e:
            print(f"Error during execution: {e}")
        finally:
            self.is_running = False

    def step_over(self):
        """Step over the current statement."""
        if not self.emulator_connected:
            print("Emulator not initialized. Run 'load' first.")
            return
            
        if self.is_running:
            print("Program is currently running. Stop it first.")
            return
            
        try:
            # Execute one instruction
            old_pc = self.proc.pc
            self.proc.step()
            
            # Update current line if we have mapping
            if self.proc.pc in self.address_to_line:
                self.current_line = self.address_to_line[self.proc.pc]
                
            print(f"Stepped to PC: 0x{self.proc.pc:04X}")
            if self.current_line > 0:
                print(f"Line: {self.current_line}")
                
        except Exception as e:
            print(f"Error during step: {e}")

    def step_into(self):
        """Step into function calls (same as step_over for now)."""
        self.step_over()

    def step_out(self):
        """Step out of current function (not implemented yet)."""
        print("Step out not implemented yet")

    def stop_execution(self):
        """Stop program execution."""
        self.is_running = False
        print("Execution stopped")

    def inspect_registers(self):
        """Display current CPU register values."""
        if not self.emulator_connected:
            print("Emulator not initialized")
            return
            
        print("CPU Registers:")
        print("-" * 60)
        
        # General purpose registers
        print("General Purpose Registers:")
        print(f"  R0-R9: {[f'{r:3}' for r in self.proc.Rregisters[:10]]}")
        print(f"  P0-P9: {[f'0x{r:04X}' for r in self.proc.Pregisters[:10]]}")
        
        # Special registers
        print("\nSpecial Registers:")
        print(f"  PC:    0x{self.proc.pc:04X} ({self.proc.pc})")
        print(f"  SP:    P8 = 0x{self.proc.Pregisters[8]:04X} ({self.proc.Pregisters[8]})")
        print(f"  FP:    P9 = 0x{self.proc.Pregisters[9]:04X} ({self.proc.Pregisters[9]})")
        
        # Flags
        flags = self.proc.flags
        flag_names = ['T', 'S', 'O', 'B', 'D', 'I', 'C', 'Z', 'P', 'H', 'A', 'E']
        flag_values = [flags[i] for i in range(12)]
        print(f"\nFlags:  {' '.join(f'{name}={val}' for name, val in zip(flag_names, flag_values))}")
        
        # Status
        print(f"\nStatus:")
        print(f"  Halted:     {self.proc.halted}")
        print(f"  Cycles:     {self.proc.cycles}")
        print(f"  Interrupts: {[f'{i}={self.proc.interrupts[i]}' for i in range(8)]}")
        
        # Current line mapping
        if self.proc.pc in self.address_to_line:
            line_num = self.address_to_line[self.proc.pc]
            print(f"  Source:     Line {line_num}")
            if line_num <= len(self.source_lines):
                print(f"               {self.source_lines[line_num-1].strip()}")

    def inspect_memory(self, address: int, count: int = 16):
        """Inspect memory contents at the specified address."""
        if not self.emulator_connected:
            print("Emulator not initialized")
            return
            
        print(f"Memory at 0x{address:04X}:")
        print("-" * 80)
        print("Address  | 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F | ASCII")
        print("-" * 80)
        
        for row_start in range(0, count, 16):
            row_addr = address + row_start
            if row_addr >= 0x10000:
                break
                
            # Hex values
            hex_values = []
            ascii_values = []
            
            for i in range(16):
                if row_addr + i < 0x10000:
                    byte_val = self.mem.read_byte(row_addr + i)
                    hex_values.append(f"{byte_val:02X}")
                    
                    # ASCII representation
                    if 32 <= byte_val <= 126:
                        ascii_values.append(chr(byte_val))
                    else:
                        ascii_values.append('.')
                else:
                    hex_values.append("--")
                    ascii_values.append(' ')
                    
            hex_str = ' '.join(hex_values)
            ascii_str = ''.join(ascii_values)
            
            print(f"0x{row_addr:04X} | {hex_str} | {ascii_str}")

    def inspect_variables(self):
        """Display current values of watched variables."""
        if not self.emulator_connected:
            print("Emulator not initialized")
            return
            
        if not self.watch_variables:
            print("No variables being watched. Use 'watch <var>' to add variables.")
            return
            
        print("Watched Variables:")
        print("-" * 50)
        
        for var_name in sorted(self.watch_variables):
            if var_name in self.variable_addresses:
                addr = self.variable_addresses[var_name]
                value = self.mem.read_word(addr)
                var_type = self._symbol_type_name(self.symbols.get(var_name))
                print(f"{var_name:12} = {value:5} (0x{value:04X}) [{var_type:8}] @ 0x{addr:04X}")
            else:
                print(f"{var_name:12} = <not allocated>")

    def inspect_graphics(self):
        """Display graphics system state."""
        if not self.emulator_connected:
            print("Emulator not initialized")
            return
            
        print("Graphics State:")
        print("-" * 40)
        print(f"VX: 0x{self.gfx.Vregisters[0]:04X} ({self.gfx.Vregisters[0]})")
        print(f"VY: 0x{self.gfx.Vregisters[1]:04X} ({self.gfx.Vregisters[1]})")
        print(f"VM: 0x{self.gfx.Vregisters[2]:02X}")
        print(f"VL: 0x{self.gfx.Vregisters[3]:02X}")
        
        # Count non-zero pixels
        screen = self.gfx.get_screen()
        non_zero_pixels = (screen != 0).sum()
        print(f"Screen: {non_zero_pixels} non-black pixels")

    def inspect_sound(self):
        """Display sound system state."""
        if not self.emulator_connected:
            print("Emulator not initialized")
            return
            
        if self.snd:
            print("Sound State:")
            print("-" * 40)
            print(f"SA: 0x{self.snd.get_register('SA'):04X}")
            print(f"SF: 0x{self.snd.get_register('SF'):02X} ({self.snd.get_register('SF')} Hz)")
            print(f"SV: 0x{self.snd.get_register('SV'):02X} ({self.snd.get_register('SV')})")
            print(f"SW: 0x{self.snd.get_register('SW'):02X}")
        else:
            print("Sound system not available")
            
    def _handle_memory_command(self, command: str):
        """Handle memory inspection command."""
        parts = command.split()
        if len(parts) < 2:
            print("Usage: memory <address> [count]")
            return
        try:
            address = int(parts[1], 0)  # Allow hex (0x) or decimal
            count = 16
            if len(parts) > 2:
                count = int(parts[2])
            self.inspect_memory(address, count)
        except ValueError:
            print("Invalid address or count")
            
    def _handle_eval_command(self, command: str):
        """Handle expression evaluation command."""
        parts = command.split()
        if len(parts) < 2:
            print("Usage: eval <expression>")
            return
        
        expr = ' '.join(parts[1:])
        self.evaluate_expression(expr)

    def evaluate_expression(self, expr: str):
        """Evaluate a simple NoBASIC expression."""
        if not self.emulator_connected:
            print("Emulator not initialized")
            return
            
        try:
            # Parse the expression
            tokens = self.lexer.tokenize(expr, "<eval>")
            parsed_expr = self.parser.parse_expression(tokens)
            
            # For now, handle simple variable lookups and literals
            if isinstance(parsed_expr, VariableExpr):
                var_name = parsed_expr.name
                if var_name in self.variable_addresses:
                    addr = self.variable_addresses[var_name]
                    value = self.mem.read_word(addr)
                    print(f"{expr} = {value} (0x{value:04X})")
                else:
                    print(f"Variable '{var_name}' not found")
            elif isinstance(parsed_expr, LiteralExpr):
                print(f"{expr} = {parsed_expr.value}")
            else:
                print(f"Complex expressions not yet supported: {type(parsed_expr).__name__}")
                
        except Exception as e:
            print(f"Error evaluating expression: {e}")

    def _handle_breakpoint_command(self, command: str):
        """Handle breakpoint setting command."""
        parts = command.split()
        if len(parts) < 2:
            print("Usage: break <line_number> [condition]")
            return
        
        try:
            line_number = int(parts[1])
            condition = ' '.join(parts[2:]) if len(parts) > 2 else None
            self.set_breakpoint(line_number, condition)
        except ValueError:
            print("Invalid line number")