"""Regression tests for CPU internal execution state management."""

import pytest


class TestCPUPrefetchInvalidation:
    @pytest.mark.parametrize("offset,new_value", [(0, 0x11), (15, 0x22), (16, 0x33), (63, 0x44)])
    def test_write_byte_invalidates_prefetch_across_full_buffer(self, cpu, offset, new_value):
        base_addr = 0x0200
        cpu.pc = base_addr

        for index in range(len(cpu.prefetch_buffer)):
            cpu.memory.write_byte(base_addr + index, index & 0xFF)

        cpu._fill_prefetch_buffer()

        assert cpu.prefetch_valid is True
        assert int(cpu.prefetch_buffer[offset]) == offset

        cpu.write_byte(base_addr + offset, new_value)

        assert cpu.prefetch_valid is False

        cpu.pc = base_addr + offset
        assert cpu.fetch_byte() == new_value

    @pytest.mark.parametrize("offset,value,width", [(16, 0xAA, 1), (48, 0xBEEF, 2)])
    def test_write_memory_invalidates_prefetch_across_full_buffer(self, cpu, offset, value, width):
        base_addr = 0x0300
        cpu.pc = base_addr

        for index in range(len(cpu.prefetch_buffer)):
            cpu.memory.write_byte(base_addr + index, 0)

        cpu._fill_prefetch_buffer()

        assert cpu.prefetch_valid is True

        cpu.write_memory(base_addr + offset, value, bytes=width)

        assert cpu.prefetch_valid is False

        cpu.pc = base_addr + offset
        if width == 1:
            assert cpu.fetch_byte() == value
        else:
            assert cpu.fetch_word() == value

    def test_self_modifying_code_uses_updated_opcode_beyond_old_window(self, cpu):
        base_addr = 0x0500
        target_offset = 63

        cpu.pc = base_addr
        for index in range(80):
            cpu.memory.write_byte(base_addr + index, 0xFF)

        cpu._fill_prefetch_buffer()
        assert cpu.prefetch_valid is True
        assert int(cpu.prefetch_buffer[target_offset]) == 0xFF

        cpu.write_byte(base_addr + target_offset, 0x00)

        for _ in range(target_offset + 1):
            cpu.step()

        assert cpu.halted is True
        assert cpu.pc == base_addr + target_offset + 1

    @pytest.mark.parametrize("address,new_value", [(0x0000, 0x5A), (0x001F, 0x6B)])
    def test_wrapped_prefetch_window_invalidates_on_write_byte(self, cpu, address, new_value):
        base_addr = 0xFFE0
        cpu.pc = base_addr

        for index in range(len(cpu.prefetch_buffer)):
            cpu.memory.write_byte((base_addr + index) & 0xFFFF, index & 0xFF)

        cpu._fill_prefetch_buffer()

        assert cpu.prefetch_valid is True
        assert cpu._get_prefetch_offset(address) is not None

        cpu.write_byte(address, new_value)

        assert cpu.prefetch_valid is False

        cpu.pc = address
        assert cpu.fetch_byte() == new_value

    def test_wrapped_prefetch_window_invalidates_on_write_memory_word(self, cpu):
        base_addr = 0xFFE0
        target_addr = 0x001E
        cpu.pc = base_addr

        for index in range(len(cpu.prefetch_buffer)):
            cpu.memory.write_byte((base_addr + index) & 0xFFFF, 0)

        cpu._fill_prefetch_buffer()

        assert cpu.prefetch_valid is True
        assert cpu._get_prefetch_offset(target_addr) is not None
        assert cpu._get_prefetch_offset((target_addr + 1) & 0xFFFF) is not None

        cpu.write_memory(target_addr, 0xBEEF, bytes=2)

        assert cpu.prefetch_valid is False

        cpu.pc = target_addr
        assert cpu.fetch_word() == 0xBEEF

    def test_wrapped_prefetch_window_fetch_word_wraps_program_counter(self, cpu):
        cpu.pc = 0xFFFE
        cpu.memory.write_byte(0xFFFE, 0x12)
        cpu.memory.write_byte(0xFFFF, 0x34)
        cpu.memory.write_byte(0x0000, 0x56)
        cpu.memory.write_byte(0x0001, 0x78)

        cpu._fill_prefetch_buffer()

        assert cpu.fetch_byte() == 0x12
        assert cpu.pc == 0xFFFF

        assert cpu.fetch_word() == 0x3456
        assert cpu.pc == 0x0001


class TestCPUPrefetchRefill:
    def test_fetch_byte_refills_prefetch_after_window_exhaustion(self, cpu):
        base_addr = 0x0200

        for index in range(96):
            cpu.memory.write_byte(base_addr + index, index & 0xFF)

        cpu.pc = base_addr
        cpu._fill_prefetch_buffer()

        for expected in range(len(cpu.prefetch_buffer)):
            assert cpu.fetch_byte() == expected

        assert cpu.pc == base_addr + len(cpu.prefetch_buffer)
        assert cpu.prefetch_pc == base_addr

        assert cpu.fetch_byte() == len(cpu.prefetch_buffer)
        assert cpu.prefetch_pc == base_addr + len(cpu.prefetch_buffer)
        assert cpu.prefetch_valid is True

        assert cpu.fetch_byte() == len(cpu.prefetch_buffer) + 1

    def test_fetch_word_refills_prefetch_when_pc_moves_past_window(self, cpu):
        base_addr = 0x0300

        for index in range(96):
            cpu.memory.write_byte(base_addr + index, index & 0xFF)

        cpu.pc = base_addr
        cpu._fill_prefetch_buffer()
        cpu.pc = base_addr + len(cpu.prefetch_buffer)

        assert cpu.fetch_word() == 0x4041
        assert cpu.prefetch_pc == base_addr + len(cpu.prefetch_buffer)
        assert cpu.pc == base_addr + len(cpu.prefetch_buffer) + 2

    def test_step_advances_prefetch_window_during_long_sequential_execution(self, cpu):
        base_addr = 0x0400
        program_length = len(cpu.prefetch_buffer) + 16

        for index in range(program_length):
            cpu.memory.write_byte(base_addr + index, 0xFF)
        cpu.memory.write_byte(base_addr + program_length, 0x00)

        cpu.pc = base_addr

        for _ in range(program_length + 1):
            cpu.step()

        assert cpu.halted is True
        assert cpu.pc == base_addr + program_length + 1
        assert cpu.prefetch_pc >= base_addr + len(cpu.prefetch_buffer)


class TestCPUStateReset:
    def test_reinit_clears_transient_execution_state(self, cpu):
        cpu.pc = 0x0400
        cpu.memory.write_byte(0x0400, 0x5A)
        cpu._fill_prefetch_buffer()
        cpu.interrupt_check_counter = 7
        cpu.last_interrupt_state = 0xF0
        cpu.instruction_cache[0x0400] = (0xFF, 0x00, object())
        cpu.operand_cache[(0x0400, 0x04)] = ([('imm', 0x12)], 1)
        cpu.register_cache['R0'] = 0x12

        cpu.reinit()

        assert cpu.prefetch_valid is False
        assert cpu.interrupt_check_counter == 0
        assert cpu.last_interrupt_state == 0
        assert cpu.instruction_cache == {}
        assert cpu.operand_cache == {}
        assert cpu.register_cache == {}


class TestCPUTimerControl:
    def test_timer_enable_resets_stale_counter_state(self, cpu):
        cpu.timer[0] = 9
        cpu.timer_cycles = 13
        cpu.timer_update_counter = 5
        cpu.timer_enabled = False

        cpu.set_timer_control(0x01)

        assert cpu.timer_enabled is True
        assert cpu.timer[0] == 0
        assert cpu.timer_cycles == 0
        assert cpu.timer_update_counter == 0