#!/usr/bin/env python3
"""
Nova GPU Profiler - Performance analysis tool for Nova-16 graphics system.
Measures frame rates, rendering times, pixel throughput, and graphics operation efficiency.
"""

import sys
import os
import time
import json
import argparse
from typing import Dict, List, Optional, Tuple
import numpy as np

sys.path.append(os.path.dirname(__file__))

from nova_cpu import CPU
from nova_memory import Memory
from nova_gfx import GFX
from nova_keyboard import NovaKeyboard
from nova_sound import NovaSound

class GPUProfiler:
    """GPU performance profiler for Nova-16 emulator"""

    def __init__(self, output_file: str = "gpu_profile.json", enable_charts: bool = True):
        self.output_file = output_file
        self.enable_charts = enable_charts

        # Profiling data
        self.profile_data = {
            'session_start': time.time(),
            'total_cycles': 0,
            'graphics_instructions': 0,
            'pixel_writes': 0,
            'layer_operations': 0,
            'composite_events': 0,
            'frame_times': [],  # List of (cycle, timestamp) for frame events
            'instruction_timings': {},  # opcode -> list of execution times
            'layer_usage': {i: 0 for i in range(9)},  # Layer -> pixel writes
            'memory_bandwidth': 0,  # Bytes transferred for graphics
            'peak_frame_rate': 0,
            'average_frame_rate': 0,
            'total_render_time': 0,
            'instruction_breakdown': {}
        }

        # Graphics instruction opcodes (from opcodes.py)
        self.graphics_opcodes = {
            0x31: 'SBLEND',   # Set blend mode
            0x32: 'SREAD',    # Read screen pixel
            0x33: 'SWRITE',   # Write screen pixel
            0x34: 'SROL',     # Roll screen by axis, amount
            0x35: 'SROT',     # Rotate screen by direction, amount
            0x36: 'SSHFT',    # Shift screen by axis, amount
            0x37: 'SFLIP',    # Flip screen by axis, amount
            0x38: 'SLINE',    # Line x1, y1, x2, y2, color
            0x39: 'SRECT',    # Rectangle x1, y1, x2, y2, color, un/filled
            0x3A: 'SCIRC',    # Circle x, y, radius, color, un/filled
            0x3B: 'SINV',     # Invert screen colors
            0x3C: 'SBLIT',    # Blit screen
            0x3D: 'SFILL',    # Fill screen
            0x3E: 'VREAD',    # Read VRAM
            0x3F: 'VWRITE',   # Write VRAM
            0x40: 'VBLIT',    # Blit VRAM
            0x41: 'CHAR',     # Draw character
            0x42: 'TEXT',     # Draw text
            0x55: 'SPBLIT',   # Blit sprite
            0x56: 'SPBLITALL', # Blit all sprites
            # Layer operations
            0x83: 'LCPY',     # Copy contents of layer dest, source
            0x84: 'LCLR',     # Clear layer to color
            0x86: 'LSHFT',    # Shift layer by axis, amount
            0x87: 'LROT',     # Rotate layer by direction, amount
            0x88: 'LFLIP',    # Flip layer by axis, amount
            0x89: 'LSWAP'     # Swap two layers dest, source
        }

        # State tracking
        self.last_composite_time = None
        self.instruction_start_time = None
        self.current_instruction = None

        # Frame timing simulation for headless mode
        self.frame_interval = 1.0 / 60.0  # 60 FPS target
        self.last_frame_time = time.time()
        self.simulated_frames = 0

        # Hook references
        self.cpu = None
        self.gfx = None

    def attach_to_emulator(self, cpu: CPU, gfx: GFX):
        """Attach profiler to running emulator"""
        self.cpu = cpu
        self.gfx = gfx

        # Monkey patch CPU methods for profiling
        original_step = cpu.step
        original_execute = cpu.execute

        def profiled_step():
            self._on_step_start()
            result = original_step()
            self._on_step_end()
            return result

        def profiled_execute(opcode):
            self._on_instruction_start(opcode)
            result = original_execute(opcode)
            self._on_instruction_end(opcode)
            return result

        cpu.step = profiled_step
        cpu.execute = profiled_execute

        # Hook into GFX for compositing events
        original_composite = gfx.composite_layers
        def profiled_composite():
            self._on_composite_start()
            result = original_composite()
            self._on_composite_end()
            return result
        gfx.composite_layers = profiled_composite

        # Hook into pixel writes
        original_set_pixel = gfx._set_pixel_to_layer
        def profiled_set_pixel(x, y, value):
            self._on_pixel_write(x, y, value, gfx.VL)
            return original_set_pixel(x, y, value)
        gfx._set_pixel_to_layer = profiled_set_pixel

    def _on_step_start(self):
        """Called at start of each CPU cycle"""
        self.profile_data['total_cycles'] += 1

    def _on_step_end(self):
        """Called at end of each CPU cycle"""
        # Simulate frame timing for headless profiling
        current_time = time.time()
        if current_time - self.last_frame_time >= self.frame_interval:
            # Trigger compositing to simulate a frame
            if self.gfx and hasattr(self.gfx, 'layers_dirty') and self.gfx.layers_dirty:
                self._on_composite_start()
                self.gfx.composite_layers()
                self._on_composite_end()
                self.simulated_frames += 1

            self.last_frame_time = current_time

    def _on_instruction_start(self, opcode: int):
        """Called when instruction execution starts"""
        self.instruction_start_time = time.time()
        self.current_instruction = opcode

        if opcode in self.graphics_opcodes:
            self.profile_data['graphics_instructions'] += 1

    def _on_instruction_end(self, opcode: int):
        """Called when instruction execution ends"""
        if self.instruction_start_time is not None:
            execution_time = time.time() - self.instruction_start_time

            if opcode not in self.profile_data['instruction_timings']:
                self.profile_data['instruction_timings'][opcode] = []
            self.profile_data['instruction_timings'][opcode].append(execution_time)

            if opcode in self.graphics_opcodes:
                self.profile_data['total_render_time'] += execution_time

            # Update instruction breakdown
            opcode_name = self.graphics_opcodes.get(opcode, f'0x{opcode:02X}')
            if opcode_name not in self.profile_data['instruction_breakdown']:
                self.profile_data['instruction_breakdown'][opcode_name] = {
                    'count': 0, 'total_time': 0, 'avg_time': 0
                }
            breakdown = self.profile_data['instruction_breakdown'][opcode_name]
            breakdown['count'] += 1
            breakdown['total_time'] += execution_time
            breakdown['avg_time'] = breakdown['total_time'] / breakdown['count']

        self.instruction_start_time = None
        self.current_instruction = None

    def _on_composite_start(self):
        """Called when layer compositing starts"""
        pass

    def _on_composite_end(self):
        """Called when layer compositing ends"""
        current_time = time.time()
        self.profile_data['composite_events'] += 1

        if self.last_composite_time is not None:
            frame_time = current_time - self.last_composite_time
            self.profile_data['frame_times'].append((self.profile_data['total_cycles'], frame_time))

            # Calculate frame rate
            if frame_time > 0:
                fps = 1.0 / frame_time
                self.profile_data['peak_frame_rate'] = max(self.profile_data['peak_frame_rate'], fps)

        self.last_composite_time = current_time

    def _on_pixel_write(self, x: int, y: int, value: int, layer: int):
        """Called when a pixel is written"""
        self.profile_data['pixel_writes'] += 1
        self.profile_data['layer_usage'][layer] += 1
        self.profile_data['memory_bandwidth'] += 1  # 1 byte per pixel

    def finalize_profile(self):
        """Finalize profiling data and calculate statistics"""
        session_duration = time.time() - self.profile_data['session_start']

        # Calculate average frame rate
        if self.profile_data['frame_times']:
            total_frame_time = sum(ft for _, ft in self.profile_data['frame_times'])
            if total_frame_time > 0:
                self.profile_data['average_frame_rate'] = len(self.profile_data['frame_times']) / total_frame_time
        elif self.simulated_frames > 0:
            # If we have simulated frames but no real frame times, estimate based on frame interval
            self.profile_data['average_frame_rate'] = self.simulated_frames / session_duration

        # Add session metadata
        self.profile_data['session_duration'] = session_duration
        self.profile_data['cycles_per_second'] = self.profile_data['total_cycles'] / session_duration if session_duration > 0 else 0
        self.profile_data['graphics_percentage'] = (self.profile_data['graphics_instructions'] / self.profile_data['total_cycles'] * 100) if self.profile_data['total_cycles'] > 0 else 0

        # Calculate pixel throughput
        self.profile_data['pixel_throughput'] = self.profile_data['pixel_writes'] / session_duration if session_duration > 0 else 0

        # Add simulated frame info
        self.profile_data['simulated_frames'] = self.simulated_frames

    def save_profile(self):
        """Save profiling data to JSON file"""
        self.finalize_profile()

        with open(self.output_file, 'w') as f:
            json.dump(self.profile_data, f, indent=2)

        print(f"GPU profile saved to {self.output_file}")

        # Print summary
        print("\n=== GPU Profiling Summary ===")
        print(f"Total cycles: {self.profile_data['total_cycles']:,}")
        print(f"Graphics instructions: {self.profile_data['graphics_instructions']:,} ({self.profile_data['graphics_percentage']:.1f}%)")
        print(f"Pixel writes: {self.profile_data['pixel_writes']:,}")
        print(f"Composite events: {self.profile_data['composite_events']}")
        print(f"Simulated frames: {self.simulated_frames}")
        print(f"Average FPS: {self.profile_data['average_frame_rate']:.1f}")
        print(f"Peak FPS: {self.profile_data['peak_frame_rate']:.1f}")
        print(f"Pixel throughput: {self.profile_data['pixel_throughput']:.0f} pixels/sec")
        print(f"Session duration: {self.profile_data['session_duration']:.2f}s")

        if self.enable_charts:
            self._generate_charts()

    def _generate_charts(self):
        """Generate visualization charts (placeholder for future implementation)"""
        # This could use matplotlib or similar to create charts
        # For now, just note that charts would be generated here
        print("Chart generation not implemented yet - data saved for external analysis")

def run_profiled_program(program_path: str, max_cycles: int = 10000, output_file: str = "gpu_profile.json"):
    """Run a program with GPU profiling enabled"""
    # Initialize components
    mem = Memory()
    gfx = GFX()
    kbd = NovaKeyboard()
    snd = NovaSound()
    cpu = CPU(mem, gfx, kbd, snd)

    # Connect keyboard
    kbd.cpu = cpu

    # Load program
    entry_point = mem.load(program_path)
    cpu.pc = entry_point

    # Initialize profiler
    profiler = GPUProfiler(output_file=output_file)
    profiler.attach_to_emulator(cpu, gfx)

    print(f"Running {program_path} with GPU profiling...")
    print(f"Entry point: 0x{entry_point:04X}")

    # Run with profiling
    cycle = 0
    start_time = time.time()

    while cycle < max_cycles and not cpu.halted:
        cycle += 1
        try:
            cpu.step()

            if cpu.halted:
                print(f"Program halted at PC: 0x{cpu.pc:04X}")
                break

            if cycle % 1000 == 0:
                elapsed = time.time() - start_time
                print(f"Cycle {cycle:,}, PC: 0x{cpu.pc:04X}, FPS: {profiler.profile_data['average_frame_rate']:.1f}")

        except Exception as e:
            print(f"Error at cycle {cycle}, PC: 0x{cpu.pc:04X}: {e}")
            break

    # Save profile
    profiler.save_profile()

    # Cleanup
    if snd:
        snd.cleanup()

    return cpu, mem, gfx

def main():
    parser = argparse.ArgumentParser(description='Nova-16 GPU Profiler')
    parser.add_argument('program', help='Binary program file to profile')
    parser.add_argument('--cycles', type=int, default=10000, help='Maximum cycles to run')
    parser.add_argument('--output', type=str, default='gpu_profile.json', help='Output profile file')
    parser.add_argument('--no-charts', action='store_true', help='Disable chart generation')

    args = parser.parse_args()

    run_profiled_program(
        program_path=args.program,
        max_cycles=args.cycles,
        output_file=args.output
    )

if __name__ == "__main__":
    main()