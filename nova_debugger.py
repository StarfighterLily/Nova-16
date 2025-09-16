
import sys
import argparse
import nova_cpu as cpu
import nova_memory as ram
import nova_gfx as gpu
import nova_sound as sound
import nova_keyboard as keyboard

class NovaDebugger:
    def __init__(self, cpu, memory, gpu=None, snd=None):
        self.cpu = cpu
        self.memory = memory
        self.gpu = gpu
        self.sound = snd
        self.running = True

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
            self.print_registers()
            self.print_stack()
            self.print_memory(self.cpu.pc)
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
                        except Exception as e:
                            print(f"Error during step {i+1}: {e}")
                            break
                    self.print_registers()
                    self.print_stack()
                    self.print_memory(self.cpu.pc)
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
        elif cmd.startswith("load "):
            parts = cmd.split(maxsplit=1)
            if len(parts) == 2:
                try:
                    filename = parts[1].strip()
                    entry_point = self.memory.load(filename)
                    self.cpu.pc = entry_point
                    print(f"Loaded {filename} at entry point 0x{entry_point:04X}")
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

    def print_memory(self, addr):
        # Show 16 bytes from addr
        vals = self.memory.memory[addr:addr+16]
        print(f"Memory[0x{addr:04X}..0x{addr+15:04X}]:", ' '.join(f"{v:02X}" for v in vals))

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

    dbg = NovaDebugger(proc, memory, gfx, snd)
    
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
