"""
Nova-16 Programmable Timer — standalone peripheral communicating via event bus.

Extracted from the monolithic CPU class (nova_cpu.py).  The timer subscribes
to ``cpu.tick`` events and publishes ``timer.fired`` when the modulo threshold
is crossed.

Registers (4 bytes in timer[]):
    [0] TT — Timer counter (current tick count)
    [1] TM — Timer modulo (threshold)
    [2] TC — Timer control (bit 0 = enable, bit 1 = interrupt enable)
    [3] TS — Timer speed (divisor = TS + 1)
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nova.bus.eventbus import EventBus


class Timer:
    """Programmable timer — standalone peripheral communicating via event bus."""

    def __init__(self, bus: EventBus, interrupt_controller=None):
        self.bus = bus
        self._intr_ctrl = interrupt_controller

        # Public timer registers (accessed directly by the CPU register file
        # via external getter/setter callbacks — keep the 4-element list
        # convention for backward compatibility).
        self.regs = [0, 0, 0, 0]   # TT, TM, TC, TS

        # Internal state
        self._cycle_count = 0
        self._enabled = False
        self._interrupt_enabled = False
        self._divisor = 1           # Derived from TS register

        # Subscribe to CPU ticks
        bus.subscribe('cpu.tick', self._on_tick)

    # ── Event handler ──────────────────────────────────────────────────

    def _on_tick(self, _data=None):
        """Called on every CPU cycle via event bus subscription."""
        if not self._enabled:
            return

        self._cycle_count += 1

        if self._cycle_count < self._divisor:
            return

        # Divisor threshold crossed — advance counter
        increments = self._cycle_count // self._divisor
        self._cycle_count %= self._divisor

        # Cap increments to avoid overflow noise
        increments = min(increments, 255)

        self.regs[0] = (self.regs[0] + increments) & 0xFF

        # Check modulo threshold
        if self._interrupt_enabled and self.regs[1] > 0 and self.regs[0] >= self.regs[1]:
            self.regs[0] = 0
            self.bus.publish('timer.fired')

    # ── Register access (called by CPU register-file callbacks) ────────

    def get_register(self, idx: int) -> int:
        """Get a timer register value (idx 0-3 → TT, TM, TC, TS)."""
        return self.regs[idx] if 0 <= idx < 4 else 0

    def set_register(self, idx: int, value: int):
        """Set a timer register (idx 0-3)."""
        if idx < 0 or idx >= 4:
            return
        if idx == 2:          # TC — control
            self._set_control(value & 0xFF)
        elif idx == 3:        # TS — speed
            self._set_speed(value & 0xFF)
        else:
            self.regs[idx] = value & 0xFF

    def _set_control(self, value: int):
        """Set timer control register and update internal state."""
        was_enabled = self._enabled
        self.regs[2] = value

        self._enabled = bool(value & 0x01)
        self._interrupt_enabled = bool(value & 0x02)

        # Sync interrupt enable with the central interrupt controller
        if self._intr_ctrl is not None:
            self._intr_ctrl.set_enable(
                self._intr_ctrl.VECTOR_TIMER, self._interrupt_enabled
            )

        if not self._enabled:
            self._cycle_count = 0
            self.regs[0] = 0
        elif not was_enabled:
            # Just enabled — reset counters
            self._cycle_count = 0
            self.regs[0] = 0

    def _set_speed(self, value: int):
        """Set timer speed register and cache divisor."""
        self.regs[3] = value
        self._divisor = value + 1          # TS=0 → 1 cycle, TS=255 → 256 cycles

    # ── Lifecycle ──────────────────────────────────────────────────────

    def reset(self):
        """Reset timer to default state."""
        self.regs = [0, 0, 0, 0]
        self._cycle_count = 0
        self._enabled = False
        self._interrupt_enabled = False
        self._divisor = 1

    def get_status(self) -> dict:
        """Get timer status for debugging/monitoring."""
        return {
            'counter': self.regs[0],
            'modulo': self.regs[1],
            'control': self.regs[2],
            'speed': self.regs[3],
            'enabled': self._enabled,
            'cycles': self._cycle_count,
            'interrupt_enabled': self._interrupt_enabled,
        }