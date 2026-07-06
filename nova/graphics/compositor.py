"""
Nova-16 Layer Compositor — dirty-tracked layer compositing engine.

Extracted from nova_gfx.py.  Responsible for:
    - Maintaining 9 compositing layers (layer_0 + 4 BG + 4 sprite)
    - Tracking per-layer dirty flags for incremental recompositing
    - Compositing visible layers back-to-front into the screen buffer
    - Mouse-cursor overlay

Phase 5 (Performance): Added pixel count tracking to avoid np.any() scans.

Pixel-level behavior is identical to the original GFX.composite_layers().
"""

import numpy as np


class Compositor:
    """Layer compositing engine with per-layer dirty tracking."""

    NUM_LAYERS = 9  # 0=base, 1-4=BG, 5-8=sprite
    WIDTH = 256
    HEIGHT = 256

    def __init__(self):
        # 9 compositing layers
        self.layers = [
            np.zeros((self.HEIGHT, self.WIDTH), dtype=np.uint8)
            for _ in range(self.NUM_LAYERS)
        ]
        # Per-layer dirty flags
        self.dirty = [True] * self.NUM_LAYERS
        # Global composite dirty flag
        self._composite_dirty = True
        # Cached composited screen
        self._screen = np.zeros((self.HEIGHT, self.WIDTH), dtype=np.uint8)

        # Layer visibility (index 0-8)
        self.layer_visibility = {i: True for i in range(self.NUM_LAYERS)}

        # Pixel count tracking per layer — avoids expensive np.any() scans
        self._pixel_counts = [0] * self.NUM_LAYERS

        # Mouse cursor overlay
        self.mouse_cursor_visible = False
        self.mouse_cursor_position = (0, 0)
        self.mouse_cursor_color = 0xFF
        self.mouse_cursor_bitmap = np.array(
            [
                [1, 1, 1, 0],
                [1, 1, 0, 0],
                [1, 0, 1, 0],
                [0, 0, 0, 1],
            ],
            dtype=np.uint8,
        )

    # ── Pixel count tracking ────────────────────────────────────────────

    def update_pixel_count(self, layer_idx: int, old_val: int, new_val: int):
        """Update pixel count for a layer when a pixel changes.
        
        Increments count if pixel becomes non-zero, decrements if it becomes zero.
        """
        if 0 <= layer_idx < self.NUM_LAYERS:
            if old_val == 0 and new_val != 0:
                self._pixel_counts[layer_idx] += 1
            elif old_val != 0 and new_val == 0:
                self._pixel_counts[layer_idx] -= 1

    def reset_pixel_counts(self):
        """Recalculate all pixel counts from scratch (after bulk operations)."""
        for i in range(self.NUM_LAYERS):
            self._pixel_counts[i] = int(np.count_nonzero(self.layers[i]))

    # ── Dirty tracking ──────────────────────────────────────────────────

    def mark_dirty(self, layer_idx: int):
        """Mark a layer as needing recompositing."""
        if 0 <= layer_idx < self.NUM_LAYERS:
            self.dirty[layer_idx] = True
            self._composite_dirty = True

    def mark_all_dirty(self):
        """Mark all layers dirty (e.g., after visibility change)."""
        self.dirty = [True] * self.NUM_LAYERS
        self._composite_dirty = True

    def mark_clean(self):
        """Mark all layers clean after a full composite."""
        self.dirty = [False] * self.NUM_LAYERS
        self._composite_dirty = False

    # ── Screen access ───────────────────────────────────────────────────

    @property
    def screen(self) -> np.ndarray:
        """Return the composited screen buffer — lazy recomposite."""
        if self._composite_dirty:
            self.composite()
        return self._screen

    @screen.setter
    def screen(self, value: np.ndarray):
        self._screen = value

    # ── Compositing ─────────────────────────────────────────────────────

    def _layer_has_visible_pixels(self, layer_idx: int) -> bool:
        """Return whether a layer contains any opaque pixels.
        
        Uses pixel count tracking instead of np.any() to avoid scanning all 65K pixels.
        """
        return self._pixel_counts[layer_idx] > 0

    def _composite_opaque_layer(self, layer: np.ndarray):
        """Back-to-front overwrite of non-zero pixels."""
        mask = layer != 0
        self._screen[mask] = layer[mask]

    def _composite_mouse_cursor(self):
        """Overlay hardware mouse cursor onto the screen."""
        if not self.mouse_cursor_visible:
            return

        cursor_x, cursor_y = self.mouse_cursor_position
        cursor_height, cursor_width = self.mouse_cursor_bitmap.shape

        if cursor_x >= self.WIDTH or cursor_y >= self.HEIGHT:
            return

        src_x_end = min(cursor_width, self.WIDTH - cursor_x)
        src_y_end = min(cursor_height, self.HEIGHT - cursor_y)
        visible_bitmap = self.mouse_cursor_bitmap[:src_y_end, :src_x_end]
        mask = visible_bitmap != 0
        if not np.any(mask):
            return

        target = self._screen[
            cursor_y:cursor_y + src_y_end,
            cursor_x:cursor_x + src_x_end
        ]
        target[mask] = self.mouse_cursor_color

    def composite(self):
        """Composite all visible layers into the main screen buffer."""
        # Recalculate pixel counts for dirty or uninitialized layers
        # (layers start dirty=True, but pixel_counts start at 0)
        for i in range(self.NUM_LAYERS):
            if self.dirty[i]:
                self._pixel_counts[i] = int(np.count_nonzero(self.layers[i]))

        # Start with layer 0 as the base (if visible)
        if self.layer_visibility.get(0, True):
            self._screen[:, :] = self.layers[0][:, :]
        else:
            self._screen.fill(0)

        # Add background layers (1-4) on top
        for i in range(1, 5):
            if self.layer_visibility.get(i, True) and self._pixel_counts[i] > 0:
                self._composite_opaque_layer(self.layers[i])

        # Add sprite layers (5-8) on top
        for i in range(5, 9):
            if self.layer_visibility.get(i, True) and self._pixel_counts[i] > 0:
                self._composite_opaque_layer(self.layers[i])

        self._composite_mouse_cursor()
        self.mark_clean()

    # ── Layer helpers ───────────────────────────────────────────────────

    def get_layer(self, idx: int) -> np.ndarray:
        """Return the numpy buffer for a given layer index."""
        if 0 <= idx < self.NUM_LAYERS:
            return self.layers[idx]
        return None

    def set_layer_visibility(self, layer: int, visible: bool):
        """Set layer visibility and mark for recompositing."""
        if 0 <= layer < self.NUM_LAYERS:
            self.layer_visibility[layer] = visible
            self.mark_all_dirty()

    def get_layer_visibility(self, layer: int) -> bool:
        """Get layer visibility status."""
        return self.layer_visibility.get(layer, False)

    def set_mouse_cursor_state(self, x, y, visible=True, color=None, bitmap=None):
        """Update mouse cursor state and mark composite dirty."""
        self.mouse_cursor_position = (int(x), int(y))
        self.mouse_cursor_visible = bool(visible)
        if color is not None:
            self.mouse_cursor_color = int(color) & 0xFF
        if bitmap is not None:
            self.mouse_cursor_bitmap = np.array(bitmap, dtype=np.uint8)
        self._composite_dirty = True

    # ── Convenience aliases for the old GFX layer names ─────────────────

    @property
    def layer_0(self) -> np.ndarray:
        return self.layers[0]

    @property
    def background_layers(self) -> list:
        return self.layers[1:5]

    @property
    def sprite_layers(self) -> list:
        return self.layers[5:9]