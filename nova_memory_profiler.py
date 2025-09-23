#!/usr/bin/env python3
"""
Nova Memory Profiler - Performance analysis tool for Nova-16 memory system.
Tracks memory access patterns, hotspots, and usage statistics.
"""

import sys
import os
import time
import json
import argparse
from typing import Dict, List, Optional, Tuple
import numpy as np
from collections import defaultdict, Counter

sys.path.append(os.path.dirname(__file__))

from nova_cpu import CPU
from nova_memory import Memory
from nova_gfx import GFX
from nova_keyboard import NovaKeyboard
from nova_sound import NovaSound

class MemoryProfiler:
    """Memory performance profiler for Nova-16 emulator"""

    def __init__(self, output_file: str = "memory_profile.json", enable_charts: bool = True):
        self.output_file = output_file
        self.enable_charts = enable_charts

        # Profiling data structures
        self.profile_data = {
            'session_start': time.time(),
            'total_cycles': 0,
            'total_reads': 0,
            'total_writes': 0,
            'read_accesses': defaultdict(int),  # address -> count
            'write_accesses': defaultdict(int),  # address -> count
            'access_timestamps': defaultdict(list),  # address -> list of cycle numbers
            'memory_regions': {
                'zero_page': (0x0000, 0x00FF),
                'interrupt_vectors': (0x0100, 0x011F),
                'general_memory': (0x0120, 0xEFFF),
                'sprite_control': (0xF000, 0xF0FF),
                'stack_area': (0xFF00, 0xFFFF)
            },
            'region_stats': defaultdict(lambda: {'reads': 0, 'writes': 0}),
            'hotspots': [],  # Top accessed addresses
            'access_patterns': [],  # Sequential access patterns
            'memory_bandwidth': 0,  # Estimated bytes transferred
            'peak_memory_usage': 0,
            'average_access_rate': 0
        }

        # Memory regions for analysis
        self.region_names = {
            (0x0000, 0x00FF): 'Zero Page',
            (0x0100, 0x011F): 'Interrupt Vectors',
            (0x0120, 0xEFFF): 'General Memory',
            (0xF000, 0xF0FF): 'Sprite Control',
            (0xFF00, 0xFFFF): 'Stack Area'
        }

        # Hook into memory system
        self.original_memory = None
        self.profiling_enabled = False
        
        # Store original methods for restoration
        self.original_read_byte = None
        self.original_write_byte = None
        self.original_read_word = None
        self.original_write_word = None

    def enable_profiling(self, memory_system: Memory):
        """Enable memory profiling by hooking into memory operations"""
        if self.profiling_enabled:
            return

        self.original_memory = memory_system
        self.profiling_enabled = True

        # Store original methods
        self.original_read_byte = memory_system.read_byte
        self.original_write_byte = memory_system.write_byte
        self.original_read_word = memory_system.read_word
        self.original_write_word = memory_system.write_word
        self.original_write = memory_system.write

        # Monkey patch memory methods to add profiling
        original_read_byte = memory_system.read_byte
        original_write_byte = memory_system.write_byte
        original_read_word = memory_system.read_word
        original_write_word = memory_system.write_word
        original_write = memory_system.write

        def profiled_read_byte(address):
            if self.profiling_enabled:
                self._record_read(address, 1)
            return original_read_byte(address)

        def profiled_write_byte(address, value):
            if self.profiling_enabled:
                self._record_write(address, 1)
            return original_write_byte(address, value)

        def profiled_read_word(address):
            if self.profiling_enabled:
                self._record_read(address, 2)
            return original_read_word(address)

        def profiled_write_word(address, value):
            if self.profiling_enabled:
                self._record_write(address, 2)
            return original_write_word(address, value)

        def profiled_write(address, value, bytes=1):
            if self.profiling_enabled:
                self._record_write(address, bytes)
            return original_write(address, value, bytes)

        memory_system.read_byte = profiled_read_byte
        memory_system.write_byte = profiled_write_byte
        memory_system.read_word = profiled_read_word
        memory_system.write_word = profiled_write_word
        memory_system.write = profiled_write

    def disable_profiling(self):
        """Disable memory profiling and restore original methods"""
        if not self.profiling_enabled:
            return

        self.profiling_enabled = False
        
        # Restore original methods
        if self.original_memory and self.original_read_byte:
            self.original_memory.read_byte = self.original_read_byte
            self.original_memory.write_byte = self.original_write_byte
            self.original_memory.read_word = self.original_read_word
            self.original_memory.write_word = self.original_write_word
            self.original_memory.write = self.original_write

    def _record_read(self, address: int, size: int):
        """Record a memory read operation"""
        try:
            self.profile_data['total_reads'] += 1
            self.profile_data['read_accesses'][address] += 1
            self.profile_data['access_timestamps'][address].append(self.profile_data['total_cycles'])
            self.profile_data['memory_bandwidth'] += size

            # Update region stats
            region = self._get_memory_region(address)
            if region:
                self.profile_data['region_stats'][region]['reads'] += 1
        except Exception as e:
            # Don't let profiling errors crash the emulator
            if self.profiling_enabled:
                print(f"Warning: Memory profiling read error at 0x{address:04X}: {e}")

    def _record_write(self, address: int, size: int):
        """Record a memory write operation"""
        try:
            self.profile_data['total_writes'] += 1
            self.profile_data['write_accesses'][address] += 1
            self.profile_data['access_timestamps'][address].append(self.profile_data['total_cycles'])
            self.profile_data['memory_bandwidth'] += size

            # Update region stats
            region = self._get_memory_region(address)
            if region:
                self.profile_data['region_stats'][region]['writes'] += 1
        except Exception as e:
            # Don't let profiling errors crash the emulator
            if self.profiling_enabled:
                print(f"Warning: Memory profiling write error at 0x{address:04X}: {e}")

    def _get_memory_region(self, address: int) -> Optional[str]:
        """Get the memory region name for an address"""
        for (start, end), name in self.region_names.items():
            if start <= address <= end:
                return name
        return None

    def update_cycle_count(self, cycles: int):
        """Update the current cycle count for timestamping"""
        self.profile_data['total_cycles'] = cycles

    def analyze_hotspots(self, top_n: int = 20):
        """Analyze memory access hotspots"""
        # Combine read and write accesses
        total_accesses = defaultdict(int)
        for addr, count in self.profile_data['read_accesses'].items():
            total_accesses[addr] += count
        for addr, count in self.profile_data['write_accesses'].items():
            total_accesses[addr] += count

        # Get top accessed addresses
        hotspots = sorted(total_accesses.items(), key=lambda x: x[1], reverse=True)[:top_n]
        self.profile_data['hotspots'] = [
            {'address': int(addr), 'total_accesses': count,
             'reads': self.profile_data['read_accesses'][addr],
             'writes': self.profile_data['write_accesses'][addr],
             'region': self._get_memory_region(addr)}
            for addr, count in hotspots
        ]

    def analyze_access_patterns(self):
        """Analyze memory access patterns for sequential accesses"""
        patterns = []
        
        # Get all addresses that were accessed
        all_addresses = set(self.profile_data['read_accesses'].keys()) | set(self.profile_data['write_accesses'].keys())
        sorted_addresses = sorted(all_addresses)
        
        if not sorted_addresses:
            self.profile_data['access_patterns'] = patterns
            return
            
        # Look for sequential access patterns
        current_pattern = {'start': sorted_addresses[0], 'length': 1, 'accesses': 0}
        
        for i in range(1, len(sorted_addresses)):
            addr = sorted_addresses[i]
            prev_addr = sorted_addresses[i-1]
            
            # Check if this is a sequential access (within 4 bytes for potential word/dword accesses)
            if addr - prev_addr <= 4:
                current_pattern['length'] += 1
                current_pattern['accesses'] += (
                    self.profile_data['read_accesses'].get(addr, 0) + 
                    self.profile_data['write_accesses'].get(addr, 0)
                )
            else:
                # End current pattern if it's significant (more than 2 accesses)
                if current_pattern['length'] > 2 and current_pattern['accesses'] > 10:
                    patterns.append(current_pattern)
                
                # Start new pattern
                current_pattern = {'start': addr, 'length': 1, 'accesses': 
                    self.profile_data['read_accesses'].get(addr, 0) + 
                    self.profile_data['write_accesses'].get(addr, 0)}
        
        # Don't forget the last pattern
        if current_pattern['length'] > 2 and current_pattern['accesses'] > 10:
            patterns.append(current_pattern)
            
        self.profile_data['access_patterns'] = patterns

    def generate_report(self):
        """Generate comprehensive profiling report"""
        self.analyze_hotspots()
        self.analyze_access_patterns()

        # Calculate additional metrics
        total_accesses = self.profile_data['total_reads'] + self.profile_data['total_writes']
        if self.profile_data['total_cycles'] > 0:
            self.profile_data['average_access_rate'] = total_accesses / self.profile_data['total_cycles']

        # Memory usage estimation (non-zero bytes)
        if self.original_memory:
            non_zero_bytes = np.count_nonzero(self.original_memory.memory)
            self.profile_data['peak_memory_usage'] = non_zero_bytes

        # Convert defaultdicts to regular dicts for JSON serialization
        self.profile_data['read_accesses'] = {int(k): int(v) for k, v in self.profile_data['read_accesses'].items()}
        self.profile_data['write_accesses'] = {int(k): int(v) for k, v in self.profile_data['write_accesses'].items()}
        self.profile_data['access_timestamps'] = {int(k): [int(t) for t in v] for k, v in self.profile_data['access_timestamps'].items()}
        self.profile_data['region_stats'] = {k: {'reads': int(v['reads']), 'writes': int(v['writes'])} for k, v in self.profile_data['region_stats'].items()}

        return self.profile_data

    def save_report(self, filename: Optional[str] = None):
        """Save profiling report to file"""
        if not filename:
            filename = self.output_file

        try:
            report = self.generate_report()

            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, default=self._json_serializer)

            print(f"Memory profiling report saved to {filename}")
        except Exception as e:
            print(f"Error saving memory profiling report: {e}")
            # Try to save with minimal data
            try:
                minimal_report = {
                    'error': str(e),
                    'total_cycles': self.profile_data.get('total_cycles', 0),
                    'total_reads': self.profile_data.get('total_reads', 0),
                    'total_writes': self.profile_data.get('total_writes', 0)
                }
                with open(filename, 'w') as f:
                    json.dump(minimal_report, f, indent=2)
                print(f"Minimal profiling report saved to {filename}")
            except Exception as e2:
                print(f"Failed to save even minimal report: {e2}")

    def _json_serializer(self, obj):
        """Custom JSON serializer for numpy types"""
        if hasattr(obj, 'item'):
            return obj.item()  # Convert numpy types to Python types
        raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')

    def print_summary(self):
        """Print a summary of profiling results"""
        report = self.generate_report()

        print("\n=== Nova-16 Memory Profiler Summary ===")
        print(f"Total Cycles: {report['total_cycles']}")
        print(f"Total Reads: {report['total_reads']}")
        print(f"Total Writes: {report['total_writes']}")
        print(f"Memory Bandwidth: {report['memory_bandwidth']} bytes")
        print(f"Average Access Rate: {report['average_access_rate']:.2f} accesses/cycle")
        print(f"Peak Memory Usage: {report['peak_memory_usage']} bytes")

        print("\n--- Memory Region Statistics ---")
        for region, stats in report['region_stats'].items():
            total = stats['reads'] + stats['writes']
            print(f"{region}: {total} accesses ({stats['reads']}R, {stats['writes']}W)")

        print("\n--- Top Memory Hotspots ---")
        for i, hotspot in enumerate(report['hotspots'][:10]):
            addr = hotspot['address']
            region = hotspot['region']
            total = hotspot['total_accesses']
            reads = hotspot['reads']
            writes = hotspot['writes']
            print(f"{i+1}. 0x{addr:04X} ({region}): {total} accesses ({reads}R, {writes}W)")

def main():
    parser = argparse.ArgumentParser(description='Nova-16 Memory Profiler')
    parser.add_argument('program', help='Binary program file to profile')
    parser.add_argument('--cycles', type=int, default=10000, help='Maximum cycles to run')
    parser.add_argument('--output', default='memory_profile.json', help='Output file for profile data')
    parser.add_argument('--summary', action='store_true', help='Print summary after profiling')

    args = parser.parse_args()

    # Initialize profiler
    profiler = MemoryProfiler(output_file=args.output)

    # Set up Nova-16 system
    memory = Memory()
    gfx = GFX()
    keyboard = NovaKeyboard()
    sound = NovaSound()
    cpu = CPU(memory, gfx, keyboard, sound)

    # Enable memory profiling
    profiler.enable_profiling(memory)

    # Load program
    entry_point = memory.load(args.program)
    cpu.pc = entry_point

    print(f"Starting memory profiling of {args.program}...")
    print(f"Entry point: 0x{entry_point:04X}")

    # Run profiling
    cycles = 0
    try:
        while not cpu.halted and cycles < args.cycles:
            profiler.update_cycle_count(cycles)
            cpu.step()
            cycles += 1

            if cycles % 1000 == 0:
                print(f"Executed {cycles} cycles...")

    except KeyboardInterrupt:
        print("Profiling interrupted by user")

    print(f"Profiling completed after {cycles} cycles")

    # Generate and save report
    profiler.save_report()

    if args.summary:
        profiler.print_summary()

if __name__ == "__main__":
    main()