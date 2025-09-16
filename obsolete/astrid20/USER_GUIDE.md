# Astrid 2.0 User Guide

**Version**: 2.0.0
**Date**: August 29, 2025
**Status**: Complete ✅

---

## 🚀 Getting Started with Astrid 2.0

Welcome to Astrid 2.0! This guide will help you get started with programming the Nova-16 CPU using our hardware-optimized C-like language.

### What is Astrid 2.0?

Astrid 2.0 is a modern programming language designed specifically for the Nova-16 CPU emulator. It combines familiar C-like syntax with native support for Nova-16's unique hardware capabilities, including graphics, sound, and system operations.

### Prerequisites

- Python 3.8 or higher
- Nova-16 emulator installed
- Basic understanding of C programming

---

## 📦 Installation

1. **Navigate to the Astrid 2.0 directory:**
   ```powershell
   cd e:\Storage\Scripts\Nova\astrid2.0
   ```

2. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Verify installation:**
   ```powershell
   python -m astrid2 --help
   ```

---

## 🏃 Your First Program

Let's create a simple program that displays a pixel on the screen.

### Step 1: Create the Source File

Create a file called `hello.ast`:

```c
void main() {
    pixel x = 100;
    pixel y = 120;
    color red = 0x1F;

    set_pixel(x, y, red);
}
```

### Step 2: Compile the Program

```powershell
python -m astrid2 hello.ast -o hello.asm
```

### Step 3: Assemble to Binary

```powershell
python ..\nova_assembler.py hello.asm
```

### Step 4: Run on Nova-16

```powershell
python ..\nova.py hello.bin
```

You should see a red pixel at coordinates (100, 120) on the screen!

---

## 📚 Language Basics

### Variables and Types

Astrid 2.0 supports several data types optimized for Nova-16 hardware:

```c
// Basic integer types
int8 small_number = 42;      // 8-bit, uses R registers
int16 large_number = 1000;   // 16-bit, uses P registers

// Hardware-specific types
pixel x = 128;               // Screen coordinate (0-255)
color pixel_color = 0x1F;    // Color value (0-31)
layer graphics_layer = 1;    // Graphics layer (0-7)
sprite player = 0;           // Sprite index (0-15)
```

### Control Flow

```c
void main() {
    int8 counter = 0;

    // If statement
    if (counter < 10) {
        counter = counter + 1;
    }

    // While loop
    while (counter < 20) {
        counter = counter + 1;
    }

    // For loop
    for (int8 i = 0; i < 5; i = i + 1) {
        // Loop body
    }
}
```

### Functions

```c
// Simple function
int8 add_numbers(int8 a, int8 b) {
    return a + b;
}

void main() {
    int8 result = add_numbers(5, 3);
    // result now contains 8
}
```

---

## 📦 Modules and Code Organization

Astrid 2.0 supports modular programming to help you organize larger programs into reusable components.

### Creating Modules

Create separate `.ast` files in directories to organize your code:

```
mygame/
├── main.ast          # Main program
├── graphics/
│   └── shapes.ast   # Shape drawing functions
└── sound/
    └── effects.ast  # Sound effect functions
```

### shapes.ast (Graphics Module)
```c
// Export functions to make them available to other modules
export void draw_circle(pixel center_x, pixel center_y, pixel radius, color c) {
    // Bresenham's circle algorithm implementation
    int8 x = radius;
    int8 y = 0;
    int8 err = 0;

    while (x >= y) {
        set_pixel(center_x + x, center_y + y, c);
        set_pixel(center_x + y, center_y + x, c);
        set_pixel(center_x - y, center_y + x, c);
        set_pixel(center_x - x, center_y + y, c);
        set_pixel(center_x - x, center_y - y, c);
        set_pixel(center_x - y, center_y - x, c);
        set_pixel(center_x + y, center_y - x, c);
        set_pixel(center_x + x, center_y - y, c);

        y = y + 1;
        if (err <= 0) {
            err = err + 2 * y + 1;
        } else {
            x = x - 1;
            err = err + 2 * (y - x) + 1;
        }
    }
}

export void draw_rectangle(pixel x1, pixel y1, pixel x2, pixel y2, color c) {
    // Draw a filled rectangle
    for (pixel x = x1; x <= x2; x = x + 1) {
        for (pixel y = y1; y <= y2; y = y + 1) {
            set_pixel(x, y, c);
        }
    }
}
```

### effects.ast (Sound Module)
```c
export void play_beep(sound frequency, sound duration) {
    // Play a simple beep sound
    set_sound_frequency(0, frequency);
    set_sound_volume(0, 255);
    play_sound(0);
    
    // Simple delay (not accurate timing)
    for (int16 i = 0; i < duration; i = i + 1) {
        // Busy wait
    }
    
    stop_sound(0);
}

export void play_explosion() {
    // Play explosion sound effect
    set_sound_frequency(0, 100);
    set_sound_volume(0, 200);
    set_sound_waveform(0, 3);  // Noise
    play_sound(0);
    
    // Fade out
    for (int8 vol = 200; vol > 0; vol = vol - 10) {
        set_sound_volume(0, vol);
    }
    
    stop_sound(0);
}
```

### main.ast (Main Program)
```c
// Import modules to use their functions
import graphics.shapes;
import sound.effects;

void main() {
    // Clear screen
    clear_screen();
    
    // Draw some shapes
    graphics.shapes.draw_circle(64, 64, 20, 0x1F);   // Red circle
    graphics.shapes.draw_rectangle(100, 50, 150, 80, 0x03);  // Blue rectangle
    
    // Play sound effects
    sound.effects.play_beep(440, 1000);  // A4 note
    sound.effects.play_explosion();
}
```

### Benefits of Modules

- **Organization**: Keep related code together
- **Reusability**: Use the same functions in multiple programs
- **Maintainability**: Easier to update and debug
- **Collaboration**: Multiple developers can work on different modules

---

## 🎨 Graphics Programming Tutorial

### Drawing Pixels

```c
void main() {
    // Draw a diagonal line
    for (pixel i = 0; i < 50; i = i + 1) {
        set_pixel(i + 50, i + 50, 0x1F);  // Red pixels
    }
}
```

### Working with Colors

```c
void main() {
    color red = 0x1F;      // Full red
    color green = 0x0F;    // Full green
    color blue = 0x03;     // Full blue
    color white = 0x1F;    // White (all colors)

    // Draw colored squares
    set_pixel(50, 50, red);
    set_pixel(60, 50, green);
    set_pixel(70, 50, blue);
    set_pixel(80, 50, white);
}
```

### Graphics Layers

```c
void main() {
    // Draw on different layers
    layer background = 0;
    layer foreground = 1;

    set_layer(background);
    clear_screen(0x00);  // Clear background to black

    set_layer(foreground);
    set_pixel(100, 100, 0x1F);  // Draw on foreground
}
```

---

## 🔊 Sound Programming Tutorial

### Playing Simple Tones

```c
void main() {
    int8 channel = 0;
    int16 frequency = 440;  // A4 note
    int8 volume = 128;      // Medium volume
    int8 waveform = 1;      // Square wave

    play_sound(channel, frequency, volume, waveform);
    delay(1000);  // Play for 1 second
    stop_sound(channel);
}
```

### Musical Notes

```c
void play_note(int16 frequency, int16 duration) {
    int8 channel = 0;
    int8 volume = 192;
    int8 waveform = 1;

    play_sound(channel, frequency, volume, waveform);
    delay(duration);
    stop_sound(channel);
}

void main() {
    // Play a simple melody (C4, E4, G4)
    play_note(262, 500);  // C4
    delay(50);
    play_note(330, 500);  // E4
    delay(50);
    play_note(392, 500);  // G4
}
```

### Multiple Channels

```c
void main() {
    // Play two notes simultaneously
    play_sound(0, 440, 128, 1);  // Channel 0: A4
    play_sound(1, 554, 128, 1);  // Channel 1: C#5

    delay(1000);

    stop_sound(0);
    stop_sound(1);
}
```

---

## 🎮 Game Development Tutorial

### Simple Pong-like Game

```c
pixel ball_x = 128;
pixel ball_y = 128;
int8 ball_dx = 2;
int8 ball_dy = 1;

void update_ball() {
    // Update ball position
    ball_x = ball_x + ball_dx;
    ball_y = ball_y + ball_dy;

    // Bounce off walls
    if (ball_x <= 0 || ball_x >= 255) {
        ball_dx = -ball_dx;
    }
    if (ball_y <= 0 || ball_y >= 255) {
        ball_dy = -ball_dy;
    }
}

void draw_ball() {
    clear_screen(0x00);  // Clear screen
    set_pixel(ball_x, ball_y, 0x1F);  // Draw ball
}

void main() {
    while (true) {
        update_ball();
        draw_ball();
        delay(16);  // ~60 FPS
    }
}
```

### Input Handling

```c
pixel paddle_x = 128;
pixel paddle_y = 200;

void handle_input() {
    int8 key = get_key();

    if (key == 37) {  // Left arrow
        if (paddle_x > 0) {
            paddle_x = paddle_x - 5;
        }
    } else if (key == 39) {  // Right arrow
        if (paddle_x < 240) {
            paddle_x = paddle_x + 5;
        }
    }
}

void draw_paddle() {
    // Draw paddle as a line
    for (pixel i = 0; i < 30; i = i + 1) {
        set_pixel(paddle_x + i, paddle_y, 0x1F);
    }
}

void main() {
    while (true) {
        handle_input();
        clear_screen(0x00);
        draw_paddle();
        delay(16);
    }
}
```

---

## 🔧 System Programming Tutorial

### Timer Interrupts

```c
int16 frame_count = 0;

interrupt timer_interrupt() {
    frame_count = frame_count + 1;

    // Update animations every 60 frames (1 second at 60 FPS)
    if (frame_count % 60 == 0) {
        update_animation();
    }

    return;  // Hardware-specific return
}

void main() {
    enable_interrupts();

    while (true) {
        // Main game loop
        handle_input();
        update_game();
        render_frame();

        delay(16);
    }
}
```

### Memory Management

```c
// Simple memory allocation (conceptual)
int16 heap_start = 0x2000;
int16 next_free = 0x2000;

int16 allocate(int16 size) {
    int16 address = next_free;
    next_free = next_free + size;
    return address;
}

void main() {
    // Allocate some memory
    int16 buffer1 = allocate(100);
    int16 buffer2 = allocate(50);

    // Use the allocated memory...
}
```

---

## 🐛 Debugging Tips

### Common Issues

1. **Compilation Errors**
   - Check for missing semicolons
   - Verify variable types match usage
   - Ensure function calls have correct parameters

2. **Runtime Issues**
   - Use `delay()` to slow down execution
   - Add debug output with pixel drawing
   - Check coordinate bounds (0-255)

### Debug Techniques

```c
void debug_value(int8 value) {
    // Display value as pixels
    pixel x = 10;
    pixel y = 10;

    // Convert value to binary display
    for (int8 i = 0; i < 8; i = i + 1) {
        if ((value & (1 << i)) != 0) {
            set_pixel(x + i * 5, y, 0x1F);
        }
    }
}

void main() {
    int8 test_value = 42;
    debug_value(test_value);  // Shows binary representation
    delay(2000);
}
```

---

## 📚 Advanced Topics

### Performance Optimization

1. **Use appropriate types**: `int8` for small values, `int16` for addresses
2. **Minimize memory access**: Let the compiler handle register allocation
3. **Use hardware features**: Leverage builtin functions for performance

### Memory Layout

```
0x0000-0x00FF: Zero page (fast access)
0x0100-0x011F: Interrupt vectors
0x0120-0xFFFF: General memory
0xF000-0xF0FF: Sprite control blocks
```

### Best Practices

1. **Keep main loop fast**: Use interrupts for background tasks
2. **Use meaningful names**: Hardware types help document intent
3. **Test incrementally**: Build and test small pieces
4. **Comment hardware operations**: Explain what the code does

---

## 🔗 Next Steps

- Explore the [API Reference](API_REFERENCE.md) for detailed function documentation
- Check out the examples in the `examples/` directory
- Review the [Language Specification](Astrid2.0_Specification.md) for advanced features
- Join the community for support and examples

---

Happy coding with Astrid 2.0! 🎉
