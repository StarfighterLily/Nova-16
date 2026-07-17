"""
Nova-16 Graphics Orchestrator — thin wrapper preserving the public API.

Delegates compositing, sprite rendering, and blitting to focused submodules:
    - Compositor: layer management and compositing
    - SpriteEngine: SCB parsing and sprite blitting
    - Blitter: VRAM transfers, pixel blending, batching

The public API is identical to the original monolithic GFX class so that
existing code (tests, CPU, GUI, assembler) requires zero changes.
"""

import numpy as np
from typing import TYPE_CHECKING

from .compositor import Compositor
from .sprites import SpriteEngine
from .blitter import Blitter

if TYPE_CHECKING:
    from nova.bus.eventbus import EventBus
    from nova.memory.memory import Memory


class GFX:
    """Nova-16 graphics system — thin orchestrator with backward-compatible API."""

    WIDTH = 256
    HEIGHT = 256

    def __init__(self, bus: 'EventBus' = None):
        self.width = self.WIDTH
        self.height = self.HEIGHT
        self.total_pixels = self.width * self.height

        # Subsystems
        self._compositor = Compositor()
        self._sprites = SpriteEngine(bus=bus, compositor=self._compositor)
        self._blitter = Blitter(compositor=self._compositor)

        # Direct layer access for backward compatibility
        self.layer_0 = self._compositor.layer_0
        self.background_layers = self._compositor.background_layers
        self.sprite_layers = self._compositor.sprite_layers
        self.layer_visibility = self._compositor.layer_visibility
        self.auto_composite = True

        # Video registers: VX, VY, VM, VC
        # Plain list, not numpy: these are accessed one scalar at a time on
        # every VX/VY/VM/VC register read or write, and numpy scalar boxing
        # is measurably slower than native list indexing for that access
        # pattern (confirmed as a hot leaf frame in profiling).
        self.Vregisters = [0, 0, 0, 0]

        # Video flags (HBlank, VBlank, VMode)
        self.flags = np.zeros(3, dtype=np.uint8)
        self.flags[2] = 0  # VMode
        self.flags[1] = 0  # VBlank
        self.flags[0] = 0  # HBlank

        # Layer selection
        self.VL = 0
        self.current_layer = 0

        # Legacy palette
        self.palette = []
        self.set_color_palette()

        # Font helpers
        self._font_bit_positions = np.array(
            [0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01], dtype=np.uint8
        )
        self._replacement_char_code = ord('?')

    # ── Properties ────────────────────────────────────────────────────

    @property
    def vmode(self):
        return int(self.Vregisters[2])

    @vmode.setter
    def vmode(self, value):
        self.Vregisters[2] = value & 0xFF

    @property
    def screen(self):
        if self.auto_composite and self._compositor._composite_dirty:
            self.composite_layers()
        return self._compositor._screen

    @screen.setter
    def screen(self, value):
        self._compositor._screen = value

    @property
    def blend_mode(self):
        return self._blitter.blend_mode

    @blend_mode.setter
    def blend_mode(self, value):
        self._blitter.blend_mode = value

    @property
    def blend_alpha(self):
        return self._blitter.blend_alpha

    @blend_alpha.setter
    def blend_alpha(self, value):
        self._blitter.blend_alpha = value

    @property
    def vram(self):
        return self._blitter.vram

    @vram.setter
    def vram(self, value):
        self._blitter.vram = value

    @property
    def layers_dirty(self):
        return self._compositor._composite_dirty

    @layers_dirty.setter
    def layers_dirty(self, value):
        self._compositor._composite_dirty = bool(value)
        if value:
            self._compositor.mark_all_dirty()
        else:
            self._compositor.mark_clean()

    @property
    def pending_vram_to_screen(self):
        return self._blitter.pending_vram_to_screen

    @pending_vram_to_screen.setter
    def pending_vram_to_screen(self, value):
        self._blitter.pending_vram_to_screen = bool(value)

    @property
    def pending_screen_to_vram(self):
        return self._blitter.pending_screen_to_vram

    @pending_screen_to_vram.setter
    def pending_screen_to_vram(self, value):
        self._blitter.pending_screen_to_vram = bool(value)

    @property
    def sprites_dirty(self):
        return False

    @sprites_dirty.setter
    def sprites_dirty(self, value):
        pass

    @property
    def graphics_batch_frequency(self):
        return self._blitter.graphics_batch_frequency

    @graphics_batch_frequency.setter
    def graphics_batch_frequency(self, value):
        self._blitter.graphics_batch_frequency = value

    # ── Blend helpers ──────────────────────────────────────────────────

    def blend_pixel(self, existing, new):
        return self._blitter.blend_pixel(existing, new)

    def set_blend_mode(self, mode):
        self._blitter.set_blend_mode(mode)

    def set_blend_alpha(self, alpha):
        self._blitter.set_blend_alpha(alpha)

    # ── Layer management ───────────────────────────────────────────────

    def get_target_layer(self):
        layer = self._compositor.get_layer(self.VL)
        if layer is not None:
            return layer
        return self._compositor.layers[0]

    def get_layer_buffer_by_num(self, layer_num):
        return self._compositor.get_layer(layer_num)

    def set_current_layer(self, layer):
        self.current_layer = layer & 0x0F
        self.VL = self.current_layer

    def get_current_layer(self):
        return self.current_layer

    def set_layer_visibility(self, layer, visible):
        self._compositor.set_layer_visibility(layer, visible)

    def get_layer_visibility(self, layer):
        return self._compositor.get_layer_visibility(layer)

    def copy_layer(self, source_layer, dest_layer):
        if source_layer == dest_layer:
            return
        src = self.get_layer_buffer_by_num(source_layer)
        dst = self.get_layer_buffer_by_num(dest_layer)
        if src is not None and dst is not None:
            dst[:] = src[:]
            self._compositor.mark_dirty(dest_layer)

    def swap_layers(self, layer1, layer2):
        if layer1 == layer2:
            return
        buf1 = self.get_layer_buffer_by_num(layer1)
        buf2 = self.get_layer_buffer_by_num(layer2)
        if buf1 is not None and buf2 is not None:
            temp = buf1.copy()
            buf1[:] = buf2[:]
            buf2[:] = temp
            self._compositor.mark_dirty(layer1)
            self._compositor.mark_dirty(layer2)

    # ── Clear / fill ───────────────────────────────────────────────────

    def clear(self):
        self._compositor.layers[0].fill(0)
        self._compositor._screen.fill(0)
        self._compositor.mark_all_dirty()

    def clear_layer(self, layer=None):
        if layer is None:
            layer = self.current_layer
        target = self.get_layer_buffer_by_num(layer)
        if target is not None:
            target.fill(0)
            if layer == 0:
                self._compositor._screen.fill(0)
            self._compositor.mark_dirty(layer)

    def fill_layer(self, value, layer_num=None):
        if layer_num is None:
            layer_num = self.VL
        target = self.get_layer_buffer_by_num(layer_num)
        if target is not None:
            target.fill(value)
            if layer_num == 0:
                self._compositor._screen.fill(value)
            self._compositor.mark_dirty(layer_num)

    # ── Blitting / VRAM ────────────────────────────────────────────────

    def blit(self):
        self._blitter.blit(self.VL, self._compositor)

    def blit_vram(self):
        self._blitter.blit_vram(self._compositor)

    def VRAMtoScreen(self):
        self._blitter.vram_to_screen(self._compositor)

    def ScreenToVRAM(self):
        self._blitter.screen_to_vram(self._compositor)

    # ── Pixel access (VRAM / screen) ───────────────────────────────────

    def get_vram_val(self):
        if self.Vregisters[2] == 1:
            addr = int(self.Vregisters[1]) | (int(self.Vregisters[0]) << 8)
            if 0 <= addr < self.total_pixels:
                x = addr % self.width
                y = addr // self.width
                return self.vram[y, x]
            raise IndexError(f"VRAM address out of range: {addr}")
        elif self.Vregisters[2] == 0:
            x = int(self.Vregisters[0])
            y = int(self.Vregisters[1])
            if 0 <= x < self.width and 0 <= y < self.height:
                return self.vram[y, x]
            raise IndexError(f"VRAM coordinates out of range: x={x}, y={y}")
        else:
            raise ValueError(f"Unknown vmode: {self.Vregisters[2]}")

    def set_vram_val(self, value):
        if self.Vregisters[2] == 1:
            addr = int(self.Vregisters[1]) | (int(self.Vregisters[0]) << 8)
            if 0 <= addr < self.total_pixels:
                x = addr % self.width
                y = addr // self.width
                self.vram[y, x] = value
        elif self.Vregisters[2] == 0:
            x = int(self.Vregisters[0])
            y = int(self.Vregisters[1])
            if 0 <= x < self.width and 0 <= y < self.height:
                self.vram[y, x] = value
        else:
            raise ValueError(f"Unknown vmode: {self.Vregisters[2]}")

    def get_screen_val(self):
        if self.Vregisters[2] == 1:
            addr = int(self.Vregisters[1]) | (int(self.Vregisters[0]) << 8)
            if 0 <= addr < self.total_pixels:
                x = addr % self.width
                y = addr // self.width
                return self.screen[y, x]
            raise IndexError(f"Screen address out of range: {addr}")
        elif self.Vregisters[2] == 0:
            x = int(self.Vregisters[0])
            y = int(self.Vregisters[1])
            if 0 <= x < self.width and 0 <= y < self.height:
                return self.screen[y, x]
            raise IndexError(f"Screen coordinates out of range: x={x}, y={y}")
        else:
            raise ValueError(f"Unknown vmode: {self.Vregisters[2]}")

    def set_screen_val(self, value):
        if self.Vregisters[2] == 1:
            addr = int(self.Vregisters[1]) | (int(self.Vregisters[0]) << 8)
            if 0 <= addr < self.total_pixels:
                x = addr % self.width
                y = addr // self.width
                if 0 <= x < self.width and 0 <= y < self.height:
                    self._set_pixel_fast(x, y, value)
        else:
            x = int(self.Vregisters[0])
            y = int(self.Vregisters[1])
            if 0 <= x < self.width and 0 <= y < self.height:
                self._set_pixel_fast(x, y, value)

    def _set_pixel_fast(self, x, y, value):
        vl = self.VL
        if vl == 0:
            self._compositor.layers[0][y, x] = value
            self._compositor._screen[y, x] = value
            return
        if 1 <= vl <= 4:
            old_val = self._compositor.layers[vl][y, x]
            self._compositor.layers[vl][y, x] = value
            self._compositor.update_pixel_count(vl, old_val, value)
            self._compositor.mark_dirty(vl)
        elif 5 <= vl <= 8:
            old_val = self._compositor.layers[vl][y, x]
            self._compositor.layers[vl][y, x] = value
            self._compositor.update_pixel_count(vl, old_val, value)
            self._compositor.mark_dirty(vl)

    def _set_pixel_to_layer(self, x, y, value, layer=None):
        """Set pixel to a specific layer (or current VL if layer=None)."""
        target = layer if layer is not None else self.VL
        if target == 0:
            self._compositor.layers[0][y, x] = value
            self._compositor._screen[y, x] = value
        elif 1 <= target <= 8:
            self._compositor.layers[target][y, x] = value
            self._compositor.mark_dirty(target)

    # ── Transformations ────────────────────────────────────────────────

    def _can_sync_layer0_from_screen(self):
        if self._compositor.mouse_cursor_visible:
            return False
        for i in range(1, 5):
            if self._compositor.layer_visibility.get(i, True) and self._compositor._pixel_counts[i] > 0:
                return False
        for i in range(5, 9):
            if self._compositor.layer_visibility.get(i, True) and self._compositor._pixel_counts[i] > 0:
                return False
        return True

    def _prepare_layer0_transform(self):
        if self._can_sync_layer0_from_screen():
            self._compositor.layers[0][:, :] = self._compositor._screen[:, :]

    def roll_x(self, roll_x):
        target = self.get_layer_buffer_by_num(self.VL)
        if target is not None:
            target[:] = np.roll(target, roll_x, axis=1)
            if self.VL == 0:
                self._compositor._screen[:] = np.roll(self._compositor._screen, roll_x, axis=1)
            else:
                self._compositor.mark_dirty(self.VL)

    def roll_y(self, roll_y):
        target = self.get_layer_buffer_by_num(self.VL)
        if target is not None:
            target[:] = np.roll(target, roll_y, axis=0)
            if self.VL == 0:
                self._compositor._screen[:] = np.roll(self._compositor._screen, roll_y, axis=0)
            else:
                self._compositor.mark_dirty(self.VL)

    def shift_x(self, shift_x):
        target = self.get_layer_buffer_by_num(self.VL)
        if target is None:
            return
        if shift_x > 0:
            target[:, shift_x:] = target[:, :-shift_x]
            target[:, :shift_x] = 0
        elif shift_x < 0:
            shift_amount = -shift_x
            target[:, :-shift_amount] = target[:, shift_amount:]
            target[:, -shift_amount:] = 0
        self._compositor.mark_dirty(self.VL)

    def shift_y(self, shift_y):
        target = self.get_layer_buffer_by_num(self.VL)
        if target is None:
            return
        if shift_y > 0:
            target[shift_y:, :] = target[:-shift_y, :]
            target[:shift_y, :] = 0
        elif shift_y < 0:
            shift_amount = -shift_y
            target[:-shift_amount, :] = target[shift_amount:, :]
            target[-shift_amount:, :] = 0
        self._compositor.mark_dirty(self.VL)

    def flip_x(self):
        if self.VL == 0:
            self._prepare_layer0_transform()
        target = self.get_layer_buffer_by_num(self.VL)
        if target is not None:
            target[:] = np.flip(target, axis=1)
            if self.VL == 0:
                self._compositor._screen[:] = np.flip(self._compositor._screen, axis=1)
            else:
                self._compositor.mark_dirty(self.VL)

    def flip_y(self):
        if self.VL == 0:
            self._prepare_layer0_transform()
        target = self.get_layer_buffer_by_num(self.VL)
        if target is not None:
            target[:] = np.flip(target, axis=0)
            if self.VL == 0:
                self._compositor._screen[:] = np.flip(self._compositor._screen, axis=0)
            else:
                self._compositor.mark_dirty(self.VL)

    def rotate_r(self, times):
        target = self.get_layer_buffer_by_num(self.VL)
        if target is not None:
            target[:] = np.rot90(target, times, axes=(1, 0))
            self._compositor.mark_dirty(self.VL)

    def rotate_l(self, times):
        target = self.get_layer_buffer_by_num(self.VL)
        if target is not None:
            target[:] = np.rot90(target, times, axes=(0, 1))
            self._compositor.mark_dirty(self.VL)

    def rotate_left(self, times):
        self.rotate_l(times)

    def rotate_right(self, times):
        self.rotate_r(times)

    def roll_x_layer(self, roll_x, layer_num=None):
        if layer_num is None:
            layer_num = self.VL
        target = self.get_layer_buffer_by_num(layer_num)
        if target is not None:
            target[:] = np.roll(target, roll_x, axis=1)
            self._compositor.mark_dirty(layer_num)

    def roll_y_layer(self, roll_y, layer_num=None):
        if layer_num is None:
            layer_num = self.VL
        target = self.get_layer_buffer_by_num(layer_num)
        if target is not None:
            target[:] = np.roll(target, roll_y, axis=0)
            self._compositor.mark_dirty(layer_num)

    def flip_x_layer(self, layer_num=None):
        if layer_num is None:
            layer_num = self.VL
        target = self.get_layer_buffer_by_num(layer_num)
        if target is not None:
            target[:] = np.flip(target, axis=1)
            self._compositor.mark_dirty(layer_num)

    def flip_y_layer(self, layer_num=None):
        if layer_num is None:
            layer_num = self.VL
        target = self.get_layer_buffer_by_num(layer_num)
        if target is not None:
            target[:] = np.flip(target, axis=0)
            self._compositor.mark_dirty(layer_num)

    def shift_layer_x(self, amount, layer_num=None):
        if layer_num is None:
            layer_num = self.VL
        target = self.get_layer_buffer_by_num(layer_num)
        if target is None:
            return
        if amount > 0:
            target[:, amount:] = target[:, :-amount]
            target[:, :amount] = 0
        elif amount < 0:
            target[:, :amount] = target[:, -amount:]
            target[:, amount:] = 0
        self._compositor.mark_dirty(layer_num)

    def shift_layer_y(self, amount, layer_num=None):
        if layer_num is None:
            layer_num = self.VL
        target = self.get_layer_buffer_by_num(layer_num)
        if target is None:
            return
        if amount > 0:
            target[amount:, :] = target[:-amount, :]
            target[:amount, :] = 0
        elif amount < 0:
            target[:amount, :] = target[-amount:, :]
            target[amount:, :] = 0
        self._compositor.mark_dirty(layer_num)

    def rotate_layer_left(self, amount, layer_num=None):
        if layer_num is None:
            layer_num = self.VL
        target = self.get_layer_buffer_by_num(layer_num)
        if target is None:
            return
        rotations = (amount // 90) % 4
        for _ in range(rotations):
            target[:, :] = np.rot90(target, k=1)
        self._compositor.mark_dirty(layer_num)

    def rotate_layer_right(self, amount, layer_num=None):
        if layer_num is None:
            layer_num = self.VL
        target = self.get_layer_buffer_by_num(layer_num)
        if target is None:
            return
        rotations = (amount // 90) % 4
        for _ in range(rotations):
            target[:, :] = np.rot90(target, k=-1)
        self._compositor.mark_dirty(layer_num)

    def invert_colors(self):
        target = self.get_layer_buffer_by_num(self.VL)
        if target is not None:
            target[:, :] = 255 - target[:, :]
            self._compositor.mark_dirty(self.VL)

    # ── Drawing primitives ───────────────────────────────────────────

    def draw_line(self, x1, y1, x2, y2, color):
        target = self.get_layer_buffer_by_num(self.VL)
        if target is None:
            return
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        x, y = x1, y1
        while True:
            if 0 <= x < self.width and 0 <= y < self.height:
                target[y, x] = color
            if x == x2 and y == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        self._compositor.mark_dirty(self.VL)

    def draw_rectangle(self, x1, y1, x2, y2, color, filled=True):
        target = self.get_layer_buffer_by_num(self.VL)
        if target is None:
            return
        x1 = max(0, min(x1, self.width - 1))
        y1 = max(0, min(y1, self.height - 1))
        x2 = max(0, min(x2, self.width - 1))
        y2 = max(0, min(y2, self.height - 1))
        if filled:
            target[y1:y2 + 1, x1:x2 + 1] = color
        else:
            target[y1, x1:x2 + 1] = color
            target[y2, x1:x2 + 1] = color
            target[y1:y2 + 1, x1] = color
            target[y1:y2 + 1, x2] = color
        self._compositor.mark_dirty(self.VL)

    def draw_circle(self, center_x, center_y, radius, color, filled=True):
        target = self.get_layer_buffer_by_num(self.VL)
        if target is None:
            return
        center_x, center_y, radius = int(center_x), int(center_y), int(radius)
        if filled:
            x = radius
            y = 0
            err = 0
            while x >= y:
                for i in range(center_x - x, center_x + x + 1):
                    if 0 <= i < self.width:
                        if 0 <= center_y + y < self.height:
                            target[center_y + y, i] = color
                        if 0 <= center_y - y < self.height:
                            target[center_y - y, i] = color
                for i in range(center_x - y, center_x + y + 1):
                    if 0 <= i < self.width:
                        if 0 <= center_y + x < self.height:
                            target[center_y + x, i] = color
                        if 0 <= center_y - x < self.height:
                            target[center_y - x, i] = color
                y += 1
                err += 1 + 2 * y
                if 2 * (err - x) + 1 > 0:
                    x -= 1
                    err += 1 - 2 * x
        else:
            x = radius
            y = 0
            err = 0
            while x >= y:
                points = [
                    (center_x + x, center_y + y), (center_x - x, center_y + y),
                    (center_x + x, center_y - y), (center_x - x, center_y - y),
                    (center_x + y, center_y + x), (center_x - y, center_y + x),
                    (center_x + y, center_y - x), (center_x - y, center_y - x),
                ]
                for px, py in points:
                    if 0 <= px < self.width and 0 <= py < self.height:
                        target[py, px] = color
                y += 1
                err += 1 + 2 * y
                if 2 * (err - x) + 1 > 0:
                    x -= 1
                    err += 1 - 2 * x
        self._compositor.mark_dirty(self.VL)

    # ── Text rendering ───────────────────────────────────────────────

    def _coerce_char_code(self, char):
        if isinstance(char, str):
            if not char:
                return 0
            code = ord(char[0])
            if code > 0xFF:
                return self._replacement_char_code
            return code
        return int(char) & 0xFF

    def _iterate_text_codes(self, text):
        if text is None:
            return
        if isinstance(text, str):
            for char in text:
                yield self._coerce_char_code(char)
            return
        if isinstance(text, (bytes, bytearray, memoryview)):
            for value in bytes(text):
                yield int(value)
            return
        try:
            iterator = iter(text)
        except TypeError:
            yield self._coerce_char_code(text)
            return
        for item in iterator:
            if isinstance(item, str) and len(item) > 1:
                for char in item:
                    yield self._coerce_char_code(char)
            else:
                yield self._coerce_char_code(item)

    def _normalize_screen_coordinate(self, value):
        value = int(value) & 0xFFFF
        if value > 32767:
            value -= 65536
        return value

    def _get_visible_char_region(self, x, y):
        dest_x0 = max(0, int(x))
        dest_y0 = max(0, int(y))
        dest_x1 = min(self.width, int(x) + 8)
        dest_y1 = min(self.height, int(y) + 8)
        if dest_x0 >= dest_x1 or dest_y0 >= dest_y1:
            return None
        src_x0 = dest_x0 - int(x)
        src_y0 = dest_y0 - int(y)
        src_x1 = src_x0 + (dest_x1 - dest_x0)
        src_y1 = src_y0 + (dest_y1 - dest_y0)
        return dest_x0, dest_y0, dest_x1, dest_y1, src_x0, src_y0, src_x1, src_y1

    def _render_char_matrix(self, char_data):
        char_bytes = np.asarray(char_data, dtype=np.uint8)
        return (char_bytes[:, np.newaxis] & self._font_bit_positions) != 0

    def _write_char_bitmap(self, target_buffer, char_matrix, x, y, color, background):
        visible_region = self._get_visible_char_region(x, y)
        if visible_region is None:
            return False
        dest_x0, dest_y0, dest_x1, dest_y1, src_x0, src_y0, src_x1, src_y1 = visible_region
        visible_matrix = char_matrix[src_y0:src_y1, src_x0:src_x1]
        target_slice = target_buffer[dest_y0:dest_y1, dest_x0:dest_x1]
        if background is None:
            target_slice[visible_matrix] = color
        else:
            target_slice[:, :] = np.where(visible_matrix, color, background)
        return True

    def _get_font_char_data(self, char):
        import nova_gfx
        font_data = nova_gfx.font_data
        code = self._coerce_char_code(char)
        glyph_count = len(font_data) // 8
        if glyph_count == 0:
            return [0] * 8
        if glyph_count >= 256:
            font_index = code
        elif glyph_count >= (256 - 32):
            font_index = code - 32
        else:
            font_index = code
        if font_index < 0 or font_index >= glyph_count:
            return [0] * 8
        start = font_index * 8
        return font_data[start:start + 8]

    def draw_char(self, char, x, y, color=0xFF, background=None):
        char_data = self._get_font_char_data(char)
        char_matrix = self._render_char_matrix(char_data)
        target_buffer = self.get_layer_buffer_by_num(self.VL)
        if target_buffer is None:
            target_buffer = self._compositor.layers[0]
        if not self._write_char_bitmap(target_buffer, char_matrix, x, y, color, background):
            return
        if self.VL != 0:
            self._compositor.mark_dirty(self.VL)
        else:
            self._write_char_bitmap(self._compositor._screen, char_matrix, x, y, color, background)

    def draw_string(self, text, x, y, color=0xFF, background=None, char_spacing=8):
        current_x = x
        for char_code in self._iterate_text_codes(text):
            if char_code == 0x0A:
                current_x = 0
                y += 8
            elif char_code == 0x0D:
                current_x = 0
            elif char_code == 0x09:
                current_x += char_spacing * 4
            else:
                self.draw_char(char_code, current_x, y, color, background)
                current_x += char_spacing
                if current_x + char_spacing > self.width:
                    current_x = 0
                    y += 8
        return current_x, y

    def draw_char_to_screen(self, char, x, y, color=0xFF, background=None):
        char_data = self._get_font_char_data(char)
        char_matrix = self._render_char_matrix(char_data)
        x = self._normalize_screen_coordinate(x)
        y = self._normalize_screen_coordinate(y)
        target_buffer = self.get_layer_buffer_by_num(self.VL)
        if target_buffer is None:
            target_buffer = self._compositor.layers[0]
        if not self._write_char_bitmap(target_buffer, char_matrix, x, y, color, background):
            return
        if self.VL != 0:
            self._compositor.mark_dirty(self.VL)
        else:
            self._write_char_bitmap(self._compositor._screen, char_matrix, x, y, color, background)

    def draw_string_to_screen(self, text, x, y, color=0xFF, background=None, char_spacing=8):
        x = self._normalize_screen_coordinate(x)
        y = self._normalize_screen_coordinate(y)
        current_x = x
        for char_code in self._iterate_text_codes(text):
            if char_code == 0x0A:
                current_x = 0
                y += 8
            elif char_code == 0x0D:
                current_x = 0
            elif char_code == 0x09:
                current_x += char_spacing * 4
            else:
                self.draw_char_to_screen(char_code, current_x, y, color, background)
                current_x += char_spacing
                if current_x + char_spacing > self.width:
                    current_x = 0
                    y += 8
        return current_x, y

    def draw_text(self, x, y, color, text_addr, memory):
        x = int(x)
        y = int(y)
        addr = text_addr
        text_bytes = []
        max_address = getattr(memory, 'size', 65536)
        while addr < max_address:
            byte = int(memory.read(addr, 1)[0])
            if byte == 0:
                break
            text_bytes.append(byte)
            addr += 1
        return self.draw_string(text_bytes, x, y, color)

    # ── Sprite system ──────────────────────────────────────────────────

    @property
    def sprite_count(self):
        return self._sprites.SPRITE_COUNT

    @property
    def sprite_block_size(self):
        return self._sprites.SPRITE_BLOCK_SIZE

    @property
    def sprite_memory_base(self):
        return self._sprites.SCB_START

    @property
    def sprite_memory_end(self):
        return self._sprites.SCB_END

    def get_sprite_control_block(self, sprite_id, memory):
        return self._sprites.get_sprite_control_block(sprite_id, memory)

    def blit_sprite(self, sprite_id, memory):
        self._sprites.blit_sprite(sprite_id, memory, self._compositor)

    def blit_all_sprites(self, memory):
        self._sprites.blit_all_sprites(memory, self._compositor)

    # ── Compositing ────────────────────────────────────────────────────

    def composite_layers(self):
        # Update pixel counts for dirty layers before compositing
        for i in range(self._compositor.NUM_LAYERS):
            if self._compositor.dirty[i]:
                self._compositor._pixel_counts[i] = int(np.count_nonzero(self._compositor.layers[i]))

        # Start with layer 0 as the base (if visible)
        if self._compositor.layer_visibility.get(0, True):
            self._compositor._screen[:, :] = self._compositor.layers[0][:, :]
        else:
            self._compositor._screen.fill(0)

        # Add background layers (1-4) on top
        for i in range(1, 5):
            if self._compositor.layer_visibility.get(i, True):
                if not self._compositor._layer_has_visible_pixels(i):
                    continue
                self._composite_opaque_layer(self._compositor.layers[i])

        # Add sprite layers (5-8) on top
        for i in range(5, 9):
            if self._compositor.layer_visibility.get(i, True):
                if not self._compositor._layer_has_visible_pixels(i):
                    continue
                self._composite_opaque_layer(self._compositor.layers[i])

        self._composite_mouse_cursor()
        self._compositor.mark_clean()

    def _layer_has_visible_pixels(self, layer_idx):
        return self._compositor._layer_has_visible_pixels(layer_idx)

    def _composite_opaque_layer(self, layer):
        self._compositor._composite_opaque_layer(layer)

    def _composite_mouse_cursor(self):
        self._compositor._composite_mouse_cursor()

    def set_mouse_cursor_state(self, x, y, visible=True, color=None, bitmap=None):
        self._compositor.set_mouse_cursor_state(x, y, visible, color, bitmap)

    def flip_layer_x(self, layer_num=None):
        self.flip_x_layer(layer_num)

    def flip_layer_y(self, layer_num=None):
        self.flip_y_layer(layer_num)

    # ── Palette ───────────────────────────────────────────────────────

    def set_color_palette(self, palette=None):
        if palette is not None:
            self.palette = palette
            return
        self.palette = []
        for i in range(256):
            if 0x00 <= i <= 0x0F:
                val = int(i * 255 / 15)
                color = (val, val, val)
            elif 0x10 <= i <= 0x1F:
                val = int((i - 0x10) * 255 / 15)
                color = (val, 0, 0)
            elif 0x20 <= i <= 0x2F:
                val = int((i - 0x20) * 255 / 15)
                color = (0, val, 0)
            elif 0x30 <= i <= 0x3F:
                val = int((i - 0x30) * 255 / 15)
                color = (0, 0, val)
            elif 0x40 <= i <= 0x4F:
                val = int((i - 0x40) * 255 / 15)
                color = (val, val, 0)
            elif 0x50 <= i <= 0x5F:
                val = int((i - 0x50) * 255 / 15)
                color = (val, 0, val)
            elif 0x60 <= i <= 0x6F:
                val = int((i - 0x60) * 255 / 15)
                color = (0, val, val)
            elif 0x70 <= i <= 0x7F:
                val = int((i - 0x70) * 255 / 15)
                color = (val, int(val * 0.5), 0)
            elif 0x80 <= i <= 0x8F:
                val = int((i - 0x80) * 255 / 15)
                color = (int(val * 0.5), 0, val)
            elif 0x90 <= i <= 0x9F:
                val = int((i - 0x90) * 255 / 15)
                color = (int(val * 0.5), val, 0)
            elif 0xA0 <= i <= 0xAF:
                val = int((i - 0xA0) * 255 / 15)
                color = (val, int(val * 0.5), int(val * 0.5))
            elif 0xB0 <= i <= 0xBF:
                val = int((i - 0xB0) * 255 / 15)
                color = (0, int(val * 0.5), int(val * 0.5))
            elif 0xC0 <= i <= 0xCF:
                val = int((i - 0xC0) * 255 / 15)
                color = (int(val * 0.6), int(val * 0.3), 0)
            elif 0xD0 <= i <= 0xDF:
                val = int((i - 0xD0) * 255 / 15)
                color = (int(val * 0.5), int(val * 0.5), val)
            elif 0xE0 <= i <= 0xEF:
                val = int((i - 0xE0) * 255 / 15)
                color = (int(val * 0.5), val, int(val * 0.5))
            elif 0xF0 <= i <= 0xFF:
                val = int((i - 0xF0) * 255 / 15)
                color = (val, int(val * 0.5), int(val * 0.5))
            else:
                color = (0, 0, 0)
            self.palette.append(color)

    def get_color(self, index):
        return self.palette[index]

    def set_color(self, index, color):
        self.palette[index] = color

    def get_palette(self):
        return self.palette

    # ── Legacy state helpers ───────────────────────────────────────────

    def set_registers(self, registers):
        self.registers = registers

    def get_registers(self):
        return getattr(self, 'registers', None)

    def set_vmode(self, vmode):
        self.vmode = vmode

    def get_vmode(self):
        return self.vmode

    def set_vram(self, vram):
        self.vram = vram

    def get_vram(self):
        return self.vram

    def set_flags(self, flags):
        self.flags = flags

    def get_flags(self):
        return self.flags

    def set_screen(self, screen):
        self.screen = screen

    def get_screen(self):
        return self.screen
