#!/usr/bin/env python3
"""
Comprehensive Astrid 2.0 Compiler Test Suite
Tests for missing features and bugs for systems/games programming
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

# Add the astrid2.0 src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from astrid2.main import AstridCompiler

def test_compilation(name, source_code, should_fail=False):
    """Test compilation of source code."""
    print(f"\n=== Testing: {name} ===")
    
    compiler = AstridCompiler()
    try:
        result = compiler.compile(source_code, f"test_{name}.ast", verbose=False)
        if should_fail:
            print(f"❌ {name}: Expected failure but compilation succeeded")
            return False
        else:
            print(f"✅ {name}: Compilation successful")
            return True
    except Exception as e:
        if should_fail:
            print(f"✅ {name}: Expected failure - {e}")
            return True
        else:
            print(f"❌ {name}: Compilation failed - {e}")
            return False

def main():
    """Run comprehensive compiler tests."""
    
    passed = 0
    total = 0
    
    # Test 1: Basic function parameters and return values
    total += 1
    if test_compilation("function_params", """
int16 add(int16 a, int16 b) {
    return a + b;
}

void main() {
    int16 result = add(10, 20);
    halt();
}
"""):
        passed += 1
    
    # Test 2: Arrays (should fail - not implemented)
    total += 1
    if test_compilation("arrays", """
void main() {
    int8 buffer[10];
    buffer[0] = 42;
    halt();
}
""", should_fail=True):
        passed += 1
    
    # Test 3: Structs (should fail - not implemented)
    total += 1
    if test_compilation("structs", """
struct Point {
    int16 x;
    int16 y;
}

void main() {
    Point p;
    p.x = 100;
    halt();
}
""", should_fail=True):
        passed += 1
    
    # Test 4: Interrupt handlers
    total += 1
    if test_compilation("interrupts", """
interrupt timer_handler() {
    set_pixel(100, 100, 15);
    return;
}

void main() {
    configure_timer(255, 80, 3);
    enable_interrupts();
    halt();
}
"""):
        passed += 1
    
    # Test 5: Complex graphics programming
    total += 1
    if test_compilation("complex_graphics", """
void draw_line(int8 x1, int8 y1, int8 x2, int8 y2, int8 color) {
    int8 dx = x2 - x1;
    int8 dy = y2 - y1;
    int8 steps = dx > dy ? dx : dy;
    
    for(int8 i = 0; i <= steps; i++) {
        int8 x = x1 + (dx * i) / steps;
        int8 y = y1 + (dy * i) / steps;
        set_pixel(x, y, color);
    }
}

void main() {
    set_layer(1);
    draw_line(0, 0, 255, 255, 31);
    halt();
}
"""):
        passed += 1
    
    # Test 6: Sound programming
    total += 1
    if test_compilation("sound_system", """
void play_note(int16 frequency, int8 volume, int8 duration) {
    play_tone(frequency, volume);
    // Need timer-based duration control
    configure_timer(duration, 10, 1);
}

void main() {
    play_note(440, 128, 100);  // A4 note
    halt();
}
"""):
        passed += 1
    
    # Test 7: Keyboard input handling
    total += 1
    if test_compilation("keyboard_input", """
void main() {
    while(true) {
        int8 key = read_keyboard();
        if(key != 0) {
            // Echo key as pixel color
            set_pixel(100, 100, key);
        }
    }
}
"""):
        passed += 1
    
    # Test 8: Memory management
    total += 1
    if test_compilation("memory_ops", """
void main() {
    // Direct memory access
    memory_write(0x2000, 42);
    int8 value = memory_read(0x2000);
    
    // Use value
    set_pixel(100, 100, value);
    halt();
}
"""):
        passed += 1
    
    # Test 9: Switch statements (should fail - not implemented)
    total += 1
    if test_compilation("switch_stmt", """
void main() {
    int8 key = read_keyboard();
    switch(key) {
        case 65: // 'A'
            set_pixel(100, 100, 31);
            break;
        case 66: // 'B'
            set_pixel(100, 100, 15);
            break;
        default:
            set_pixel(100, 100, 0);
            break;
    }
    halt();
}
""", should_fail=True):
        passed += 1
    
    # Test 10: Function pointers (should fail - not implemented)  
    total += 1
    if test_compilation("function_pointers", """
typedef void (*DrawFunc)(int8, int8, int8);

void draw_pixel(int8 x, int8 y, int8 color) {
    set_pixel(x, y, color);
}

void main() {
    DrawFunc draw = draw_pixel;
    draw(100, 100, 31);
    halt();
}
""", should_fail=True):
        passed += 1
    
    # Test 11: Game programming patterns
    total += 1
    if test_compilation("game_patterns", """
void update_sprite(int8 sprite_id, int8 x, int8 y, int8 visible) {
    // This should use actual sprite system calls
    set_pixel(x, y, visible ? 31 : 0);
}

void main() {
    // Game loop
    for(int16 frame = 0; frame < 1000; frame++) {
        // Update sprites
        for(int8 i = 0; i < 8; i++) {
            update_sprite(i, frame % 256, 100, true);
        }
        
        // Simple frame delay
        for(int16 delay = 0; delay < 100; delay++) {
            // Busy wait
        }
    }
    halt();
}
"""):
        passed += 1
    
    # Test 12: Hardware register access
    total += 1
    if test_compilation("hardware_access", """
void main() {
    // These should be built-in hardware access functions
    set_video_mode(0);  // Coordinate mode
    set_video_layer(1); // Active layer
    
    // Timer setup
    set_timer_value(0);
    set_timer_match(255);
    
    halt();
}
""", should_fail=True):  # Should fail - these functions don't exist
        passed += 1
    
    print(f"\n=== TEST SUMMARY ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed < total:
        print(f"\n❌ {total - passed} tests failed - indicating missing features or bugs")
        return 1
    else:
        print(f"\n✅ All tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
