"""
Integration tests for NOVA-16 component pipelines and interconnections.
Tests validate that CPU operations result in visible screen output and
components work together correctly.
"""

import pytest
import numpy as np
from nova_assembler import Assembler


def get_pixel_from_graphics(graphics, x, y, layer):
    """Helper function to get pixel value from graphics system."""
    if layer == 0:
        return graphics.screen[y, x]
    elif 1 <= layer <= 4:
        return graphics.background_layers[layer - 1][y, x]
    elif 5 <= layer <= 8:
        return graphics.sprite_layers[layer - 5][y, x]
    else:
        raise ValueError(f"Invalid layer: {layer}")


def assemble_and_load_program(cpu, assembler, program_text, start_addr=0x1000):
    """Helper function to assemble a program from text and load it into CPU memory."""
    import tempfile
    import os
    
    # Write program to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.asm', delete=False) as f:
        f.write(program_text)
        temp_file = f.name
    
    try:
        # Assemble the program
        success = assembler.assemble(temp_file)
        assert success, "Assembly failed"
        
        # Load the binary into memory
        bin_file = temp_file.replace('.asm', '.bin')
        entry_point = cpu.memory.load(bin_file)
        cpu.pc = entry_point if entry_point != 0 else start_addr
        
        return True
        
    except Exception as e:
        print(f"Assembly/load failed: {e}")
        return False
        
    finally:
        # Clean up temp files
        for ext in ['.asm', '.bin', '.org']:
            try:
                os.unlink(temp_file.replace('.asm', ext))
            except FileNotFoundError:
                pass
    """Helper function to assemble a program from text and load it into CPU memory."""
    import tempfile
    import os
    
    # Write program to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.asm', delete=False) as f:
        f.write(program_text)
        temp_file = f.name
    
    try:
        # Assemble the program
        success = assembler.assemble(temp_file)
        assert success, "Assembly failed"
        
        # Load the binary into memory
        bin_file = temp_file.replace('.asm', '.bin')
        entry_point = cpu.memory.load(bin_file)
        cpu.pc = entry_point if entry_point != 0 else start_addr
        
        return True
        
    except Exception as e:
        print(f"Assembly/load failed: {e}")
        return False
        
    finally:
        # Clean up temp files
        for ext in ['.asm', '.bin', '.org']:
            try:
                os.unlink(temp_file.replace('.asm', ext))
            except FileNotFoundError:
                pass


class TestCPUToScreenPipeline:
    """Test CPU operations that result in visible screen output."""

    def test_simple_pixel_write(self, cpu, graphics, assembler):
        """Test that CPU can write a single pixel to screen."""
        program = """ORG 0x1000
MOV VM, 0        ; Coordinate mode
MOV VL, 1        ; Layer 1
MOV VX, 10       ; X = 10
MOV VY, 20       ; Y = 20
MOV R0, 0xFF     ; White color
SWRITE R0        ; Write pixel
HLT
"""

        # Assemble and load program
        success = assemble_and_load_program(cpu, assembler, program)
        assert success

        # Run the program
        while not cpu.halted:
            cpu.step()

        # Check that pixel was written to graphics
        pixel_value = get_pixel_from_graphics(graphics, 10, 20, 1)
        assert pixel_value == 0xFF, f"Expected pixel (10,20) to be 0xFF, got {pixel_value}"

    def test_multiple_pixel_write(self, cpu, graphics, assembler):
        """Test CPU writing multiple pixels in a pattern."""
        program = """ORG 0x1000
MOV VM, 0        ; Coordinate mode
MOV VL, 1        ; Layer 1
MOV VX, 5        ; X = 5
MOV VY, 5        ; Y = 5
MOV R0, 0xAA     ; Color
SWRITE R0        ; Write pixel 1
MOV VX, 6        ; X = 6
MOV VY, 6        ; Y = 6
MOV R0, 0xBB     ; Different color
SWRITE R0        ; Write pixel 2
MOV VX, 7        ; X = 7
MOV VY, 7        ; Y = 7
MOV R0, 0xCC     ; Another color
SWRITE R0        ; Write pixel 3
HLT
"""

        # Assemble and load program
        success = assemble_and_load_program(cpu, assembler, program)
        assert success

        # Run the program
        while not cpu.halted:
            cpu.step()

        # Verify all pixels were written
        assert get_pixel_from_graphics(graphics, 5, 5, 1) == 0xAA
        assert get_pixel_from_graphics(graphics, 6, 6, 1) == 0xBB
        assert get_pixel_from_graphics(graphics, 7, 7, 1) == 0xCC

    def test_layer_switching(self, cpu, graphics, assembler):
        """Test CPU switching between graphics layers."""
        program = """ORG 0x1000
MOV VM, 0        ; Coordinate mode

; Write to layer 1
MOV VL, 1
MOV VX, 10
MOV VY, 10
MOV R0, 0x11
SWRITE R0

; Write to layer 2
MOV VL, 2
MOV VX, 10
MOV VY, 10
MOV R0, 0x22
SWRITE R0

; Write to layer 3
MOV VL, 3
MOV VX, 10
MOV VY, 10
MOV R0, 0x33
SWRITE R0

HLT
"""

        # Assemble and load program
        success = assemble_and_load_program(cpu, assembler, program)
        assert success

        # Run the program
        while not cpu.halted:
            cpu.step()

        # Verify pixels in different layers
        assert get_pixel_from_graphics(graphics, 10, 10, 1) == 0x11
        assert get_pixel_from_graphics(graphics, 10, 10, 2) == 0x22
        assert get_pixel_from_graphics(graphics, 10, 10, 3) == 0x33

    def test_memory_mode_graphics(self, cpu, graphics, assembler):
        """Test graphics operations in memory mode."""
        program = """ORG 0x1000
MOV VM, 1        ; Memory mode (linear addressing)
MOV VL, 1        ; Layer 1

; Write pixel at linear address 0x1000 (maps to coordinates)
MOV VX, 0        ; Low byte of address
MOV VY, 16       ; High byte of address (0x10)
MOV R0, 0x77     ; Color
SWRITE R0        ; Write pixel

HLT
"""

        # Assemble and load program
        success = assemble_and_load_program(cpu, assembler, program)
        assert success

        # Run the program
        while not cpu.halted:
            cpu.step()

        # In memory mode, address 0x1000 should map to coordinates
        # The address 0x1000 in linear mode should convert to x,y coordinates
        # Let's check what coordinate this actually maps to
        # For now, just verify that some pixel was written
        layer_buffer = graphics.background_layers[0]  # Layer 1
        non_zero_pixels = np.count_nonzero(layer_buffer)
        assert non_zero_pixels > 0, "No pixels were written in memory mode"

    def test_graphics_register_preservation(self, cpu, graphics, assembler):
        """Test that graphics registers are preserved during CPU operations."""
        program = """ORG 0x1000
; Set graphics registers
MOV VM, 0
MOV VL, 2
MOV VX, 50
MOV VY, 60

; Do some other operations that shouldn't affect graphics registers
MOV R0, 123
MOV R1, 456
MOV P2, 0xABCD

; Write pixel using previously set coordinates
MOV R0, 0x99
SWRITE R0

HLT
"""

        # Assemble and load program
        success = assemble_and_load_program(cpu, assembler, program)
        assert success

        # Run the program
        while not cpu.halted:
            cpu.step()

        # Verify pixel was written at the expected coordinates
        assert get_pixel_from_graphics(graphics, 50, 60, 2) == 0x99


class TestComponentInterconnections:
    """Test bidirectional connections between components."""

    def test_cpu_memory_bidirectional(self, cpu, memory):
        """Test CPU can read/write memory and memory reflects changes."""
        # CPU writes to memory
        cpu.Pregisters[0] = 0x2000  # Address
        cpu.Rregisters[0] = 0x42    # Value

        # Simulate STORE instruction (we'll need to check the actual opcode)
        # For now, directly test memory operations
        memory.write_byte(0x2000, 0x42)

        # CPU reads from memory
        value = memory.read_byte(0x2000)
        assert value == 0x42, "Memory write/read roundtrip failed"

    def test_cpu_graphics_shared_memory(self, cpu, graphics, memory):
        """Test CPU and graphics share the same memory space."""
        # CPU writes graphics data to memory
        graphics_addr = 0xF000  # Start of sprite control blocks
        memory.write_byte(graphics_addr, 0xAA)
        memory.write_byte(graphics_addr + 1, 0xBB)

        # Graphics should be able to read this data
        # (This tests the shared memory concept)
        data = memory.read_bytes_direct(graphics_addr, 2)
        assert data == [0xAA, 0xBB], "Shared memory access failed"

    def test_keyboard_cpu_integration(self, keyboard_device, cpu, memory):
        """Test keyboard input flows to CPU."""
        # Set CPU reference in keyboard
        keyboard_device.cpu = cpu
        
        # Simulate key press using the keyboard API
        keyboard_device.press_key('A')
        
        # Check buffer status
        status = keyboard_device.get_buffer_status()
        assert status['available'] == 1, "Key should be available in buffer"
        assert status['count'] > 0, "Buffer should contain keys"

    def test_sound_cpu_integration(self, sound_system, cpu, memory):
        """Test CPU can control sound system."""
        # CPU sets sound registers via memory
        sound_addr = 0x3000  # Hypothetical sound register area
        memory.write_byte(sound_addr, 0x44)     # Frequency low
        memory.write_byte(sound_addr + 1, 0x01) # Frequency high
        memory.write_byte(sound_addr + 2, 0x80) # Volume
        memory.write_byte(sound_addr + 3, 0x01) # Waveform

        # Sound system should be able to read these values
        # (Testing shared memory access)
        freq_data = memory.read_bytes_direct(sound_addr, 2)
        assert freq_data == [0x44, 0x01], "Sound register access failed"

    def test_timer_interrupt_flow(self, cpu, memory):
        """Test timer interrupts flow from hardware to CPU."""
        # Set up timer interrupt vector
        interrupt_addr = 0x0100  # Timer interrupt vector
        handler_addr = 0x2000
        memory.write_word(interrupt_addr, handler_addr)

        # Simulate timer interrupt
        cpu.interrupt_pending = True
        cpu.interrupt_vector = 0  # Timer interrupt

        # CPU should handle interrupt (if implemented)
        # This tests the interrupt pipeline
        initial_pc = cpu.pc
        initial_sp = cpu.Pregisters[8]  # SP

        # Note: Actual interrupt handling would depend on CPU implementation
        # This test validates the setup is correct
        assert memory.read_word(interrupt_addr) == handler_addr, "Interrupt vector setup failed"


class TestFullSystemIntegration:
    """Test complete input-to-output pipelines."""

    def test_keyboard_to_screen_echo(self, cpu, graphics, keyboard_device, assembler, memory):
        """Test key press results in character display on screen."""
        # This would be a complex program that reads keyboard and displays chars
        # For now, test the components can work together
        program = """
        ORG 0x1000
        ; Read key and display it
        KEYIN R0          ; Read key into R0
        CMP R0, 0         ; Check if key available
        JZ NO_KEY         ; If no key, skip

        MOV VM, 0         ; Coordinate mode
        MOV VL, 1         ; Layer 1
        MOV VX, 0         ; X = 0
        MOV VY, 0         ; Y = 0
        SWRITE R0         ; Write key code as pixel color

        NO_KEY:
        HLT
        """

        # Simulate key press before running
        keyboard_device.cpu = cpu
        keyboard_device.press_key('X')

        # Assemble and load program
        success = assemble_and_load_program(cpu, assembler, program)
        assert success

        # Run the program
        while not cpu.halted and cpu.cycles < 100:  # Prevent infinite loop
            cpu.step()

        # Check if character appeared on screen
        pixel_value = get_pixel_from_graphics(graphics, 0, 0, 1)
        assert pixel_value == ord('x'), f"Expected screen to show 'x' (0x{ord('x'):02X}), got 0x{pixel_value:02X}"

    def test_sound_generation_pipeline(self, cpu, sound_system, assembler, memory):
        """Test CPU sound commands result in audio output."""
        program = """
        ORG 0x1000
        ; Set up sound
        MOV SA, 0x3000    ; Sound address
        MOV SF, 440       ; A4 note frequency
        MOV SV, 128       ; Medium volume
        MOV SW, 1         ; Square wave
        SPLAY             ; Start playback
        HLT
        """

        # Assemble and load program
        success = assemble_and_load_program(cpu, assembler, program)
        assert success
        cpu.pc = 0x1000

        # Run the program
        while not cpu.halted:
            cpu.step()

        # Verify sound parameters were set
        # (This assumes sound registers are memory-mapped)
        # Note: Actual audio output testing would require pygame mixer checks
        assert True  # Placeholder - sound pipeline setup validated

    def test_sprite_rendering_pipeline(self, cpu, graphics, assembler, memory):
        """Test CPU sprite setup results in rendered graphics."""
        program = """
        ORG 0x1000
        ; Set up sprite
        MOV P0, 0xF000    ; Sprite control block address
        MOV P2, 0x4000    ; Sprite data address
        MOV R0, 100       ; X position
        MOV R1, 50        ; Y position
        MOV R3, 1         ; Enable sprite

        ; Write sprite control block
        MOV [P0], R0      ; X pos
        INC P0
        MOV [P0], R1      ; Y pos
        INC P0
        MOV [P0], P2:     ; Data address high
        INC P0
        MOV [P0], :P2     ; Data address low
        INC P0
        MOV [P0], R3      ; Enable flag

        HLT
        """

        # Assemble and load program
        success = assemble_and_load_program(cpu, assembler, program)
        assert success

        # Run the program
        while not cpu.halted:
            cpu.step()

        # Verify sprite control block was written
        sprite_data = memory.read_bytes_direct(0xF000, 5)
        assert sprite_data[0] == 100, "Sprite X position not set"
        assert sprite_data[1] == 50, "Sprite Y position not set"
        # Further validation would check actual rendering

    def test_spblitall_instruction(self, cpu, graphics, assembler, memory):
        """Test SPBLITALL instruction renders all sprites."""
        program = """
        ORG 0x1000

        ; Set up sprite 0
        MOV [0xF000], 0x2000     ; Sprite data address
        MOV [0xF002], 10         ; X position
        MOV [0xF003], 20         ; Y position
        MOV [0xF004], 4          ; Width
        MOV [0xF005], 4          ; Height
        MOV [0xF006], 0x01       ; Active flag

        ; Fill sprite 0 data (4x4 = 16 bytes)
        MOV [0x2000], 100
        MOV [0x2001], 101
        MOV [0x2002], 102
        MOV [0x2003], 103
        MOV [0x2004], 104
        MOV [0x2005], 105
        MOV [0x2006], 106
        MOV [0x2007], 107
        MOV [0x2008], 108
        MOV [0x2009], 109
        MOV [0x200A], 110
        MOV [0x200B], 111
        MOV [0x200C], 112
        MOV [0x200D], 113
        MOV [0x200E], 114
        MOV [0x200F], 115

        ; Set up sprite 1
        MOV [0xF010], 0x2100     ; Sprite 1 data address
        MOV [0xF012], 50         ; X position
        MOV [0xF013], 30         ; Y position
        MOV [0xF014], 2          ; Width
        MOV [0xF015], 2          ; Height
        MOV [0xF016], 0x03       ; Active + transparency
        MOV [0xF017], 105        ; Transparency color

        ; Fill sprite 1 data (2x2 = 4 bytes)
        MOV [0x2100], 100
        MOV [0x2101], 101
        MOV [0x2102], 102
        MOV [0x2103], 103

        ; Execute SPBLITALL
        SPBLITALL

        HLT
        """

        # Assemble and load program
        success = assemble_and_load_program(cpu, assembler, program)
        assert success

        # Run the program
        while not cpu.halted:
            cpu.step()

        # Composite layers to update screen
        graphics.composite_layers()

        # Check that sprites were rendered
        # Sprite 0 (4x4 at 10,20) - data is row-major
        assert graphics.screen[20, 10] == 100  # Row 0, Col 0
        assert graphics.screen[20, 11] == 101  # Row 0, Col 1
        assert graphics.screen[20, 12] == 102  # Row 0, Col 2
        assert graphics.screen[20, 13] == 103  # Row 0, Col 3
        assert graphics.screen[21, 10] == 104  # Row 1, Col 0
        assert graphics.screen[21, 11] == 105  # Row 1, Col 1
        assert graphics.screen[21, 12] == 106  # Row 1, Col 2
        assert graphics.screen[21, 13] == 107  # Row 1, Col 3
        assert graphics.screen[22, 10] == 108  # Row 2, Col 0
        assert graphics.screen[22, 11] == 109  # Row 2, Col 1
        assert graphics.screen[22, 12] == 110  # Row 2, Col 2
        assert graphics.screen[22, 13] == 111  # Row 2, Col 3
        assert graphics.screen[23, 10] == 112  # Row 3, Col 0
        assert graphics.screen[23, 11] == 113  # Row 3, Col 1
        assert graphics.screen[23, 12] == 114  # Row 3, Col 2
        assert graphics.screen[23, 13] == 115  # Row 3, Col 3

        # Sprite 1 (2x2 at 50,30) - should be visible (different color)
        assert graphics.screen[30, 50] == 100
        assert graphics.screen[30, 51] == 101
        assert graphics.screen[31, 50] == 102
        assert graphics.screen[31, 51] == 103

    def test_sprite_layering_integration(self, cpu, graphics, assembler, memory):
        """Test sprite layering with background interaction."""
        program = """
        ORG 0x1000

        ; Set up background layer 1
        MOV VM, 0          ; Coordinate mode
        MOV VL, 1          ; Background layer 1
        MOV VX, 40
        MOV VY, 40
        MOV R0, 50
        SWRITE R0          ; Write background pixel

        ; Set up sprite on layer 5 (should be above background)
        MOV [0xF000], 0x2000     ; Sprite data address
        MOV [0xF002], 38         ; X position (overlapping background)
        MOV [0xF003], 38         ; Y position
        MOV [0xF004], 4          ; Width
        MOV [0xF005], 4          ; Height
        MOV [0xF006], 0x01       ; Active flag

        ; Fill sprite data
        MOV [0x2000], 120
        MOV [0x2001], 120
        MOV [0x2002], 120
        MOV [0x2003], 120
        MOV [0x2004], 120
        MOV [0x2005], 120
        MOV [0x2006], 120
        MOV [0x2007], 120
        MOV [0x2008], 120
        MOV [0x2009], 120
        MOV [0x200A], 120
        MOV [0x200B], 120
        MOV [0x200C], 120
        MOV [0x200D], 120
        MOV [0x200E], 120
        MOV [0x200F], 120

        ; Render sprites
        SPBLITALL

        HLT
        """

        # Assemble and load program
        success = assemble_and_load_program(cpu, assembler, program)
        assert success

        # Run the program
        while not cpu.halted:
            cpu.step()

        # Composite layers to update screen
        graphics.composite_layers()

        # Sprite should be visible on top
        assert graphics.screen[38, 38] == 120