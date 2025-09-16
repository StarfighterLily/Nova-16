import sys
import argparse
import nova_cpu as cpu
import nova_memory as ram
import nova_gfx as gpu
import nova_sound as sound


import nova_gui as gui
import nova_keyboard as keyboard

def run_headless(program_path, max_cycles=10000):
    """Run a program headlessly for testing"""
    mem = ram.Memory()
    gfx = gpu.GFX()
    kbd = keyboard.NovaKeyboard()
    snd = sound.NovaSound()
    proc = cpu.CPU(mem, gfx, kbd, snd)
    
    # Ensure keyboard is properly connected
    kbd.cpu = proc
    
    # Load the program and get entry point
    entry_point = mem.load(program_path)
    proc.pc = entry_point  # Set PC to the entry point from ORG directive
    
    print(f"Running {program_path} headlessly...")
    print(f"Entry point: 0x{entry_point:04X}")
    print(f"Initial PC: 0x{proc.pc:04X}")
    
    # Run for max_cycles or until halt
    for cycle in range(max_cycles):
        try:
            # Check if we've hit a halt instruction or infinite loop
            old_pc = proc.pc
            proc.step()
            
            # Check if CPU halted (HLT instruction executed)
            if proc.halted:
                print(f"Program halted at PC: 0x{proc.pc:04X}")
                break
            
            # Simple infinite loop detection (only if not halted)
            if proc.pc == old_pc:
                print(f"Possible infinite loop detected at PC: 0x{proc.pc:04X}")
                break
                
            # Print every 1000 cycles for progress
            if cycle % 1000 == 0 and cycle > 0:
                print(f"Cycle {cycle}, PC: 0x{proc.pc:04X}")
                
        except Exception as e:
            print(f"Error at cycle {cycle}, PC: 0x{proc.pc:04X}: {e}")
            break
    
    print(f"Execution finished after {cycle + 1} cycles")
    
# Memory dump after execution
def dump_memory_range(memory, start, end, label):
    print(f"\n{label} (0x{start:04X}-0x{end:04X}):")
    for addr in range(start, end, 2):
        if addr + 1 < end:
            value = (memory[addr] << 8) | memory[addr + 1]
            print(f"  0x{addr:04X}: 0x{value:04X}")

# After main loop
dump_memory_range(memory.data, 0x2000, 0x2020, "BENCHMARK RESULTS")
\nprint(f"Final PC: 0x{proc.pc:04X}")
    print("Final register states:")
    print(f"R0-R9: {[f'0x{r:04X}' for r in proc.Rregisters[:10]]}")
    print(f"P0-P9: {[f'0x{r:04X}' for r in proc.Pregisters[:10]]}")
    print(f"VX,VY: 0x{gfx.Vregisters[0]:04X}, 0x{gfx.Vregisters[1]:04X}")
    
    # Sound system info
    print(f"Sound: SA=0x{proc.sound.get_register('SA'):04X}, SF=0x{proc.sound.get_register('SF'):02X}, SV=0x{proc.sound.get_register('SV'):02X}, SW=0x{proc.sound.get_register('SW'):02X}")
    
    # Check if there's any graphics output
    screen = gfx.get_screen()
    non_zero_pixels = (screen != 0).sum()
    print(f"Graphics: {non_zero_pixels} non-black pixels on screen")
    
    # Cleanup sound system
    snd.cleanup()
    
    return proc, mem, gfx

def main():
    parser = argparse.ArgumentParser(description='Nova-16 CPU Emulator')
    parser.add_argument('program', nargs='?', help='Binary program file to load and run')
    parser.add_argument('--headless', action='store_true', help='Run without GUI for testing')
    parser.add_argument('--cycles', type=int, default=10000, help='Maximum cycles to run in headless mode')
    
    args = parser.parse_args()
    
    if args.headless and args.program:
        run_headless(args.program, args.cycles)
    else:
        mem = ram.Memory()
        gfx = gpu.GFX()
        kbd = keyboard.NovaKeyboard()
        snd = sound.NovaSound()
        proc = cpu.CPU(mem, gfx, kbd, snd)
        
        # Ensure keyboard is properly connected to CPU
        kbd.cpu = proc
        
        print(f"Nova-16 Emulator")
        print(f"CPU: Standard Python implementation")
        print(f"Sound: {snd.max_channels} channels, {snd.sample_rate}Hz")
        
        # Load program if specified
        if args.program:
            entry_point = mem.load(args.program)
            proc.pc = entry_point  # Set PC to the entry point from ORG directive
            print(f"Loaded {args.program}")
            print(f"Entry point: 0x{entry_point:04X}")
        
        # Run GUI
        gui.main(proc, mem, gfx, kbd)

if __name__ == "__main__":
    main()

