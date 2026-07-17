#!/usr/bin/env python3
"""
Nova-16 CPU Profiler — unified profiling tool for the Nova-16 emulator.

Provides comprehensive CPU performance analysis:
  - Built-in CPU profiling with detailed metrics (instruction counts, opcode frequencies)
  - cProfile integration for Python-level profiling
  - Instruction set benchmarking
  - JSON/CSV export for reports
  - Visualization of profiling data (matplotlib optional)
  - Profile comparison between runs

Usage:
    python nova_profiler.py run <program.bin> [--cpu-profile] [--cycles N] [--export-json file.json]
    python nova_profiler.py benchmark [instruction_set] [--export-json file.json]
    python nova_profiler.py compare profile1.json profile2.json [--output diff.json]
    python nova_profiler.py visualize profile.json --output chart.png
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

import nova_cpu as cpu_mod
from nova.memory import Memory
import nova_gfx as gpu_mod
import nova_sound as sound_mod
import nova_keyboard as kbd_mod
from nova.bus import EventBus, InterruptController
from nova.peripherals.timer import Timer


class NovaProfiler:
    """Unified CPU profiler for the Nova-16 emulator.

    Replaces the former cpu_profiler.py (now deleted) and consolidates all
    CPU profiling functionality into a single, well-maintained tool that
    uses the current event-bus / interrupt-controller / timer architecture.
    """

    def __init__(self) -> None:
        self.cpu: Optional[cpu_mod.CPU] = None
        self.memory: Optional[Memory] = None
        self.gfx: Optional[gpu_mod.GFX] = None
        self.keyboard: Optional[kbd_mod.NovaKeyboard] = None
        self.sound: Optional[sound_mod.NovaSound] = None
        self.timer: Optional[Timer] = None
        self.bus: Optional[EventBus] = None
        self.intr_ctrl: Optional[InterruptController] = None

    # ------------------------------------------------------------------
    # System initialisation (modern event-bus architecture)
    # ------------------------------------------------------------------

    def setup_system(self, program_path: Optional[str] = None) -> None:
        """Initialise the Nova-16 system with the current architecture.

        Mirrors the initialisation sequence from ``nova_main.py`` so that
        profiling data reflects real-world execution characteristics.
        """
        bus = EventBus()
        self.bus = bus
        self.memory = Memory(bus=bus)
        self.gfx = gpu_mod.GFX()
        self.keyboard = kbd_mod.NovaKeyboard(bus=bus)
        self.sound = sound_mod.NovaSound()

        self.intr_ctrl = InterruptController(bus=bus, memory=self.memory)
        self.timer = Timer(bus=bus, interrupt_controller=self.intr_ctrl)

        self.cpu = cpu_mod.CPU(
            self.memory, self.gfx, self.keyboard, self.sound,
            bus=bus,
            interrupt_controller=self.intr_ctrl,
            timer_device=self.timer,
        )
        self.intr_ctrl.cpu = self.cpu

        # Wire the post-step interrupt check (done in nova_main.py)
        bus.subscribe("cpu.post_step", lambda _: self.intr_ctrl.check())

        if program_path:
            entry_point = self.memory.load(program_path)
            self.cpu.pc = entry_point
            _loaded = getattr(self.memory, "loaded_program", program_path)
            print(
                f"Loaded {program_path}, entry point: 0x{entry_point:04X}"
            )

    # ------------------------------------------------------------------
    # Main profiling entry points
    # ------------------------------------------------------------------

    def run_profiling(
        self,
        max_cycles: int = 10000,
        enable_cpu_profile: bool = True,
        use_cprofile: bool = False,
        export_json: Optional[str] = None,
        export_csv: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run the loaded program with profiling enabled.

        Parameters
        ----------
        max_cycles:
            Hard ceiling on the number of CPU cycles to execute.
        enable_cpu_profile:
            Enable the CPU's built-in profiling (opcode counts, memory
            access counts, method timing).
        use_cprofile:
            Additionally wrap execution with Python's ``cProfile`` so that
            the host-Python call graph is captured.
        export_json / export_csv:
            Optional file paths for exporting results.
        """
        assert self.cpu is not None, "Call setup_system() first"

        print("Starting CPU profiling…")

        if enable_cpu_profile:
            self.cpu.enable_profiling()

        pr = None
        if use_cprofile:
            import cProfile
            pr = cProfile.Profile()
            pr.enable()

        start_time = time.time()
        cycles = 0

        try:
            while not self.cpu.halted and cycles < max_cycles:
                self.cpu.step()
                cycles += 1

                if cycles % 1000 == 0:
                    print(f"  {cycles:,} cycles …")

        except KeyboardInterrupt:
            print("\nProfiling interrupted by user")

        except Exception:
            print(
                f"\nCPU error at cycle {cycles}, PC=0x{self.cpu.pc:04X}"
            )
            raise

        end_time = time.time()
        total_time = end_time - start_time

        if pr is not None:
            pr.disable()

        # ── assemble results ─────────────────────────────────────────
        results: Dict[str, Any] = {
            "execution_time": total_time,
            "cycles_executed": cycles,
            "cycles_per_second": cycles / total_time if total_time > 0 else 0.0,
            "timestamp": time.time(),
            "program": getattr(self.memory, "loaded_program", None),
        }

        if enable_cpu_profile and self.cpu.profiling_enabled:
            cpu_report = self.cpu.get_profile_report()
            pd = self.cpu.profile_data
            results.update(
                {
                    "cpu_profile": {
                        k: v for k, v in pd.items()
                        if k not in ("instruction_start_times", "cycle_start_time")
                    },
                    "cpu_report_text": cpu_report,
                    "instructions_per_second": (
                        pd["instructions_executed"] / total_time
                        if total_time > 0
                        else 0.0
                    ),
                }
            )

        if pr is not None:
            s = io.StringIO()
            import pstats
            ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
            ps.print_stats(30)
            results["cprofile_report"] = s.getvalue()

        # ── export ────────────────────────────────────────────────────
        if export_json:
            _dump_json(results, export_json)

        if export_csv:
            self._export_csv(results, export_csv)

        # ── summary ───────────────────────────────────────────────────
        print()
        print(f"Execution completed:")
        print(f"  Total cycles:    {cycles:,}")
        print(f"  Wall-clock time: {total_time:.4f} s")
        print(f"  Cycles / sec:    {cycles / total_time:,.1f}" if total_time > 0 else "")
        if enable_cpu_profile and self.cpu.profiling_enabled:
            pd = self.cpu.profile_data
            print(f"  Instructions:    {pd['instructions_executed']:,}")
            ips = pd["instructions_executed"] / total_time if total_time > 0 else 0
            print(f"  IPS:             {ips:,.1f}")
            print(f"  Memory accesses: {pd['memory_accesses']:,}")

        return results

    # ------------------------------------------------------------------
    # Micro-benchmarks (self-contained, no external program needed)
    # ------------------------------------------------------------------

    def run_benchmark(
        self,
        benchmark_type: str = "instruction_set",
        export_json: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run a built-in micro-benchmark.

        ``benchmark_type`` may be ``"instruction_set"`` (default) or
        ``"memory_access"``.
        """
        if benchmark_type == "instruction_set":
            return self._benchmark_instruction_set(export_json)
        elif benchmark_type == "memory_access":
            return self._benchmark_memory_access(export_json)
        else:
            raise ValueError(f"Unknown benchmark type: {benchmark_type}")

    # ── instruction-set benchmark ─────────────────────────────────────

    def _benchmark_instruction_set(
        self, export_json: Optional[str] = None
    ) -> Dict[str, Any]:
        print("Running instruction-set benchmark …")
        assert self.cpu is not None

        # fmt: off
        program = [
            0x06, 0x04, 0xE7, 0x00,              # MOV R0, 0
            0x06, 0x04, 0xE8, 0x01,              # MOV R1, 1
            0x08, 0x00, 0xE7, 0xE8,              # ADD R0, R1
            0x0A, 0x00, 0xE7, 0xE8,              # SUB R0, R1
            0x10, 0x00, 0xE7, 0xE8,              # AND R0, R1
            0x11, 0x00, 0xE7, 0xE8,              # OR  R0, R1
            0x12, 0x00, 0xE7, 0xE8,              # XOR R0, R1
            0x06, 0x08, 0xF1, 0x00, 0x20,        # MOV [0x2000], R0
            0x07, 0x08, 0xF1, 0x00, 0x20,        # MOV R0, [0x2000]
            0x0E, 0x08, 0xF0, 0x00, 0x00,        # JMP 0x0000  (loop)
        ]
        # fmt: on

        for i, byte in enumerate(program):
            self.memory.write_byte(i, byte)

        self.cpu.pc = 0
        self.cpu.enable_profiling()

        start = time.time()
        cycles = 0
        max_cycles = 10000

        while not self.cpu.halted and cycles < max_cycles:
            self.cpu.step()
            cycles += 1

        elapsed = time.time() - start
        pd = self.cpu.profile_data

        results: Dict[str, Any] = {
            "benchmark_type": "instruction_set",
            "cycles": cycles,
            "time": elapsed,
            "avg_time_per_instruction_us": (
                elapsed / pd["instructions_executed"] * 1_000_000
            ),
            "instructions_per_second": pd["instructions_executed"] / elapsed,
            "profile_data": dict(pd),
            "timestamp": time.time(),
        }

        if export_json:
            _dump_json(results, export_json)

        print(f"Benchmark completed:")
        print(f"  Cycles:      {cycles:,}")
        print(f"  Time:        {elapsed:.6f} s")
        print(f"  Avg / instr: {results['avg_time_per_instruction_us']:.2f} µs")
        print(f"  IPS:         {results['instructions_per_second']:,.1f}")

        return results

    # ── memory-access benchmark ───────────────────────────────────────

    def _benchmark_memory_access(
        self, export_json: Optional[str] = None
    ) -> Dict[str, Any]:
        print("Running memory-access benchmark …")
        assert self.cpu is not None

        # fmt: off
        program = [
            # Zero-page access
            0x06, 0x08, 0xF0, 0x00, 0x00,        # MOV R0, [0x0000]
            0x06, 0x08, 0xF0, 0x01, 0x00,        # MOV R0, [0x0001]
            0x06, 0x08, 0xF0, 0x02, 0x00,        # MOV R0, [0x0002]
            # General-memory sequential
            0x06, 0x08, 0xF0, 0x00, 0x20,        # MOV R0, [0x2000]
            0x06, 0x08, 0xF0, 0x01, 0x20,        # MOV R0, [0x2001]
            0x06, 0x08, 0xF0, 0x02, 0x20,        # MOV R0, [0x2002]
            # Random access
            0x06, 0x08, 0xF0, 0xFF, 0x2F,        # MOV R0, [0x2FFF]
            0x06, 0x08, 0xF0, 0x80, 0x15,        # MOV R0, [0x1580]
            0x06, 0x08, 0xF0, 0x00, 0xF0,        # MOV R0, [0xF000] (SCB)
            # Stack
            0x1A,                                   # PUSH R0
            0x1B,                                   # POP  R0
            # Loop
            0x0E, 0x08, 0xF0, 0x00, 0x00,        # JMP 0x0000
        ]
        # fmt: on

        for i, byte in enumerate(program):
            self.memory.write_byte(i, byte)

        self.cpu.pc = 0
        self.cpu.enable_profiling()

        start = time.time()
        cycles = 0
        max_cycles = 5000

        while not self.cpu.halted and cycles < max_cycles:
            self.cpu.step()
            cycles += 1

        elapsed = time.time() - start
        pd = self.cpu.profile_data

        results: Dict[str, Any] = {
            "benchmark_type": "memory_access",
            "cycles": cycles,
            "time": elapsed,
            "memory_accesses": pd["memory_accesses"],
            "accesses_per_second": pd["memory_accesses"] / elapsed,
            "profile_data": dict(pd),
            "timestamp": time.time(),
        }

        if export_json:
            _dump_json(results, export_json)

        print(f"Memory benchmark completed:")
        print(f"  Memory accesses: {results['memory_accesses']:,}")
        print(f"  Time:            {elapsed:.6f} s")
        print(f"  Accesses / sec:  {results['accesses_per_second']:,.1f}")

        return results

    # ------------------------------------------------------------------
    # Profile comparison
    # ------------------------------------------------------------------

    def compare_profiles(
        self,
        profile1_path: str,
        profile2_path: str,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compare two JSON profile exports side-by-side."""
        print(f"Comparing {profile1_path}  vs  {profile2_path}")

        with open(profile1_path) as f:
            p1 = json.load(f)
        with open(profile2_path) as f:
            p2 = json.load(f)

        comparison: Dict[str, Any] = {
            "profile1": profile1_path,
            "profile2": profile2_path,
            "timestamp": time.time(),
            "differences": {},
        }

        metrics = [
            "execution_time",
            "cycles_executed",
            "instructions_per_second",
            "cycles_per_second",
        ]
        for metric in metrics:
            v1 = p1.get(metric, 0)
            v2 = p2.get(metric, 0)
            diff = v2 - v1
            pct = (diff / v1 * 100) if v1 != 0 else 0.0
            comparison["differences"][metric] = {
                "value1": v1,
                "value2": v2,
                "difference": diff,
                "percent_change": pct,
            }

        # Opcode deltas
        cp1 = p1.get("cpu_profile") or {}
        cp2 = p2.get("cpu_profile") or {}
        oc1 = cp1.get("opcode_counts", {})
        oc2 = cp2.get("opcode_counts", {})
        all_keys = set(oc1.keys()) | set(oc2.keys())
        opcode_diffs = {}
        for k in all_keys:
            c1 = oc1.get(k) if isinstance(oc1.get(k), int) else 0
            c2 = oc2.get(k) if isinstance(oc2.get(k), int) else 0
            d = c2 - c1
            pct = (d / c1 * 100) if c1 else 0.0
            key = f"0x{k:02X}" if isinstance(k, int) else str(k)
            opcode_diffs[key] = {
                "count1": c1,
                "count2": c2,
                "difference": d,
                "percent_change": pct,
            }
        comparison["opcode_differences"] = opcode_diffs

        if output_path:
            _dump_json(comparison, output_path)

        print("\nComparison summary:")
        for metric, data in comparison["differences"].items():
            print(
                f"  {metric}: {data['value1']:.4f} → {data['value2']:.4f} "
                f"({data['percent_change']:+.1f}%)"
            )

        return comparison

    # ------------------------------------------------------------------
    # CSV export helper
    # ------------------------------------------------------------------

    def _export_csv(
        self, profile_data: Dict[str, Any], csv_path: str
    ) -> None:
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Metric", "Value"])
            w.writerow(["Execution Time (s)", profile_data.get("execution_time", 0)])
            w.writerow(["Cycles Executed", profile_data.get("cycles_executed", 0)])
            w.writerow(["Cycles per Second", profile_data.get("cycles_per_second", 0)])
            w.writerow(
                ["Instructions per Second", profile_data.get("instructions_per_second", 0)]
            )

            cp = profile_data.get("cpu_profile")
            if cp and "opcode_counts" in cp:
                w.writerow([])
                w.writerow(["Opcode", "Count", "Percentage"])
                total = cp["instructions_executed"]
                for opcode, count in sorted(
                    cp["opcode_counts"].items(),
                    key=lambda kv: kv[1],
                    reverse=True,
                ):
                    pct = (count / total * 100) if total else 0.0
                    w.writerow([f"0x{opcode:02X}", count, f"{pct:.1f}%"])

        print(f"Profile data exported to {csv_path}")


# ----------------------------------------------------------------------
# Standalone visualisation helper (does not require a NovaProfiler instance)
# ----------------------------------------------------------------------

def create_visualization(profile_path: str, output_path: str) -> None:
    """Generate matplotlib charts from a profile JSON file.

    Handles both ``run``-format profiles (keys: ``execution_time``,
    ``cycles_executed``, ``cpu_profile``) and ``benchmark``-format
    profiles (keys: ``time``, ``cycles``, ``profile_data``).
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed. Install with: pip install matplotlib")
        return

    with open(profile_path) as f:
        data = json.load(f)

    # ── Normalise data across run / benchmark formats ───────────────
    is_benchmark = "benchmark_type" in data

    exec_time: float = data.get("execution_time") or data.get("time") or 0.0
    total_cycles: int = data.get("cycles_executed") or data.get("cycles") or 0

    # Profile sub-dict can be "cpu_profile" (run) or "profile_data" (benchmark)
    cp = data.get("cpu_profile") or data.get("profile_data") or {}

    instr_executed: int = cp.get("instructions_executed", 0)
    memory_accesses: int = cp.get("memory_accesses", 0)

    # Throughput — prefer top-level, fall back to sub-dict
    ips: float = data.get("instructions_per_second") or cp.get(
        "instructions_per_second", 0.0
    )

    # Opcode counts — JSON round-trips int keys as strings; normalise
    raw_oc = cp.get("opcode_counts", {})
    oc: dict = {}
    for k, v in raw_oc.items():
        try:
            oc[int(k)] = v
        except (ValueError, TypeError):
            oc[k] = v

    # ── Build figure ─────────────────────────────────────────────────
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
    kind = "Benchmark" if is_benchmark else "Run"
    fig.suptitle(f"Nova-16 CPU Profiling Results ({kind})")

    # ── Execution metrics (scaled) ────────────────────────────────────
    metrics_labels = ["Exec Time (s)", "Cycles (÷1k)"]
    metrics_vals = [exec_time, total_cycles / 1000.0]
    if instr_executed:
        metrics_labels.append("Instructions (÷1k)")
        metrics_vals.append(instr_executed / 1000.0)

    bars1 = ax1.bar(metrics_labels, metrics_vals)
    ax1.set_ylabel("Value (scaled)")
    ax1.set_title("Execution Metrics")
    _autolabel_bars(ax1, bars1)

    # ── Throughput ────────────────────────────────────────────────────
    bars2 = ax2.bar(["IPS"], [ips])
    ax2.set_ylabel("Instructions / sec")
    ax2.set_title("Throughput")
    _autolabel_bars(ax2, bars2)

    # ── Opcode frequency top-10 ───────────────────────────────────────
    if oc:
        top = sorted(oc.items(), key=lambda kv: kv[1], reverse=True)[:10]
        labels = [f"0x{k:02X}" if isinstance(k, int) else str(k) for k, _ in top]
        counts = [v for _, v in top]
        bars3 = ax3.bar(labels, counts)
        ax3.set_ylabel("Count")
        ax3.set_title("Top 10 Opcodes")
        ax3.tick_params(axis="x", rotation=45)
        _autolabel_bars(ax3, bars3)
    else:
        ax3.text(
            0.5, 0.5, "No opcode data\n(enable --cpu-profile)",
            transform=ax3.transAxes, ha="center", va="center",
            fontsize=10, color="gray",
        )
        ax3.set_title("Top 10 Opcodes")

    # ── Memory accesses ───────────────────────────────────────────────
    bars4 = ax4.bar(["Memory Accesses"], [memory_accesses])
    ax4.set_ylabel("Count")
    ax4.set_title("Memory Operations")
    _autolabel_bars(ax4, bars4)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Visualisation saved to {output_path}")
    plt.close()


def _autolabel_bars(ax, bars) -> None:
    """Place value labels on top of each bar."""
    for bar in bars:
        height = bar.get_height()
        if height == 0:
            continue
        ax.annotate(
            f"{height:,.1f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),  # 3 points vertical offset
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _dump_json(obj: Dict[str, Any], path: str) -> None:
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=str)
    print(f"Exported to {path}")


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Nova-16 CPU Profiler (unified)"
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # ── run ───────────────────────────────────────────────────────────
    run_p = sub.add_parser("run", help="Run profiling on a program")
    run_p.add_argument("program", nargs="?", help=".bin program to profile")
    run_p.add_argument("--cycles", type=int, default=10000, help="Max cycles")
    run_p.add_argument(
        "--cpu-profile", action="store_true", help="Enable built-in CPU profiling"
    )
    run_p.add_argument(
        "--cprofile", action="store_true", help="Also use Python cProfile"
    )
    run_p.add_argument("--export-json", help="Export results to JSON")
    run_p.add_argument("--export-csv", help="Export results to CSV")

    # ── benchmark ─────────────────────────────────────────────────────
    bench_p = sub.add_parser("benchmark", help="Run built-in micro-benchmarks")
    bench_p.add_argument(
        "type",
        nargs="?",
        choices=["instruction_set", "memory_access"],
        default="instruction_set",
        help="Benchmark type",
    )
    bench_p.add_argument("--export-json", help="Export results to JSON")

    # ── compare ───────────────────────────────────────────────────────
    cmp_p = sub.add_parser("compare", help="Compare two profile JSON files")
    cmp_p.add_argument("profile1", help="First profile JSON")
    cmp_p.add_argument("profile2", help="Second profile JSON")
    cmp_p.add_argument("--output", help="Write comparison to JSON")

    # ── visualize ─────────────────────────────────────────────────────
    viz_p = sub.add_parser("visualize", help="Generate charts from profile JSON")
    viz_p.add_argument("profile", help="Profile JSON file")
    viz_p.add_argument("--output", required=True, help="Output PNG path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    profiler = NovaProfiler()

    if args.command == "run":
        profiler.setup_system(args.program)
        profiler.run_profiling(
            max_cycles=args.cycles,
            enable_cpu_profile=args.cpu_profile,
            use_cprofile=args.cprofile,
            export_json=args.export_json,
            export_csv=args.export_csv,
        )

    elif args.command == "benchmark":
        profiler.setup_system()  # no program — inject micro-benchmark code
        profiler.run_benchmark(
            benchmark_type=args.type,
            export_json=args.export_json,
        )

    elif args.command == "compare":
        profiler.compare_profiles(
            args.profile1, args.profile2, args.output
        )

    elif args.command == "visualize":
        create_visualization(args.profile, args.output)


if __name__ == "__main__":
    main()