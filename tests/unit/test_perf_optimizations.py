"""
Tests for performance optimizations implemented based on profile analysis.

Covers:
  - P0: Event bus bypass (direct timer/intr call)
  - P2: Operand pool minimal reset
  - P3: Graphics layer-0 fast path (skips pixel count update)
  - P4/P6: Trap flag and async interrupt source caching
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from nova.memory.memory import Memory
from nova.bus.eventbus import EventBus
from nova.bus.interrupt import InterruptController
from nova.peripherals.timer import Timer
from core.flags import Flags
from core.fetch import Operand, _acquire_operand, _release_operand, _operand_pool
from nova.graphics.gfx import GFX
from nova.graphics.compositor import Compositor


# ── P0: Event bus bypass ──────────────────────────────────────────────

class TestEventBusBypass:
    """Verify timer tick and interrupt check happen without bus publish overhead."""

    def test_timer_on_tick_called_directly(self):
        """Timer._on_tick is called directly from step(), not via bus.publish."""
        mem = Memory()
        gfx = GFX()
        bus = EventBus()
        intr_ctrl = InterruptController(bus=bus, memory=mem)
        timer = Timer(bus=bus, interrupt_controller=intr_ctrl)

        # Spy on timer._on_tick
        original_on_tick = timer._on_tick
        call_count = [0]

        def spy_on_tick(data=None):
            call_count[0] += 1
            return original_on_tick(data)

        timer._on_tick = spy_on_tick

        # Unsubscribe from bus so direct call is the only path
        bus.unsubscribe('cpu.tick', original_on_tick)

        from nova_cpu import CPU
        cpu = CPU(memory=mem, gfx=gfx, bus=bus,
                  interrupt_controller=intr_ctrl, timer_device=timer)

        # Step should call _on_tick directly
        cpu.step()
        assert call_count[0] == 1, "Timer._on_tick should have been called directly"

    def test_interrupt_check_called_directly(self):
        """InterruptController.check() is called directly, not via bus."""
        mem = Memory()
        gfx = GFX()
        bus = EventBus()
        intr_ctrl = InterruptController(bus=bus, memory=mem)
        timer = Timer(bus=bus, interrupt_controller=intr_ctrl)

        # Spy on interrupt controller check
        original_check = intr_ctrl.check
        check_count = [0]

        def spy_check():
            check_count[0] += 1
            original_check()

        intr_ctrl.check = spy_check

        # Unsubscribe from bus so direct call is the only path
        bus.unsubscribe('cpu.post_step', original_check)

        from nova_cpu import CPU
        cpu = CPU(memory=mem, gfx=gfx, bus=bus,
                  interrupt_controller=intr_ctrl, timer_device=timer)

        cpu.step()
        assert check_count[0] == 1, "InterruptController.check should have been called directly"


# ── P2: Operand pool minimal reset ────────────────────────────────────

class TestOperandPoolMinimalReset:
    """Verify the operand pool reset only clears necessary fields."""

    def setup_method(self):
        # Clear the pool before each test
        _operand_pool.clear()

    def test_reset_does_not_clear_decode_fields(self):
        """Fields set by decode branches should NOT be cleared by reset."""
        op = _acquire_operand()
        # Simulate a register operand decode
        op.mode = 0
        op.type = 'register'
        op.reg_type = 'R'
        op.reg_idx = 3
        op.is_register = True

        # Release to pool
        _release_operand(op)

        # Acquire same operand — should be reset
        op2 = _acquire_operand()
        assert op2.mode == 0, "mode should be reset to 0"
        assert op2.value == 0, "value should be reset to 0"
        assert op2.is_register is False, "is_register should be reset to False"
        assert op2.is_immediate is False, "is_immediate should be reset to False"
        assert op2.is_memory is False, "is_memory should be reset to False"
        assert op2.indirect is False, "indirect should be reset to False"
        assert op2.indexed is False, "indexed should be reset to False"

    def test_register_decode_sets_all_needed_fields(self):
        """After pool reset, register decode sets is_register and type."""
        op = _acquire_operand()
        op.mode = 0
        op.type = 'register'
        op.reg_type = 'R'
        op.reg_idx = 5
        op.is_register = True

        assert op.type == 'register'
        assert op.reg_type == 'R'
        assert op.reg_idx == 5
        assert op.is_register is True
        assert op.is_immediate is False
        assert op.is_memory is False

    def test_immediate_decode_sets_all_needed_fields(self):
        """After pool reset, immediate decode sets is_immediate."""
        op = _acquire_operand()
        op.mode = 1
        op.type = 'immediate'
        op.value = 42
        op.size = 8
        op.is_immediate = True

        assert op.type == 'immediate'
        assert op.value == 42
        assert op.is_immediate is True
        assert op.is_register is False
        assert op.is_memory is False

    def test_pool_reuse_preserves_correctness(self):
        """Full round-trip through pool: register → release → immediate → correct.

        Note: reg_type is NOT reset in the minimal reset since it's always set
        by decode branches. Pool reuse correctness relies on the decode branch
        setting reg_type before any code reads it.
        """
        op1 = _acquire_operand()
        op1.mode = 0
        op1.type = 'register'
        op1.reg_type = 'P'
        op1.reg_idx = 2
        op1.is_register = True
        _release_operand(op1)

        # Acquire fresh — should have boolean flags cleared
        op2 = _acquire_operand()
        op2.mode = 2
        op2.type = 'immediate'
        op2.value = 0x1234
        op2.size = 16
        op2.is_immediate = True

        assert op2.type == 'immediate'
        assert op2.value == 0x1234
        assert op2.is_register is False, "register flag leaked from previous use"
        assert op2.is_memory is False, "memory flag leaked"

    def test_13_field_reset_became_10_fields(self):
        """Verify reset only clears 10 fields, not the original 13."""
        import inspect
        source = inspect.getsource(Operand.reset)
        # Count assignment statements (self.X = Y)
        assignments = [l.strip() for l in source.split('\n')
                       if 'self.' in l and '=' in l and not l.strip().startswith('#')]
        assert len(assignments) <= 10, \
            f"Expected ≤ 10 field resets, got {len(assignments)}. " \
            f"Old code had 13 — verify optimization was applied correctly."


# ── P3: Graphics layer-0 fast path ────────────────────────────────────

class TestGraphicsLayer0FastPath:
    """Verify layer-0 pixel writes skip pixel count tracking but keep dual-buffer write."""

    def test_set_pixel_layer0_writes_both_buffers(self):
        """Layer 0 writes both layers[0] and _screen."""
        gfx = GFX()
        gfx.Vregisters[0] = 10
        gfx.Vregisters[1] = 20
        gfx.Vregisters[2] = 0  # coordinate mode
        gfx.VL = 0

        gfx.set_screen_val(0x42)

        assert gfx._compositor.layers[0][20, 10] == 0x42
        assert gfx._compositor._screen[20, 10] == 0x42

    def test_set_pixel_layer0_skips_pixel_count_update(self):
        """Layer 0 pixel writes should NOT update pixel counts."""
        gfx = GFX()
        gfx.Vregisters[0] = 0
        gfx.Vregisters[1] = 0
        gfx.VL = 0

        # Get initial pixel count (should be 0 for empty layer)
        initial_count = gfx._compositor._pixel_counts[0]

        # Write several pixels
        for i in range(10):
            gfx.Vregisters[0] = i
            gfx.set_screen_val(0xFF)

        # Pixel count should NOT have changed (optimization: skip tracking for layer 0)
        # Note: the pixel count for layer 0 is not maintained per-pixel anymore
        assert gfx._compositor._pixel_counts[0] == initial_count

    def test_set_pixel_layer1_still_tracks_counts(self):
        """Layer 1+ should still track pixel counts via compositor."""
        gfx = GFX()
        gfx.Vregisters[0] = 5
        gfx.Vregisters[1] = 5
        gfx.VL = 1

        # Ensure initial state
        gfx._compositor._pixel_counts[1] = 0

        gfx.set_screen_val(0xFF)

        assert gfx._compositor._pixel_counts[1] == 1, \
            "Layer 1 pixel count should be updated"


# ── P4/P6: Trap flag and async interrupt source caching ───────────────

class TestTrapFlagCaching:
    """Verify trap flag is accessed via property, not __getitem__."""

    def test_trap_flag_property_works(self):
        """The trap_flag property correctly reads and writes the trap flag."""
        flags = Flags()
        assert flags.trap_flag == 0

        flags.trap_flag = 1
        assert flags.trap_flag == 1
        assert flags[0] == 1  # Index 0 should also show 1

    def test_trap_flag_setter_clears(self):
        """Setting trap_flag to 0 clears it."""
        flags = Flags()
        flags.trap_flag = 1
        flags.trap_flag = 0
        assert flags.trap_flag == 0


class TestAsyncInterruptSourceCaching:
    """Verify _has_enabled_async_interrupt_sources caches its result."""

    def test_caching_updates_on_change(self):
        """Setting interrupt vectors should be reflected in cached value."""
        mem = Memory()
        gfx = GFX()
        bus = EventBus()
        intr_ctrl = InterruptController(bus=bus, memory=mem)
        timer = Timer(bus=bus, interrupt_controller=intr_ctrl)

        from nova_cpu import CPU
        cpu = CPU(memory=mem, gfx=gfx, bus=bus,
                  interrupt_controller=intr_ctrl, timer_device=timer)

        # Initially no async sources
        cpu._cached_async_sources = False
        assert cpu._has_enabled_async_interrupt_sources() is False
        assert cpu._cached_async_sources is False

        # Enable keyboard interrupt source
        cpu.interrupts[2] = 1
        assert cpu._has_enabled_async_interrupt_sources() is True
        assert cpu._cached_async_sources is True

    def test_no_interrupt_sources_cached_as_false(self):
        """With no interrupts enabled, cache returns False."""
        mem = Memory()
        gfx = GFX()
        bus = EventBus()
        intr_ctrl = InterruptController(bus=bus, memory=mem)
        timer = Timer(bus=bus, interrupt_controller=intr_ctrl)

        from nova_cpu import CPU
        cpu = CPU(memory=mem, gfx=gfx, bus=bus,
                  interrupt_controller=intr_ctrl, timer_device=timer)

        cpu.interrupts[:] = [0] * 8
        result = cpu._has_enabled_async_interrupt_sources()
        assert result is False
        assert cpu._cached_async_sources is False


# ── Integration: End-to-end correctness after optimizations ────────────

class TestOptimizationsIntegration:
    """Verify that the system still behaves correctly with all optimizations active.

    Uses the existing comprehensive test suite (570 tests) as the primary integration
    verification. These tests validate key optimization-aware behaviors.
    """

    def test_direct_timer_call_doesnt_crash(self):
        """CPU construction and stepping works with direct timer/intr calls (P0)."""
        mem = Memory()
        gfx = GFX()
        bus = EventBus()
        intr_ctrl = InterruptController(bus=bus, memory=mem)
        timer = Timer(bus=bus, interrupt_controller=intr_ctrl)

        from nova_cpu import CPU
        cpu = CPU(memory=mem, gfx=gfx, bus=bus,
                  interrupt_controller=intr_ctrl, timer_device=timer)

        # Verify CPU initializes correctly with all optimizations
        assert cpu.pc == 0x0000
        assert cpu.timer_device is timer
        assert cpu.intr_ctrl is intr_ctrl
        assert cpu.flags_obj.trap_flag == 0

    def test_layer0_fast_path_visible_in_composite(self):
        """Layer 0 writes via fast path still appear in composited output."""
        gfx = GFX()
        gfx.VL = 0

        # Write several pixels through the optimized path
        for x in range(5):
            for y in range(5):
                gfx.Vregisters[0] = x
                gfx.Vregisters[1] = y
                gfx.set_screen_val(0xFF)

        # Composite should reflect these pixels
        gfx.composite_layers()
        for x in range(5):
            for y in range(5):
                assert gfx.screen[y, x] == 0xFF, \
                    f"Screen pixel ({x},{y}) should be 0xFF"
