# NoBASIC SDL Runtime

This directory contains the SDL-based graphics runtime for NoBASIC programs compiled to LLVM IR.

## Overview

The SDL runtime provides native execution of NoBASIC programs that use Nova-16 hardware graphics functions. It creates a 256x256 pixel window scaled 3x (768x768 actual window size).

## Files

- `nobasic_sdl_runtime.h` - Header file with function declarations and type definitions
- `nobasic_sdl_runtime.c` - Core graphics implementation (pixel buffer, rendering, font)
- `CMakeLists.txt` - CMake build configuration

## Supported NoBASIC Functions

| NoBASIC Function | Description |
|-----------------|-------------|
| `ClrDraw` | Clear current graphics layer |
| `PxlOn(x, y, color)` | Draw a pixel on |
| `PxlOff(x, y)` | Draw a pixel off |
| `Line(x1, y1, x2, y2, color)` | Draw a line (Bresenham) |
| `Circle(x, y, radius, color)` | Draw a filled circle |
| `Text(x, y, string, color)` | Draw text with 8x8 bitmap font |
| `SetLayer(layer)` | Set current graphics layer (0-8) |
| `Pause` | Wait for key press |

## Build Requirements

- SDL2 library and development files
- LLVM/Clang (for compiling generated LLVM IR)

### Windows

Using vcpkg:
```powershell
vcpkg install sdl2
```

Or download SDL2 from https://www.libsdl.org/download-2.0.php

## Build Workflow

### Step 1: Compile NoBASIC to LLVM IR
```powershell
cd ..
py -3.13 nobasic_compiler.py progs/sdl_demo.nobasic --target llvm
```

### Step 2: Compile with Clang
```powershell
cd sdl
clang ../progs/sdl_demo.ll ../llvm_runtime_sdl.c nobasic_sdl_runtime.c -o sdl_demo.exe -lSDL2 -I.
```

### Using CMake
```powershell
mkdir build
cd build
cmake .. -DCMAKE_TOOLCHAIN_FILE=[vcpkg toolchain]
cmake --build . --config Release
```

## Graphics Details

- **Resolution**: 256x256 pixels (8-bit X/Y coordinates)
- **Scale**: 3x (window is 768x768)
- **Layers**: 8 layers (0-8) plus screen composite
- **Colors**: 256-color palette matching Nova-16
- **Font**: 8x8 bitmap font (Nova PC-8001 compatible)

## Palette Layout

The palette uses a segmented layout:
- `0x00-0x0F`: Grayscale
- `0x10-0x1F`: Red gradient
- `0x20-0x2F`: Green gradient
- `0x30-0x3F`: Blue gradient
- `0x40-0x4F`: Yellow gradient
- `0x50-0x5F`: Magenta gradient
- `0x60-0x6F`: Cyan gradient
- `0x70-0xFF`: Various colors

## Layer Compositing

Layers are composited from bottom to top:
1. Layer 0 (base)
2. Layers 1-4 (overlaid on base)
3. Layers 5-8 (top overlay)

Non-zero pixels from upper layers overwrite lower layer pixels.