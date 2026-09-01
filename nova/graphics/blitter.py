"""
Nova-16 Blitter — VRAM transfers, pixel blending, and batching.

Extracted from nova_gfx.py.  Responsible for:
    - VRAM ↔ screen transfers (VRAMtoScreen, ScreenToVRAM, blit, blit_vram)
    - Per-pixel blending with 5 blend modes
    - Pixel writes to layers with optional blending
    - Batching optimization for VRAM transfers

Pixel-level behavior is identical to the original GFX.
"""

import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .compositor import Compositor


class Blitter:
    """VRAM transfer and pixel blending operations."""

    WIDTH = 256
    HEIGHT = 256

    def __init__(self, compositor: 'Compositor' = None):
        self.compositor = compositor

        # Blending state
        self._blend_mode = 0     # 0=normal, 1=add, 2=subtract, 3=multiply, 4=screen
        self._blend_alpha = 255  # Alpha/intensity (0-255)
        self.blend_enabled = False
        self._update_blend_enabled()

        # VRAM buffer (mirrors the old GFX.vram)
        self.vram = np.zeros((self.HEIGHT, self.WIDTH), dtype=np.uint8)

        # Batching state
        self.graphics_batch_counter = 0
        self.graphics_batch_frequency = 4
        self.pending_vram_to_screen = False
        self.pending_screen_to_vram = False

    # ── Blend properties ────────────────────────────────────────────────

    @property
    def blend_mode(self) -> int:
        return self._blend_mode

    @blend_mode.setter
    def blend_mode(self, value: int):
        self._blend_mode = int(value)
        self._update_blend_enabled()

    @property
    def blend_alpha(self) -> int:
        return self._blend_alpha

    @blend_alpha.setter
    def blend_alpha(self, value: int):
        self._blend_alpha = int(value)
        self._update_blend_enabled()

    def _update_blend_enabled(self):
        """Cache the fast-path condition for per-pixel writes."""
        self.blend_enabled = not (self._blend_mode == 0 and self._blend_alpha == 255)

    def _divide_by_255_squared(self, value: int) -> int:
        """Return a rounded integer division by 255^2 without losing full-scale intensity."""
        return (int(value) + 32512) // 65025

    def blend_pixel(self, existing: int, new: int) -> int:
        """Apply current blend mode to combine existing and new pixel values."""
        existing = max(0, min(255, int(existing)))
        new = max(0, min(255, int(new)))
        alpha = max(0, min(255, int(self._blend_alpha)))

        if self._blend_mode == 0:  # Normal (alpha-blend toward new)
            # When alpha == 255 this collapses to a pure overwrite (return new).
            # When alpha < 255 we linearly interpolate existing -> new by alpha,
            # which is the transparency effect the fast-path gate in
            # _update_blend_enabled() already accounts for.
            if alpha >= 255:
                return new
            result = existing + ((new - existing) * alpha + 127) // 255
            return max(0, min(255, result))
        elif self._blend_mode == 1:  # Additive
            result = existing + ((new * alpha + 127) // 255)
            return min(255, result)
        elif self._blend_mode == 2:  # Subtractive
            result = existing - ((new * alpha + 127) // 255)
            return max(0, result)
        elif self._blend_mode == 3:  # Multiply
            result = self._divide_by_255_squared(existing * new * alpha)
            return min(255, result)
        elif self._blend_mode == 4:  # Screen
            inv_existing = 255 - existing
            inv_new = 255 - new
            result = 255 - self._divide_by_255_squared(inv_existing * inv_new * alpha)
            return min(255, max(0, result))
        else:
            return new

    def blend_array(self, existing: np.ndarray, new) -> np.ndarray:
        """Vectorized equivalent of blend_pixel() for numpy array/slice regions.

        `new` may be a scalar or an array broadcastable against `existing`.
        Mirrors blend_pixel's per-mode formulas exactly so batched drawing
        primitives (fill, rect, char) produce the same result a per-pixel
        blend_pixel() loop would.
        """
        existing = np.asarray(existing, dtype=np.int32)
        new = np.asarray(new, dtype=np.int32)
        alpha = max(0, min(255, int(self._blend_alpha)))

        if self._blend_mode == 1:  # Additive
            result = existing + ((new * alpha + 127) // 255)
            result = np.minimum(255, result)
        elif self._blend_mode == 2:  # Subtractive
            result = existing - ((new * alpha + 127) // 255)
            result = np.maximum(0, result)
        elif self._blend_mode == 3:  # Multiply
            result = (existing * new * alpha + 32512) // 65025
            result = np.minimum(255, result)
        elif self._blend_mode == 4:  # Screen
            inv_existing = 255 - existing
            inv_new = 255 - new
            result = 255 - ((inv_existing * inv_new * alpha + 32512) // 65025)
            result = np.clip(result, 0, 255)
        elif self._blend_mode == 0:  # Normal (alpha-blend toward new)
            if alpha >= 255:
                result = new
            else:
                result = existing + ((new - existing) * alpha + 127) // 255
                result = np.clip(result, 0, 255)
        else:  # Unknown mode
            result = new

        return np.broadcast_to(result, existing.shape).astype(np.uint8)

    def set_blend_mode(self, mode: int):
        """Set blend mode with bounds checking."""
        self.blend_mode = max(0, min(4, int(mode)))

    def set_blend_alpha(self, alpha: int):
        """Set blend alpha with bounds checking."""
        self.blend_alpha = max(0, min(255, int(alpha)))

    # ── Pixel writes ────────────────────────────────────────────────────

    def _set_pixel_to_layer(self, x: int, y: int, value: int, vl: int, compositor: 'Compositor'):
        """Set a pixel to the current layer with optional blending.
        
        Tracks pixel counts for optimized visibility checking.
        """
        if not self.blend_enabled:
            # Fast path: no blending
            if vl == 0:
                # Layer 0 is always composited unconditionally, so its pixel
                # count is never consulted — skip tracking it (measured hot path).
                compositor.layers[0][y, x] = value
                compositor._screen[y, x] = value
            elif 1 <= vl <= 4:
                old_val = compositor.layers[vl][y, x]
                compositor.layers[vl][y, x] = value
                compositor.update_pixel_count(vl, old_val, value)
                compositor.mark_dirty(vl)
            elif 5 <= vl <= 8:
                old_val = compositor.layers[vl][y, x]
                compositor.layers[vl][y, x] = value
                compositor.update_pixel_count(vl, old_val, value)
                compositor.mark_dirty(vl)
            return

        # Slow path: full blending
        if vl == 0:
            existing = compositor.layers[0][y, x]
            blended = self.blend_pixel(existing, value)
            compositor.layers[0][y, x] = blended
            compositor._screen[y, x] = blended
        elif 1 <= vl <= 4:
            old_val = compositor.layers[vl][y, x]
            existing = old_val
            blended = self.blend_pixel(existing, value)
            compositor.layers[vl][y, x] = blended
            compositor.update_pixel_count(vl, old_val, blended)
            compositor.mark_dirty(vl)
        elif 5 <= vl <= 8:
            old_val = compositor.layers[vl][y, x]
            existing = old_val
            blended = self.blend_pixel(existing, value)
            compositor.layers[vl][y, x] = blended
            compositor.update_pixel_count(vl, old_val, blended)
            compositor.mark_dirty(vl)

    # ── VRAM transfers ────────────────────────────────────────────────────

    def _copy_vram_to_screen(self, compositor: 'Compositor'):
        """Transfer VRAM into the base screen layer and final screen buffer."""
        compositor.reset_pixel_counts()  # Update pixel counts after bulk VRAM copy
        compositor.layers[0][:, :] = self.vram[:, :]
        compositor._screen[:, :] = self.vram[:, :]
        self.vram.fill(0)
        compositor.mark_clean()
        self.pending_vram_to_screen = False

    def _copy_screen_to_vram(self, compositor: 'Compositor'):
        """Transfer the current visible frame into VRAM and clear screen."""
        self.vram[:, :] = compositor.screen[:, :]
        compositor._screen.fill(0)
        self.pending_screen_to_vram = False

    def _execute_batched_operations(self, compositor: 'Compositor'):
        """Execute all pending graphics operations in a batch."""
        self.graphics_batch_counter = 0
        if self.pending_vram_to_screen:
            self._copy_vram_to_screen(compositor)
        if self.pending_screen_to_vram:
            self._copy_screen_to_vram(compositor)

    def vram_to_screen(self, compositor: 'Compositor'):
        """VRAM to Screen transfer with batching."""
        self.pending_vram_to_screen = True
        self.graphics_batch_counter += 1
        if self.graphics_batch_counter >= self.graphics_batch_frequency:
            self._execute_batched_operations(compositor)
        else:
            self._copy_vram_to_screen(compositor)

    def screen_to_vram(self, compositor: 'Compositor'):
        """Screen to VRAM transfer with batching."""
        self.pending_screen_to_vram = True
        self.graphics_batch_counter += 1
        if self.graphics_batch_counter >= self.graphics_batch_frequency:
            self._execute_batched_operations(compositor)
        else:
            self._copy_screen_to_vram(compositor)

    def blit(self, vl: int, compositor: 'Compositor'):
        """SBLIT: Copy VRAM contents into the layer specified by VL, then clear VRAM."""
        target = compositor.get_layer(vl) if vl != 0 else compositor.layers[0]
        if target is not None:
            # Recalculate pixel count after bulk VRAM copy
            compositor.reset_pixel_counts()
            target[:, :] = self.vram[:, :]
            if vl == 0:
                compositor._screen[:, :] = self.vram[:, :]
            else:
                compositor.mark_dirty(vl)
        self.vram.fill(0)

    def blit_vram(self, compositor: 'Compositor'):
        """VBLIT: Copy the composited screen into VRAM, then clear the screen."""
        self.vram[:, :] = compositor.screen[:, :]
        compositor._screen.fill(0)
        compositor.mark_all_dirty()
