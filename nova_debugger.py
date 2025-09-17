
import sys
import argparse
import nova_cpu as cpu
import nova_memory as ram
import nova_gfx as gpu
import nova_sound as sound
import nova_keyboard as keyboard
from nova_disassembler import create_reverse_maps, disassemble_instruction_new, is_string_data, format_string_data

class NovaDebugger:
    def __init__(self, cpu, memory, gpu=None, snd=None, program_path=None):
        self.cpu = cpu
        self.memory = memory
        self.gpu = gpu
        self.sound = snd
        self.running = True
        self.program_path = program_path
        self.breakpoints = set()
        self.symbol_table = {}
        self.reverse_symbol_table = {}
        self.opcode_map, self.register_map = create_reverse_maps()
        
        # Load symbol table if available
        if program_path:
            self.load_symbol_table(program_path)
            
    def load_symbol_table(self, program_path):
        """Load symbol table from .sym file"""
        sym_file = program_path.replace('.bin', '.sym')
        try:
            with open(sym_file, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split(None, 1)
                        if len(parts) >= 2:
                            symbol = parts[0]
                            value = parts[1]
                            self.symbol_table[symbol] = value
                            if value.startswith('0x'):
                                try:
                                    addr = int(value, 16)
                                    self.reverse_symbol_table[addr] = symbol
                                except ValueError:
                                    pass
        except FileNotFoundError:
            pass

    def repl(self):
        print("Nova-16 Debugger CLI. Type 'help' for commands.")
        while self.running:
            try:
                cmd = input("(nova-debug) ").strip()
                self.handle_command(cmd)
            except (EOFError, KeyboardInterrupt):
                print("\nExiting debugger.")
                break

    def handle_command(self, cmd):
        if cmd in ("q", "quit", "exit"):
            self.running = False
        elif cmd in ("s", "step"):
            self.cpu.step()
            self.print_current_instruction()
            self.print_registers()
            self.print_stack()
            print("Stepped one instruction.")
        elif cmd.startswith("step ") or cmd.startswith("s "):
            parts = cmd.split()
            if len(parts) == 2:
                try:
                    steps = int(parts[1])
                    print(f"Stepping {steps} instructions...")
                    for i in range(steps):
                        try:
                            self.cpu.step()
                            print(f"Step {i+1}/{steps}: PC=0x{self.cpu.pc:04X}")
                            self.print_current_instruction()
                        except Exception as e:
                            print(f"Error during step {i+1}: {e}")
                            break
                    self.print_registers()
                    self.print_stack()
                except ValueError:
                    print("Invalid number of steps.")
            else:
                print("Usage: step <number> or s <number>")
        elif cmd in ("r", "regs", "registers"):
            self.print_registers()
        elif cmd.startswith("mem "):
            parts = cmd.split()
            if len(parts) == 2:
                try:
                    addr = int(parts[1], 0)
                    self.print_memory(addr)
                except ValueError:
                    print("Invalid address.")
            else:
                print("Usage: mem <address>")
        elif cmd == "stack":
            self.print_stack()
        elif cmd.startswith("disasm") or cmd.startswith("d "):
            parts = cmd.split()
            addr = self.cpu.pc
            count = 5
            
            if len(parts) > 1:
                try:
                    addr = int(parts[1], 0)
                except ValueError:
                    print("Invalid address.")
                    return
                    
            if len(parts) > 2:
                try:
                    count = int(parts[2])
                except ValueError:
                    print("Invalid count.")
                    return
                    
            self.print_disassembly(addr, count)
        elif cmd.startswith("break ") or cmd.startswith("b "):
            parts = cmd.split()
            if len(parts) == 2:
                try:
                    addr = int(parts[1], 0)
                    self.breakpoints.add(addr)
                    print(f"Breakpoint set at 0x{addr:04X}")
                except ValueError:
                    print("Invalid address.")
            else:
                print("Usage: break <address> or b <address>")
        elif cmd == "breakpoints" or cmd == "bp":
            if self.breakpoints:
                print("Breakpoints:")
                for addr in sorted(self.breakpoints):
                    symbol = self.reverse_symbol_table.get(addr, "")
                    if symbol:
                        print(f"  0x{addr:04X} ({symbol})")
                    else:
                        print(f"  0x{addr:04X}")
            else:
                print("No breakpoints set")
        elif cmd.startswith("clear ") or cmd.startswith("c "):
            parts = cmd.split()
            if len(parts) == 2:
                try:
                    addr = int(parts[1], 0)
                    if addr in self.breakpoints:
                        self.breakpoints.remove(addr)
                        print(f"Breakpoint cleared at 0x{addr:04X}")
                    else:
                        print(f"No breakpoint at 0x{addr:04X}")
                except ValueError:
                    print("Invalid address.")
            else:
                print("Usage: clear <address> or c <address>")
        elif cmd == "run" or cmd == "continue" or cmd == "cont":
            self.run_until_breakpoint()
        elif cmd.startswith("load "):
            parts = cmd.split(maxsplit=1)
            if len(parts) == 2:
                try:
                    filename = parts[1].strip()
                    entry_point = self.memory.load(filename)
                    self.cpu.pc = entry_point
                    self.program_path = filename
                    self.load_symbol_table(filename)
                    print(f"Loaded {filename} at entry point 0x{entry_point:04X}")
                    self.print_current_instruction()
                    self.print_registers()
                except Exception as e:
                    print(f"Error loading file: {e}")
            else:
                print("Usage: load <filename>")
        elif cmd in ("h", "help", "?"):
            self.print_help()
        else:
            print("Unknown command. Type 'help' for a list of commands.")

    def print_registers(self):
        # Show Nova-16 CPU registers
        print("PC: 0x{:04X}".format(self.cpu.pc))
        print("R0-R9:", ' '.join(f"R{i}:0x{int(val):02X}  " for i, val in enumerate(self.cpu.Rregisters[:10])))
        print("P0-P9:", ' '.join(f"P{i}:0x{int(val):04X}" for i, val in enumerate(self.cpu.Pregisters[:10])))
        print(f"VM: 0x{self.gpu.Vregisters[2]:04X} VX: 0x{self.gpu.Vregisters[0]:04X} VY: 0x{self.gpu.Vregisters[1]:04X} VL: 0x{self.gpu.VL:04X}")
        print(f"SA: 0x{self.sound.SA:04X} SF: 0x{self.sound.SF:04X} SV: 0x{self.sound.SV:04X} SW: 0x{self.sound.SW:04X}")
        print(f"TT: 0x{self.cpu.timer[0]:04X} TM: 0x{self.cpu.timer[1]:04X} TC: 0x{self.cpu.timer[2]:04X} TS: 0x{self.cpu.timer[3]:04X}")
        # Show flags if available
        if hasattr(self.cpu, '_flags'):
            print("FLAGS:", ' '.join(str(int(f)) for f in self.cpu._flags))

    def print_current_instruction(self):
        """Print the current instruction at PC"""
        try:
            pc = self.cpu.pc
            if pc >= len(self.memory.memory):
                print(f"PC 0x{pc:04X} is beyond memory bounds")
                return
                
            opcode = self.memory.memory[pc]
            
            # Check for string data
            is_string, str_length = is_string_data(self.memory.memory, pc)
            if is_string and str_length > 1:
                hex_dump = ' '.join(f'{self.memory.memory[pc + i]:02X}' for i in range(min(str_length, 8)))
                if str_length > 8:
                    hex_dump += "..."
                string_directive = format_string_data(self.memory.memory, pc, str_length)
                symbol = self.reverse_symbol_table.get(pc, "")
                label = f"{symbol}:" if symbol else ""
                print(f"{label} 0x{pc:04X}:  {hex_dump:<12} {string_directive}")
                return
            
            if opcode in self.opcode_map:
                mnemonic, operands, size = disassemble_instruction_new(self.memory.memory, pc, self.opcode_map, self.register_map, self.reverse_symbol_table)
                
                if pc + size > len(self.memory.memory):
                    hex_dump = ' '.join(f'{self.memory.memory[pc + i]:02X}' for i in range(len(self.memory.memory) - pc))
                    print(f"0x{pc:04X}:  {hex_dump:<12} ??? (Incomplete)")
                    return
                    
                instruction_bytes = self.memory.memory[pc:pc + size]
                hex_dump = ' '.join(f'{b:02X}' for b in instruction_bytes)
                operand_str = ', '.join(operands) if operands else ""
                symbol = self.reverse_symbol_table.get(pc, "")
                label = f"{symbol}:" if symbol else ""
                print(f"{label} 0x{pc:04X}:  {hex_dump:<12} {mnemonic:<8} {operand_str}")
            else:
                hex_dump = f"{opcode:02X}"
                symbol = self.reverse_symbol_table.get(pc, "")
                label = f"{symbol}:" if symbol else ""
                print(f"{label} 0x{pc:04X}:  {hex_dump:<12} DB 0x{opcode:02X}")
        except Exception as e:
            print(f"Error disassembling current instruction: {e}")
    
    def print_disassembly(self, addr, count):
        """Print disassembly starting from addr"""
        pc = addr
        for i in range(count):
            if pc >= len(self.memory.memory):
                break
                
            opcode = self.memory.memory[pc]
            
            # Check for string data
            is_string, str_length = is_string_data(self.memory.memory, pc)
            if is_string and str_length > 1:
                hex_dump = ' '.join(f'{self.memory.memory[pc + i]:02X}' for i in range(min(str_length, 8)))
                if str_length > 8:
                    hex_dump += "..."
                string_directive = format_string_data(self.memory.memory, pc, str_length)
                symbol = self.reverse_symbol_table.get(pc, "")
                label = f"{symbol}:" if symbol else ""
                print(f"{label} 0x{pc:04X}:  {hex_dump:<12} {string_directive}")
                pc += str_length
                continue
            
            if opcode in self.opcode_map:
                mnemonic, operands, size = disassemble_instruction_new(self.memory.memory, pc, self.opcode_map, self.register_map, self.reverse_symbol_table)
                
                if pc + size > len(self.memory.memory):
                    hex_dump = ' '.join(f'{self.memory.memory[pc + i]:02X}' for i in range(len(self.memory.memory) - pc))
                    print(f"0x{pc:04X}:  {hex_dump:<12} ??? (Incomplete)")
                    break
                    
                instruction_bytes = self.memory.memory[pc:pc + size]
                hex_dump = ' '.join(f'{b:02X}' for b in instruction_bytes)
                operand_str = ', '.join(operands) if operands else ""
                symbol = self.reverse_symbol_table.get(pc, "")
                label = f"{symbol}:" if symbol else ""
                print(f"{label} 0x{pc:04X}:  {hex_dump:<12} {mnemonic:<8} {operand_str}")
                pc += size
            else:
                hex_dump = f"{opcode:02X}"
                symbol = self.reverse_symbol_table.get(pc, "")
                label = f"{symbol}:" if symbol else ""
                print(f"{label} 0x{pc:04X}:  {hex_dump:<12} DB 0x{opcode:02X}")
                pc += 1
    
    def run_until_breakpoint(self):
        """Run until a breakpoint is hit or program halts"""
        print("Running until breakpoint...")
        steps = 0
        max_steps = 100000  # Prevent infinite loops
        
        while steps < max_steps:
            if self.cpu.pc in self.breakpoints:
                print(f"Breakpoint hit at 0x{self.cpu.pc:04X}")
                self.print_current_instruction()
                break
                
            if self.cpu.halted:
                print("Program halted")
                break
                
            try:
                self.cpu.step()
                steps += 1
            except Exception as e:
                print(f"Error during execution at PC 0x{self.cpu.pc:04X}: {e}")
                break
                
        if steps >= max_steps:
            print(f"Stopped after {max_steps} steps (possible infinite loop)")
            
        self.print_registers()
        self.print_stack()

    def print_stack(self):
        # Show stack contents from memory
        sp = self.cpu.Pregisters[8]
        print("Stack:")
        print(f"  SP: 0x{sp:04X} (stack pointer)")
        print(f"  FP: 0x{self.cpu.Pregisters[9]:04X} (frame pointer)")
        
        # Show some stack contents from memory (last 16 entries)
        stack_entries = []
        addr = int(sp) & 0xFFFF  # Convert to Python int to avoid numpy overflow warnings
        for i in range(16):
            if addr <= 0xFFFF:
                val = self.cpu.memory.read_word(addr)
                stack_entries.append(f"0x{val:04X}")
                addr = (addr + 2) & 0xFFFF  # Use explicit masking to prevent overflow
            else:
                break
        
        if stack_entries:
            print("  Stack contents (top to bottom):")
            print("  " + " ".join(stack_entries))
        else:
            print("  (empty or invalid SP)")

    def print_help(self):
        print("""
Commands:
  step, s           Step one instruction
  step <n>, s <n>   Step <n> instructions
  run, continue     Run until breakpoint or halt
  disasm [addr] [n] Show disassembly (default: PC, 5 instructions)
  break <addr>, b   Set breakpoint at address
  clear <addr>, c   Clear breakpoint at address
  breakpoints, bp   List all breakpoints
  regs, r           Show CPU registers
  mem <addr>        Show memory at <addr>
  stack             Show stack contents
  load <file>       Load a binary file into memory
  quit, q, exit     Exit debugger
  help, h, ?        Show this help
""")


def main():
    parser = argparse.ArgumentParser(description='Nova-16 Debugger')
    parser.add_argument('program', nargs='?', help='Binary program file to load and debug')
    parser.add_argument('--steps', type=int, help='Number of instructions to step through automatically')
    args = parser.parse_args()

    memory = ram.Memory()
    gfx = gpu.GFX()
    kbd = keyboard.NovaKeyboard()
    snd = sound.NovaSound()
    proc = cpu.CPU(memory, gfx, kbd, snd)
    kbd.cpu = proc

    if args.program:
        entry_point = memory.load(args.program)
        proc.pc = entry_point
        print(f"Loaded {args.program} at entry point 0x{entry_point:04X}")
    else:
        print("No program loaded. You can still inspect/step the CPU.")

    dbg = NovaDebugger(proc, memory, gfx, snd, args.program)
    
    # If --steps specified, execute that many steps automatically
    if args.steps:
        print(f"Stepping through {args.steps} instructions...")
        for i in range(args.steps):
            try:
                print(f"\nStep {i+1}/{args.steps}:")
                proc.step()
                dbg.print_registers()
                dbg.print_stack()
                dbg.print_memory(proc.pc)
            except Exception as e:
                print(f"Error during step {i+1}: {e}")
                break
        print(f"\nCompleted {min(i+1 if 'i' in locals() else args.steps, args.steps)} steps.")
        print("Entering interactive mode...")
    
    dbg.repl()

if __name__ == "__main__":
    main()
