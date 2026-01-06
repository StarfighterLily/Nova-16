# Nova-16 Advanced Graphics Monitor Usage Guide

The enhanced Nova Graphics Monitor is a sophisticated debugging tool for visual programs on the Nova-16 CPU emulator.

## Key Features

### 🎯 **Real-time Graphics Tracking**
- Monitors all 9 graphics layers (main screen + 4 background + 4 sprite layers)
- Detects pixel writes, color changes, and drawing operations
- Tracks video register changes (VX, VY, VM, VL)
- Identifies graphics instructions (SWRITE, SREAD, SFILL, etc.)

### 📊 **Comprehensive Analysis**
- Multiple monitor regions with custom names and sizes
- Layer-specific change detection and reporting
- Drawing bounds and color usage statistics
- Instruction counting and performance metrics

### 📁 **Data Export**
- JSON export of all graphics operations
- Final analysis reports with statistics
- Debug data for post-analysis

## Basic Usage

### Simple Monitoring
```powershell
# Monitor with default settings
python nova_graphics_monitor.py program.bin

# Monitor with custom cycle limit
python nova_graphics_monitor.py program.bin --cycles 10000
```

### Advanced Monitoring
```powershell
# Monitor specific regions
python nova_graphics_monitor.py program.bin --regions "main:90,90,20,20" "ui:200,50,50,30"

# Focus on specific layers
python nova_graphics_monitor.py program.bin --layers 0 1 5

# Export debug data
python nova_graphics_monitor.py program.bin --export debug_output

# Use configuration file
python nova_graphics_monitor.py program.bin --config graphics_monitor_config.json
```

## Configuration File Format

```json
{
  "regions": [
    {"name": "center", "x": 100, "y": 100, "width": 56, "height": 56},
    {"name": "ui", "x": 200, "y": 50, "width": 50, "height": 30}
  ],
  "layers": [0, 1, 5],
  "verbose": true,
  "export": true,
  "check_interval": 25
}
```

## Sample Output

```
================================================================================
Nova-16 Advanced Graphics Monitor  
================================================================================
Program: simple_pixel_test.bin
Monitor Regions:
  - main: 20x20 at (90, 90)
Tracking Layers: [0, 1, 2, 3, 4, 5, 6, 7, 8]
Max Cycles: 1000
Check Interval: 50 cycles

[Cycle     2] Video Register VL: 0x00 -> 0x01
[Cycle     3] Video Register VX: 0x00 -> 0x64  
[Cycle     4] Video Register VY: 0x00 -> 0x64
[Cycle     6] Graphics Instruction: SWRITE at PC: 0x1011
[Cycle     6] Layer 1 pixel change at (100,100): 0x00 -> 0x0F

=== Graphics Analysis - Cycle 6 ===
  Background Layer 1:
    Pixel (100,100): 0x00 -> 0x0F
  Video Registers: VX=0x64, VY=0x64, VM=0, VL=1

================================================================================
FINAL ANALYSIS
================================================================================
Graphics Statistics:
  Total pixel writes: 1
  Colors used: [15] (1 unique)
  Drawing bounds: (100, 100) to (100, 100)
  Graphics instructions:
    SWRITE: 1

Final Video Registers:
  VX: 0x64, VY: 0x64, VM: 0x00, VL: 0x01
```

## Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--regions` | Monitor regions as name:x,y,width,height | `--regions "main:90,90,20,20"` |
| `--layers` | Layer numbers to monitor (0-8) | `--layers 0 1 5` |
| `--cycles` | Maximum cycles to run | `--cycles 10000` |
| `--interval` | Analysis interval in cycles | `--interval 25` |
| `--quiet` | Reduce verbose output | `--quiet` |
| `--export` | Export debug data with prefix | `--export debug_output` |
| `--config` | Load configuration from JSON | `--config config.json` |

## Use Cases

### 🐛 **Debugging Graphics Programs**
- Track exactly where and when pixels are drawn
- Identify incorrect coordinates or colors
- Monitor layer usage and composition

### 📈 **Performance Analysis**  
- Count graphics instructions per frame
- Analyze drawing patterns and efficiency
- Identify hotspots in graphics code

### 🎮 **Game Development**
- Monitor sprite movements and collisions
- Debug layer composition and blending
- Track UI element updates

### 🧪 **Testing Graphics Algorithms**
- Verify pixel-perfect drawing operations
- Test color palettes and gradients
- Validate graphics transformations

## Tips for Effective Debugging

1. **Use focused layer monitoring** for better performance
2. **Set appropriate check intervals** based on program complexity
3. **Use multiple monitor regions** to track different screen areas
4. **Export data** for detailed post-analysis
5. **Start with quiet mode** for long-running programs

The enhanced graphics monitor transforms Nova-16 visual debugging from guesswork into precise, data-driven analysis.
