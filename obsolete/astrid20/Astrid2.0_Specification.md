# Astrid 2.0: Nova-16 Hardware-Optimized Compiler Implementation Plan

## Executive Summary

The new Astrid compiler will be designed from the ground up to fully leverage Nova-16's unique hardware capabilities, addressing the fundamental flaws of the current implementation. The focus will be on hardware-aware language design, efficient code generation, and seamless integration with the system's graphics, sound, and interrupt subsystems.

## Core Design Principles

### 1. Hardware-First Language Design
- **Graphics-Centric**: Language constructs specifically for the 8-layer graphics system
- **Sound-Aware**: Native support for programmable waveforms and multi-channel audio
- **Interrupt-Native**: First-class interrupt handling with proper context management
- **Memory-Conscious**: Optimize for 64KB address space and memory-mapped I/O

### 2. Modern Compiler Architecture
- **Multi-Pass Pipeline**: Separate phases for analysis, optimization, and code generation
- **Intermediate Representation**: SSA-based IR for optimization opportunities
- **Hardware-Specific Optimizations**: Register allocation and instruction selection tuned for Nova-16
- **Modular Design**: Clean separation of concerns for maintainability

## Phase 1: Language Specification & Design

### 1.1 Type System Redesign
```c
// Native hardware types
int8    // R registers (0-255)
int16   // P registers (0-65535)
pixel   // Graphics coordinates (0-255)
color   // Color values with blending support
sound   // Audio samples/waveforms
```

### 1.2 Hardware Integration Constructs

#### Graphics System Integration
```c
// Layer management
layer screen = layer(0);        // Main screen buffer
layer bg1 = layer(1);           // Background layer 1
layer sprites = layer(5);       // Sprite layer

// Coordinate system
pixel x = 100, y = 120;
screen.set_pos(x, y);
screen.write(color.red);

// Blending modes
bg1.blend_mode = blend.add;
bg1.blend_mode = blend.multiply;

// Sprite system integration
sprite star = sprite(0);        // Sprite slot 0
star.x = 50; star.y = 75;
star.visible = true;
```

#### Sound System Integration
```c
// Channel management
sound_channel music = channel(0);
sound_channel sfx = channel(1);

// Waveform programming
waveform square_wave = waveform.square;
music.frequency = 440;          // A4 note
music.volume = 128;
music.waveform = square_wave;
music.play();

// Sample playback
sound sample = load_sample("explosion.wav");
sfx.play_sample(sample);
```

#### Interrupt System Integration
```c
// Interrupt handlers
interrupt timer_handler() {
    // Hardware-specific interrupt code
    for (layer l : layers) {
        l.scroll_x(1);
    }
    return;  // Compiler generates proper IRET/RET
}

// Interrupt configuration
timer.configure(255, 80, 3);    // TT, TM, TS, TC
interrupts.enable();
```

### 1.3 Memory and I/O Integration
```c
// Memory-mapped access
memory.zero_page = 0x42;        // Fast zero-page access
memory.sprite_table[0] = star;  // Sprite control blocks

// Hardware register access
hardware.vmode = coord_mode;    // VM register
hardware.vlayer = 1;            // VL register
```

## Phase 2: Compiler Architecture

### 2.1 Multi-Pass Pipeline Design

#### Frontend Pipeline
```
Source Code → Lexer → Parser → AST → Semantic Analyzer → IR Generation
```

#### Optimization Pipeline
```
IR → Constant Folding → Dead Code Elimination → Register Allocation → Instruction Selection
```

#### Backend Pipeline
```
Optimized IR → Assembly Generation → Hardware-Specific Optimization → Binary Output
```

### 2.2 Intermediate Representation (IR)

#### SSA-Based Design
```llvm
; Example IR for graphics operation
%coord_mode = constant 0
%layer_1 = constant 1
%x_pos = constant 100
%y_pos = constant 120
%color = constant 0x1F

call @set_vmode(%coord_mode)
call @set_layer(%layer_1)
call @set_pos(%x_pos, %y_pos)
call @write_screen(%color)
```

#### Hardware-Specific IR Extensions
```llvm
; Graphics operations
%pixel = pixel_op %x, %y, %color
%sprite = sprite_op %sprite_id, %x, %y

; Sound operations
%channel = sound_op %frequency, %volume, %waveform

; Memory operations with hardware awareness
%fast_access = load_zero_page %address
%mmio = load_mmio %hardware_register
```

## Phase 3: Hardware-Aware Code Generation

### 3.1 Register Allocation Strategy

#### Register Classes
```python
class RegisterAllocator:
    R_REGISTERS = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']
    P_REGISTERS = ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9']
    GFX_REGISTERS = ['VX', 'VY', 'VM', 'VL']
    SOUND_REGISTERS = ['SA', 'SF', 'SV', 'SW']
    TIMER_REGISTERS = ['TT', 'TM', 'TC', 'TS']
```

#### Allocation Algorithm
1. **Type-Based Assignment**: `int8` → R registers, `int16` → P registers
2. **Hardware Register Reservation**: Reserve VX, VY for graphics operations
3. **Live Range Analysis**: Minimize register spills using graph coloring
4. **Special Register Optimization**: Use hardware registers for common operations

### 3.2 Memory Access Optimization

#### Zero-Page Optimization
```asm
; Fast zero-page access for frequently used variables
MOV R0, [0x00]      ; Instead of complex stack frame calculations
MOV [0x01], R1
```

#### Stack Frame Optimization
```asm
; Efficient local variable access
MOV P8, 0xFE00      ; Stack pointer
MOV P9, P8          ; Frame pointer = stack pointer (simplified)

; Local variables at negative offsets from frame pointer
MOV R0, [P9-1]      ; Local variable 1
MOV [P9-2], R1      ; Local variable 2
```

### 3.3 Graphics Code Generation

#### Layer Management
```asm
; Optimized layer switching
MOV VL, 1           ; Set active layer
MOV VM, 0           ; Coordinate mode

; Batch operations on same layer
MOV VX, 100
MOV VY, 120
SWRITE 0x1F
```

#### Sprite System Integration
```asm
; Sprite control block access (0xF000-0xF0FF)
MOV P0, 0xF000      ; Sprite 0 control block
MOV [P0], 0x01      ; Enable sprite
MOV [P0+2], 100     ; X position
MOV [P0+4], 120     ; Y position
```

## Phase 4: Built-in Function Library

### 4.1 Graphics Functions
```c
// Core graphics operations
void set_mode(video_mode mode);
void set_layer(int layer);
void set_position(pixel x, pixel y);
void write_pixel(color c);
void read_pixel() -> color;

// Advanced graphics
void scroll_layer(int layer, int amount);
void set_blend_mode(blend_mode mode);
void clear_layer(int layer);
void copy_layer(int src, int dst);
```

### 4.2 Sound Functions
```c
// Channel management
sound_channel get_channel(int id);
void set_frequency(sound_channel ch, int hz);
void set_volume(sound_channel ch, int volume);
void set_waveform(sound_channel ch, waveform type);
void play_channel(sound_channel ch);
void stop_channel(sound_channel ch);

// Sample playback
sound load_sample(string filename);
void play_sample(sound_channel ch, sound sample);
```

### 4.3 System Functions
```c
// Interrupt management
void enable_interrupts();
void disable_interrupts();
interrupt_handler set_interrupt_handler(int vector, function handler);

// Timer system
timer configure_timer(int modulo, int speed, int control);
int get_timer_value();
void reset_timer();

// Memory operations
void fast_memcpy(int16 dst, int16 src, int16 size);
int16 allocate_memory(int16 size);
void free_memory(int16 address);
```

## Phase 5: Implementation Roadmap

### 5.1 Month 1-2: Core Infrastructure
1. **Lexer & Parser**: Implement with proper error handling
2. **AST Design**: Hardware-aware AST nodes
3. **Basic IR**: Simple IR generation
4. **Test Framework**: Unit tests for each component

### 5.2 Month 3-4: Language Features
1. **Type System**: Implement hardware-specific types
2. **Graphics Integration**: Layer and sprite support
3. **Sound System**: Channel and waveform management
4. **Interrupt Handling**: Proper interrupt function generation

### 5.3 Month 5-6: Optimization & Code Generation
1. **Register Allocator**: Hardware-aware allocation
2. **Instruction Selection**: Nova-16 specific optimizations
3. **Memory Optimization**: Zero-page and stack frame optimization
4. **Built-in Functions**: Complete hardware integration library

### 5.4 Month 7-8: Advanced Features & Testing
1. **Optimization Passes**: Constant folding, dead code elimination
2. **Debug Support**: Source-level debugging integration
3. **Performance Tuning**: Benchmark against hand-written assembly
4. **Documentation**: Complete language reference and examples

## Phase 6: Testing & Validation Strategy

### 6.1 Hardware Validation Tests
```c
// Graphics test suite
void test_graphics_layers() {
    for (int layer = 0; layer < 8; layer++) {
        set_layer(layer);
        set_pos(100, 100);
        write_screen(layer * 32);  // Different colors per layer
    }
}

// Sound test suite
void test_sound_channels() {
    for (int ch = 0; ch < 8; ch++) {
        sound_channel channel = get_channel(ch);
        set_frequency(channel, 220 + ch * 110);  // Different frequencies
        set_volume(channel, 64);
        play_channel(channel);
    }
}

// Interrupt test suite
interrupt timer_test() {
    static int counter = 0;
    counter++;
    if (counter % 60 == 0) {  // Every second at 60Hz
        scroll_x(1);
    }
}
```

### 6.2 Performance Benchmarks
1. **Code Size**: Compare generated assembly size vs hand-written
2. **Execution Speed**: Cycle counts for common operations
3. **Memory Usage**: Stack and heap utilization patterns
4. **Graphics Performance**: Frame rates for different rendering techniques

## Phase 7: Documentation & Ecosystem

### 7.1 Developer Documentation
1. **Language Reference**: Complete syntax and semantics
2. **Hardware Integration Guide**: How to use Nova-16 features
3. **Optimization Guide**: Writing efficient Astrid code
4. **Debugging Guide**: Using the debugger with Astrid programs

### 7.2 Example Programs
1. **Graphics Demos**: Starfield, sprites, blending effects
2. **Sound Demos**: Music playback, sound effects
3. **Game Examples**: Simple games utilizing full hardware
4. **System Programs**: Utilities and tools

## Success Metrics

### 1. Hardware Utilization
- **95%+** of Nova-16 instructions used in generated code
- **Zero overhead** for hardware register access
- **Optimal memory layout** utilization

### 2. Code Quality
- **50% smaller** assembly output vs current Astrid
- **30% faster** execution for typical programs
- **Zero runtime errors** in validated programs

### 3. Developer Experience
- **Intuitive syntax** for hardware operations
- **Clear error messages** with hardware context
- **Comprehensive documentation** and examples

## Risk Mitigation

### 1. Incremental Development
- **Working prototypes** at each phase milestone
- **Backward compatibility** considerations
- **Fallback options** for complex features

### 2. Hardware Testing
- **Emulator validation** for all hardware features
- **Real hardware testing** when available
- **Performance profiling** throughout development

### 3. Community Feedback
- **Early access** to advanced users
- **Issue tracking** and feature requests
- **Documentation review** by hardware experts

---

*This plan provides a comprehensive roadmap for building a Nova-16 optimized Astrid compiler that fully leverages the system's unique capabilities while maintaining clean, maintainable code architecture.*

*Last updated: August 29, 2025*
*Version: Astrid 2.0 Specification v1.0*
