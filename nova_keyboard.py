#!/usr/bin/env python3
"""
Nova-16 Keyboard Module

Provides keyboard input handling for the Nova-16 system.
Maps physical keyboard events to Nova-16 scan codes and manages keyboard state.

Key Features:
- ASCII to Nova-16 scan code mapping
- Special key handling (Enter, Backspace, Arrow keys, etc.)
- Integration with CPU keyboard buffer
- Keyboard event simulation for testing

Scan Code Layout:
0x00-0x1F: Control characters (NULL, SOH, STX, etc.)
0x20-0x7E: Printable ASCII characters
0x80-0xFF: Special keys and extended codes

Special Key Codes:
0x80: Left Arrow    0x84: F1        0x88: F5        0x8C: F9
0x81: Right Arrow   0x85: F2        0x89: F6        0x8D: F10
0x82: Up Arrow      0x86: F3        0x8A: F7        0x8E: F11
0x83: Down Arrow    0x87: F4        0x8B: F8        0x8F: F12
0x90: Insert        0x94: Page Up   0x98: Home      0x9C: Caps Lock
0x91: Delete        0x95: Page Down 0x99: End       0x9D: Num Lock
0x92: Backspace     0x96: Tab       0x9A: Escape    0x9E: Scroll Lock
0x93: Enter         0x97: Shift     0x9B: Space     0x9F: Pause/Break
"""

import threading
import time
from typing import Optional, Callable, Dict
from nova.bus.eventbus import EventBus


class NovaKeyboard:
    """Keyboard buffer — publishes events instead of calling CPU methods directly.

    Manages its own key buffer and publishes ``keyboard.key_pressed`` events
    on the event bus when a key is pressed.  The InterruptController subscribes
    to these events and triggers the keyboard interrupt vector on the CPU.

    Legacy ``cpu`` and ``get_buffer_status()`` API is preserved for backward
    compatibility during the Phase 3 migration.
    """

    BUFFER_MAX = 64

    def __init__(self, bus: Optional[EventBus] = None, cpu_ref=None, debounce_ms: int = 35):
        """Initialize keyboard.

        Args:
            bus: Event bus for publishing key events.  If None, no events
                 are published (for testing without bus).
            cpu_ref: Legacy CPU reference (optional).  If provided, directly
                     calls ``cpu.add_key_to_buffer()`` for backward compat.
            debounce_ms: Debounce window in milliseconds for physical keys.
        """
        self.bus = bus
        self._cpu_legacy = cpu_ref  # Only used if bus is None (fallback mode)

        self.key_mapping = self._create_key_mapping()
        self.modifier_state = {
            'shift': False,
            'ctrl': False,
            'alt': False,
            'caps_lock': False,
            'num_lock': False
        }
        self.event_callback = None

        # Keyboard registers visible to CPU
        self.data_register = 0          # Most recent key code
        self.status_register = 0        # Status flags (bit 0: key avail, bit 1: buffer full)
        self.control_register = 0       # Control flags
        self.buffer_count = 0           # Number of keys in buffer

        # Internal key buffer
        self._buffer = []               # Circular buffer (list used as queue)

        # Debounce window
        self.debounce_window_seconds = max(0, debounce_ms) / 1000.0
        self._last_key_press_time = {}

    def _create_key_mapping(self) -> Dict[str, int]:
        """Create mapping from key names to Nova-16 scan codes"""
        mapping = {}

        # ASCII printable characters (0x20-0x7E)
        for i in range(32, 127):
            mapping[chr(i)] = i

        # Control characters
        mapping['null'] = 0x00
        mapping['backspace'] = 0x08
        mapping['tab'] = 0x09
        mapping['enter'] = 0x0A
        mapping['escape'] = 0x1B

        # Special keys
        mapping['left'] = 0x80
        mapping['right'] = 0x81
        mapping['up'] = 0x82
        mapping['down'] = 0x83
        mapping['f1'] = 0x84
        mapping['f2'] = 0x85
        mapping['f3'] = 0x86
        mapping['f4'] = 0x87
        mapping['f5'] = 0x88
        mapping['f6'] = 0x89
        mapping['f7'] = 0x8A
        mapping['f8'] = 0x8B
        mapping['f9'] = 0x8C
        mapping['f10'] = 0x8D
        mapping['f11'] = 0x8E
        mapping['f12'] = 0x8F
        mapping['insert'] = 0x90
        mapping['delete'] = 0x91
        mapping['home'] = 0x98
        mapping['end'] = 0x99
        mapping['page_up'] = 0x94
        mapping['page_down'] = 0x95
        mapping['caps_lock'] = 0x9C
        mapping['num_lock'] = 0x9D
        mapping['scroll_lock'] = 0x9E

        return mapping

    def get_scan_code(self, key: str) -> int:
        """Convert key name to Nova-16 scan code"""
        if key in ['shift', 'ctrl', 'alt']:
            return 0  # Modifiers don't generate scan codes directly

        # Apply case conversion if needed
        if len(key) == 1 and key.isalpha():
            if self.modifier_state['shift'] ^ self.modifier_state['caps_lock']:
                key = key.upper()
            else:
                key = key.lower()

        return self.key_mapping.get(key, 0)

    def should_debounce_key(self, key: str) -> bool:
        """Return True if this key should be dropped due to debounce timing."""
        if self.debounce_window_seconds <= 0:
            return False

        now = time.monotonic()
        last_time = self._last_key_press_time.get(key)
        if last_time is not None and (now - last_time) < self.debounce_window_seconds:
            return True

        self._last_key_press_time[key] = now
        return False

    def add_key(self, key_code: int):
        """Add a key press to the internal buffer and publish event.

        This is the internal method used by both the legacy ``press_key`` path
        and direct test calls.
        """
        if len(self._buffer) >= self.BUFFER_MAX:
            return  # Buffer full, discard

        self._buffer.append(key_code & 0xFF)
        self.data_register = key_code & 0xFF
        self.buffer_count = len(self._buffer)

        # Update status flags
        self.status_register |= 0x01  # Key available
        if len(self._buffer) >= self.BUFFER_MAX:
            self.status_register |= 0x02  # Buffer full

        # Publish event on bus (InterruptController subscribes)
        if self.bus:
            self.bus.publish('keyboard.key_pressed', key_code & 0xFF)

    def read_key(self) -> int:
        """Read and remove the oldest key from the buffer."""
        if not self._buffer:
            self.data_register = 0
            self.buffer_count = 0
            self.status_register &= ~0x01  # Clear key available
            self.status_register &= ~0x02  # Clear buffer full
            return 0

        key = self._buffer.pop(0)
        self.buffer_count = len(self._buffer)

        if self._buffer:
            self.data_register = self._buffer[0]  # Next key
        else:
            self.data_register = 0
            self.status_register &= ~0x01  # Clear key available

        if len(self._buffer) < self.BUFFER_MAX:
            self.status_register &= ~0x02  # Clear buffer full

        return key

    def clear_buffer(self):
        """Clear the keyboard buffer and reset status."""
        self._buffer.clear()
        self.data_register = 0
        self.status_register = 0
        self.control_register = 0
        self.buffer_count = 0

    # ── Legacy API (preserved for backward compatibility) ──────────────

    @property
    def cpu(self):
        """Legacy CPU reference (deprecated)."""
        return self._cpu_legacy

    @cpu.setter
    def cpu(self, value):
        self._cpu_legacy = value

    def press_key(self, key: str, apply_debounce: bool = False):
        """Simulate a key press — legacy API.

        If ``_cpu_legacy`` is set and bus is None, falls back to direct
        CPU buffer injection for backward compatibility.
        """
        if apply_debounce and self.should_debounce_key(key):
            return

        # Handle modifier keys
        if key in ['shift', 'ctrl', 'alt']:
            self.modifier_state[key] = True
            return

        if key == 'caps_lock':
            self.modifier_state['caps_lock'] = not self.modifier_state['caps_lock']

        # Get scan code
        scan_code = self.get_scan_code(key)
        if scan_code > 0:
            # Legacy path: call CPU directly if bus is not available
            if self._cpu_legacy and not self.bus:
                self._cpu_legacy.add_key_to_buffer(scan_code)
            else:
                # New path: manage buffer internally + publish event
                self.add_key(scan_code)

            if self.event_callback:
                self.event_callback('press', key, scan_code)

    def release_key(self, key: str):
        """Simulate a key release"""
        if key in ['shift', 'ctrl', 'alt']:
            self.modifier_state[key] = False

        if self.event_callback:
            scan_code = self.get_scan_code(key)
            self.event_callback('release', key, scan_code)

    def type_string(self, text: str):
        """Type a string by pressing keys in sequence"""
        for char in text:
            if char == '\n':
                self.press_key('enter', apply_debounce=False)
            elif char == '\t':
                self.press_key('tab', apply_debounce=False)
            elif char == '\b':
                self.press_key('backspace', apply_debounce=False)
            else:
                self.press_key(char, apply_debounce=False)

    def set_event_callback(self, callback: Callable[[str, str, int], None]):
        """Set callback function for keyboard events"""
        self.event_callback = callback

    def set_debounce_window_ms(self, debounce_ms: int):
        """Update keyboard debounce window in milliseconds."""
        self.debounce_window_seconds = max(0, debounce_ms) / 1000.0

    def get_buffer_status(self) -> Dict[str, int]:
        """Get keyboard buffer status — works with or without CPU ref."""
        if self._cpu_legacy and not self._buffer:
            # Legacy path: get from CPU
            return {
                'available': self._cpu_legacy.keyboard[1] & 0x01,
                'count': self._cpu_legacy.keyboard[3],
                'status': self._cpu_legacy.keyboard[1],
                'full': (self._cpu_legacy.keyboard[1] & 0x02) >> 1
            }
        # New path: read from internal buffer
        return {
            'available': self.status_register & 0x01,
            'count': self.buffer_count,
            'status': self.status_register,
            'full': (self.status_register & 0x02) >> 1
        }

    # ── CPU-readable register access for instruction handlers ──────────

    def read_key_from_buffer(self):
        """Read and remove oldest key (compatible with CPU instruction handler calls)."""
        return self.read_key()

    def add_key_to_buffer(self, key_code):
        """Add a key press (compatible with CPU instruction handler calls)."""
        self.add_key(key_code)

    def clear_keyboard_buffer(self):
        """Clear buffer (compatible with CPU instruction handler calls)."""
        self.clear_buffer()


class KeyboardSimulator:
    """Simulate keyboard input for testing purposes"""

    def __init__(self, keyboard: NovaKeyboard):
        self.keyboard = keyboard
        self.running = False
        self.thread = None

    def start_simulation(self):
        """Start keyboard simulation thread"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._simulation_loop)
            self.thread.daemon = True
            self.thread.start()

    def stop_simulation(self):
        """Stop keyboard simulation"""
        self.running = False
        if self.thread:
            self.thread.join()

    def _simulation_loop(self):
        """Main simulation loop"""
        test_sequence = [
            "Hello Nova-16!",
            "enter",
            "Testing keyboard input...",
            "enter",
            "Special keys: ",
            "f1", "f2", "escape",
            "enter"
        ]

        while self.running:
            for item in test_sequence:
                if not self.running:
                    break

                if self.keyboard is not None:
                    if len(item) == 1 or item in ['enter', 'f1', 'f2', 'escape']:
                        self.keyboard.press_key(item)
                    else:
                        self.keyboard.type_string(item)

                time.sleep(0.5)

            time.sleep(2)


def create_test_keyboard(cpu_ref=None) -> NovaKeyboard:
    """Create a keyboard instance for testing"""
    keyboard = NovaKeyboard(cpu_ref=cpu_ref)

    def debug_callback(event_type, key, scan_code):
        print(f"Keyboard {event_type}: '{key}' -> 0x{scan_code:02X}")

    keyboard.set_event_callback(debug_callback)
    return keyboard


if __name__ == "__main__":
    print("Testing Nova-16 Keyboard Module")
    keyboard = create_test_keyboard()
    print(f"'A' -> 0x{keyboard.get_scan_code('A'):02X}")
    print(f"'a' -> 0x{keyboard.get_scan_code('a'):02X}")
    print(f"'1' -> 0x{keyboard.get_scan_code('1'):02X}")
    print(f"'enter' -> 0x{keyboard.get_scan_code('enter'):02X}")
    print(f"'f1' -> 0x{keyboard.get_scan_code('f1'):02X}")
    print("\nTesting key presses:")
    keyboard.type_string("Hello!")
    keyboard.press_key('enter')
    keyboard.press_key('f1')