"""
Nova-16 Memory module — backward-compatibility shim.

This module now re-exports ``Memory`` from ``nova.memory``.
All new code should import directly from ``nova.memory``:

    from nova.memory import Memory

The root-level ``nova_memory.py`` will be removed in a future cleanup phase.
"""

import warnings
from nova.memory import Memory as _Memory


class Memory(_Memory):
    """Backward-compatible Memory class.

    Subclass of ``nova.memory.Memory`` for drop-in compatibility with
    existing code that imports ``Memory`` from ``nova_memory``.
    """
    pass


__all__ = ['Memory']