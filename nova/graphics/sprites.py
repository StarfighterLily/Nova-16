"""
Nova-16 Sprite Engine — sprite rendering with event-bus SCB monitoring.

Extracted from nova_gfx.py.  Responsible for:
    - Reading sprite control blocks (SCB) from memory
    - Blitting individual sprites to their designated layers
    - Subscribing to ``memory.scb_written`` events to auto-mark layers dirty
    - Clearing and re-blit of all active sprites

Pixel-level behavior is identical to the original GFX sprite system.
"""

import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nova.bus.eventbus import EventBus
    from nova.memory.memory import Memory


class SpriteEngine:
    """Sprite rendering engine with event-bus SCB monitoring."""

    SPRITE_COUNT = 16
    SPRITE_BLOCK_SIZE = 16
    SCB_START = 0xF000
    SCB_END = 0xF0FF

    def __init__(self, bus: 'EventBus' = None, compositor=None):
        self.bus = bus
        self.compositor = compositor
        self._pending_dirty = False

        # Subscribe to SCB write events via the bus
        if bus is not None:
            bus.subscribe('memory.scb_written', self._on_scb_write)

    # ── Event handler ───────────────────────────────────────────────────

    def _on_scb_write(self, addr: int):
        """A sprite control block byte was written — mark relevant layers dirty."""
        if self.SCB_START <= addr < self.SCB_END:
            sprite_idx = (addr - self.SCB_START) // self.SPRITE_BLOCK_SIZE
            # Sprites 0-3 → layer 5, 4-7 → layer 6, 8-11 → layer 7, 12-15 → layer 8
            layer_idx = 5 + (sprite_idx // 4)
            if self.compositor is not None:
                self.compositor.mark_dirty(layer_idx)
            self._pending_dirty = True

    # ── SCB parsing ───────────────────────────────────────────────────────

    def get_sprite_control_block(self, sprite_id: int, memory: 'Memory') -> dict:
        """Get sprite control block data from memory."""
        if sprite_id < 0 or sprite_id >= self.SPRITE_COUNT:
            return None

        base_addr = int(self.SCB_START) + (int(sprite_id) * int(self.SPRITE_BLOCK_SIZE))

        # Read sprite control block (16 bytes)
        control_block = memory.read_bytes_direct(base_addr, 16)

        return {
            'data_addr': (control_block[0] << 8) | control_block[1],  # Big-endian 16-bit
            'x': control_block[2],
            'y': control_block[3],
            'width': control_block[4],
            'height': control_block[5],
            'flags': control_block[6],
            'transparency_color': control_block[7],
            'active': (control_block[6] & 0x01) != 0,
            'transparency_enabled': (control_block[6] & 0x02) != 0,
            'layer': 5 if (control_block[6] & 0x80) == 0 else 6,  # Bit 7 selects sprite layer
        }

    # ── Sprite blitting ─────────────────────────────────────────────────

    def blit_sprite(self, sprite_id: int, memory: 'Memory', compositor=None):
        """Blit a single sprite to its designated layer."""
        comp = compositor or self.compositor
        if comp is None:
            return

        sprite = self.get_sprite_control_block(sprite_id, memory)
        if not sprite or not sprite['active'] or sprite['width'] == 0 or sprite['height'] == 0:
            return

        sprite_size = sprite['width'] * sprite['height']
        if sprite['data_addr'] + sprite_size > memory.size:
            return  # Invalid sprite data address

        sprite_data = memory.read_bytes_direct(sprite['data_addr'], sprite_size)

        # Convert to 2D array
        sprite_bitmap = np.array(sprite_data, dtype=np.uint8).reshape(
            sprite['height'], sprite['width']
        )

        # Determine target layer buffer
        target_layer = sprite['layer']
        if target_layer == 5:
            target_buffer = comp.layers[5]
        elif target_layer == 6:
            target_buffer = comp.layers[6]
        else:
            target_buffer = comp.layers[5]  # Default to sprite layer 5

        # Calculate blit bounds with clipping
        x, y = sprite['x'], sprite['y']
        width, height = sprite['width'], sprite['height']

        if x >= comp.WIDTH or y >= comp.HEIGHT or x + width <= 0 or y + height <= 0:
            return  # Completely off-screen

        src_x_start = max(0, -x)
        src_y_start = max(0, -y)
        src_x_end = min(width, comp.WIDTH - x)
        src_y_end = min(height, comp.HEIGHT - y)

        dst_x_start = max(0, x)
        dst_y_start = max(0, y)
        dst_x_end = dst_x_start + (src_x_end - src_x_start)
        dst_y_end = dst_y_start + (src_y_end - src_y_start)

        # Extract visible portion of the sprite
        visible_sprite = sprite_bitmap[src_y_start:src_y_end, src_x_start:src_x_end]

        if sprite['transparency_enabled']:
            transparent_color = sprite['transparency_color']
            mask = visible_sprite != transparent_color
            # Track pixel count changes for non-transparent pixels
            for dy in range(dst_y_start, dst_y_end):
                for dx in range(dst_x_start, dst_x_end):
                    local_y = dy - dst_y_start
                    local_x = dx - dst_x_start
                    if local_y < visible_sprite.shape[0] and local_x < visible_sprite.shape[1]:
                        if mask[local_y, local_x]:
                            old_val = target_buffer[dy, dx]
                            new_val = int(visible_sprite[local_y, local_x])
                            if old_val == 0 and new_val != 0:
                                comp._pixel_counts[target_layer] += 1
                            elif old_val != 0 and new_val == 0:
                                comp._pixel_counts[target_layer] -= 1
                            target_buffer[dy, dx] = new_val
        else:
            target_buffer[dst_y_start:dst_y_end, dst_x_start:dst_x_end] = visible_sprite
            # Update pixel count for bulk write
            comp._pixel_counts[target_layer] = int(np.count_nonzero(target_buffer))

        # Mark the layer as dirty
        comp.mark_dirty(target_layer)

    def blit_all_sprites(self, memory: 'Memory', compositor=None):
        """Blit all active sprites to their designated layers."""
        comp = compositor or self.compositor
        if comp is None:
            return

        # Clear sprite layers first (indices 5-8) and update pixel counts
        for idx in range(5, 7):  # Layers 5 and 6 for sprites
            comp.layers[idx].fill(0)
            comp._pixel_counts[idx] = 0

        # Blit all sprites in order (0-15)
        for sprite_id in range(self.SPRITE_COUNT):
            self.blit_sprite(sprite_id, memory, comp)

        # Update pixel counts after all sprites blitted
        comp.reset_pixel_counts()
        self._pending_dirty = False
