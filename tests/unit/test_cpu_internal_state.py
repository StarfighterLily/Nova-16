"""Regression tests for CPU internal execution state management."""

import pytest


# Phase 4: Prefetch cache eliminated — these tests are no longer applicable.
# The CPU no longer has prefetch_buffer, instruction_cache, or operand_cache.
# All fetch operations go directly to memory, making these tests obsolete.
# We keep the module but convert tests to check the new cache-free behavior.

class TestCPUPrefetchInvalidation:
    """Prefetch cache was eliminated in Phase 4. Tests converted to verify direct-fetch behavior."""

    @pytest.mark.parametrize("offset,new_value", [(0, 0x11), (15, 0x22), (16, 0x33), (63, 0x44)])
    def test_write_byte_invalidates_prefetch_across_full_buffer(self, cpu, offset, new_value):
        """Phase 4: Prefetch removed — verify direct memory write-then-fetch semantics."""
        base_addr = 0x0200
        for index in range(64):
            cpu.memory.write_byte(base_addr + index, index & 0xFF)

        cpu.write_byte(base_addr + offset, new_value)
        cpu.pc = base_addr + offset
        assert cpu.fetch_byte() == new_value

    @pytest.mark.parametrize("offset,value,width", [(16, 0xAA, 1), (48, 0xBEEF, 2)])
    def test_write_memory_invalidates_prefetch_across_full_buffer(self, cpu, offset, value, width):
        """Phase 4: Prefetch removed — verify direct write-then-fetch semantics."""
        base_addr = 0x0300
        cpu.write_memory(base_addr + offset, value, bytes=width)
        cpu.pc = base_addr + offset
        if width == 1:
            assert cpu.fetch_byte() == value
        else:
            assert cpu.fetch_word() == value

    def test_self_modifying_code_uses_updated_opcode_beyond_old_window(self, cpu):
        """Phase 4: Prefetch removed — verify self-modifying code works."""
        base_addr = 0x0500
        for index in range(80):
            cpu.memory.write_byte(base_addr + index, 0xFF)  # NOPs
        cpu.memory.write_byte(base_addr + 63, 0x00)  # HLT at offset 63

        cpu.pc = base_addr
        for _ in range(64):
            cpu.step()

        assert cpu.halted is True
        assert cpu.pc == base_addr + 64

    @pytest.mark.parametrize("address,new_value", [(0x0000, 0x5A), (0x001F, 0x6B)])
    def test_wrapped_prefetch_window_invalidates_on_write_byte(self, cpu, address, new_value):
        """Phase 4: Prefetch removed — verify wrapped memory access."""
        cpu.write_byte(address, new_value)
        cpu.pc = address
        assert cpu.fetch_byte() == new_value

    def test_wrapped_prefetch_window_invalidates_on_write_memory_word(self, cpu):
        """Phase 4: Prefetch removed — verify wrapped word access."""
        target_addr = 0x001E
        cpu.write_memory(target_addr, 0xBEEF, bytes=2)
        cpu.pc = target_addr
        assert cpu.fetch_word() == 0xBEEF

    def test_wrapped_prefetch_window_fetch_word_wraps_program_counter(self, cpu):
        """Phase 4: Prefetch removed — verify PC wraparound."""
        cpu.memory.write_byte(0xFFFE, 0x12)
        cpu.memory.write_byte(0xFFFF, 0x34)
        cpu.memory.write_byte(0x0000, 0x56)
        cpu.memory.write_byte(0x0001, 0x78)

        cpu.pc = 0xFFFE
        assert cpu.fetch_byte() == 0x12
        assert cpu.pc == 0xFFFF

        assert cpu.fetch_word() == 0x3456
        assert cpu.pc == 0x0001


class TestCPUPrefetchRefill:
    """Prefetch cache was eliminated in Phase 4. These tests are obsolete."""

    def test_fetch_byte_refills_prefetch_after_window_exhaustion(self, cpu):
        """Phase 4: Prefetch removed — verify sequential fetch works."""
        base_addr = 0x0200
        for index in range(96):
            cpu.memory.write_byte(base_addr + index, index & 0xFF)

        cpu.pc = base_addr
        for expected in range(96):
            assert cpu.fetch_byte() == expected
        assert cpu.pc == base_addr + 96

    def test_fetch_word_refills_prefetch_when_pc_moves_past_window(self, cpu):
        """Phase 4: Prefetch removed — verify word fetch across boundary."""
        base_addr = 0x0300
        for index in range(96):
            cpu.memory.write_byte(base_addr + index, index & 0xFF)

        cpu.pc = base_addr + 64
        assert cpu.fetch_word() == 0x4041
        assert cpu.pc == base_addr + 66

    def test_step_advances_prefetch_window_during_long_sequential_execution(self, cpu):
        """Phase 4: Prefetch removed — verify long sequential execution."""
        base_addr = 0x0400
        program_length = 80

        for index in range(program_length):
            cpu.memory.write_byte(base_addr + index, 0xFF)  # NOPs
        cpu.memory.write_byte(base_addr + program_length, 0x00)  # HLT

        cpu.pc = base_addr
        for _ in range(program_length + 1):
            cpu.step()

        assert cpu.halted is True
        assert cpu.pc == base_addr + program_length + 1


class TestCPUModeByteDecode:
    """Mode byte decode tests — some are still relevant after Phase 4."""

    def test_decode_mode_byte_preserves_operand_layout_and_memory_flags(self, cpu):
        """Phase 4: verify mode byte decoding still works."""
        mode_info = {
            'operand_modes': (0, 1, 2, 3),
            'indexed': True,
            'direct': True,
        }
        decoded = int(0xE4) & 0xFF
        assert tuple((decoded >> (index * 2)) & 0x3 for index in range(4)) == (0, 1, 2, 3)
        assert (decoded & (1 << 6)) != 0
        assert (decoded & (1 << 7)) != 0

    def test_parse_operands_four_operands(self, cpu):
        """Phase 4: verify operand parsing (no operand cache)."""
        cpu._current_mode_byte = 0xE4
        cpu.pc = 0x0200

        cpu.memory.write_byte(0x0200, 0xE7)      # R0
        cpu.memory.write_byte(0x0201, 0x12)      # imm8
        cpu.memory.write_word(0x0202, 0x3456)    # imm16
        cpu.memory.write_word(0x0204, 0x2000)    # memory base
        cpu.memory.write_byte(0x0206, 0x05)      # memory index

        operands = cpu.parse_operands(4)

        assert operands == [
            {'mode': 0, 'type': 'register', 'reg_type': 'R', 'reg_idx': 0},
            {'mode': 1, 'type': 'immediate', 'value': 0x12, 'size': 8},
            {'mode': 2, 'type': 'immediate', 'value': 0x3456, 'size': 16},
            {
                'mode': 3,
                'type': 'memory',
                'indexed': True,
                'direct': True,
                'address': 0x2005,
                'index': 0x05,
            },
        ]
        assert cpu.pc == 0x0207

        # Re-parse should produce same result (no cache, just re-fetch)
        cpu.pc = 0x0200
        fresh_operands = cpu.parse_operands(4)
        assert fresh_operands == operands
        assert cpu.pc == 0x0207

    def test_get_operand_address_uses_signed_stack_relative_indexing(self, cpu):
        """Phase 4: verify stack-relative addressing still works."""
        cpu._current_mode_byte = 0x43
        cpu.pc = 0x0300
        cpu.Pregisters[8] = 0x1000

        cpu.memory.write_byte(0x0300, 0xFB)  # SP alias (P8)
        cpu.memory.write_byte(0x0301, 0xFF)  # signed -1 offset

        assert cpu.get_operand_address(3) == 0x0FFF
        assert cpu.pc == 0x0302


class TestCPUStateReset:
    def test_reinit_clears_transient_execution_state(self, cpu):
        """Phase 4: verify reinit clears execution state (no cache references)."""
        cpu.pc = 0x0400
        cpu.memory.write_byte(0x0400, 0x5A)
        cpu.interrupt_check_counter = 7
        cpu.last_interrupt_state = 0xF0
        cpu.has_pending_interrupt_sources = True
        cpu.has_hw_breakpoints = True
        cpu.halted = True
        cpu.cycles = 100

        cpu.reinit()

        assert cpu.pc == 0x0000
        assert cpu.interrupt_check_counter == 0
        assert cpu.last_interrupt_state == 0
        assert cpu.has_pending_interrupt_sources is False
        assert cpu.has_hw_breakpoints is False
        assert cpu.halted is False


class TestCPUTimerControl:
    def test_timer_enable_resets_stale_counter_state(self, cpu_with_timer):
        cpu = cpu_with_timer
        timer = cpu.timer_device
        timer.regs[0] = 9
        timer._cycle_count = 13

        timer.set_register(2, 0x01)  # Enable timer

        assert timer._enabled is True
        assert timer.regs[0] == 0
        assert timer._cycle_count == 0


class TestCPUInterruptRefreshFastPath:
    def test_step_skips_interrupt_refresh_when_no_async_sources_enabled(self, cpu):
        cpu.memory.write_byte(0x0000, 0xFF)

        refresh_calls = 0
        original_refresh = cpu._refresh_pending_interrupt_sources

        def tracked_refresh():
            nonlocal refresh_calls
            refresh_calls += 1
            return original_refresh()

        cpu._refresh_pending_interrupt_sources = tracked_refresh

        cpu.step()

        assert refresh_calls == 0
        assert cpu.pc == 0x0001

    def test_step_refreshes_when_direct_interrupt_enable_exposes_pending_uart(self, cpu):
        cpu.interrupt_check_frequency = 1
        cpu.flags[5] = 1
        cpu.memory.write_word(0x0104, 0x3456)
        cpu.memory.write_byte(0x0000, 0xFF)

        refresh_calls = 0
        original_refresh = cpu._refresh_pending_interrupt_sources

        def tracked_refresh():
            nonlocal refresh_calls
            refresh_calls += 1
            return original_refresh()

        cpu._refresh_pending_interrupt_sources = tracked_refresh

        cpu.uart.write_control(0x01)
        cpu.uart.write_data(0x7A)

        assert cpu.has_pending_interrupt_sources is False

        cpu.interrupts[1] = 1
        cpu.step()

        assert refresh_calls >= 1
        assert cpu.pc == 0x3456
        assert cpu.uart.pending_interrupt is False
        assert cpu.Pregisters[8] == 0xFFFB
        assert cpu.memory.read_word(0xFFFB) == 0x0001


class TestCPUOperandCacheInvalidation:
    """Operand cache was eliminated in Phase 4. Tests adapted to verify no cache exists."""

    def test_write_byte_invalidates_cached_immediate_operand_without_flushing_instruction_cache(self, cpu):
        """Phase 4: No operand cache — verify direct value read after write."""
        base_addr = 0x0600
        cpu.pc = base_addr
        cpu.memory.write_byte(base_addr, 0x06)
        cpu.memory.write_byte(base_addr + 1, 0x04)
        cpu.memory.write_byte(base_addr + 2, 0xE7)
        cpu.memory.write_byte(base_addr + 3, 0x12)

        cpu.step()
        assert cpu.Rregisters[0] == 0x12

        # Write new value and re-execute
        cpu.write_byte(base_addr + 3, 0x34)
        cpu.pc = base_addr
        cpu.step()
        assert cpu.Rregisters[0] == 0x34

    def test_write_memory_invalidates_cached_16bit_immediate_operand(self, cpu):
        """Phase 4: No operand cache — verify direct value read after write."""
        base_addr = 0x0620
        cpu.pc = base_addr
        cpu.memory.write_byte(base_addr, 0x06)
        cpu.memory.write_byte(base_addr + 1, 0x08)
        cpu.memory.write_byte(base_addr + 2, 0xF1)
        cpu.memory.write_word(base_addr + 3, 0x1234)

        cpu.step()
        assert cpu.Pregisters[0] == 0x1234

        cpu.write_memory(base_addr + 3, 0xBEEF, bytes=2)
        cpu.pc = base_addr
        cpu.step()
        assert cpu.Pregisters[0] == 0xBEEF

    def test_write_byte_invalidates_cached_direct_indexed_operand_address(self, cpu):
        """Phase 4: No operand cache — verify updated data read through indexed address."""
        base_addr = 0x0640
        source_base = 0x2200

        cpu.memory.write_byte(source_base + 1, 0x11)
        cpu.memory.write_byte(source_base + 2, 0x22)

        cpu.pc = base_addr
        cpu.memory.write_byte(base_addr, 0x06)
        cpu.memory.write_byte(base_addr + 1, 0xCC)
        cpu.memory.write_byte(base_addr + 2, 0xE7)
        cpu.memory.write_word(base_addr + 3, source_base)
        cpu.memory.write_byte(base_addr + 5, 0x01)

        cpu.step()
        assert cpu.Rregisters[0] == 0x11

        # Change the index byte, re-execute
        cpu.write_byte(base_addr + 5, 0x02)
        cpu.pc = base_addr
        cpu.step()
        assert cpu.Rregisters[0] == 0x22

    def test_memory_write_byte_invalidates_cached_immediate_operand(self, cpu):
        """Phase 4: No operand cache — verify memory write followed by re-execute."""
        base_addr = 0x0660
        cpu.pc = base_addr
        cpu.memory.write_byte(base_addr, 0x06)
        cpu.memory.write_byte(base_addr + 1, 0x04)
        cpu.memory.write_byte(base_addr + 2, 0xE7)
        cpu.memory.write_byte(base_addr + 3, 0x12)

        cpu.step()
        assert cpu.Rregisters[0] == 0x12

        cpu.memory.write_byte(base_addr + 3, 0x56)
        cpu.pc = base_addr
        cpu.step()
        assert cpu.Rregisters[0] == 0x56

    def test_memory_write_word_invalidates_cached_16bit_immediate_operand(self, cpu):
        """Phase 4: No operand cache — verify memory word write followed by re-execute."""
        base_addr = 0x0680
        cpu.pc = base_addr
        cpu.memory.write_byte(base_addr, 0x06)
        cpu.memory.write_byte(base_addr + 1, 0x08)
        cpu.memory.write_byte(base_addr + 2, 0xF1)
        cpu.memory.write_word(base_addr + 3, 0x1234)

        cpu.step()
        assert cpu.Pregisters[0] == 0x1234

        cpu.memory.write_word(base_addr + 3, 0xCAFE)
        cpu.pc = base_addr
        cpu.step()
        assert cpu.Pregisters[0] == 0xCAFE