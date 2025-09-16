"""
Unit tests for nova_keyboard.py - Nova-16 keyboard system.
"""

import pytest
import time


class TestKeyboardInitialization:
    """Test keyboard system initialization."""

    def test_keyboard_initialization(self, keyboard_device):
        """Test that keyboard initializes correctly."""
        assert keyboard_device.cpu is None
        assert keyboard_device.event_callback is None
        assert isinstance(keyboard_device.key_mapping, dict)
        assert len(keyboard_device.key_mapping) > 0

    def test_keyboard_modifier_state(self, keyboard_device):
        """Test that modifier states are initialized."""
        expected_modifiers = {
            'shift': False,
            'ctrl': False,
            'alt': False,
            'caps_lock': False,
            'num_lock': False
        }
        assert keyboard_device.modifier_state == expected_modifiers

    def test_keyboard_with_cpu(self, keyboard_device, cpu):
        """Test keyboard initialization with CPU reference."""
        keyboard_with_cpu = type(keyboard_device)(cpu_ref=cpu)
        assert keyboard_with_cpu.cpu is cpu


class TestKeyboardScanCodes:
    """Test keyboard scan code generation."""

    def test_scan_code_basic_letters(self, keyboard_device):
        """Test scan codes for basic letters."""
        assert keyboard_device.get_scan_code('a') == ord('a')
        assert keyboard_device.get_scan_code('A') == ord('a')  # Mapping doesn't distinguish case
        assert keyboard_device.get_scan_code('z') == ord('z')
        assert keyboard_device.get_scan_code('Z') == ord('z')  # Mapping doesn't distinguish case

    def test_scan_code_numbers(self, keyboard_device):
        """Test scan codes for numbers."""
        assert keyboard_device.get_scan_code('0') == ord('0')
        assert keyboard_device.get_scan_code('9') == ord('9')

    def test_scan_code_special_keys(self, keyboard_device):
        """Test scan codes for special keys."""
        assert keyboard_device.get_scan_code('enter') == 0x0A  # 10
        assert keyboard_device.get_scan_code('backspace') == 0x08  # 8
        assert keyboard_device.get_scan_code(' ') == 0x20  # 32
        assert keyboard_device.get_scan_code('tab') == 0x09  # 9
        assert keyboard_device.get_scan_code('escape') == 0x1B  # 27

    def test_scan_code_arrow_keys(self, keyboard_device):
        """Test scan codes for arrow keys."""
        assert keyboard_device.get_scan_code('left') == 0x80
        assert keyboard_device.get_scan_code('right') == 0x81
        assert keyboard_device.get_scan_code('up') == 0x82
        assert keyboard_device.get_scan_code('down') == 0x83

    def test_scan_code_function_keys(self, keyboard_device):
        """Test scan codes for function keys."""
        assert keyboard_device.get_scan_code('f1') == 0x84
        assert keyboard_device.get_scan_code('f10') == 0x8D
        assert keyboard_device.get_scan_code('f12') == 0x8F

    def test_scan_code_modifiers(self, keyboard_device):
        """Test that modifiers return 0 scan code."""
        assert keyboard_device.get_scan_code('shift') == 0
        assert keyboard_device.get_scan_code('ctrl') == 0
        assert keyboard_device.get_scan_code('alt') == 0


class TestKeyboardModifiers:
    """Test keyboard modifier handling."""

    def test_shift_modifier(self, keyboard_device):
        """Test shift modifier changes case."""
        # Without shift
        assert keyboard_device.get_scan_code('a') == ord('a')

        # Press shift
        keyboard_device.press_key('shift')
        assert keyboard_device.modifier_state['shift'] == True
        assert keyboard_device.get_scan_code('a') == ord('A')

        # Release shift
        keyboard_device.release_key('shift')
        assert keyboard_device.modifier_state['shift'] == False
        assert keyboard_device.get_scan_code('a') == ord('a')

    def test_caps_lock_modifier(self, keyboard_device):
        """Test caps lock modifier."""
        # Initially lowercase
        assert keyboard_device.get_scan_code('a') == ord('a')

        # Toggle caps lock
        keyboard_device.press_key('caps_lock')
        assert keyboard_device.modifier_state['caps_lock'] == True
        assert keyboard_device.get_scan_code('a') == ord('A')

        # Toggle caps lock again
        keyboard_device.press_key('caps_lock')
        assert keyboard_device.modifier_state['caps_lock'] == False
        assert keyboard_device.get_scan_code('a') == ord('a')

    def test_shift_caps_lock_interaction(self, keyboard_device):
        """Test shift and caps lock interaction."""
        # Enable caps lock
        keyboard_device.press_key('caps_lock')

        # With caps lock, 'a' should be 'A'
        assert keyboard_device.get_scan_code('a') == ord('A')

        # With caps lock + shift, 'a' should be 'a' (shift cancels caps)
        keyboard_device.press_key('shift')
        assert keyboard_device.get_scan_code('a') == ord('a')

        keyboard_device.release_key('shift')
        assert keyboard_device.get_scan_code('a') == ord('A')


class TestKeyboardEvents:
    """Test keyboard event handling."""

    def test_key_press_event(self, keyboard_device):
        """Test key press event callback."""
        events = []

        def callback(event_type, key, scan_code):
            events.append((event_type, key, scan_code))

        keyboard_device.set_event_callback(callback)
        keyboard_device.press_key('a')

        assert len(events) == 1
        assert events[0] == ('press', 'a', ord('a'))

    def test_key_release_event(self, keyboard_device):
        """Test key release event callback."""
        events = []

        def callback(event_type, key, scan_code):
            events.append((event_type, key, scan_code))

        keyboard_device.set_event_callback(callback)
        keyboard_device.release_key('a')

        assert len(events) == 1
        assert events[0] == ('release', 'a', ord('a'))

    def test_modifier_key_events(self, keyboard_device):
        """Test that modifier keys don't generate events."""
        events = []

        def callback(event_type, key, scan_code):
            events.append((event_type, key, scan_code))

        keyboard_device.set_event_callback(callback)
        keyboard_device.press_key('shift')
        keyboard_device.press_key('a')  # This should generate an event

        assert len(events) == 1
        assert events[0] == ('press', 'a', ord('A'))  # Uppercase due to shift


class TestKeyboardTyping:
    """Test keyboard typing functionality."""

    def test_type_string_basic(self, keyboard_device):
        """Test typing a basic string."""
        events = []

        def callback(event_type, key, scan_code):
            events.append((event_type, key, scan_code))

        keyboard_device.set_event_callback(callback)
        keyboard_device.type_string("hello")

        assert len(events) == 5
        expected_keys = ['h', 'e', 'l', 'l', 'o']
        for i, key in enumerate(expected_keys):
            assert events[i] == ('press', key, ord(key))

    def test_type_string_special_chars(self, keyboard_device):
        """Test typing string with special characters."""
        events = []

        def callback(event_type, key, scan_code):
            events.append((event_type, key, scan_code))

        keyboard_device.set_event_callback(callback)
        keyboard_device.type_string("a\n\t\b")

        assert len(events) == 4
        assert events[0] == ('press', 'a', ord('a'))
        assert events[1] == ('press', 'enter', 0x0A)
        assert events[2] == ('press', 'tab', 0x09)
        assert events[3] == ('press', 'backspace', 0x08)


class TestKeyboardBufferStatus:
    """Test keyboard buffer status reporting."""

    def test_buffer_status_no_cpu(self, keyboard_device):
        """Test buffer status when no CPU is attached."""
        status = keyboard_device.get_buffer_status()
        assert status == {'available': 0, 'count': 0, 'status': 0}

    def test_buffer_status_with_cpu(self, keyboard_device, cpu):
        """Test buffer status with CPU attached."""
        keyboard_device.cpu = cpu
        status = keyboard_device.get_buffer_status()

        # Should return CPU keyboard register values
        assert 'available' in status
        assert 'count' in status
        assert 'status' in status
        assert 'full' in status


class TestKeyboardSimulator:
    """Test keyboard simulator functionality."""

    def test_simulator_initialization(self, keyboard_device):
        """Test keyboard simulator initialization."""
        from nova_keyboard import KeyboardSimulator
        simulator = KeyboardSimulator(keyboard_device)

        assert simulator.keyboard is keyboard_device
        assert simulator.running == False
        assert simulator.thread is None

    def test_simulator_start_stop(self, keyboard_device):
        """Test starting and stopping the simulator."""
        from nova_keyboard import KeyboardSimulator
        simulator = KeyboardSimulator(keyboard_device)

        simulator.start_simulation()
        assert simulator.running == True
        assert simulator.thread is not None

        simulator.stop_simulation()
        assert simulator.running == False


class TestKeyboardStressTesting:
    """Aggressive stress testing for keyboard operations."""

    def test_rapid_typing_stress(self, keyboard_device):
        """Stress test with rapid typing of many characters."""
        events = []

        def callback(event_type, key, scan_code):
            events.append((event_type, key, scan_code))

        keyboard_device.set_event_callback(callback)

        # Type a very long string rapidly
        long_text = "The quick brown fox jumps over the lazy dog. " * 100  # ~4500 characters
        keyboard_device.type_string(long_text)

        # Should generate press events for each character
        assert len(events) == len(long_text)
        for i, char in enumerate(long_text):
            # The key name stays as passed, but scan_code is lowercased
            expected_code = ord(char.lower())  # Always lowercase scan code
            assert events[i] == ('press', char, expected_code)

    def test_simultaneous_key_presses(self, keyboard_device):
        """Test pressing many keys simultaneously."""
        events = []

        def callback(event_type, key, scan_code):
            events.append((event_type, key, scan_code))

        keyboard_device.set_event_callback(callback)

        # Press many keys at once
        keys_to_press = ['a', 'b', 'c', 'f1', 'f2', 'left', 'right', 'up', 'down']
        for key in keys_to_press:
            keyboard_device.press_key(key)

        # Should generate events for all non-modifier keys
        assert len(events) == len(keys_to_press)

        # Release all keys
        events.clear()  # Clear press events
        for key in keys_to_press:
            keyboard_device.release_key(key)

        # Should generate release events
        assert len(events) == len(keys_to_press)

    def test_buffer_overflow_simulation(self, keyboard_device, cpu):
        """Test behavior when keyboard buffer would overflow."""
        keyboard_device.cpu = cpu

        # Simulate filling the buffer
        for i in range(100):  # More than typical buffer size
            # Simulate key press by directly calling the method that would add to buffer
            keyboard_device.press_key('a')

        # Check buffer status
        status = keyboard_device.get_buffer_status()
        assert 'count' in status
        assert 'full' in status

    def test_rapid_key_toggle_stress(self, keyboard_device):
        """Stress test rapid pressing and releasing of keys."""
        events = []

        def callback(event_type, key, scan_code):
            events.append((event_type, key, scan_code))

        keyboard_device.set_event_callback(callback)

        # Rapidly toggle a key many times
        for _ in range(1000):
            keyboard_device.press_key(' ')  # Use space character, not 'space'
            keyboard_device.release_key(' ')

        # Should generate 2000 events (1000 press + 1000 release)
        assert len(events) == 2000
        for i in range(0, 2000, 2):
            assert events[i] == ('press', ' ', 32)
            assert events[i + 1] == ('release', ' ', 32)

    def test_complex_modifier_combinations(self, keyboard_device):
        """Test complex combinations of modifiers."""
        events = []

        def callback(event_type, key, scan_code):
            events.append((event_type, key, scan_code))

        keyboard_device.set_event_callback(callback)

        # Press multiple modifiers
        keyboard_device.press_key('shift')
        keyboard_device.press_key('ctrl')
        keyboard_device.press_key('alt')

        # All modifiers should be active
        assert keyboard_device.modifier_state['shift'] == True
        assert keyboard_device.modifier_state['ctrl'] == True
        assert keyboard_device.modifier_state['alt'] == True

        # Press a key with all modifiers
        keyboard_device.press_key('a')
        assert len(events) == 1
        # The scan code should reflect the modifiers (implementation dependent)

        # Release modifiers in different order
        keyboard_device.release_key('alt')
        keyboard_device.release_key('ctrl')
        keyboard_device.release_key('shift')

        assert keyboard_device.modifier_state['shift'] == False
        assert keyboard_device.modifier_state['ctrl'] == False
        assert keyboard_device.modifier_state['alt'] == False

    def test_caps_lock_toggle_stress(self, keyboard_device):
        """Stress test caps lock toggling."""
        initial_state = keyboard_device.modifier_state['caps_lock']

        # Toggle caps lock many times
        for i in range(100):
            keyboard_device.press_key('caps_lock')
            # Caps lock should toggle on each press
            expected_state = (i + 1) % 2 == 1
            assert keyboard_device.modifier_state['caps_lock'] == expected_state

        # Should be back to initial state (even number of toggles)
        assert keyboard_device.modifier_state['caps_lock'] == initial_state

    def test_mixed_case_typing_stress(self, keyboard_device):
        """Stress test typing with mixed case and modifiers."""
        events = []

        def callback(event_type, key, scan_code):
            events.append((event_type, key, scan_code))

        keyboard_device.set_event_callback(callback)

        # Type mixed case text with manual modifier control
        text = "Hello World!"
        for char in text:
            if char.isupper():
                keyboard_device.press_key('shift')
                keyboard_device.press_key(char.lower())
                keyboard_device.release_key('shift')
            else:
                keyboard_device.press_key(char)

        # Should generate events for each character press (and shift releases)
        # 'H','e','l','l','o',' ','W','o','r','l','d','!' = 12 chars
        # Plus 2 shift releases for 'H' and 'W' = 2 extra events
        # Total: 14 events (shift presses don't generate events)
        assert len(events) == 14

        # Check that we have the expected types of events
        press_events = [e for e in events if e[0] == 'press']
        release_events = [e for e in events if e[0] == 'release']
        assert len(press_events) == 12  # 12 chars
        assert len(release_events) == 2  # 2 shift releases


class TestKeyboardEdgeCases:
    """Edge case and boundary testing for keyboard operations."""

    def test_invalid_key_names(self, keyboard_device):
        """Test handling of invalid key names."""
        # Invalid key names should not crash
        keyboard_device.press_key('invalid_key_123')
        keyboard_device.release_key('nonexistent_key')
        keyboard_device.get_scan_code('bad_key_name')

        # Should not crash and return 0 for unknown keys
        assert keyboard_device.get_scan_code('invalid_key') == 0

    def test_empty_string_typing(self, keyboard_device):
        """Test typing empty strings."""
        events = []

        def callback(event_type, key, scan_code):
            events.append((event_type, key, scan_code))

        keyboard_device.set_event_callback(callback)

        # Empty string should not generate events
        keyboard_device.type_string("")
        assert len(events) == 0

        # String with only whitespace
        keyboard_device.type_string("   ")
        assert len(events) == 3  # Three space characters

    def test_unicode_and_special_characters(self, keyboard_device):
        """Test handling of unicode and special characters."""
        # Unicode characters not in ASCII mapping should return 0
        assert keyboard_device.get_scan_code('ñ') == 0  # Not in ASCII range
        assert keyboard_device.get_scan_code('©') == 0  # Not in ASCII range

        # Control characters that are mapped
        assert keyboard_device.get_scan_code('enter') == 0x0A  # enter key
        assert keyboard_device.get_scan_code('tab') == 0x09  # tab key
        assert keyboard_device.get_scan_code('backspace') == 0x08  # backspace key

        # Raw control characters return 0
        assert keyboard_device.get_scan_code('\n') == 0  # newline char not directly mapped
        assert keyboard_device.get_scan_code('\t') == 0  # tab char not directly mapped

    def test_modifier_state_preservation(self, keyboard_device):
        """Test that modifier states are preserved correctly."""
        # Set initial modifier states
        keyboard_device.press_key('shift')
        keyboard_device.press_key('caps_lock')

        assert keyboard_device.modifier_state['shift'] == True
        assert keyboard_device.modifier_state['caps_lock'] == True

        # Perform many operations
        for _ in range(100):
            keyboard_device.press_key('a')
            keyboard_device.release_key('a')

        # Modifiers should still be active
        assert keyboard_device.modifier_state['shift'] == True
        assert keyboard_device.modifier_state['caps_lock'] == True

        # Release modifiers
        keyboard_device.release_key('shift')
        keyboard_device.press_key('caps_lock')  # Toggle off

        assert keyboard_device.modifier_state['shift'] == False
        assert keyboard_device.modifier_state['caps_lock'] == False

    def test_callback_none_handling(self, keyboard_device):
        """Test behavior when no callback is set."""
        # Should not crash when no callback is set
        keyboard_device.press_key('a')
        keyboard_device.release_key('a')
        keyboard_device.type_string("test")

        # Set callback to None explicitly
        keyboard_device.set_event_callback(None)
        keyboard_device.press_key('b')
        keyboard_device.release_key('b')

        # Should not crash

    def test_simulator_thread_safety(self, keyboard_device):
        """Test simulator thread safety."""
        from nova_keyboard import KeyboardSimulator
        import threading

        simulator = KeyboardSimulator(keyboard_device)

        # Start simulator
        simulator.start_simulation()

        # Perform operations while simulator is running
        events_received = []

        def test_callback(event_type, key, scan_code):
            events_received.append((event_type, key, scan_code))

        keyboard_device.set_event_callback(test_callback)

        # Simulate some activity
        for _ in range(10):
            keyboard_device.press_key('a')
            keyboard_device.release_key('a')

        # Stop simulator
        simulator.stop_simulation()

        # Should have received events
        assert len(events_received) == 20  # 10 press + 10 release

    def test_memory_reference_handling(self, keyboard_device, cpu):
        """Test memory reference handling edge cases."""
        # No CPU reference
        status = keyboard_device.get_buffer_status()
        assert status == {'available': 0, 'count': 0, 'status': 0}

        # With CPU reference
        keyboard_device.cpu = cpu
        status = keyboard_device.get_buffer_status()
        assert isinstance(status, dict)
        assert 'available' in status

        # CPU with no memory
        cpu.memory = None
        status = keyboard_device.get_buffer_status()
        # Should handle gracefully
        assert isinstance(status, dict)

    def test_key_mapping_completeness(self, keyboard_device):
        """Test that key mapping covers expected keys."""
        # Should have mappings for common keys
        common_keys = ['a', 'z', '0', '9', 'enter', ' ', 'backspace', 'tab', 'escape']
        for key in common_keys:
            scan_code = keyboard_device.get_scan_code(key)
            assert scan_code != 0 or key in ['shift', 'ctrl', 'alt']  # Modifiers return 0

        # Should have arrow keys
        arrow_keys = ['left', 'right', 'up', 'down']
        for key in arrow_keys:
            scan_code = keyboard_device.get_scan_code(key)
            assert scan_code >= 0x80  # Arrow keys start at 0x80

    def test_event_callback_error_handling(self, keyboard_device):
        """Test error handling in event callbacks."""
        def failing_callback(event_type, key, scan_code):
            raise Exception("Callback error")

        keyboard_device.set_event_callback(failing_callback)

        # Current implementation does not handle callback errors - they propagate up
        with pytest.raises(Exception, match="Callback error"):
            keyboard_device.press_key('a')

    def test_simulator_configuration_edge_cases(self, keyboard_device):
        """Test simulator configuration edge cases."""
        from nova_keyboard import KeyboardSimulator

        # Create simulator with None keyboard (should handle gracefully)
        simulator = KeyboardSimulator(None)
        assert simulator.keyboard is None

        # Operations on simulator with None keyboard
        simulator.start_simulation()  # Should not crash
        simulator.stop_simulation()   # Should not crash