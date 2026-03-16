import sys
import warnings
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)
import argparse
import nova_cpu as cpu
import nova_memory as ram
import nova_gfx as gpu
import nova_sound as sound
import nova_uart as uart


import nova_gui as gui
import nova_keyboard as keyboard
import nova_memory_profiler as mem_profiler

def build_uart_config(args):
    return uart.validate_bridge_config(
        uart.UARTBridgeConfig(
            mode=args.uart_bridge,
            tcp_role=args.uart_tcp_role,
            host=args.uart_host,
            port=args.uart_port,
            timeout=args.uart_timeout,
        )
    )


def initialize_system(enable_sound=True, uart_config=None):
    """Initialize all Nova-16 system components with consistent state"""
    mem = ram.Memory()
    gfx = gpu.GFX()
    kbd = keyboard.NovaKeyboard()
    snd = sound.NovaSound() if enable_sound else None
    uart_device = uart.NovaUART(host_bridge=uart.create_host_bridge(uart_config))
    
    proc = cpu.CPU(mem, gfx, kbd, snd, uart_device=uart_device)
    
    # Ensure keyboard is properly connected
    kbd.cpu = proc
    
    # Connect graphics system to memory for sprite updates
    mem.gfx_system = gfx
    
    return proc, mem, gfx, kbd, snd

def run_headless(program_path, max_cycles=10000, enable_memory_profiling=False, profile_output=None, uart_config=None):
    """Run a program headlessly for testing"""
    proc, mem, gfx, kbd, snd = initialize_system(enable_sound=False, uart_config=uart_config)
    
    # Initialize memory profiler if requested
    profiler = None
    if enable_memory_profiling:
        profiler = mem_profiler.MemoryProfiler(output_file=profile_output or "memory_profile.json")
        profiler.enable_profiling(mem)
        print("Memory profiling enabled")
    
    # Load the program and get entry point
    entry_point = mem.load(program_path)
    proc.pc = entry_point  # Set PC to the entry point from ORG directive
    
    print(f"Running {program_path} headlessly...")
    print(f"Entry point: 0x{entry_point:04X}")
    print(f"Initial PC: 0x{proc.pc:04X}")
    
    # Run for max_cycles or until halt
    cycle = 0
    while cycle < max_cycles and not proc.halted:
        cycle += 1
        
        # Update profiler cycle count
        if profiler:
            profiler.update_cycle_count(cycle)
            
        try:
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
            if cycle % 1000 == 0:
                print(f"Cycle {cycle}, PC: 0x{proc.pc:04X}")
                
        except Exception as e:
            print(f"Error at cycle {cycle}, PC: 0x{proc.pc:04X}: {e}")
            break
    
    print(f"Execution finished after {cycle} cycles")
    print(f"Final PC: 0x{proc.pc:04X}")
    print(f"CPU Halted: {proc.halted}")
    print("Final register states:")
    print(f"R0-R9: {[f'0x{r:02X}' for r in proc.Rregisters[:10]]}")
    print(f"P0-P9: {[f'0x{r:04X}' for r in proc.Pregisters[:10]]}")
    print(f"VX,VY,VC: 0x{gfx.Vregisters[0]:04X}, 0x{gfx.Vregisters[1]:04X}, 0x{gfx.Vregisters[3]:02X}")
    
    # Sound system info
    if proc.sound:
        print(f"Sound: SA=0x{proc.sound.get_register('SA'):04X}, SF=0x{proc.sound.get_register('SF'):02X}, SV=0x{proc.sound.get_register('SV'):02X}, SW=0x{proc.sound.get_register('SW'):02X}")
    else:
        print("Sound: Disabled")
    
    # Check if there's any graphics output (composite layers first)
    print(f"Debug: Layer 0 pixels: {(gfx.layer_0 != 0).sum()}")
    for i in range(4):
        print(f"Debug: Background layer {i+1} pixels: {(gfx.background_layers[i] != 0).sum()}")
    for i in range(4):
        print(f"Debug: Sprite layer {i+5} pixels: {(gfx.sprite_layers[i] != 0).sum()}")
    screen = gfx.get_screen()  # Use get_screen() to trigger layer compositing
    non_zero_pixels = (screen != 0).sum()
    print(f"Graphics: {non_zero_pixels} non-black pixels on screen")
    
    # Generate profiling report if enabled
    if profiler:
        profiler.save_report()
        profiler.print_summary()
    
    # Cleanup sound system and UART bridge
    if snd:
        snd.cleanup()
    proc.uart.close_host_bridge()
    
    return proc, mem, gfx

def main():
    parser = argparse.ArgumentParser(description='Nova-16 CPU Emulator')
    parser.add_argument('program', nargs='?', help='Binary program file to load and run')
    parser.add_argument('--headless', action='store_true', help='Run without GUI for testing')
    parser.add_argument('--cycles', type=int, default=10000, help='Maximum cycles to run in headless mode')
    parser.add_argument('--memory-profile', action='store_true', help='Enable memory profiling')
    parser.add_argument('--profile-output', default='memory_profile.json', help='Output file for memory profile data')
    parser.add_argument('--uart-bridge', choices=['none', 'terminal', 'tcp'], default='none', help='UART bridge transport to attach')
    parser.add_argument('--uart-tcp-role', choices=['client', 'server'], default='client', help='UART TCP bridge role when --uart-bridge=tcp')
    parser.add_argument('--uart-host', default=uart.DEFAULT_TCP_HOST, help='UART TCP bridge host')
    parser.add_argument('--uart-port', type=int, help='UART TCP bridge port')
    parser.add_argument('--uart-timeout', type=float, default=uart.DEFAULT_TCP_TIMEOUT, help='UART bridge socket timeout in seconds')
    
    args = parser.parse_args()
    try:
        uart_config = build_uart_config(args)
    except ValueError as exc:
        parser.error(str(exc))
    
    if args.headless and args.program:
        try:
            run_headless(args.program, args.cycles, args.memory_profile, args.profile_output, uart_config)
        except OSError as exc:
            parser.error(f'Unable to initialize UART bridge: {exc}')
    else:
        try:
            proc, mem, gfx, kbd, snd = initialize_system(enable_sound=True, uart_config=uart_config)
        except OSError as exc:
            parser.error(f'Unable to initialize UART bridge: {exc}')
        
        # Enable memory profiling if requested
        profiler = None
        if args.memory_profile:
            profiler = mem_profiler.MemoryProfiler(output_file=args.profile_output)
            profiler.enable_profiling(mem)
            print("Memory profiling enabled")
        
        print(f"Nova-16 Emulator")
        if snd:
            print(f"Sound: {snd.max_channels} channels, {snd.sample_rate}Hz")
        else:
            print("Sound: Disabled")
        print(uart.describe_bridge(uart_config))
        
        # Load program if specified
        if args.program:
            entry_point = mem.load(args.program)
            proc.pc = entry_point  # Set PC to the entry point from ORG directive
            print(f"Loaded {args.program}")
            print(f"Entry point: 0x{entry_point:04X}")
        
        # Run GUI
        try:
            gui.main(proc, mem, gfx, kbd)
        finally:
            if snd:
                snd.cleanup()
            proc.uart.close_host_bridge()

if __name__ == "__main__":
    main()

