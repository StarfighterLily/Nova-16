"""
Nova-16 Graphics Subsystem

Modular decomposition of the monolithic GFX class into focused components:
    - Compositor: layer compositing with dirty tracking
    - SpriteEngine: sprite rendering with event-bus SCB monitoring
    - Blitter: VRAM transfers, pixel blending, batching
    - GFX: thin orchestrator preserving the public API
"""

from .gfx import GFX
from .compositor import Compositor
from .sprites import SpriteEngine
from .blitter import Blitter

__all__ = ['GFX', 'Compositor', 'SpriteEngine', 'Blitter']
