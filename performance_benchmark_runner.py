#!/usr/bin/env python3
"""
Nova-16 Performance Benchmark Runner

Runs the Nova-16 performance benchmark suite in headless mode and
analyses the results.  Uses the same component initialisation as
``nova_main.py`` so that bench numbers reflect the real runtime.

Usage:
    py -3.13 performance_benchmark_runner.py
    py -3.13 performance_benchmark_runner.py --cycles 100000
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Project root (where nova_main.py lives)
ROOT = Path(__file__).parent.resolve()

BENCHMARK_BIN = ROOT / "asm" / "performance_benchmark.bin"


class NovaBenchmarkRunner:
    """Thin wrapper that drives nova_main.py with the benchmark binary."""

    def __init__(self, binary_path: Path | None = None) -> None:
        self.binary_path = binary_path or BENCHMARK_BIN

    # ------------------------------------------------------------------
    # Core run
    # ------------------------------------------------------------------

    def run_benchmark(self, max_cycles: int = 50000, timeout: int = 60) -> bool:
        """Run the performance benchmark binary in headless mode.

        Returns ``True`` if the emulator exited cleanly.
        """
        cmd = [
            sys.executable,       # use the same Python, not bare "python"
            str(ROOT / "nova_main.py"),
            "--headless",
            str(self.binary_path),
            "--cycles",
            str(max_cycles),
        ]

        print(f"Running benchmark: {' '.join(cmd)}")
        start = time.time()

        try:
            result = subprocess.run(
                cmd,
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            print(f"Benchmark timed out after {timeout} s")
            return False
        except OSError as exc:
            print(f"Failed to launch benchmark: {exc}")
            return False

        elapsed = time.time() - start

        print(f"Benchmark completed in {elapsed:.2f} s")
        print(f"Return code: {result.returncode}")
        if result.stdout:
            print("STDOUT:\n" + result.stdout.strip())
        if result.stderr and result.returncode != 0:
            print("STDERR:\n" + result.stderr.strip())

        return result.returncode == 0

    # ------------------------------------------------------------------
    # Quick analysis (reads the benchmark binary metadata)
    # ------------------------------------------------------------------

    def analyse(self) -> None:
        print("\n=== Nova-16 Performance Analysis ===")

        # If the benchmark binary exists, print its size as a rough gauge
        if self.binary_path.exists():
            size = self.binary_path.stat().st_size
            print(f"Benchmark binary size: {size:,} bytes")
        else:
            print(f"Benchmark binary not found: {self.binary_path}")

        print("Test parameters (embedded in benchmark.asm):")
        print("  Memory test block: 0x1000 (4096) bytes")
        print("  Loop iterations:   0x1000 (4096)")
        print("  Timer speed:       1 (base unit)")

        print("\n--- Results are stored at runtime addresses ---")
        print("  0x2000 – memory throughput timer snapshot")
        print("  0x2004 – memory latency timer snapshot")
        print("  0x2008 – instructions-per-second snapshot")
        print("  0x200C – ALU operation count")
        print("  0x2010 – stack operation count")
        print("  0x2014 – branch operation count")
        print("  0x2018 – graphics operation count")
        print("  0x201C – timer accuracy check")

        print("\nFor detailed profiling, run:")
        print("  py -3.13 nova_profiler.py run asm/performance_benchmark.bin --cpu-profile --cycles 50000")
        print("  py -3.13 nova_memory_profiler.py asm/performance_benchmark.bin --cycles 50000 --summary")
        print("  py -3.13 nova_gpu_profiler.py asm/performance_benchmark.bin --cycles 50000")


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description="Nova-16 Performance Benchmark Runner")
    p.add_argument("--cycles", type=int, default=50000, help="Max cycles")
    p.add_argument(
        "--binary",
        type=Path,
        default=BENCHMARK_BIN,
        help="Benchmark .bin path",
    )
    p.add_argument("--timeout", type=int, default=60, help="Timeout in seconds")
    args = p.parse_args()

    runner = NovaBenchmarkRunner(binary_path=args.binary)
    ok = runner.run_benchmark(max_cycles=args.cycles, timeout=args.timeout)

    if ok:
        print("\nBenchmark exited cleanly.")
    else:
        print("\nBenchmark failed — see output above for details.")

    runner.analyse()


if __name__ == "__main__":
    main()