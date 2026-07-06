"""
Nova-16 Graphics — backward-compatibility shim.

This module re-exports the modular graphics subsystem so that existing
code doing ``import nova_gfx`` or ``from nova_gfx import GFX`` continues
to work without modification.

The actual implementation lives in ``nova/graphics/``:
    - nova/graphics/gfx.py       — GFX orchestrator
    - nova/graphics/compositor.py — layer compositing
    - nova/graphics/sprites.py    — sprite engine
    - nova/graphics/blitter.py    — VRAM / blending
"""

from nova.graphics.gfx import GFX
from nova.graphics.compositor import Compositor
from nova.graphics.sprites import SpriteEngine
from nova.graphics.blitter import Blitter

# Re-export font_data for tests that monkeypatch nova_gfx.font_data
from font import font_data

__all__ = ["GFX", "Compositor", "SpriteEngine", "Blitter", "font_data"]
