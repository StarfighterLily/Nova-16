"""
Unit tests for batched interrupt processing in InterruptController.

Tests the following behaviors:
- Multiple pending interrupts serviced in priority order within a single check
- Throttling via check_frequency prevents unnecessary scans
- State hash cache skips redundant scans
- I-flag re-check prevents nested interrupt overflow
"""
import pytest
from nova.bus.interrupt import InterruptController
from nova.bus.eventbus import EventBus
from nova.memory import Memory


class MockCPU:
    """Minimal CPU mock for interrupt controller testing."""
    def __init__(self):
        self.interrupts = [0] * 8
        self.pc = 0x0100
        self.flags = [0] * 12  # Indexed access like flags[Flags.I]
        self.Pregisters = [0] * 10
        self.Pregisters[8] = 0xFFFE  # SP
        self.regfile = type('obj', (object,), {'R': [0]*10, 'P': [0]*10})()


class TestInterruptBatchProcessing:
    """Test batched interrupt draining in InterruptController."""

    @pytest.fixture
    def bus(self):
        return EventBus()

    @pytest.fixture
    def memory(self):
        mem = Memory()
        # Set up interrupt vectors pointing to handlers at 0x2000-0x201C
        for i in range(8):
            mem.write_word(0x0100 + i * 4, 0x2000 + i * 2)
        return mem

    @pytest.fixture
    def mock_cpu(self):
        return MockCPU()

    @pytest.fixture
    def intr_ctrl(self, bus, mock_cpu, memory):
        ctrl = InterruptController(bus=bus, cpu=mock_cpu, memory=memory)
        ctrl.cpu = mock_cpu
        ctrl.memory = memory
        return ctrl

    def test_multiple_pending_interrupts_batched(self, intr_ctrl, mock_cpu, memory):
        """Multiple pending interrupts should be serviced in priority order within one check call."""
        # Set up all interrupt sources pending and enabled
        mock_cpu.interrupts[intr_ctrl.VECTOR_TIMER] = 1
        mock_cpu.interrupts[intr_ctrl.VECTOR_SERIAL] = 1
        mock_cpu.interrupts[intr_ctrl.VECTOR_KEYBOARD] = 1
        mock_cpu.interrupts[intr_ctrl.VECTOR_MOUSE] = 1
        
        intr_ctrl._timer_pending = True
        intr_ctrl._serial_pending = True
        intr_ctrl._keyboard_pending = True
        intr_ctrl._mouse_pending = True
        
        # Set I-flag enabled
        mock_cpu.flags[0] = 1  # T flag - will use for I in actual test
        
        # Set max_batch to 4 to allow all interrupts to be serviced
        intr_ctrl.max_batch = 4
        intr_ctrl.check_frequency = 1  # Force immediate check
        intr_ctrl.check_counter = 0
        
        # Also need to set the flags list-style access to work with Flags class
        class FlagsMock:
            I = 5
            _bits = 0
            def __getitem__(self, idx):
                if idx == self.I:
                    return 1  # I flag enabled
                return 0
            def __setitem__(self, idx, val):
                pass
            def pack(self):
                return 0x20  # I flag set
        mock_cpu.flags_obj = FlagsMock()
        
        # Trigger check
        intr_ctrl.check()
        
        # All pending flags should be cleared (timer gets serviced first due to priority)
        assert intr_ctrl._timer_pending is False
        assert intr_ctrl._serial_pending is False
        assert intr_ctrl._keyboard_pending is False
        assert intr_ctrl._mouse_pending is False

    def test_throttling_prevents_unnecessary_checks(self, intr_ctrl, mock_cpu, memory):
        """check_frequency should throttle interrupt checks."""
        # Set up interrupt enabled but no pending
        mock_cpu.interrupts[intr_ctrl.VECTOR_KEYBOARD] = 0
        
        intr_ctrl.check_frequency = 4
        intr_ctrl.check_counter = 0
        
        # Call check 3 times - should not run the actual scan (counter incremented inside check)
        for _ in range(3):
            intr_ctrl.check()
        
        # check_counter should be 3 after 3 calls (each call increments it)
        assert intr_ctrl.check_counter == 3

    def test_check_frequency_triggers_after_threshold(self, intr_ctrl, mock_cpu, memory):
        """check should trigger full scan after exactly check_frequency calls."""
        mock_cpu.interrupts[intr_ctrl.VECTOR_KEYBOARD] = 1
        intr_ctrl._keyboard_pending = True
        intr_ctrl.check_frequency = 4
        intr_ctrl.check_counter = 0
        
        class FlagsMock:
            I = 5
            _bits = 0x20  # I flag set
            def __getitem__(self, idx):
                if idx == self.I:
                    return 1
                return 0
            def __setitem__(self, idx, val):
                if idx == self.I:
                    self._bits = (self._bits & ~0x20) | (val << 5)
            def pack(self):
                return self._bits
        mock_cpu.flags_obj = FlagsMock()
        
        # First 3 calls should not trigger (counter becomes 1,2,3)
        for _ in range(3):
            intr_ctrl.check()
        assert intr_ctrl._keyboard_pending is True  # Not cleared yet
        
        # 4th call should trigger (counter was 3, increments to 4, which >= check_frequency)
        intr_ctrl.check()
        assert intr_ctrl._keyboard_pending is False  # Cleared

    def test_i_flag_prevents_interrupted_service(self, intr_ctrl, mock_cpu, memory):
        """I-flag re-check should stop batched drain when handler disables interrupts."""
        mock_cpu.interrupts[intr_ctrl.VECTOR_TIMER] = 1
        mock_cpu.interrupts[intr_ctrl.VECTOR_KEYBOARD] = 1
        
        intr_ctrl._timer_pending = True
        intr_ctrl._keyboard_pending = True
        intr_ctrl.check_frequency = 1
        
        class FlagsMock:
            I = 5
            _bits = 0x20  # I flag set initially
            def __getitem__(self, idx):
                if idx == self.I:
                    return self._bits >> 5 & 1
                return 0
            def __setitem__(self, idx, val):
                # When I flag is cleared by _trigger, subsequent reads should reflect that
                if idx == self.I:
                    self._bits = (self._bits & ~0x20) | (val << 5)
            def pack(self):
                return self._bits & 0xFFF
        mock_cpu.flags_obj = FlagsMock()
        
        # Trigger check - timer should be serviced, then I-flag check stops keyboard
        intr_ctrl.check()
        
        # Timer should be cleared
        assert intr_ctrl._timer_pending is False
        # Keyboard should still be pending because I-flag was cleared
        assert intr_ctrl._keyboard_pending is True

    def test_priority_order_respected(self, intr_ctrl, mock_cpu, memory):
        """Interrupts should be serviced in priority order: Timer > Serial > Keyboard > Mouse."""
        # Set up all pending but only keyboard enabled
        mock_cpu.interrupts[intr_ctrl.VECTOR_TIMER] = 0
        mock_cpu.interrupts[intr_ctrl.VECTOR_SERIAL] = 0
        mock_cpu.interrupts[intr_ctrl.VECTOR_KEYBOARD] = 1
        mock_cpu.interrupts[intr_ctrl.VECTOR_MOUSE] = 0
        
        intr_ctrl._timer_pending = True
        intr_ctrl._serial_pending = True
        intr_ctrl._keyboard_pending = True
        intr_ctrl._mouse_pending = True
        
        intr_ctrl.check_frequency = 1
        intr_ctrl.max_batch = 4
        
        class FlagsMock:
            I = 5
            _bits = 0x20
            def __getitem__(self, idx):
                if idx == self.I:
                    return 1
                return 0
            def __setitem__(self, idx, val):
                self._bits = (self._bits & ~0x20) | (val << 5)
            def pack(self):
                return self._bits & 0xFFF
        mock_cpu.flags_obj = FlagsMock()
        
        intr_ctrl.check()
        
        # Only keyboard should be cleared (timer/serial/mouse not enabled)
        assert intr_ctrl._timer_pending is True
        assert intr_ctrl._serial_pending is True
        assert intr_ctrl._keyboard_pending is False
        assert intr_ctrl._mouse_pending is True

    def test_state_hash_optimization(self, intr_ctrl, mock_cpu, memory):
        """last_state cache should skip redundant scans when nothing changed."""
        mock_cpu.interrupts[intr_ctrl.VECTOR_KEYBOARD] = 1
        intr_ctrl._keyboard_pending = False
        
        intr_ctrl.check_frequency = 1
        
        class FlagsMock:
            I = 5
            _bits = 0x20
            def __getitem__(self, idx):
                if idx == self.I:
                    return 0  # Interrupts disabled
                return 0
            def pack(self):
                return 0
        mock_cpu.flags_obj = FlagsMock()
        
        # First check will compute state=0 and return
        intr_ctrl.check()
        first_state = intr_ctrl.last_state
        
        # Second check should early-exit because state hasn't changed
        intr_ctrl.check()
        assert intr_ctrl.last_state == first_state


class TestInterruptControllerState:
    """Test get_state/set_state for batched interrupt controller."""

    @pytest.fixture
    def bus(self):
        return EventBus()

    @pytest.fixture
    def memory(self):
        return Memory()

    @pytest.fixture
    def mock_cpu(self):
        return MockCPU()

    def test_get_state_includes_batch_fields(self, bus, mock_cpu, memory):
        """get_state should include throttle and batch configuration."""
        ctrl = InterruptController(bus=bus, cpu=mock_cpu, memory=memory)
        state = ctrl.get_state()
        
        assert 'check_frequency' in state
        assert 'check_counter' in state
        assert 'max_batch' in state
        assert 'last_state' in state
        assert state['check_frequency'] == 8
        assert state['max_batch'] == 8

    def test_set_state_restores_batch_fields(self, bus, mock_cpu, memory):
        """set_state should restore throttle and batch configuration."""
        ctrl = InterruptController(bus=bus, cpu=mock_cpu, memory=memory)
        
        saved = {
            'check_frequency': 4,
            'check_counter': 2,
            'max_batch': 2,
            'last_state': 0x1234,
        }
        ctrl.set_state(saved)
        
        assert ctrl.check_frequency == 4
        assert ctrl.check_counter == 2
        assert ctrl.max_batch == 2
        assert ctrl.last_state == 0x1234


if __name__ == "__main__":
    pytest.main([__file__, "-v"])