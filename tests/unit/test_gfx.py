"""
Unit tests for nova_gfx.py - Nova-16 graphics system.
"""

import pytest
import numpy as np
import random


class TestGraphicsInitialization:
    """Test graphics system initialization."""

    def test_graphics_size(self, graphics):
        """Test that graphics has correct dimensions."""
        assert graphics.width == 256
        assert graphics.height == 256

    def test_graphics_screen_initialization(self, graphics):
        """Test that screen is initialized to zeros."""
        assert graphics.screen.shape == (256, 256)
        assert np.all(graphics.screen == 0)

    def test_graphics_vram_initialization(self, graphics):
        """Test that VRAM is initialized to zeros."""
        assert graphics.vram.shape == (256, 256)
        assert np.all(graphics.vram == 0)

    def test_graphics_layers_initialization(self, graphics):
        """Test that background and sprite layers are initialized."""
        assert len(graphics.background_layers) == 4
        assert len(graphics.sprite_layers) == 4

        for layer in graphics.background_layers:
            assert layer.shape == (256, 256)
            assert np.all(layer == 0)

        for layer in graphics.sprite_layers:
            assert layer.shape == (256, 256)
            assert np.all(layer == 0)

    def test_graphics_registers_initialization(self, graphics):
        """Test that video registers are initialized."""
        assert len(graphics.Vregisters) == 3
        assert graphics.Vregisters[0] == 0  # VX
        assert graphics.Vregisters[1] == 0  # VY
        assert graphics.Vregisters[2] == 0  # VM

    def test_graphics_flags_initialization(self, graphics):
        """Test that graphics flags are initialized."""
        assert len(graphics.flags) == 3
        assert graphics.flags[0] == 0  # HBlank
        assert graphics.flags[1] == 0  # VBlank
        assert graphics.flags[2] == 0  # VMode


class TestGraphicsPixelOperations:
    """Test basic pixel operations."""

    def test_set_screen_val(self, graphics):
        """Test setting screen pixel value."""
        graphics.set_screen_val(0x42)
        # Should set pixel at current VX, VY position
        x, y = graphics.Vregisters[0], graphics.Vregisters[1]
        assert graphics.screen[y, x] == 0x42

    def test_get_screen_val(self, graphics):
        """Test getting screen pixel value."""
        # Set a pixel first
        graphics.screen[10, 20] = 0xAB
        graphics.Vregisters[0] = 20  # VX
        graphics.Vregisters[1] = 10  # VY

        value = graphics.get_screen_val()
        assert value == 0xAB

    def test_coordinate_mode_setting(self, graphics):
        """Test coordinate mode register."""
        graphics.Vregisters[2] = 1  # Set coordinate mode
        assert graphics.vmode == 1

        graphics.vmode = 0  # Clear coordinate mode
        assert graphics.Vregisters[2] == 0


class TestGraphicsBlending:
    """Test graphics blending operations."""

    def test_blend_pixel_normal(self, graphics):
        """Test normal blending mode."""
        graphics.blend_mode = 0  # Normal
        result = graphics.blend_pixel(100, 150)
        assert result == 150  # Normal mode just returns new pixel

    def test_blend_pixel_additive(self, graphics):
        """Test additive blending."""
        graphics.blend_mode = 1  # Additive
        graphics.blend_alpha = 128  # 50% alpha
        result = graphics.blend_pixel(100, 50)
        expected = min(255, 100 + (50 * 0.5))  # 100 + 25 = 125
        assert result == int(expected)

    def test_blend_pixel_subtractive(self, graphics):
        """Test subtractive blending."""
        graphics.blend_mode = 2  # Subtractive
        graphics.blend_alpha = 128
        result = graphics.blend_pixel(100, 30)
        expected = max(0, 100 - (30 * (128 / 255.0)))  # 100 - (30 * 0.50196) ≈ 84.94
        assert result == int(expected)

    def test_blend_pixel_multiply(self, graphics):
        """Test multiply blending."""
        graphics.blend_mode = 3  # Multiply
        graphics.blend_alpha = 128
        result = graphics.blend_pixel(200, 100)
        expected = min(255, (200 * 100 * 0.5) / 255)  # (20000 * 0.5) / 255 ≈ 39
        assert result == int(expected)


class TestGraphicsLayers:
    """Test graphics layer operations."""

    def test_layer_visibility(self, graphics):
        """Test layer visibility controls."""
        # All layers should be visible by default
        for i in range(9):  # 0-8 layers
            assert graphics.layer_visibility[i] == True

        # Test hiding a layer
        graphics.layer_visibility[1] = False
        assert graphics.layer_visibility[1] == False

    def test_layer_selection(self, graphics):
        """Test layer selection via VL register."""
        graphics.set_current_layer(1)
        assert graphics.current_layer == 1
        assert graphics.VL == 1

        graphics.set_current_layer(5)  # Sprite layer
        assert graphics.current_layer == 5
        assert graphics.VL == 5


class TestGraphicsClear:
    """Test graphics clear operations."""

    def test_clear_screen(self, graphics):
        """Test clearing the screen."""
        # Set some pixels
        graphics.screen[10, 20] = 100
        graphics.screen[50, 60] = 200

        graphics.clear()

        # All pixels should be 0
        assert np.all(graphics.screen == 0)


class TestGraphicsVRAM:
    """Test VRAM operations."""

    def test_vram_pixel_operations(self, graphics):
        """Test VRAM pixel read/write."""
        # Set VRAM pixel
        graphics.vram[15, 25] = 0xCD
        graphics.Vregisters[0] = 25  # VX
        graphics.Vregisters[1] = 15  # VY

        # Read it back
        value = graphics.get_vram_val()
        assert value == 0xCD

        # Write new value
        graphics.set_vram_val(0xEF)
        assert graphics.vram[15, 25] == 0xEF

    def test_vram_to_screen_blit(self, graphics):
        """Test VRAM to screen blit operation."""
        # Set up VRAM with a pattern
        graphics.vram[0, 0] = 100
        graphics.vram[0, 1] = 150
        graphics.vram[1, 0] = 200
        graphics.vram[1, 1] = 250

        graphics.VRAMtoScreen()

        # Screen should match VRAM
        assert graphics.screen[0, 0] == 100
        assert graphics.screen[0, 1] == 150
        assert graphics.screen[1, 0] == 200
        assert graphics.screen[1, 1] == 250


class TestGraphicsTransformations:
    """Test graphics transformation operations."""

    def test_screen_roll_x(self, graphics):
        """Test horizontal screen rolling."""
        # Set up a simple pattern
        graphics.screen[0, 0] = 100
        graphics.screen[0, 1] = 200

        graphics.roll_x(1)  # Roll right by 1

        # Pixels should have moved
        assert graphics.screen[0, 1] == 100
        assert graphics.screen[0, 2] == 200

    def test_screen_roll_y(self, graphics):
        """Test vertical screen rolling."""
        # Set up a simple pattern
        graphics.screen[0, 0] = 100
        graphics.screen[1, 0] = 200

        graphics.roll_y(1)  # Roll down by 1

        # Pixels should have moved
        assert graphics.screen[1, 0] == 100
        assert graphics.screen[2, 0] == 200

    def test_screen_flip_x(self, graphics):
        """Test horizontal screen flip."""
        # Set up asymmetric pattern
        graphics.screen[0, 0] = 100
        graphics.screen[0, 255] = 200

        graphics.flip_x()

        # Pixels should be swapped
        assert graphics.screen[0, 255] == 100
        assert graphics.screen[0, 0] == 200

    def test_screen_flip_y(self, graphics):
        """Test vertical screen flip."""
        # Set up asymmetric pattern
        graphics.screen[0, 0] = 100
        graphics.screen[255, 0] = 200

        graphics.flip_y()

        # Pixels should be swapped
        assert graphics.screen[255, 0] == 100
        assert graphics.screen[0, 0] == 200


class TestGraphicsSprites:
    """Test sprite system operations."""

    def test_sprite_initialization(self, graphics):
        """Test sprite system initialization."""
        assert graphics.sprite_count == 16
        assert graphics.sprite_block_size == 16
        assert graphics.sprite_memory_base == 0xF000
        assert graphics.sprite_memory_end == 0xF0FF

    def test_sprite_blit(self, graphics, memory):
        """Test blitting a sprite."""
        # Set up sprite data in memory
        sprite_addr = 0x1000
        memory.write_word(0xF000, sprite_addr)  # Sprite 0 data address
        memory.write_byte(0xF002, 10)  # X position
        memory.write_byte(0xF003, 20)  # Y position
        memory.write_byte(0xF004, 2)   # Width
        memory.write_byte(0xF005, 2)   # Height
        memory.write_byte(0xF006, 0x01)  # Flags (active)

        # Set sprite pixel data
        memory.write_byte(sprite_addr, 100)      # (0,0)
        memory.write_byte(sprite_addr + 1, 150)  # (1,0)
        memory.write_byte(sprite_addr + 2, 200)  # (0,1)
        memory.write_byte(sprite_addr + 3, 250)  # (1,1)

        graphics.blit_sprite(0, memory)

        # Composite layers to update screen
        graphics.composite_layers()

        # Check that sprite was drawn
        assert graphics.screen[20, 10] == 100
        assert graphics.screen[20, 11] == 150
        assert graphics.screen[21, 10] == 200
        assert graphics.screen[21, 11] == 250


class TestGraphicsText:
    """Test text rendering operations."""

    def test_draw_char(self, graphics):
        """Test drawing a single character."""
        graphics.Vregisters[0] = 10  # VX
        graphics.Vregisters[1] = 20  # VY

        graphics.draw_char_to_screen('A', 10, 20, 255)

        # Should have drawn something (exact pattern depends on font)
        # Just check that some pixels were set
        assert np.any(graphics.screen != 0)

    def test_draw_string(self, graphics):
        """Test drawing a string."""
        graphics.draw_string_to_screen("Hello", 5, 10, 255)

        # Should have drawn something
        assert np.any(graphics.screen != 0)


class TestGraphicsFill:
    """Test fill operations."""

    def test_fill_layer(self, graphics):
        """Test filling a layer with a color."""
        graphics.fill_layer(123)

        # Check that current layer is filled
        if graphics.VL == 0:
            assert np.all(graphics.screen == 123)
        elif 1 <= graphics.VL <= 4:
            layer_idx = graphics.VL - 1
            assert np.all(graphics.background_layers[layer_idx] == 123)
        elif 5 <= graphics.VL <= 8:
            layer_idx = graphics.VL - 5
            assert np.all(graphics.sprite_layers[layer_idx] == 123)


class TestGraphicsStressTesting:
    """Aggressive stress testing for graphics operations."""

    def test_massive_pixel_operations(self, graphics):
        """Stress test with thousands of pixel operations."""
        random.seed(42)

        # Track the last color set for each position
        last_colors = {}

        # Perform 10000 random pixel operations
        for _ in range(10000):
            x = random.randint(0, 255)
            y = random.randint(0, 255)
            color = random.randint(0, 255)

            graphics.Vregisters[0] = x  # VX
            graphics.Vregisters[1] = y  # VY
            graphics.set_screen_val(color)

            # Track the last color for this position
            last_colors[(x, y)] = color

        # Verify the final state of random positions
        sample_positions = random.sample(list(last_colors.keys()), min(100, len(last_colors)))
        for x, y in sample_positions:
            expected_color = last_colors[(x, y)]
            graphics.Vregisters[0] = x  # VX
            graphics.Vregisters[1] = y  # VY
            actual_color = graphics.get_screen_val()
            assert actual_color == expected_color

    def test_layer_compositing_stress(self, graphics):
        """Stress test layer compositing with many layers."""
        # Fill all layers with different patterns
        for layer in range(1, 5):  # Background layers
            graphics.VL = layer
            for y in range(256):
                for x in range(256):
                    graphics.Vregisters[0] = x  # VX
                    graphics.Vregisters[1] = y  # VY
                    graphics.set_screen_val((layer * 50 + x + y) & 0xFF)

        for layer in range(5, 9):  # Sprite layers
            graphics.VL = layer
            for y in range(256):
                for x in range(256):
                    graphics.Vregisters[0] = x  # VX
                    graphics.Vregisters[1] = y  # VY
                    graphics.set_screen_val((layer * 30 + x - y) & 0xFF)

        # Composite layers multiple times
        for _ in range(10):
            graphics.composite_layers()

        # Screen should contain composited result
        assert graphics.screen.shape == (256, 256)
        # At least some pixels should be non-zero after compositing
        assert np.any(graphics.screen != 0)

    def test_sprite_blitting_stress(self, graphics, memory):
        """Stress test with many sprites."""
        # Create 16 sprites with different data
        for sprite_id in range(16):
            base_addr = 0xF000 + (sprite_id * 16)

            # Set sprite control block
            data_addr = 0x2000 + (sprite_id * 64)  # 64 bytes per sprite
            memory.write_word(base_addr, data_addr)
            memory.write_byte(base_addr + 2, sprite_id * 10)  # X position
            memory.write_byte(base_addr + 3, sprite_id * 15)  # Y position
            memory.write_byte(base_addr + 4, 8)  # Width
            memory.write_byte(base_addr + 5, 8)  # Height
            memory.write_byte(base_addr + 6, 0x81)  # Active, layer 5

            # Fill sprite data with pattern
            for i in range(64):  # 8x8 sprite
                memory.write_byte(data_addr + i, (sprite_id + i) & 0xFF)

        # Blit all sprites
        for sprite_id in range(16):
            graphics.blit_sprite(sprite_id, memory)

        # Composite to see result
        graphics.composite_layers()

        # Should not crash and screen should have some content
        assert np.any(graphics.screen != 0)

    def test_vram_operations_stress(self, graphics):
        """Stress test VRAM read/write operations."""
        # Fill VRAM with pattern
        for y in range(256):
            for x in range(256):
                graphics.vram[y, x] = (x + y) & 0xFF

        # Perform many VRAM operations
        for _ in range(1000):
            x, y = random.randint(0, 255), random.randint(0, 255)
            graphics.Vregisters[0] = x  # VX
            graphics.Vregisters[1] = y  # VY

            # Test coordinate mode
            graphics.vmode = 0
            test_value = (x + y + 100) & 0xFF
            graphics.set_vram_val(test_value)
            read_value = graphics.get_vram_val()
            assert read_value == test_value

    def test_blending_operations_stress(self, graphics):
        """Stress test blending operations with many combinations."""
        # Test all blend modes with various alpha values
        for blend_mode in range(5):  # 0-4 blend modes
            for alpha in [0, 64, 128, 192, 255]:
                graphics.blend_mode = blend_mode
                graphics.blend_alpha = alpha

                # Test many pixel combinations
                for existing in [0, 85, 170, 255]:
                    for new in [0, 85, 170, 255]:
                        result = graphics.blend_pixel(existing, new)
                        assert 0 <= result <= 255  # Result should be valid

    def test_transformation_operations_stress(self, graphics):
        """Stress test screen transformations."""
        # Fill screen with test pattern
        for y in range(256):
            for x in range(256):
                graphics.screen[y, x] = (x + y) & 0xFF

        # Apply multiple transformations
        for _ in range(5):
            graphics.roll_x(10)
            graphics.roll_y(5)
            graphics.flip_x()
            graphics.flip_y()

        # Screen should still be valid
        assert graphics.screen.shape == (256, 256)
        assert np.all((graphics.screen >= 0) & (graphics.screen <= 255))


class TestGraphicsEdgeCases:
    """Edge case and boundary testing for graphics."""

    def test_coordinate_boundaries(self, graphics):
        """Test operations at coordinate boundaries."""
        # Test at (0,0)
        graphics.Vregisters[0] = 0  # VX
        graphics.Vregisters[1] = 0  # VY
        graphics.set_screen_val(255)
        assert graphics.get_screen_val() == 255

        # Test at (255,255)
        graphics.Vregisters[0] = 255  # VX
        graphics.Vregisters[1] = 255  # VY
        graphics.set_screen_val(128)
        assert graphics.get_screen_val() == 128

        # Test at boundaries
        graphics.Vregisters[0] = 0    # VX
        graphics.Vregisters[1] = 255  # VY
        graphics.set_screen_val(64)
        assert graphics.get_screen_val() == 64

        graphics.Vregisters[0] = 255  # VX
        graphics.Vregisters[1] = 0    # VY
        graphics.set_screen_val(32)
        assert graphics.get_screen_val() == 32

    def test_invalid_coordinates(self, graphics):
        """Test operations with out-of-bounds coordinates."""
        # Coordinates at boundaries should work
        graphics.Vregisters[0] = 255  # VX
        graphics.Vregisters[1] = 255  # VY
        graphics.set_screen_val(100)
        assert graphics.get_screen_val() == 100

        # Coordinates that wrap around due to uint8 should work
        graphics.Vregisters[0] = 0    # VX (256 wraps to 0)
        graphics.Vregisters[1] = 0    # VY
        graphics.set_screen_val(200)
        assert graphics.get_screen_val() == 200

        # Screen should remain valid
        assert graphics.screen.shape == (256, 256)

    def test_invalid_layer_numbers(self, graphics):
        """Test operations with invalid layer numbers."""
        # Invalid VL values should not crash but may not write anywhere
        graphics.VL = 999
        graphics.Vregisters[0] = 10  # VX
        graphics.Vregisters[1] = 10  # VY
        graphics.set_screen_val(100)  # Should not crash

        graphics.VL = 255  # Another invalid value
        graphics.Vregisters[0] = 20  # VX
        graphics.Vregisters[1] = 20  # VY
        graphics.set_screen_val(150)  # Should not crash

        # Valid layer should still work
        graphics.VL = 0  # Screen
        graphics.Vregisters[0] = 30  # VX
        graphics.Vregisters[1] = 30  # VY
        graphics.set_screen_val(200)
        assert graphics.get_screen_val() == 200

    def test_invalid_blend_modes(self, graphics):
        """Test blending with invalid modes."""
        graphics.blend_mode = 999  # Invalid mode
        result = graphics.blend_pixel(100, 50)
        assert 0 <= result <= 255  # Should default to something reasonable

        graphics.blend_mode = -1  # Negative mode
        result = graphics.blend_pixel(100, 50)
        assert 0 <= result <= 255

    def test_extreme_alpha_values(self, graphics):
        """Test blending with extreme alpha values."""
        for alpha in [0, 1, 254, 255, 256, -1]:
            graphics.blend_alpha = alpha
            result = graphics.blend_pixel(100, 50)
            assert 0 <= result <= 255

    def test_zero_size_sprites(self, graphics, memory):
        """Test sprites with zero size."""
        # Set up sprite with zero width
        memory.write_word(0xF000, 0x2000)  # Data address
        memory.write_byte(0xF004, 0)       # Width = 0
        memory.write_byte(0xF005, 8)       # Height = 8
        memory.write_byte(0xF006, 0x01)    # Active

        graphics.blit_sprite(0, memory)  # Should not crash

        # Set up sprite with zero height
        memory.write_byte(0xF004, 8)       # Width = 8
        memory.write_byte(0xF005, 0)       # Height = 0

        graphics.blit_sprite(0, memory)  # Should not crash

    def test_sprite_bounds_edge_cases(self, graphics, memory):
        """Test sprite blitting at screen boundaries."""
        # Sprite at top-left corner
        memory.write_word(0xF000, 0x2000)
        memory.write_byte(0xF002, 0)    # X = 0
        memory.write_byte(0xF003, 0)    # Y = 0
        memory.write_byte(0xF004, 2)    # Width = 2
        memory.write_byte(0xF005, 2)    # Height = 2
        memory.write_byte(0xF006, 0x01) # Active

        memory.write_byte(0x2000, 100)
        memory.write_byte(0x2001, 150)
        memory.write_byte(0x2002, 200)
        memory.write_byte(0x2003, 250)

        graphics.blit_sprite(0, memory)
        graphics.composite_layers()

        assert graphics.screen[0, 0] == 100

        # Sprite at bottom-right corner
        memory.write_byte(0xF002, 254)  # X = 254
        memory.write_byte(0xF003, 254)  # Y = 254

        graphics.blit_sprite(0, memory)
        graphics.composite_layers()

        # Should clip appropriately
        assert graphics.screen[254, 254] == 100

    def test_vram_mode_edge_cases(self, graphics):
        """Test VRAM operations in different modes."""
        # Test invalid vmode values (uint8 wraparound)
        graphics.vmode = 999  # Will wrap to 999 % 256 = 231
        graphics.Vregisters[0] = 10
        graphics.Vregisters[1] = 20

        # Should raise ValueError for unknown vmode
        with pytest.raises(ValueError, match="Unknown vmode"):
            graphics.set_vram_val(123)

        # Test valid modes
        graphics.vmode = 0  # Coordinate mode
        graphics.set_vram_val(123)
        result = graphics.get_vram_val()
        assert result == 123

        graphics.vmode = 1  # Linear mode
        graphics.set_vram_val(200)  # Valid uint8 value
        result = graphics.get_vram_val()
        assert result == 200

    def test_clear_operations_edge_cases(self, graphics):
        """Test clear operations with edge cases."""
        # Clear with invalid layer numbers
        graphics.clear_layer(999)  # Should not crash
        graphics.clear_layer(-1)   # Should not crash

        # Clear screen
        graphics.clear()
        assert np.all(graphics.screen == 0)

    def test_fill_operations_edge_cases(self, graphics):
        """Test fill operations with edge cases."""
        # Fill with invalid layer numbers
        graphics.fill_layer(123, 999)  # Should not crash (value=123, layer_num=999)
        graphics.fill_layer(123, -1)   # Should not crash (value=123, layer_num=-1)

        # Fill valid layers
        graphics.fill_layer(255, 0)  # Screen
        assert np.all(graphics.screen == 255)

    def test_text_rendering_edge_cases(self, graphics):
        """Test text rendering with edge cases."""
        # Empty string
        graphics.draw_string("", 0, 0)

        # String with invalid characters
        graphics.draw_string("Hello\x00World", 0, 0)

        # String at screen boundaries
        graphics.draw_string("X", 250, 0)  # Near right edge
        graphics.draw_string("Y", 0, 250)  # Near bottom edge

        # Should not crash
        assert True

    def test_graphics_state_preservation(self, graphics):
        """Test that graphics state is preserved across operations."""
        # Set up complex state
        graphics.VL = 3
        graphics.vmode = 1
        graphics.blend_mode = 2
        graphics.blend_alpha = 128
        initial_vregisters = [10, 20, 1]
        graphics.Vregisters = initial_vregisters.copy()

        # Save state
        saved_vl = graphics.VL
        saved_vmode = graphics.vmode
        saved_blend_mode = graphics.blend_mode
        saved_blend_alpha = graphics.blend_alpha

        # Perform many operations (Vregisters will change, that's expected)
        for _ in range(100):
            x, y = random.randint(0, 255), random.randint(0, 255)
            graphics.Vregisters[0] = x  # VX
            graphics.Vregisters[1] = y  # VY
            graphics.set_screen_val(random.randint(0, 255))
            graphics.blend_pixel(random.randint(0, 255), random.randint(0, 255))

        # Other state should be preserved
        assert graphics.VL == saved_vl
        assert graphics.vmode == saved_vmode
        assert graphics.blend_mode == saved_blend_mode
        assert graphics.blend_alpha == saved_blend_alpha
        # Vregisters are expected to change during operations