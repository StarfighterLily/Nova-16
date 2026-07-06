"""Nova-16 Memory subsystem.

Provides a simplified 64KB unified memory with a single hot-region view
(zero page + interrupt vectors) and event-bus notification for SCB writes.
"""

from .memory import Memory

__all__ = ['Memory']