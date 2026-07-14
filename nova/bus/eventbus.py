"""
Nova-16 Event Bus — typed synchronous pub/sub within the emulator thread.

Allows components (CPU, memory, keyboard, timer, GFX, etc.) to communicate
without holding direct references to each other.  Eliminates the circular
back-references that previously coupled the system.

Usage:
    bus = EventBus()
    bus.subscribe('cpu.tick', my_handler)
    bus.publish('cpu.tick', cycle_count)
"""

from collections import defaultdict
from typing import Any, Callable


class EventBus:
    """Simple typed event bus — synchronous pub/sub within the emulator thread."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._once: dict[str, list[Callable]] = defaultdict(list)

    # ── Lifecycle ──────────────────────────────────────────────────────

    def subscribe(self, event_type: str, callback: Callable[[Any], None]):
        """Subscribe to an event.  *callback* receives the event payload (or None)."""
        self._subscribers[event_type].append(callback)

    def subscribe_once(self, event_type: str, callback: Callable[[Any], None]):
        """One-shot subscription — auto-removed after first publish."""
        self._once[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        """Remove a previously registered subscription."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                cb for cb in self._subscribers[event_type] if cb is not callback
            ]

    def publish(self, event_type: str, data: Any = None):
        """Publish an event.  Subscribers are called synchronously in order.

        Optimized: skips entirely when no subscribers exist (hot-path guard).
        """
        subs = self._subscribers.get(event_type)
        if subs:
            for cb in subs:
                cb(data)
        once = self._once.get(event_type)
        if once:
            for cb in once:
                cb(data)
            once.clear()

    # ── Introspection ──────────────────────────────────────────────────

    @property
    def subscriber_count(self) -> int:
        """Total number of active subscriptions (for debugging)."""
        return sum(len(v) for v in self._subscribers.values())

    def clear(self):
        """Remove all subscribers (useful in tests)."""
        self._subscribers.clear()
        self._once.clear()

    def __repr__(self) -> str:
        events = ", ".join(
            f"{k}({len(v)})" for k, v in self._subscribers.items() if v
        )
        return f"<EventBus: {events or '(empty)'}>"