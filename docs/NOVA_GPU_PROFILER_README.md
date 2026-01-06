# Nova-16 GPU Profiler

A performance analysis tool for the Nova-16 emulator's graphics system. Measures frame rates, rendering times, pixel throughput, and graphics operation efficiency.

## Features

- **Real-time profiling**: Hooks into the emulator to track graphics operations as they execute
- **Comprehensive metrics**:
  - Frame rate (average and peak FPS) - with headless frame simulation
  - Pixel write throughput (pixels/second)
  - Graphics instruction timing and execution counts
  - Layer usage statistics across all 8 graphics layers
  - Memory bandwidth for graphics operations
- **Detailed breakdown**: Per-instruction timing and execution counts
- **JSON output**: Structured data for further analysis
- **Command-line interface**: Easy integration with existing workflows

## Usage

### Basic Profiling

```bash
python nova_gpu_profiler.py program.bin
```

### Advanced Options

```bash
python nova_gpu_profiler.py program.bin \
    --cycles 10000 \
    --output my_profile.json \
    --no-charts
```

### Options

- `program`: Binary program file to profile (required)
- `--cycles`: Maximum cycles to run (default: 10000)
- `--output`: Output profile JSON file (default: gpu_profile.json)
- `--no-charts`: Disable chart generation (charts not implemented yet)

## Output Metrics

The profiler generates a comprehensive JSON report with:

- **Session info**: Duration, total cycles, cycles per second
- **Graphics statistics**: Instructions executed, pixel writes, layer operations
- **Performance metrics**: Frame rates, throughput, memory bandwidth
- **Instruction breakdown**: Timing and counts for each graphics operation
- **Layer usage**: Pixel writes per graphics layer

## Example Output

```
=== GPU Profiling Summary ===
Total cycles: 5,000
Graphics instructions: 1,424 (28.5%)
Pixel writes: 713
Composite events: 0
Average FPS: 0.0
Peak FPS: 0.0
Pixel throughput: 10086 pixels/sec
Session duration: 0.07s
```

## Graphics Instructions Tracked

The profiler tracks all graphics operations defined in `opcodes.py`:

- **Screen Operations:**
  - `SBLEND` (0x31): Set blend mode
  - `SREAD` (0x32): Read screen pixel
  - `SWRITE` (0x33): Write screen pixel
  - `SROL` (0x34): Roll screen by axis, amount
  - `SROT` (0x35): Rotate screen by direction, amount
  - `SSHFT` (0x36): Shift screen by axis, amount
  - `SFLIP` (0x37): Flip screen by axis, amount
  - `SLINE` (0x38): Line x1, y1, x2, y2, color
  - `SRECT` (0x39): Rectangle x1, y1, x2, y2, color, un/filled
  - `SCIRC` (0x3A): Circle x, y, radius, color, un/filled
  - `SINV` (0x3B): Invert screen colors
  - `SBLIT` (0x3C): Blit screen
  - `SFILL` (0x3D): Fill screen

- **VRAM Operations:**
  - `VREAD` (0x3E): Read VRAM
  - `VWRITE` (0x3F): Write VRAM
  - `VBLIT` (0x40): Blit VRAM

- **Text Operations:**
  - `CHAR` (0x41): Draw character
  - `TEXT` (0x42): Draw text

- **Sprite Operations:**
  - `SPBLIT` (0x55): Blit sprite
  - `SPBLITALL` (0x56): Blit all sprites

## Integration

The profiler automatically integrates with the Nova-16 emulator by:

1. Attaching to CPU and GFX components
2. Monkey-patching key methods for profiling hooks
3. Collecting timing and operation data during execution
4. Generating reports when profiling completes

## Understanding FPS Measurements

**Why was it reporting 0 FPS before?**

The original profiler reported 0 FPS because it relied on GUI compositing events. In Nova-16:

- Compositing (layer blending) only happens when `get_screen()` is called
- `get_screen()` is only called by the GUI for display
- In headless mode, no GUI exists, so compositing never occurs
- Without compositing events, no frame times could be measured

**How FPS is measured now:**

The updated profiler simulates frame timing for headless operation:

- Targets 60 FPS frame interval (~16.7ms between frames)
- Periodically triggers compositing when graphics layers are dirty
- Measures time between compositing events to calculate FPS
- Reports both real compositing events and simulated frames

**Interpreting the results:**

- **Average FPS**: Theoretical frame rate based on graphics workload
- **Peak FPS**: Maximum instantaneous frame rate (often very high due to fast compositing)
- **Composite Events**: Actual layer compositing operations
- **Simulated Frames**: Frame timing simulation for headless profiling

Note: These measurements represent the GPU's theoretical performance. In a real Nova-16 system with GUI, FPS would be limited by display refresh rates (typically 60 FPS).