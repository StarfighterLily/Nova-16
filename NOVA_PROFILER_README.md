# Nova-16 CPU Profiler

A comprehensive profiling tool for the Nova-16 CPU emulator that helps identify performance bottlenecks and optimization opportunities.

## Features

- **Built-in CPU profiling** with detailed metrics (instruction counts, timing, opcode frequencies)
- **cProfile integration** for Python-level profiling
- **Memory access pattern analysis**
- **Instruction set benchmarking**
- **JSON/CSV export** for reports
- **Visualization** of profiling data with charts
- **Comparison** between profiling runs
- **Command-line interface** with subcommands

## Installation

Ensure you have the Nova-16 emulator dependencies installed:

```bash
pip install numpy pygame matplotlib
```

## Usage

### Basic Profiling

Profile a Nova-16 program for 10,000 cycles with CPU profiling enabled:

```bash
python nova_profiler.py run asm/myprogram.bin --cpu-profile --cycles 10000
```

### Export Results

Export profiling data to JSON and CSV:

```bash
python nova_profiler.py run asm/myprogram.bin --cpu-profile --export-json results.json --export-csv results.csv
```

### Benchmarking

Run built-in benchmarks to test instruction performance:

```bash
# Instruction set benchmark
python nova_profiler.py benchmark instruction_set --export-json bench.json

# Memory access benchmark
python nova_profiler.py benchmark memory_access --export-json mem_bench.json
```

### Comparison

Compare two profiling runs to identify performance differences:

```bash
python nova_profiler.py compare profile1.json profile2.json --output comparison.json
```

### Visualization

Generate charts from profiling data:

```bash
python nova_profiler.py visualize profile.json --output chart.png
```

## Command Reference

### `run` Command

Run profiling on a Nova-16 program.

```bash
python nova_profiler.py run [program.bin] [options]
```

Options:
- `--cycles N`: Maximum cycles to run (default: 10000)
- `--cpu-profile`: Enable built-in CPU profiling
- `--cprofile`: Use Python's cProfile
- `--export-json FILE`: Export results to JSON
- `--export-csv FILE`: Export results to CSV

### `benchmark` Command

Run performance benchmarks.

```bash
python nova_profiler.py benchmark <type> [options]
```

Types:
- `instruction_set`: Test various instruction types
- `memory_access`: Test memory access patterns

Options:
- `--export-json FILE`: Export results to JSON

### `compare` Command

Compare two profiling runs.

```bash
python nova_profiler.py compare <profile1.json> <profile2.json> [options]
```

Options:
- `--output FILE`: Save comparison to JSON file

### `visualize` Command

Generate visualizations from profile data.

```bash
python nova_profiler.py visualize <profile.json> --output <chart.png>
```

## Output Metrics

### Execution Metrics
- **Execution Time**: Total time spent running
- **Cycles Executed**: Number of CPU cycles
- **Instructions per Second (IPS)**: Instruction throughput
- **Cycles per Second (CPS)**: Cycle throughput

### CPU Profile Data
- **Instructions Executed**: Total instruction count
- **Memory Accesses**: Number of memory operations
- **Opcode Frequencies**: Count of each opcode executed
- **Method Timing**: Time spent in CPU methods (when using decorators)

### Benchmark Results
- **Average Time per Instruction**: Microseconds per instruction
- **Instructions per Second**: Throughput metric
- **Memory Accesses per Second**: Memory performance

## Optimization Insights

### Identifying Bottlenecks

1. **High-frequency opcodes**: Look for opcodes that dominate execution time
2. **Memory access patterns**: Excessive memory operations may indicate optimization opportunities
3. **Instruction throughput**: Compare IPS across different programs or versions

### Memory Optimization

- **Zero page access**: Use addresses 0x0000-0x00FF for fastest access
- **Sequential access**: Prefer sequential memory patterns over random access
- **Cache awareness**: Minimize scattered memory accesses

### Instruction Optimization

- **Register usage**: Prefer register operations over memory operations
- **Opcode selection**: Choose more efficient opcodes when possible
- **Loop optimization**: Minimize instructions in tight loops

## Examples

### Profile a Graphics Program

```bash
# Profile gfxtest for 5000 cycles
python nova_profiler.py run asm/gfxtest.bin --cpu-profile --cycles 5000 --export-json gfxtest_profile.json

# Generate visualization
python nova_profiler.py visualize gfxtest_profile.json --output gfxtest_analysis.png
```

### Compare Optimized vs Unoptimized

```bash
# Profile original version
python nova_profiler.py run asm/original.bin --cpu-profile --export-json original.json

# Profile optimized version
python nova_profiler.py run asm/optimized.bin --cpu-profile --export-json optimized.json

# Compare results
python nova_profiler.py compare original.json optimized.json --output optimization_comparison.json
```

### Memory Access Analysis

```bash
# Run memory benchmark
python nova_profiler.py benchmark memory_access --export-json memory_analysis.json

# Analyze results in JSON
cat memory_analysis.json | jq '.memory_accesses_per_second'
```

## Integration with Development Workflow

### Automated Profiling

Add profiling to your build process:

```bash
# In your build script
python nova_assembler.py program.asm
python nova_profiler.py run program.bin --cpu-profile --export-json profile.json
```

### Continuous Performance Monitoring

Track performance changes over time:

```bash
# Profile after each change
python nova_profiler.py run program.bin --cpu-profile --export-json "profile_$(date +%Y%m%d_%H%M%S).json"
```

### GUI Integration

For interactive profiling during GUI execution, use the built-in profiling from `cpu_profiling_example.py`:

```python
# Enable profiling in GUI mode
cpu_instance.enable_profiling()
# ... run GUI ...
print(cpu_instance.get_profile_report())
```

## Troubleshooting

### Common Issues

1. **Program not found**: Ensure the .bin file exists and was assembled correctly
2. **No profiling data**: Make sure `--cpu-profile` is enabled
3. **Visualization fails**: Install matplotlib: `pip install matplotlib`
4. **Memory errors**: Reduce cycle count with `--cycles`

### Performance Considerations

- Profiling adds overhead; results may differ from unprofiled execution
- Use appropriate cycle limits to avoid excessive runtime
- Export data for post-processing rather than real-time analysis

## Advanced Usage

### Custom Benchmarks

Extend the profiler by adding new benchmark types in the `run_benchmark` method.

### Method-Level Profiling

Use the `@cpu_instance.profile_method()` decorator for detailed method timing:

```python
@cpu_instance.profile_method("my_custom_method")
def my_function():
    # Code to profile
    pass
```

### Integration with Testing

Combine with pytest for automated performance regression testing:

```python
def test_performance_regression():
    profiler = NovaProfiler()
    profiler.setup_system("asm/test.bin")
    results = profiler.run_profiling(max_cycles=1000, enable_cpu_profile=True)

    assert results['instructions_per_second'] > 50000  # Performance threshold
```