#!/usr/bin/env python3
"""
Nova Graphics Monitor - Advanced debugging tool for Nova-16 graphics programs.
Provides comprehensive real-time analysis of graphics operations, layer management,
video register changes, memory mapping, and detailed visual output tracking.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from nova_cpu import CPU
from nova_memory import Memory
from nova_gfx import GFX
from nova_keyboard import NovaKeyboard
from nova_sound import NovaSound
import argparse
import json
from typing import Dict, List, Set, Tuple, Optional
import numpy as np

class GraphicsState:
    """Tracks detailed graphics state for debugging"""
    def __init__(self):
        self.video_registers = {'VX': 0, 'VY': 0, 'VM': 0, 'VL': 0}
        self.layers_changed = set()
        self.pixels_written = []  # List of (cycle, layer, x, y, color) tuples
        self.memory_operations = []  # List of (cycle, operation, address, value) tuples
        self.sprite_operations = []  # List of sprite-related operations
        self.register_changes = []  # Track all register changes
        self.instruction_log = []  # Track graphics-related instructions
        
    def log_pixel_write(self, cycle: int, layer: int, x: int, y: int, color: int):
        """Log a pixel write operation"""
        self.pixels_written.append((cycle, layer, x, y, color))
        self.layers_changed.add(layer)
        
    def log_register_change(self, cycle: int, register: str, old_value: int, new_value: int):
        """Log a video register change"""
        if old_value != new_value:
            self.register_changes.append((cycle, register, old_value, new_value))
            self.video_registers[register] = new_value
            
    def log_memory_operation(self, cycle: int, operation: str, address: int, value: int):
        """Log memory operations in graphics regions"""
        self.memory_operations.append((cycle, operation, address, value))
        
    def log_instruction(self, cycle: int, pc: int, instruction: str):
        """Log graphics-related instructions"""
        self.instruction_log.append((cycle, pc, instruction))

class AdvancedGraphicsMonitor:
    """Advanced graphics debugging monitor with comprehensive analysis"""
    
    def __init__(self, monitor_regions=None, layer_focus=None, track_all_layers=True):
        # Monitor configuration
        self.monitor_regions = monitor_regions or [{'x': 90, 'y': 90, 'width': 20, 'height': 20, 'name': 'main'}]
        self.layer_focus = layer_focus or list(range(9))  # Monitor all layers by default
        self.track_all_layers = track_all_layers
        
        # State tracking
        self.graphics_state = GraphicsState()
        self.last_layer_states = {}
        self.last_video_registers = {'VX': 0, 'VY': 0, 'VM': 0, 'VL': 0}
        self.instruction_hooks = {
            'SWRITE', 'SREAD', 'SFILL', 'SCOPY', 'SROLX', 'SROLY', 
            'TEXT', 'CHAR', 'SPBLIT', 'SPRITE'
        }
        
        # Analysis features
        self.detect_patterns = True
        self.verbose_output = True
        self.export_data = True
        self.real_time_analysis = True
        
        # Statistics
        self.stats = {
            'total_pixel_writes': 0,
            'layers_used': set(),
            'colors_used': set(),
            'instruction_counts': {},
            'memory_regions_accessed': set(),
            'max_x': 0, 'max_y': 0, 'min_x': 255, 'min_y': 255
        }
        
    def initialize_layer_tracking(self, gfx):
        """Initialize layer state tracking"""
        # Main screen (layer 0)
        self.last_layer_states[0] = gfx.screen.copy()
        
        # Background layers 1-4
        if hasattr(gfx, 'background_layers'):
            for i in range(min(4, len(gfx.background_layers))):
                self.last_layer_states[i+1] = gfx.background_layers[i].copy()
        else:
            # Initialize empty layers if they don't exist
            for i in range(4):
                self.last_layer_states[i+1] = np.zeros((256, 256), dtype=np.uint8)
                
        # Sprite layers 5-8
        if hasattr(gfx, 'sprite_layers'):
            for i in range(min(4, len(gfx.sprite_layers))):
                self.last_layer_states[i+5] = gfx.sprite_layers[i].copy()
        else:
            # Initialize empty layers if they don't exist
            for i in range(4):
                self.last_layer_states[i+5] = np.zeros((256, 256), dtype=np.uint8)
        
        if self.verbose_output:
            print(f"Initialized layer tracking:")
            print(f"  Background layers available: {hasattr(gfx, 'background_layers') and len(gfx.background_layers) if hasattr(gfx, 'background_layers') else 0}")
            print(f"  Sprite layers available: {hasattr(gfx, 'sprite_layers') and len(gfx.sprite_layers) if hasattr(gfx, 'sprite_layers') else 0}")
            print(f"  Tracking layers: {sorted(self.last_layer_states.keys())}")
            print()
                
    def check_video_register_changes(self, cycle, gfx, cpu):
        """Check for changes in video registers"""
        current_registers = {
            'VX': getattr(gfx, 'Vregisters', [0, 0, 0])[0] if hasattr(gfx, 'Vregisters') else 0,
            'VY': getattr(gfx, 'Vregisters', [0, 0, 0])[1] if hasattr(gfx, 'Vregisters') else 0,
            'VM': getattr(gfx, 'vmode', 0),
            'VL': getattr(gfx, 'VL', 0)
        }
        
        for reg, value in current_registers.items():
            if reg in self.last_video_registers and self.last_video_registers[reg] != value:
                self.graphics_state.log_register_change(cycle, reg, self.last_video_registers[reg], value)
                if self.verbose_output:
                    print(f"[Cycle {cycle:5d}] Video Register {reg}: 0x{self.last_video_registers[reg]:02X} -> 0x{value:02X}")
                    
        self.last_video_registers = current_registers.copy()
        
    def analyze_layer_changes(self, cycle, gfx):
        """Detect and analyze changes in all graphics layers"""
        changes_detected = []
        
        # Check main screen (layer 0)
        if 0 in self.layer_focus:
            current_screen = gfx.screen.copy()
            if 0 in self.last_layer_states:
                diff = current_screen != self.last_layer_states[0]
                if np.any(diff):
                    changes = self._extract_pixel_changes(0, self.last_layer_states[0], current_screen, diff)
                    changes_detected.extend([(0,) + change for change in changes])
                    for x, y, old_color, new_color in changes:
                        self.graphics_state.log_pixel_write(cycle, 0, x, y, new_color)
                        self._update_stats(x, y, new_color, 0)
            self.last_layer_states[0] = current_screen
            
        # Check background layers 1-4
        if hasattr(gfx, 'background_layers') and len(gfx.background_layers) > 0:
            for i, layer in enumerate(gfx.background_layers):
                layer_num = i + 1
                if layer_num in self.layer_focus and layer is not None:
                    current_layer = layer.copy()
                    if layer_num in self.last_layer_states:
                        diff = current_layer != self.last_layer_states[layer_num]
                        if np.any(diff):
                            changes = self._extract_pixel_changes(layer_num, self.last_layer_states[layer_num], current_layer, diff)
                            changes_detected.extend([(layer_num,) + change for change in changes])
                            for x, y, old_color, new_color in changes:
                                self.graphics_state.log_pixel_write(cycle, layer_num, x, y, new_color)
                                self._update_stats(x, y, new_color, layer_num)
                                if self.verbose_output:
                                    print(f"[Cycle {cycle:5d}] Layer {layer_num} pixel change at ({x},{y}): 0x{old_color:02X} -> 0x{new_color:02X}")
                    self.last_layer_states[layer_num] = current_layer
                    
        # Check sprite layers 5-8
        if hasattr(gfx, 'sprite_layers') and len(gfx.sprite_layers) > 0:
            for i, layer in enumerate(gfx.sprite_layers):
                layer_num = i + 5
                if layer_num in self.layer_focus and layer is not None:
                    current_layer = layer.copy()
                    if layer_num in self.last_layer_states:
                        diff = current_layer != self.last_layer_states[layer_num]
                        if np.any(diff):
                            changes = self._extract_pixel_changes(layer_num, self.last_layer_states[layer_num], current_layer, diff)
                            changes_detected.extend([(layer_num,) + change for change in changes])
                            for x, y, old_color, new_color in changes:
                                self.graphics_state.log_pixel_write(cycle, layer_num, x, y, new_color)
                                self._update_stats(x, y, new_color, layer_num)
                                if self.verbose_output:
                                    print(f"[Cycle {cycle:5d}] Layer {layer_num} pixel change at ({x},{y}): 0x{old_color:02X} -> 0x{new_color:02X}")
                    self.last_layer_states[layer_num] = current_layer
                    
        return changes_detected
        
    def _extract_pixel_changes(self, layer, old_array, new_array, diff_mask):
        """Extract individual pixel changes from difference mask"""
        changes = []
        y_coords, x_coords = np.where(diff_mask)
        for y, x in zip(y_coords, x_coords):
            old_color = old_array[y, x] if old_array is not None else 0
            new_color = new_array[y, x]
            changes.append((x, y, old_color, new_color))
        return changes
        
    def _update_stats(self, x, y, color, layer=None):
        """Update statistics"""
        self.stats['total_pixel_writes'] += 1
        self.stats['colors_used'].add(color)
        if layer is not None:
            self.stats['layers_used'].add(layer)
        self.stats['max_x'] = max(self.stats['max_x'], x)
        self.stats['max_y'] = max(self.stats['max_y'], y)
        self.stats['min_x'] = min(self.stats['min_x'], x)
        self.stats['min_y'] = min(self.stats['min_y'], y)
        
    def monitor_instruction(self, cycle, cpu, instruction_name):
        """Monitor graphics-related instructions"""
        if instruction_name in self.instruction_hooks:
            pc = cpu.pc
            self.graphics_state.log_instruction(cycle, pc, instruction_name)
            self.stats['instruction_counts'][instruction_name] = self.stats['instruction_counts'].get(instruction_name, 0) + 1
            
            if self.verbose_output:
                print(f"[Cycle {cycle:5d}] Graphics Instruction: {instruction_name} at PC: 0x{pc:04X}")
                
    def check_monitor_regions(self, cycle):
        """Check specific monitor regions for changes"""
        region_reports = []
        
        for region in self.monitor_regions:
            x, y, width, height, name = region['x'], region['y'], region['width'], region['height'], region['name']
            
            # Extract current region state from main screen
            if 0 in self.last_layer_states:
                current_region = self.last_layer_states[0][y:y+height, x:x+width].copy()
                region_report = self._analyze_region(cycle, name, x, y, current_region)
                if region_report:
                    region_reports.append(region_report)
                    
        return region_reports
        
    def _analyze_region(self, cycle, name, start_x, start_y, region_data):
        """Analyze a specific region for patterns and changes"""
        non_zero_pixels = np.count_nonzero(region_data)
        unique_colors = len(np.unique(region_data))
        
        if non_zero_pixels > 0:
            return {
                'cycle': cycle,
                'name': name,
                'position': (start_x, start_y),
                'size': region_data.shape,
                'non_zero_pixels': non_zero_pixels,
                'unique_colors': unique_colors,
                'color_distribution': {int(color): int(count) for color, count in zip(*np.unique(region_data, return_counts=True))},
                'region_data': region_data.tolist()
            }
        return None
        
    def generate_comprehensive_report(self, cycle, final=False):
        """Generate comprehensive analysis report"""
        report = {
            'cycle': cycle,
            'timestamp': f"{'Final' if final else 'Interim'} Report",
            'statistics': dict(self.stats),
            'video_registers': self.last_video_registers.copy(),
            'layers_changed': list(self.graphics_state.layers_changed),
            'recent_pixels': self.graphics_state.pixels_written[-20:] if len(self.graphics_state.pixels_written) > 20 else self.graphics_state.pixels_written,
            'recent_register_changes': self.graphics_state.register_changes[-10:] if len(self.graphics_state.register_changes) > 10 else self.graphics_state.register_changes,
            'instruction_summary': dict(self.stats['instruction_counts'])
        }
        
        # Convert sets to lists for JSON serialization and handle numpy types
        report['statistics']['layers_used'] = [int(x) for x in report['statistics']['layers_used']]
        report['statistics']['colors_used'] = [int(x) for x in report['statistics']['colors_used']]
        report['statistics']['memory_regions_accessed'] = list(report['statistics']['memory_regions_accessed'])
        
        return report
        
    def print_summary_report(self, cycle, changes_detected):
        """Print a formatted summary of current state"""
        if changes_detected and self.verbose_output:
            print(f"\n=== Graphics Analysis - Cycle {cycle} ===")
            
            # Group changes by layer
            layer_changes = {}
            for change in changes_detected:
                if len(change) >= 5:  # (layer, x, y, old_color, new_color)
                    layer = change[0] if isinstance(change[0], int) else 0
                    if layer not in layer_changes:
                        layer_changes[layer] = []
                    layer_changes[layer].append(change[1:])  # Remove layer from tuple
                        
            for layer, layer_change_list in layer_changes.items():
                layer_name = self._get_layer_name(layer)
                print(f"  {layer_name}:")
                for change in layer_change_list[:10]:  # Limit to 10 changes per layer
                    if len(change) >= 4:
                        x, y, old_color, new_color = change[:4]
                        print(f"    Pixel ({x:3d},{y:3d}): 0x{old_color:02X} -> 0x{new_color:02X}")
                if len(layer_change_list) > 10:
                    print(f"    ... and {len(layer_change_list) - 10} more changes")
                    
            # Show video register state
            print(f"  Video Registers: VX=0x{self.last_video_registers['VX']:02X}, VY=0x{self.last_video_registers['VY']:02X}, VM={self.last_video_registers['VM']}, VL={self.last_video_registers['VL']}")
            print()
            
    def _get_layer_name(self, layer_num):
        """Get descriptive name for layer"""
        if layer_num == 0:
            return "Main Screen (Layer 0)"
        elif 1 <= layer_num <= 4:
            return f"Background Layer {layer_num}"
        elif 5 <= layer_num <= 8:
            return f"Sprite Layer {layer_num}"
        else:
            return f"Unknown Layer {layer_num}"
    
    def _decode_graphics_instruction(self, opcode):
        """Decode graphics-related opcodes to instruction names"""
        graphics_opcodes = {
            # Screen access
            0x4E: "SBLEND",    # SBLEND reg
            0x4F: "SBLEND",    # SBLEND imm
            0x50: "SREAD",     # SREAD
            0x51: "SWRITE",    # SWRITE reg
            0x52: "SWRITE",    # SWRITE imm
            
            # Screen transformations
            0x53: "SROLX",     # SROLX reg  
            0x54: "SROLX",     # SROLX imm
            0x55: "SROLY",     # SROLY reg
            0x56: "SROLY",     # SROLY imm
            0x57: "SROTL",     # SROTL reg
            0x58: "SROTL",     # SROTL imm
            0x59: "SROTR",     # SROTR reg
            0x5A: "SROTR",     # SROTR imm
            0x5B: "SSHFTX",    # SSHFTX reg
            0x5C: "SSHFTX",    # SSHFTX imm
            0x5D: "SSHFTY",    # SSHFTY reg
            0x5E: "SSHFTY",    # SSHFTY imm
            0x5F: "SFLIPX",    # SFLIPX
            0x60: "SFLIPY",    # SFLIPY
            
            # Screen operations
            0x61: "SBLIT",     # SBLIT
            0x7F: "SFILL",     # SFILL reg
            0x80: "SFILL",     # SFILL imm
            
            # Text/Character operations
            0x6A: "CHAR",      # CHAR reg imm8
            0x6B: "TEXT",      # TEXT reg imm8
            0x6C: "TEXT",      # TEXT imm16 imm8
            0x6D: "CHAR",      # CHAR reg reg
            0x6E: "TEXT",      # TEXT reg reg
            0x6F: "TEXT",      # TEXT imm16 reg
            
            # Sprite operations
            0x94: "SPBLIT",    # SPBLIT reg
            0x95: "SPBLIT",    # SPBLIT imm
            0x96: "SPBLITALL", # SPBLITALL
            
            # Sound operations (for completeness)
            0x97: "SPLAY",     # SPLAY reg
            0x98: "SPLAY",     # SPLAY imm
            0x99: "SSTOP",     # SSTOP reg
            0x9A: "SSTOP",     # SSTOP imm
            0x9B: "STRIG",     # STRIG reg
            0x9C: "STRIG",     # STRIG imm
        }
        return graphics_opcodes.get(opcode, None)
            
    def export_debug_data(self, filename_base):
        """Export all collected debug data"""
        if not self.export_data:
            return
            
        # Export graphics state
        graphics_data = {
            'pixels_written': self.graphics_state.pixels_written,
            'register_changes': self.graphics_state.register_changes,
            'memory_operations': self.graphics_state.memory_operations,
            'instruction_log': self.graphics_state.instruction_log,
            'statistics': dict(self.stats)
        }
        
        # Convert sets to lists for JSON serialization and handle numpy types
        graphics_data['statistics']['layers_used'] = [int(x) for x in graphics_data['statistics']['layers_used']]
        graphics_data['statistics']['colors_used'] = [int(x) for x in graphics_data['statistics']['colors_used']]
        graphics_data['statistics']['memory_regions_accessed'] = list(graphics_data['statistics']['memory_regions_accessed'])
        
        try:
            with open(f"{filename_base}_graphics_debug.json", 'w') as f:
                json.dump(graphics_data, f, indent=2)
            print(f"Graphics debug data exported to {filename_base}_graphics_debug.json")
        except Exception as e:
            print(f"Failed to export debug data: {e}")

def run_graphics_monitor(program_path, monitor_config=None, max_cycles=10000, export_prefix=None):
    """Run Nova with advanced graphics monitoring and analysis"""
    
    # Configure monitor
    if monitor_config is None:
        monitor_config = {
            'regions': [{'x': 90, 'y': 90, 'width': 20, 'height': 20, 'name': 'main'}],
            'layers': list(range(9)),  # Monitor all layers
            'verbose': True,
            'export': True,
            'check_interval': 50  # Check every 50 cycles instead of 100
        }
    
    # Initialize components
    memory = Memory()
    gfx = GFX()
    keyboard = NovaKeyboard()
    sound = NovaSound()
    cpu = CPU(memory, gfx, keyboard, sound)
    
    # Initialize advanced monitor
    monitor = AdvancedGraphicsMonitor(
        monitor_regions=monitor_config['regions'],
        layer_focus=monitor_config['layers'],
        track_all_layers=True
    )
    monitor.verbose_output = monitor_config.get('verbose', True)
    monitor.export_data = monitor_config.get('export', True)
    
    print("=" * 80)
    print("Nova-16 Advanced Graphics Monitor")
    print("=" * 80)
    print(f"Program: {program_path}")
    
    # Display monitor configuration
    print(f"Monitor Regions:")
    for region in monitor_config['regions']:
        print(f"  - {region['name']}: {region['width']}x{region['height']} at ({region['x']}, {region['y']})")
    print(f"Tracking Layers: {monitor_config['layers']}")
    print(f"Max Cycles: {max_cycles}")
    print(f"Check Interval: {monitor_config['check_interval']} cycles")
    print("=" * 80)
    
    try:
        # Load program
        entry_point = memory.load(program_path)
        cpu.pc = entry_point
        
        print(f"Entry Point: 0x{entry_point:04X}")
        print(f"Initial PC: 0x{cpu.pc:04X}")
        print()
        
        # Initialize layer tracking
        monitor.initialize_layer_tracking(gfx)
        
        cycles = 0
        last_report_cycle = 0
        report_interval = monitor_config['check_interval']
        
        # Main execution loop with enhanced monitoring
        while cycles < max_cycles and not cpu.halted:
            try:
                # Store pre-execution state for detailed tracking
                pre_pc = cpu.pc
                pre_instruction = None
                
                # Simple instruction detection for graphics operations
                try:
                    # Read the opcode at current PC to identify graphics instructions
                    if hasattr(cpu, 'memory') and cpu.pc < len(cpu.memory.memory):
                        opcode = cpu.memory.memory[cpu.pc]
                        pre_instruction = monitor._decode_graphics_instruction(opcode)
                except:
                    pass  # Fall back to generic monitoring
                
                # Execute one instruction
                cpu.step()
                cycles += 1
                
                # Monitor graphics-related instructions
                if pre_instruction:
                    monitor.monitor_instruction(cycles, cpu, pre_instruction)
                
                # Check for video register changes every cycle (lightweight)
                monitor.check_video_register_changes(cycles, gfx, cpu)
                
                # Perform detailed analysis at intervals
                if cycles % report_interval == 0 or cycles - last_report_cycle >= report_interval:
                    # Analyze layer changes
                    changes_detected = monitor.analyze_layer_changes(cycles, gfx)
                    
                    if changes_detected:
                        monitor.print_summary_report(cycles, changes_detected)
                        
                    # Check monitor regions
                    region_reports = monitor.check_monitor_regions(cycles)
                    if region_reports and monitor.verbose_output:
                        print(f"=== Region Analysis - Cycle {cycles} ===")
                        for report in region_reports:
                            print(f"  Region '{report['name']}': {report['non_zero_pixels']} pixels, {report['unique_colors']} colors")
                            if report['non_zero_pixels'] > 0:
                                color_summary = {f"0x{color:02X}": count for color, count in report['color_distribution'].items() if color != 0}
                                if color_summary:
                                    print(f"    Colors: {color_summary}")
                        print()
                        
                    last_report_cycle = cycles
                
                # Progress indicator for long runs
                if cycles % 1000 == 0:
                    progress = (cycles / max_cycles) * 100
                    print(f"Progress: {cycles}/{max_cycles} cycles ({progress:.1f}%), PC: 0x{cpu.pc:04X}")
                    
            except Exception as e:
                print(f"ERROR at cycle {cycles}, PC: 0x{cpu.pc:04X}: {e}")
                print(f"Last instruction: {pre_instruction}")
                if monitor.verbose_output:
                    # Print register state for debugging
                    print(f"Registers: R0-R9={[f'0x{r:02X}' for r in cpu.Rregisters[:10]]}")
                    print(f"           P0-P9={[f'0x{r:04X}' for r in cpu.Pregisters[:10]]}")
                break
        
        # Final analysis
        print("\n" + "=" * 80)
        print("FINAL ANALYSIS")
        print("=" * 80)
        
        # Generate final comprehensive report
        final_report = monitor.generate_comprehensive_report(cycles, final=True)
        
        print(f"Execution completed after {cycles} cycles")
        print(f"Final PC: 0x{cpu.pc:04X}")
        print(f"CPU Halted: {cpu.halted}")
        print()
        
        # Statistics summary
        stats = final_report['statistics']
        print("Graphics Statistics:")
        print(f"  Total pixel writes: {stats['total_pixel_writes']}")
        print(f"  Layers used: {sorted([int(x) for x in stats['layers_used']])}")
        colors_list = sorted([int(x) for x in stats['colors_used']])
        print(f"  Colors used: {colors_list} ({len(stats['colors_used'])} unique)")
        print(f"  Drawing bounds: ({stats['min_x']}, {stats['min_y']}) to ({stats['max_x']}, {stats['max_y']})")
        
        if stats['instruction_counts']:
            print(f"  Graphics instructions:")
            for instr, count in sorted(stats['instruction_counts'].items()):
                print(f"    {instr}: {count}")
        
        # Video register final state
        print(f"\nFinal Video Registers:")
        for reg, value in final_report['video_registers'].items():
            print(f"  {reg}: 0x{value:02X}")
        
        # CPU register final state
        print(f"\nFinal CPU Registers:")
        print(f"  R0-R9: {[f'0x{r:02X}' for r in cpu.Rregisters[:10]]}")
        print(f"  P0-P9: {[f'0x{r:04X}' for r in cpu.Pregisters[:10]]}")
        
        # Final region analysis
        print(f"\nFinal Monitor Region Analysis:")
        final_regions = monitor.check_monitor_regions(cycles)
        for report in final_regions:
            print(f"  {report['name']}: {report['non_zero_pixels']} pixels in {report['size']} region")
            if report['non_zero_pixels'] > 0:
                colors = [f"0x{c:02X}({cnt})" for c, cnt in report['color_distribution'].items() if c != 0]
                print(f"    Colors: {', '.join(colors)}")
        
        # Screen statistics - check all layers
        layer_pixel_counts = {}
        total_screen_pixels = 0
        
        # Count pixels in main screen (layer 0)
        main_screen_pixels = np.count_nonzero(gfx.screen)
        layer_pixel_counts[0] = main_screen_pixels
        total_screen_pixels += main_screen_pixels
        
        # Count pixels in background layers (1-4)
        if hasattr(gfx, 'background_layers'):
            for i, layer in enumerate(gfx.background_layers):
                if layer is not None:
                    layer_pixels = np.count_nonzero(layer)
                    layer_pixel_counts[i+1] = layer_pixels
                    total_screen_pixels += layer_pixels
        
        # Count pixels in sprite layers (5-8)
        if hasattr(gfx, 'sprite_layers'):
            for i, layer in enumerate(gfx.sprite_layers):
                if layer is not None:
                    layer_pixels = np.count_nonzero(layer)
                    layer_pixel_counts[i+5] = layer_pixels
                    total_screen_pixels += layer_pixels
        
        print(f"\nLayer Pixel Counts:")
        for layer_num in sorted(layer_pixel_counts.keys()):
            if layer_pixel_counts[layer_num] > 0:
                layer_name = monitor._get_layer_name(layer_num)
                print(f"  {layer_name}: {layer_pixel_counts[layer_num]} pixels")
        
        print(f"\nTotal non-black pixels across all layers: {total_screen_pixels}")
        
        # Also show the traditional main screen count for reference
        print(f"Main screen (layer 0) pixels only: {main_screen_pixels}")
        
        # Export debug data
        if export_prefix and monitor.export_data:
            monitor.export_debug_data(export_prefix)
            
            # Export final report
            try:
                with open(f"{export_prefix}_final_report.json", 'w') as f:
                    json.dump(final_report, f, indent=2)
                print(f"Final report exported to {export_prefix}_final_report.json")
            except Exception as e:
                print(f"Failed to export final report: {e}")
        
        return True
        
    except Exception as e:
        print(f"FATAL ERROR: Failed to run graphics monitor: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description='Nova-16 Advanced Graphics Monitor', 
                                   formatter_class=argparse.RawDescriptionHelpFormatter,
                                   epilog="""
Examples:
  # Basic monitoring with default settings
  python nova_graphics_monitor.py program.bin
  
  # Monitor specific regions with custom settings
  python nova_graphics_monitor.py program.bin --regions "main:90,90,20,20" "ui:200,50,50,30"
  
  # Focus on specific layers
  python nova_graphics_monitor.py program.bin --layers 0 1 5
  
  # Quiet mode with data export
  python nova_graphics_monitor.py program.bin --quiet --export debug_output
  
  # Extended analysis for long-running programs
  python nova_graphics_monitor.py program.bin --cycles 50000 --interval 100
""")
    
    parser.add_argument('program', help='Binary program to run (.bin file)')
    parser.add_argument('--regions', nargs='+', default=['main:90,90,20,20'], 
                       help='Monitor regions as name:x,y,width,height (default: main:90,90,20,20)')
    parser.add_argument('--layers', nargs='+', type=int, default=list(range(9)),
                       help='Layer numbers to monitor (0-8, default: all)')
    parser.add_argument('--cycles', type=int, default=10000, 
                       help='Maximum cycles to run (default: 10000)')
    parser.add_argument('--interval', type=int, default=50,
                       help='Analysis interval in cycles (default: 50)')
    parser.add_argument('--quiet', action='store_true',
                       help='Reduce verbose output')
    parser.add_argument('--export', type=str, default=None,
                       help='Export debug data with given prefix')
    parser.add_argument('--config', type=str, default=None,
                       help='Load configuration from JSON file')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.program):
        print(f"Error: Program file '{args.program}' not found")
        sys.exit(1)
    
    # Parse monitor configuration
    monitor_config = {
        'verbose': not args.quiet,
        'export': args.export is not None,
        'check_interval': args.interval,
        'layers': args.layers,
        'regions': []
    }
    
    # Load from config file if specified
    if args.config and os.path.exists(args.config):
        try:
            with open(args.config, 'r') as f:
                file_config = json.load(f)
                monitor_config.update(file_config)
            print(f"Configuration loaded from {args.config}")
        except Exception as e:
            print(f"Warning: Failed to load config file {args.config}: {e}")
    
    # Parse region specifications
    for region_spec in args.regions:
        try:
            name, coords = region_spec.split(':', 1)
            x, y, width, height = map(int, coords.split(','))
            monitor_config['regions'].append({
                'name': name,
                'x': x, 'y': y, 
                'width': width, 'height': height
            })
        except ValueError:
            print(f"Warning: Invalid region specification '{region_spec}', skipping")
    
    # Ensure at least one region
    if not monitor_config['regions']:
        monitor_config['regions'] = [{'name': 'default', 'x': 90, 'y': 90, 'width': 20, 'height': 20}]
    
    # Validate layers
    monitor_config['layers'] = [l for l in monitor_config['layers'] if 0 <= l <= 8]
    if not monitor_config['layers']:
        monitor_config['layers'] = [0]  # At least monitor main screen
    
    # Run the monitor
    export_prefix = args.export if args.export else None
    success = run_graphics_monitor(args.program, monitor_config, args.cycles, export_prefix)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
