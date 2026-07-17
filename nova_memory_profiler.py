#!/usr/bin/env python3
"""
Nova-16 Memory Profiler — performance analysis tool for the memory subsystem.

Tracks memory access patterns, hotspots, usage statistics across regions:
  - Zero Page (0x0000-0x00FF)
  - Interrupt Vectors (0x0100-0x011F)
  - General Memory (0x0120-0xEFFF)
  - Sprite Control Block (0xF000-0xF0FF)
  - Stack Area (0xFF00-0xFFFF)

Uses the current event-bus / interrupt-controller / timer architecture.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

import nova_cpu as cpu_mod
from nova.memory import Memory
import nova_gfx as gpu_mod
import nova_sound as sound_mod
import nova_keyboard as kbd_mod
from nova.bus import EventBus, InterruptController
from nova.peripherals.timer import Timer


class MemoryProfiler:
    """Standalone memory-performance profiler for the Nova-16 emulator.

    Hooks into the Memory object via monkey-patching so that every
    read/write is recorded without requiring changes to the core
    memory implementation.
    """

    # Canonical region definitions (inclusive ranges)
    REGIONS: Dict[str, Tuple[int, int]] = {
        "Zero Page":         (0x0000, 0x00FF),
        "Interrupt Vectors": (0x0100, 0x011F),
        "General Memory":    (0x0120, 0xEFFF),
        "Sprite Control":    (0xF000, 0xF0FF),
        "Reserved High":     (0xF100, 0xFEFF),
        "Stack Area":        (0xFF00, 0xFFFF),
    }

    def __init__(self, output_file: str = "memory_profile.json") -> None:
        self.output_file = output_file

        # ── profiling data ──────────────────────────────────────────
        self.profile_data: Dict[str, Any] = {
            "session_start": time.time(),
            "total_cycles": 0,
            "total_reads": 0,
            "total_writes": 0,
            "read_accesses": defaultdict(int),
            "write_accesses": defaultdict(int),
            "access_timestamps": defaultdict(list),
            "region_stats": defaultdict(lambda: {"reads": 0, "writes": 0}),
            "hotspots": [],
            "access_patterns": [],
            "memory_bandwidth": 0,
            "peak_memory_usage": 0,
            "average_access_rate": 0.0,
        }

        # ── hook tracking ───────────────────────────────────────────
        self.profiling_enabled = False
        self._original_memory: Optional[Memory] = None
        self._original_read_byte = None
        self._original_write_byte = None
        self._original_read_word = None
        self._original_write_word = None
        self._original_write = None
        # Fast-path hooks (used by CPU execution hot paths)
        self._original_read_byte_fast = None
        self._original_write_byte_fast = None
        self._original_read_word_fast = None
        self._original_write_word_fast = None

    # ------------------------------------------------------------------
    # Hook management
    # ------------------------------------------------------------------

    def enable_profiling(self, memory_system: Memory) -> None:
        """Monkey-patch a Memory instance to collect access metrics.

        Hooks both the public methods AND the fast-path ``*_fast``
        variants that the CPU uses during normal execution.
        """
        if self.profiling_enabled:
            return

        self._original_memory = memory_system
        self.profiling_enabled = True

        # Save originals (public API)
        self._original_read_byte = memory_system.read_byte
        self._original_write_byte = memory_system.write_byte
        self._original_read_word = memory_system.read_word
        self._original_write_word = memory_system.write_word
        self._original_write = memory_system.write

        # Save originals (fast-path — used by CPU execution)
        self._original_read_byte_fast = memory_system.read_byte_fast
        self._original_write_byte_fast = memory_system.write_byte_fast
        self._original_read_word_fast = memory_system.read_word_fast
        self._original_write_word_fast = memory_system.write_word_fast

        orig_rb = self._original_read_byte
        orig_wb = self._original_write_byte
        orig_rw = self._original_read_word
        orig_ww = self._original_write_word
        orig_w = self._original_write

        orig_rbf = self._original_read_byte_fast
        orig_wbf = self._original_write_byte_fast
        orig_rwf = self._original_read_word_fast
        orig_wwf = self._original_write_word_fast

        def _rb(addr: int) -> int:
            self._record_read(addr, 1)
            return orig_rb(addr)

        def _wb(addr: int, value: int) -> None:
            self._record_write(addr, 1)
            return orig_wb(addr, value)

        def _rw(addr: int) -> int:
            self._record_read(addr, 2)
            return orig_rw(addr)

        def _ww(addr: int, value: int) -> None:
            self._record_write(addr, 2)
            return orig_ww(addr, value)

        def _w(addr: int, value: int, size: int = 1) -> None:
            self._record_write(addr, size)
            return orig_w(addr, value, size)

        # Fast-path wrappers
        def _rbf(addr: int) -> int:
            self._record_read(addr, 1)
            return orig_rbf(addr)

        def _wbf(addr: int, value: int) -> None:
            self._record_write(addr, 1)
            return orig_wbf(addr, value)

        def _rwf(addr: int) -> int:
            self._record_read(addr, 2)
            return orig_rwf(addr)

        def _wwf(addr: int, value: int) -> None:
            self._record_write(addr, 2)
            return orig_wwf(addr, value)

        memory_system.read_byte = _rb
        memory_system.write_byte = _wb
        memory_system.read_word = _rw
        memory_system.write_word = _ww
        memory_system.write = _w

        memory_system.read_byte_fast = _rbf
        memory_system.write_byte_fast = _wbf
        memory_system.read_word_fast = _rwf
        memory_system.write_word_fast = _wwf

    def disable_profiling(self) -> None:
        """Restore the original Memory methods (including fast-path)."""
        if not self.profiling_enabled or self._original_memory is None:
            return
        self.profiling_enabled = False

        m = self._original_memory
        if self._original_read_byte:
            m.read_byte = self._original_read_byte
        if self._original_write_byte:
            m.write_byte = self._original_write_byte
        if self._original_read_word:
            m.read_word = self._original_read_word
        if self._original_write_word:
            m.write_word = self._original_write_word
        if self._original_write:
            m.write = self._original_write
        if self._original_read_byte_fast:
            m.read_byte_fast = self._original_read_byte_fast
        if self._original_write_byte_fast:
            m.write_byte_fast = self._original_write_byte_fast
        if self._original_read_word_fast:
            m.read_word_fast = self._original_read_word_fast
        if self._original_write_word_fast:
            m.write_word_fast = self._original_write_word_fast

    # ------------------------------------------------------------------
    # Recording helpers
    # ------------------------------------------------------------------

    def _record_read(self, address: int, size: int) -> None:
        try:
            self.profile_data["total_reads"] += 1
            self.profile_data["read_accesses"][address] += 1
            self.profile_data["access_timestamps"][address].append(
                self.profile_data["total_cycles"]
            )
            self.profile_data["memory_bandwidth"] += size

            region = self._region_name(address)
            if region:
                self.profile_data["region_stats"][region]["reads"] += 1
        except Exception:
            pass  # profiling must never crash the emulator

    def _record_write(self, address: int, size: int) -> None:
        try:
            self.profile_data["total_writes"] += 1
            self.profile_data["write_accesses"][address] += 1
            self.profile_data["access_timestamps"][address].append(
                self.profile_data["total_cycles"]
            )
            self.profile_data["memory_bandwidth"] += size

            region = self._region_name(address)
            if region:
                self.profile_data["region_stats"][region]["writes"] += 1
        except Exception:
            pass

    @staticmethod
    def _region_name(address: int) -> Optional[str]:
        for name, (lo, hi) in MemoryProfiler.REGIONS.items():
            if lo <= address <= hi:
                return name
        return None

    # ------------------------------------------------------------------
    # Cycle tracking
    # ------------------------------------------------------------------

    def update_cycle_count(self, cycles: int) -> None:
        """Advance the profiler's cycle counter (called by the runner)."""
        self.profile_data["total_cycles"] = cycles

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def analyze_hotspots(self, top_n: int = 20) -> None:
        """Identify the most-accessed memory addresses."""
        combined = defaultdict(int)
        for addr, cnt in self.profile_data["read_accesses"].items():
            combined[addr] += cnt
        for addr, cnt in self.profile_data["write_accesses"].items():
            combined[addr] += cnt

        sorted_hot = sorted(combined.items(), key=lambda kv: kv[1], reverse=True)
        self.profile_data["hotspots"] = [
            {
                "address": int(addr),
                "total_accesses": cnt,
                "reads": self.profile_data["read_accesses"][addr],
                "writes": self.profile_data["write_accesses"][addr],
                "region": self._region_name(addr),
            }
            for addr, cnt in sorted_hot[:top_n]
        ]

    def analyze_access_patterns(self) -> None:
        """Detect sequential-access runs in the address space."""
        patterns: List[Dict[str, Any]] = []
        all_addrs = (
            set(self.profile_data["read_accesses"].keys())
            | set(self.profile_data["write_accesses"].keys())
        )
        sorted_addrs = sorted(all_addrs)

        if not sorted_addrs:
            self.profile_data["access_patterns"] = patterns
            return

        current = {
            "start": sorted_addrs[0],
            "length": 1,
            "accesses": (
                self.profile_data["read_accesses"].get(sorted_addrs[0], 0)
                + self.profile_data["write_accesses"].get(sorted_addrs[0], 0)
            ),
        }

        for i in range(1, len(sorted_addrs)):
            a, prev = sorted_addrs[i], sorted_addrs[i - 1]
            if a - prev <= 4:  # tolerate word/dword gaps
                current["length"] += 1
                current["accesses"] += (
                    self.profile_data["read_accesses"].get(a, 0)
                    + self.profile_data["write_accesses"].get(a, 0)
                )
            else:
                if current["length"] > 2 and current["accesses"] > 10:
                    patterns.append(current)
                current = {
                    "start": a,
                    "length": 1,
                    "accesses": (
                        self.profile_data["read_accesses"].get(a, 0)
                        + self.profile_data["write_accesses"].get(a, 0)
                    ),
                }

        if current["length"] > 2 and current["accesses"] > 10:
            patterns.append(current)

        self.profile_data["access_patterns"] = patterns

    # ------------------------------------------------------------------
    # Report generation & output
    # ------------------------------------------------------------------

    def generate_report(self) -> Dict[str, Any]:
        """Compute derived metrics and return the full profile dict."""
        self.analyze_hotspots()
        self.analyze_access_patterns()

        total = self.profile_data["total_reads"] + self.profile_data["total_writes"]
        if self.profile_data["total_cycles"] > 0:
            self.profile_data["average_access_rate"] = (
                total / self.profile_data["total_cycles"]
            )

        if self._original_memory is not None:
            self.profile_data["peak_memory_usage"] = int(
                np.count_nonzero(self._original_memory.memory)
            )

        # Make JSON-safe
        self.profile_data["read_accesses"] = {
            int(k): int(v)
            for k, v in self.profile_data["read_accesses"].items()
        }
        self.profile_data["write_accesses"] = {
            int(k): int(v)
            for k, v in self.profile_data["write_accesses"].items()
        }
        self.profile_data["access_timestamps"] = {
            int(k): [int(t) for t in v]
            for k, v in self.profile_data["access_timestamps"].items()
        }
        self.profile_data["region_stats"] = {
            str(k): {"reads": int(v["reads"]), "writes": int(v["writes"])}
            for k, v in self.profile_data["region_stats"].items()
        }

        return self.profile_data

    def save_report(self, filename: Optional[str] = None) -> None:
        filename = filename or self.output_file
        try:
            report = self.generate_report()
            with open(filename, "w") as f:
                json.dump(report, f, indent=2, default=_json_default)
            print(f"Memory profiling report saved to {filename}")
        except Exception as exc:
            print(f"Error saving memory report: {exc}")
            # Best-effort minimal write
            try:
                minimal = {
                    "error": str(exc),
                    "total_cycles": self.profile_data.get("total_cycles", 0),
                    "total_reads": self.profile_data.get("total_reads", 0),
                    "total_writes": self.profile_data.get("total_writes", 0),
                }
                with open(filename, "w") as f:
                    json.dump(minimal, f, indent=2)
            except Exception:
                pass

    def print_summary(self) -> None:
        r = self.generate_report()
        print("\n=== Nova-16 Memory Profiler Summary ===")
        print(f"Total Cycles:    {r['total_cycles']:,}")
        print(f"Total Reads:     {r['total_reads']:,}")
        print(f"Total Writes:    {r['total_writes']:,}")
        print(f"Memory BW:       {r['memory_bandwidth']:,} bytes")
        print(f"Access Rate:     {r['average_access_rate']:.2f} / cycle")
        print(f"Peak Usage:      {r['peak_memory_usage']:,} bytes")
        print()
        print("--- Region Statistics ---")
        for region, stats in r["region_stats"].items():
            total = stats["reads"] + stats["writes"]
            print(f"  {region}: {total:,} accesses  ({stats['reads']}R / {stats['writes']}W)")
        print()
        print("--- Top Hotspots ---")
        for i, hs in enumerate(r["hotspots"][:10]):
            print(
                f"  {i+1}. 0x{hs['address']:04X}  ({hs['region']}): "
                f"{hs['total_accesses']:,}  ({hs['reads']}R / {hs['writes']}W)"
            )


def _json_default(obj: Any) -> Any:
    if hasattr(obj, "item"):
        return obj.item()
    raise TypeError(f"Not JSON serializable: {type(obj).__name__}")


# ----------------------------------------------------------------------
# Runner & CLI
# ----------------------------------------------------------------------

def run_memory_profiler(
    program_path: str,
    max_cycles: int = 10000,
    output_file: str = "memory_profile.json",
    print_summary: bool = False,
) -> None:
    """Run a program under the memory profiler."""

    # ── System init (modern architecture) ────────────────────────────
    bus = EventBus()
    mem = Memory(bus=bus)
    gfx = gpu_mod.GFX()
    kbd = kbd_mod.NovaKeyboard(bus=bus)
    snd = sound_mod.NovaSound()
    intr_ctrl = InterruptController(bus=bus, memory=mem)
    timer_dev = Timer(bus=bus, interrupt_controller=intr_ctrl)

    cpu = cpu_mod.CPU(
        mem, gfx, kbd, snd,
        bus=bus, interrupt_controller=intr_ctrl, timer_device=timer_dev,
    )
    intr_ctrl.cpu = cpu
    bus.subscribe("cpu.post_step", lambda _: intr_ctrl.check())

    # ── Load program ─────────────────────────────────────────────────
    entry = mem.load(program_path)
    cpu.pc = entry
    print(f"Loaded {program_path}, entry point: 0x{entry:04X}")

    # ── Attach profiler ──────────────────────────────────────────────
    profiler = MemoryProfiler(output_file=output_file)
    profiler.enable_profiling(mem)

    print(f"Profiling memory for up to {max_cycles:,} cycles …")

    cycles = 0
    try:
        while not cpu.halted and cycles < max_cycles:
            profiler.update_cycle_count(cycles)
            cpu.step()
            cycles += 1

            if cycles % 1000 == 0:
                print(f"  {cycles:,} cycles …")

    except KeyboardInterrupt:
        print("\nProfiling interrupted by user")
    except Exception:
        print(f"\nError at cycle {cycles}, PC=0x{cpu.pc:04X}")
        raise

    print(f"\nProfiling completed after {cycles:,} cycles")

    profiler.save_report()
    if print_summary:
        profiler.print_summary()


def main() -> None:
    p = argparse.ArgumentParser(description="Nova-16 Memory Profiler")
    p.add_argument("program", help=".bin program to profile")
    p.add_argument("--cycles", type=int, default=10000, help="Max cycles")
    p.add_argument("--output", default="memory_profile.json", help="Output JSON")
    p.add_argument("--summary", action="store_true", help="Print summary")

    args = p.parse_args()
    if not os.path.exists(args.program):
        print(f"Error: program '{args.program}' not found")
        sys.exit(1)

    run_memory_profiler(
        program_path=args.program,
        max_cycles=args.cycles,
        output_file=args.output,
        print_summary=args.summary,
    )


if __name__ == "__main__":
    main()