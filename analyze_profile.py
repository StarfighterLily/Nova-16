#!/usr/bin/env python3

import sys
from collections import defaultdict

def analyze_pyspy_profile(filename):
    function_counts = defaultdict(int)
    total_samples = 0

    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Split by semicolon to get stack frames
            parts = line.split(';')
            if not parts:
                continue

            # Last part before the count is the count
            last_part = parts[-1]
            if ' ' in last_part:
                stack_str, count_str = last_part.rsplit(' ', 1)
                try:
                    count = int(count_str)
                except ValueError:
                    continue
                # Add the stack_str back if it was split
                if stack_str:
                    parts[-1] = stack_str
            else:
                continue

            total_samples += count

            # Count each function in the stack
            for frame in parts:
                if '(' in frame and ')' in frame:
                    # Extract function name
                    func_part = frame.split('(')[0].strip()
                    function_counts[func_part] += count

    # Sort by count descending
    sorted_functions = sorted(function_counts.items(), key=lambda x: x[1], reverse=True)

    print(f"Total samples: {total_samples}")
    print("\nTop functions by sample count:")
    print("-" * 50)
    for func, count in sorted_functions[:20]:  # Top 20
        percentage = (count / total_samples) * 100
        print(f"{func:<25} {count:>8} {percentage:>6.2f}%")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analyze_profile.py profile.pyspy")
        sys.exit(1)

    analyze_pyspy_profile(sys.argv[1])