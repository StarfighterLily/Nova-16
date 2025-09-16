"""
Astrid 2.0 Built-in Graphics Functions
Provides hardware-accelerated graphics operations for Nova-16.
"""

from typing import Dict, List, Any
from ..utils.logger import get_logger

logger = get_logger(__name__)


class GraphicsBuiltins:
    """Built-in graphics functions for Astrid 2.0."""

    def __init__(self):
        self.functions = {
            'set_pixel': self._set_pixel,
            'get_pixel': self._get_pixel,
            'clear_screen': self._clear_screen,
            'draw_line': self._draw_line,
            'draw_rect': self._draw_rect,
            'fill_rect': self._fill_rect,
            'set_layer': self._set_layer,
            'set_blend_mode': self._set_blend_mode,
            'scroll_layer': self._scroll_layer,
            'roll_screen_x': self._roll_screen_x,
            'roll_screen_y': self._roll_screen_y,
            'flip_screen_x': self._flip_screen_x,
            'flip_screen_y': self._flip_screen_y,
            'rotate_screen_left': self._rotate_screen_left,
            'rotate_screen_right': self._rotate_screen_right,
            'shift_screen_x': self._shift_screen_x,
            'shift_screen_y': self._shift_screen_y,
            'set_sprite': self._set_sprite,
            'move_sprite': self._move_sprite,
            'show_sprite': self._show_sprite,
            'hide_sprite': self._hide_sprite,
        }

    def get_function(self, name: str):
        """Get a built-in function by name."""
        return self.functions.get(name)

    def _set_pixel(self, x: int, y: int, color: int) -> str:
        """
        Set a pixel at coordinates (x, y) to the specified color.

        Args:
            x: X coordinate (0-255)
            y: Y coordinate (0-255)
            color: Color value (0-31)

        Returns:
            Assembly code for setting the pixel
        """
        # Use R8 as temp register for color to avoid conflicts with common loop variables (R0-R3)
        return f"""
; Set pixel at ({x}, {y}) to color {color}
MOV VM, 0
MOV VX, {x}
MOV VY, {y}
MOV R8, {color}
SWRITE R8
"""

    def _get_pixel(self, x: int, y: int) -> str:
        """
        Get the color of a pixel at coordinates (x, y).

        Args:
            x: X coordinate (0-255)
            y: Y coordinate (0-255)

        Returns:
            Assembly code for reading the pixel
        """
        return f"""
; Get pixel at ({x}, {y})
MOV VX, {x}
MOV VY, {y}
SREAD R0
"""

    def _clear_screen(self, color: int = 0) -> str:
        """
        Clear the screen to the specified color.

        Args:
            color: Color value (0-31), defaults to black

        Returns:
            Assembly code for clearing the screen
        """
        return f"""
; Clear screen to color {color}
SFILL {color}
"""

    def _draw_line(self, x1: int, y1: int, x2: int, y2: int, color: int) -> str:
        """
        Draw a line from (x1, y1) to (x2, y2) in the specified color.
        Uses Bresenham's line algorithm implemented in software.

        Args:
            x1, y1: Start coordinates
            x2, y2: End coordinates
            color: Color value (0-31)

        Returns:
            Assembly code for drawing the line
        """
        return f"""
; Draw line from ({x1}, {y1}) to ({x2}, {y2}) in color {color}
; Software implementation using Bresenham's algorithm
MOV VM, 0               ; Coordinate mode
MOV R0, {x1}            ; x1
MOV R1, {y1}            ; y1
MOV R2, {x2}            ; x2
MOV R3, {y2}            ; y2
MOV R4, {color}         ; color
MOV R5, 0               ; dx = abs(x2 - x1)
SUB R5, R2, R0
CMP R5, 0
JGE line_dx_pos
NEG R5
line_dx_pos:
MOV R6, 0               ; dy = abs(y2 - y1)
SUB R6, R3, R1
CMP R6, 0
JGE line_dy_pos
NEG R6
line_dy_pos:
MOV R7, 0               ; sx = x1 < x2 ? 1 : -1
CMP R0, R2
JL line_sx_pos
MOV R7, -1
JMP line_sx_done
line_sx_pos:
MOV R7, 1
line_sx_done:
MOV R8, 0               ; sy = y1 < y2 ? 1 : -1
CMP R1, R3
JL line_sy_pos
MOV R8, -1
JMP line_sy_done
line_sy_pos:
MOV R8, 1
line_sy_done:
MOV R9, 0               ; err = dx - dy
SUB R9, R5, R6
line_loop:
MOV VX, R0              ; Set pixel at (x1, y1)
MOV VY, R1
SWRITE R4
CMP R0, R2              ; Check if x1 == x2
JNE line_continue
CMP R1, R3              ; Check if y1 == y2
JE line_done            ; If both equal, we're done
line_continue:
MOV P0, R9              ; e2 = 2 * err
SHL P0, 1
CMP P0, R6              ; if e2 > -dy
JNG line_skip_x
ADD R9, R9, R6          ; err += -dy
ADD R0, R0, R7          ; x1 += sx
line_skip_x:
NEG P1, R5              ; -dx
CMP P0, P1              ; if e2 < dx
JNL line_skip_y
ADD R9, R9, R5          ; err += dx
ADD R1, R1, R8          ; y1 += sy
line_skip_y:
JMP line_loop
line_done:
"""

    def _draw_rect(self, x: int, y: int, width: int, height: int, color: int) -> str:
        """
        Draw a rectangle outline at (x, y) with the specified dimensions and color.
        Implemented using four line segments.

        Args:
            x, y: Top-left coordinates
            width, height: Rectangle dimensions
            color: Color value (0-31)

        Returns:
            Assembly code for drawing the rectangle
        """
        return f"""
; Draw rectangle outline at ({x}, {y}) size {width}x{height} in color {color}
MOV VM, 0               ; Coordinate mode
MOV R4, {color}         ; Store color
; Draw top line
MOV R0, {x}             ; Start x
MOV R1, {y}             ; Start y
MOV R2, {x + width - 1} ; End x
MOV R3, {y}             ; End y
rect_top_loop:
MOV VX, R0
MOV VY, R1
SWRITE R4
INC R0
CMP R0, R2
JLE rect_top_loop
; Draw bottom line
MOV R0, {x}             ; Start x
MOV R1, {y + height - 1} ; Start y
MOV R2, {x + width - 1} ; End x
rect_bottom_loop:
MOV VX, R0
MOV VY, R1
SWRITE R4
INC R0
CMP R0, R2
JLE rect_bottom_loop
; Draw left line
MOV R0, {x}             ; Start x
MOV R1, {y}             ; Start y
MOV R3, {y + height - 1} ; End y
rect_left_loop:
MOV VX, R0
MOV VY, R1
SWRITE R4
INC R1
CMP R1, R3
JLE rect_left_loop
; Draw right line
MOV R0, {x + width - 1} ; Start x
MOV R1, {y}             ; Start y
MOV R3, {y + height - 1} ; End y
rect_right_loop:
MOV VX, R0
MOV VY, R1
SWRITE R4
INC R1
CMP R1, R3
JLE rect_right_loop
"""

    def _fill_rect(self, x: int, y: int, width: int, height: int, color: int) -> str:
        """
        Fill a rectangle at (x, y) with the specified dimensions and color.
        Implemented using nested loops.

        Args:
            x, y: Top-left coordinates
            width, height: Rectangle dimensions
            color: Color value (0-31)

        Returns:
            Assembly code for filling the rectangle
        """
        return f"""
; Fill rectangle at ({x}, {y}) size {width}x{height} in color {color}
MOV VM, 0               ; Coordinate mode
MOV R4, {color}         ; Store color
MOV R0, {x}             ; Start x
MOV R1, {y}             ; Start y
MOV R2, {x + width}     ; End x (exclusive)
MOV R3, {y + height}    ; End y (exclusive)
MOV R5, R0              ; Current x
fill_y_loop:
MOV R5, R0              ; Reset x to start
fill_x_loop:
MOV VX, R5              ; Set pixel position
MOV VY, R1
SWRITE R4               ; Write color
INC R5                  ; Next x
CMP R5, R2              ; Check if x < end_x
JL fill_x_loop
INC R1                  ; Next y
CMP R1, R3              ; Check if y < end_y
JL fill_y_loop
"""

    def _set_layer(self, layer: int) -> str:
        """
        Set the active graphics layer.

        Args:
            layer: Layer number (0-7)

        Returns:
            Assembly code for setting the layer
        """
        if layer == 0:
            return ""
        else:
            return f"""
; Set active layer to {layer}
MOV VL, {layer}
"""

    def _set_blend_mode(self, mode: str) -> str:
        """
        Set the blending mode for the current layer.

        Args:
            mode: Blend mode name ('normal', 'add', 'subtract', 'multiply', 'screen')

        Returns:
            Assembly code for setting the blend mode
        """
        mode_map = {
            'normal': 0,
            'add': 1,
            'subtract': 2,
            'multiply': 3,
            'screen': 4
        }

        mode_value = mode_map.get(mode.lower(), 0)
        return f"""
; Set blend mode to {mode} ({mode_value})
MOV R0, {mode_value}
SBLEND R0
"""

    def _scroll_layer(self, dx: int, dy: int) -> str:
        """
        Scroll the current layer by the specified offset.
        Implemented using combination of rolling operations.

        Args:
            dx: Horizontal scroll amount (-128 to 127)
            dy: Vertical scroll amount (-128 to 127)

        Returns:
            Assembly code for scrolling the layer
        """
        return f"""
; Scroll layer by ({dx}, {dy}) using roll operations
MOV R0, {dx}
SROLX R0               ; Roll horizontally
MOV R0, {dy}
SROLY R0               ; Roll vertically
"""

    def _roll_screen_x(self, amount: int) -> str:
        """
        Roll the screen horizontally by the specified amount.

        Args:
            amount: Roll amount (-128 to 127)

        Returns:
            Assembly code for rolling the screen
        """
        return f"""
; Roll screen horizontally by {amount}
MOV R0, {amount}
SROLX R0
"""

    def _roll_screen_y(self, amount: int) -> str:
        """
        Roll the screen vertically by the specified amount.

        Args:
            amount: Roll amount (-128 to 127)

        Returns:
            Assembly code for rolling the screen
        """
        return f"""
; Roll screen vertically by {amount}
MOV R0, {amount}
SROLY R0
"""

    def _flip_screen_x(self) -> str:
        """
        Flip the screen horizontally.

        Returns:
            Assembly code for flipping the screen horizontally
        """
        return """
; Flip screen horizontally
SFLIPX
"""

    def _flip_screen_y(self) -> str:
        """
        Flip the screen vertically.

        Returns:
            Assembly code for flipping the screen vertically
        """
        return """
; Flip screen vertically
SFLIPY
"""

    def _rotate_screen_left(self, times: int = 1) -> str:
        """
        Rotate the screen counter-clockwise.

        Args:
            times: Number of 90-degree rotations (1-3)

        Returns:
            Assembly code for rotating the screen
        """
        return f"""
; Rotate screen left {times} times
MOV R0, {times}
SROTL R0
"""

    def _rotate_screen_right(self, times: int = 1) -> str:
        """
        Rotate the screen clockwise.

        Args:
            times: Number of 90-degree rotations (1-3)

        Returns:
            Assembly code for rotating the screen
        """
        return f"""
; Rotate screen right {times} times
MOV R0, {times}
SROTR R0
"""

    def _shift_screen_x(self, amount: int) -> str:
        """
        Shift the screen horizontally (pixels lost at edges).

        Args:
            amount: Shift amount (-128 to 127)

        Returns:
            Assembly code for shifting the screen
        """
        return f"""
; Shift screen horizontally by {amount}
MOV R0, {amount}
SSHFTX R0
"""

    def _shift_screen_y(self, amount: int) -> str:
        """
        Shift the screen vertically (pixels lost at edges).

        Args:
            amount: Shift amount (-128 to 127)

        Returns:
            Assembly code for shifting the screen
        """
        return f"""
; Shift screen vertically by {amount}
MOV R0, {amount}
SSHFTY R0
"""

    def _set_sprite(self, sprite_id: int, x: int, y: int, width: int, height: int, data_addr: int) -> str:
        """
        Set up a sprite with the specified parameters.

        Args:
            sprite_id: Sprite number (0-15)
            x, y: Sprite position
            width, height: Sprite dimensions
            data_addr: Address of sprite data

        Returns:
            Assembly code for setting up the sprite
        """
        sprite_base = 0xF000 + (sprite_id * 16)
        return f"""
; Set up sprite {sprite_id} at ({x}, {y}) size {width}x{height}
MOV P0, 0x{sprite_base:04X}      ; Sprite control block
MOV P1, 0x{data_addr:04X}       ; Data address
MOV [P0], P1:                   ; Store high byte of data address
MOV [P0+1], :P1                 ; Store low byte of data address
MOV R0, {x}
MOV [P0+2], R0                  ; X position
MOV R0, {y}
MOV [P0+3], R0                  ; Y position
MOV R0, {width}
MOV [P0+4], R0                  ; Width
MOV R0, {height}
MOV [P0+5], R0                  ; Height
"""

    def _move_sprite(self, sprite_id: int, x: int, y: int) -> str:
        """
        Move a sprite to a new position.

        Args:
            sprite_id: Sprite number (0-15)
            x, y: New position

        Returns:
            Assembly code for moving the sprite
        """
        sprite_base = 0xF000 + (sprite_id * 16)
        return f"""
; Move sprite {sprite_id} to ({x}, {y})
MOV P0, 0x{sprite_base + 2:04X}  ; Sprite position offset
MOV R0, {x}
MOV [P0], R0                    ; X position
MOV R0, {y}
MOV [P0+1], R0                  ; Y position
"""

    def _show_sprite(self, sprite_id: int) -> str:
        """
        Show/activate a sprite.

        Args:
            sprite_id: Sprite number (0-15)

        Returns:
            Assembly code for showing the sprite
        """
        sprite_base = 0xF000 + (sprite_id * 16)
        return f"""
; Show sprite {sprite_id}
MOV P0, 0x{sprite_base + 6:04X}  ; Sprite flags offset
MOV R0, [P0]
OR R0, 0x01                     ; Set active bit
MOV [P0], R0
"""

    def _hide_sprite(self, sprite_id: int) -> str:
        """
        Hide/deactivate a sprite.

        Args:
            sprite_id: Sprite number (0-15)

        Returns:
            Assembly code for hiding the sprite
        """
        sprite_base = 0xF000 + (sprite_id * 16)
        return f"""
; Hide sprite {sprite_id}
MOV P0, 0x{sprite_base + 6:04X}  ; Sprite flags offset
MOV R0, [P0]
AND R0, 0xFE                    ; Clear active bit
MOV [P0], R0
"""


# Global instance for use by the compiler
graphics_builtins = GraphicsBuiltins()
