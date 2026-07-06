"""
Nova-16 Interrupt Controller — central interrupt management via event bus.

Subscribes to peripheral events (timer, keyboard, UART, mouse) and triggers
the appropriate interrupt vector on the CPU when conditions are met.

This replaces the inline interrupt logic that was previously spread across
the CPU, memory, keyboard, mouse, and UART modules.
"""

from typing import TYPE_CHECKING

from core.flags import Flags

if TYPE_CHECKING:
    from .eventbus import EventBus


class InterruptController:
    """Central interrupt controller — subscribes to peripheral events.

    The controller holds a reference to the *cpu* (and its flags / registers /
    memory) so it can push the CPU context and jump to the handler.  This is
    the **only** component beyond the event bus that retains a CPU back-reference,
    and it is intentionally limited to interrupt dispatch logic.
    """

    # Vector indices
    VECTOR_TIMER = 0
    VECTOR_SERIAL = 1
    VECTOR_KEYBOARD = 2
    VECTOR_MOUSE = 3
    VECTOR_USER1 = 4
    VECTOR_USER2 = 5
    VECTOR_USER3 = 6
    VECTOR_DEBUG = 7

    def __init__(self, bus: 'EventBus', cpu=None, memory=None):
        self.bus = bus
        self._cpu = cpu
        self._memory = memory

        # Per-vector enable flags (written by STI/CLI variants)
        self.enabled = [0] * 8

        # Pending flag per source (set by event handlers, cleared on dispatch)
        self._timer_pending = False
        self._serial_pending = False
        self._keyboard_pending = False
        self._mouse_pending = False

        # Subscribe to peripheral events
        bus.subscribe('timer.fired', self._on_timer)
        bus.subscribe('keyboard.key_pressed', self._on_keyboard)
        bus.subscribe('uart.data_received', self._on_serial)
        bus.subscribe('mouse.button_changed', self._on_mouse)

    # ── CPU / Memory binding (set after construction) ──────────────────

    @property
    def cpu(self):
        return self._cpu

    @cpu.setter
    def cpu(self, value):
        self._cpu = value

    @property
    def memory(self):
        return self._memory

    @memory.setter
    def memory(self, value):
        self._memory = value

    # ── Peripheral event handlers ──────────────────────────────────────

    def _on_timer(self, _data=None):
        """Called when the timer fires a tick event."""
        self._timer_pending = True
        self._check()

    def _on_keyboard(self, _data=None):
        """Called when a key is pressed."""
        self._keyboard_pending = True
        self._check()

    def _on_serial(self, _data=None):
        """Called when UART data is received."""
        self._serial_pending = True
        self._check()

    def _on_mouse(self, _data=None):
        """Called when a mouse button state changes."""
        self._mouse_pending = True
        self._check()

    # ── Interrupt checking / dispatch ──────────────────────────────────

    def check(self, _data=None):
        """Explicit check call (used from CPU post-step hook)."""
        self._check()

    def _check(self):
        """Check pending interrupts in priority order and trigger if enabled."""
        cpu = self._cpu
        if cpu is None:
            return

        # Fast exit: nothing pending and no level-triggered user interrupt
        # requested. VECTOR_USER1 has no "pending" edge flag (it's checked
        # directly against cpu.interrupts below), so has_pending() alone
        # would silently starve it if used as the sole fast-exit condition.
        if not self.has_pending() and not cpu.interrupts[self.VECTOR_USER1]:
            return

        flags = cpu.flags_obj

        # Fast exit if global interrupts are disabled
        if flags[Flags.I] == 0:
            return

        # Use cpu.interrupts for per-vector enable (KEYCTRL/ENABRK set these)
        # Priority order: Timer → Serial → Keyboard → Mouse → User
        if cpu.interrupts[self.VECTOR_TIMER] and self._timer_pending:
            self._trigger(self.VECTOR_TIMER)
            self._timer_pending = False

        elif cpu.interrupts[self.VECTOR_SERIAL] and self._serial_pending:
            self._trigger(self.VECTOR_SERIAL)
            self._serial_pending = False

        elif cpu.interrupts[self.VECTOR_KEYBOARD] and self._keyboard_pending:
            self._trigger(self.VECTOR_KEYBOARD)
            self._keyboard_pending = False

        elif cpu.interrupts[self.VECTOR_MOUSE] and self._mouse_pending:
            self._trigger(self.VECTOR_MOUSE)
            self._mouse_pending = False

        elif cpu.interrupts[self.VECTOR_USER1]:
            self._trigger(self.VECTOR_USER1)

    def _trigger(self, vector: int):
        """Push PC + flags to stack, jump to handler."""
        cpu = self._cpu
        mem = self._memory
        if cpu is None or mem is None:
            return

        # Use flags_obj directly
        flags_obj = cpu.flags_obj

        # Check if global interrupts are enabled (redundant with _check but safe)
        if flags_obj[Flags.I] == 0:
            return

        # Get registers
        pc = getattr(cpu, 'pc', 0)
        sp = cpu.Pregisters[8] if hasattr(cpu, 'Pregisters') else 0xFFFF

        # Stack overflow check
        if sp < 0x0124:
            # Stack too close to interrupt vector region — disable interrupts
            flags_obj[Flags.I] = 0
            return

        # Calculate interrupt handler address from vector table
        vector_address = 0x0100 + (vector * 4)
        handler_address = mem.read_word_fast(vector_address)

        # Pack flags into 12-bit value
        flags_val = flags_obj.pack()

        # Push flags onto stack (use fast-path writes for performance)
        sp = (sp - 2) & 0xFFFF
        mem.write_word_fast(sp, flags_val)

        # Push PC onto stack (use fast-path writes for performance)
        sp = (sp - 2) & 0xFFFF
        mem.write_word_fast(sp, pc)

        # Update SP
        cpu.Pregisters[8] = sp

        # Disable interrupts during handler
        flags_obj[Flags.I] = 0

        # Jump to handler
        cpu.pc = handler_address

    # ── Vector enable/disable helpers ──────────────────────────────────

    def set_enable(self, vector: int, enabled: bool):
        """Enable or disable a specific interrupt vector."""
        if 0 <= vector < 8:
            self.enabled[vector] = 1 if enabled else 0
            # Sync with cpu.interrupts so both APIs work
            if self._cpu is not None and hasattr(self._cpu, 'interrupts'):
                self._cpu.interrupts[vector] = self.enabled[vector]

    def is_enabled(self, vector: int) -> bool:
        """Check if a specific vector is enabled."""
        if 0 <= vector < 8:
            # Prefer cpu.interrupts when available, fall back to self.enabled
            if self._cpu is not None and hasattr(self._cpu, 'interrupts'):
                return bool(self._cpu.interrupts[vector])
            return bool(self.enabled[vector])
        return False

    def pending(self, vector: int) -> bool:
        """Check if a specific vector has a pending interrupt."""
        if vector == self.VECTOR_TIMER:
            return self._timer_pending
        elif vector == self.VECTOR_SERIAL:
            return self._serial_pending
        elif vector == self.VECTOR_KEYBOARD:
            return self._keyboard_pending
        elif vector == self.VECTOR_MOUSE:
            return self._mouse_pending
        return False

    def clear_pending(self, vector: int):
        """Manually clear a pending interrupt flag."""
        if vector == self.VECTOR_TIMER:
            self._timer_pending = False
        elif vector == self.VECTOR_SERIAL:
            self._serial_pending = False
        elif vector == self.VECTOR_KEYBOARD:
            self._keyboard_pending = False
        elif vector == self.VECTOR_MOUSE:
            self._mouse_pending = False

    def has_pending(self) -> bool:
        """Check if any interrupt is pending."""
        return bool(self._timer_pending or self._serial_pending or
                    self._keyboard_pending or self._mouse_pending)

    # ── State (for save/restore in tests) ──────────────────────────────

    def get_state(self) -> dict:
        """Return the current interrupt controller state."""
        return {
            'enabled': list(self.enabled),
            'timer_pending': self._timer_pending,
            'serial_pending': self._serial_pending,
            'keyboard_pending': self._keyboard_pending,
            'mouse_pending': self._mouse_pending,
        }

    def set_state(self, state: dict):
        """Restore interrupt controller state."""
        if 'enabled' in state:
            self.enabled = list(state['enabled'])
        self._timer_pending = state.get('timer_pending', False)
        self._serial_pending = state.get('serial_pending', False)
        self._keyboard_pending = state.get('keyboard_pending', False)
        self._mouse_pending = state.get('mouse_pending', False)