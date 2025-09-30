import numpy as np
from font import font_data

class GFX:
    """Simplified GFX class for Star interpreter."""

    def __init__(self, width=256, height=256):
        self.width = width
        self.height = height
        self.screen = np.zeros((self.height, self.width), dtype=np.uint8)
        self.VL = 0  # Current layer
        self.palette = self._create_default_palette()

    def _create_default_palette(self):
        """Create a default color palette."""
        palette = np.zeros((256, 3), dtype=np.uint8)
        # Grayscale
        for i in range(16):
            palette[i] = [i * 17] * 3
        # Red
        for i in range(16):
            palette[16 + i] = [i * 17, 0, 0]
        # Green
        for i in range(16):
            palette[32 + i] = [0, i * 17, 0]
        # Blue
        for i in range(16):
            palette[48 + i] = [0, 0, i * 17]
        # And so on... (simplified)
        return palette

    def clear(self):
        """Clear the screen."""
        self.screen.fill(0)

    def _set_pixel_fast(self, x, y, color):
        """Set a pixel on the screen."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.screen[y, x] = color

    def draw_line(self, x1, y1, x2, y2, color):
        """Draw a line using Bresenham's algorithm."""
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        while True:
            self._set_pixel_fast(x1, y1, color)
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

    def draw_circle(self, center_x, center_y, radius, color, filled=True):
        """Draw a circle."""
        x = radius
        y = 0
        err = 0

        while x >= y:
            if filled:
                # Draw filled circle by drawing horizontal lines
                for i in range(center_x - x, center_x + x + 1):
                    self._set_pixel_fast(i, center_y + y, color)
                    self._set_pixel_fast(i, center_y - y, color)
                for i in range(center_x - y, center_x + y + 1):
                    self._set_pixel_fast(i, center_y + x, color)
                    self._set_pixel_fast(i, center_y - x, color)
            else:
                # Draw circle outline
                self._set_pixel_fast(center_x + x, center_y + y, color)
                self._set_pixel_fast(center_x + y, center_y + x, color)
                self._set_pixel_fast(center_x - y, center_y + x, color)
                self._set_pixel_fast(center_x - x, center_y + y, color)
                self._set_pixel_fast(center_x - x, center_y - y, color)
                self._set_pixel_fast(center_x - y, center_y - x, color)
                self._set_pixel_fast(center_x + y, center_y - x, color)
                self._set_pixel_fast(center_x + x, center_y - y, color)

            y += 1
            err += 1 + 2 * y
            if 2 * (err - x) + 1 > 0:
                x -= 1
                err += 1 - 2 * x

    def draw_string(self, text, x, y, color=255, background=None, char_spacing=8):
        """Draw text string."""
        for i, char in enumerate(text):
            self.draw_char(char, x + i * char_spacing, y, color, background)

    def draw_char(self, char, x, y, color=255, background=None):
        """Draw a single character."""
        if char not in font_data:
            return

        char_data = font_data[char]
        for row in range(8):
            for col in range(8):
                if char_data[row] & (1 << (7 - col)):
                    self._set_pixel_fast(x + col, y + row, color)
                elif background is not None:
                    self._set_pixel_fast(x + col, y + row, background)

    def set_current_layer(self, layer):
        """Set current layer (simplified - just store it)."""
        self.VL = layer

    def get_screen(self):
        """Get the screen buffer."""
        return self.screen