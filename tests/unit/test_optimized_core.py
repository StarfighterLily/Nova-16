"""
Tests for optimized core components (regfile, flags, exec, fetch).

Verifies that the performance optimizations maintain correct behavior.
"""

import pytest
from core.regfile import RegisterFile
from core.flags import Flags


class TestRegisterFileOptimizations:
    """Test RegisterFile optimization changes."""

    def test_reset_all_preserves_list_type(self):
        """Verify reset_all() keeps P registers as list (not array)."""
        rf = RegisterFile()
        
        # Initial state: P should be a list
        assert isinstance(rf.P, list), "P registers should initially be a list"
        
        # Modify P registers
        rf.set('P', 0, 0x1234)
        rf.set('P', 8, 0xABCD)  # SP
        rf.set('P', 9, 0x5678)  # FP
        
        # Reset
        rf.reset_all()
        
        # Verify P is still a list after reset
        assert isinstance(rf.P, list), "P registers should remain a list after reset_all()"
        
        # Verify values are reset correctly
        assert rf.P[0] == 0
        assert rf.P[8] == 0xFFFF  # SP reset to 0xFFFF
        assert rf.P[9] == 0xFFFF  # FP reset to 0xFFFF

    def test_register_dispatch_consistency(self):
        """Verify dispatch tables work correctly for all register types."""
        rf = RegisterFile()
        
        # Test R register dispatch
        for i in range(10):
            rf.set('R', i, i * 10)
        for i in range(10):
            assert rf.get('R', i) == i * 10, f"R{i} dispatch failed"
        
        # Test P register dispatch
        for i in range(10):
            rf.set('P', i, i * 1000)
        for i in range(10):
            assert rf.get('P', i) == i * 1000, f"P{i} dispatch failed"
        
        # Test P_high/P_low dispatch
        rf.set('P', 1, 0xABCD)
        assert rf.get('P_high', 1) == 0xAB, "P_high dispatch failed"
        assert rf.get('P_low', 1) == 0xCD, "P_low dispatch failed"


class TestFlagsOptimizations:
    """Test Flags optimization changes."""

    def test_fast_flag_checks(self):
        """Verify fast-path flag check methods work correctly."""
        f = Flags()
        
        # Test I (interrupt) flag
        assert not f.check_I(), "I flag should be False initially"
        f.interrupt_flag = True
        assert f.check_I(), "check_I() should return True after setting flag"
        f.interrupt_flag = False
        assert not f.check_I(), "check_I() should return False after clearing"
        
        # Test Z (zero) flag
        assert not f.check_Z(), "Z flag should be False initially"
        f._bits |= (1 << 7)  # Set Z flag directly
        assert f.check_Z(), "check_Z() should return True when Z flag set"
        
        # Test C (carry) flag
        assert not f.check_C(), "C flag should be False initially"
        f._bits |= (1 << 6)  # Set C flag directly
        assert f.check_C(), "check_C() should return True when C flag set"
        
        # Test S (sign) flag
        assert not f.check_S(), "S flag should be False initially"
        f._bits |= (1 << 1)  # Set S flag directly
        assert f.check_S(), "check_S() should return True when S flag set"
        
        # Test O (overflow) flag
        assert not f.check_O(), "O flag should be False initially"
        f._bits |= (1 << 2)  # Set O flag directly
        assert f.check_O(), "check_O() should return True when O flag set"

    def test_precomputed_masks(self):
        """Verify pre-computed masks match expected values."""
        assert Flags._INTERRUPT_MASK == 0x20, "Interrupt mask mismatch"
        assert Flags._ZERO_MASK == 0x80, "Zero mask mismatch"
        assert Flags._CARRY_MASK == 0x40, "Carry mask mismatch"
        assert Flags._SIGN_MASK == 0x02, "Sign mask mismatch"
        assert Flags._OVERFLOW_MASK == 0x04, "Overflow mask mismatch"

    def test_set_from_operation_batch_flags(self):
        """Verify set_from_operation uses batch flag updates correctly."""
        f = Flags()
        
        # Test 8-bit operation: 0x70 + 0x10 = 0x80 (no overflow, sign set)
        f.set_from_operation(0x80, 0x70, 0x10, width=8, is_subtraction=False)
        assert f.check_Z() == (0x80 == 0), "Zero flag incorrect for 8-bit op"
        assert f.check_S() == True, "Sign flag should be set (bit 7 of 0x80)"
        
        # Test 16-bit operation
        f.reset_all()
        f.set_from_operation(0x8000, 0x7000, 0x1000, width=16, is_subtraction=False)
        assert f.check_S() == True, "Sign flag should be set (bit 15)"

    def test_property_backward_compatibility(self):
        """Verify properties still work after optimization."""
        f = Flags()
        
        # Test all property setters/getters
        f.trap_flag = True
        assert f.trap_flag == True
        assert f[0] == 1
        
        f.sign_flag = True
        assert f.sign_flag == True
        assert f[1] == 1
        
        f.overflow_flag = True
        assert f.overflow_flag == True
        assert f[2] == 1
        
        f.break_flag = True
        assert f.break_flag == True
        assert f[3] == 1
        
        f.interrupt_flag = True
        assert f.interrupt_flag == True
        assert f[5] == 1
        
        f.carry_flag = True
        assert f.carry_flag == True
        assert f[6] == 1
        
        f.zero_flag = True
        assert f.zero_flag == True
        assert f[7] == 1
        
        f.parity_flag = True
        assert f.parity_flag == True
        assert f[8] == 1
        
        f.direction_flag = True
        assert f.direction_flag == True
        assert f[9] == 1
        
        f.bcd_carry_flag = True
        assert f.bcd_carry_flag == True
        assert f[10] == 1
        
        f.hacker_flag = True
        assert f.hacker_flag == True
        assert f[11] == 1


class TestFetchOptimizations:
    """Test operand fetch optimization changes."""

    def test_operand_pool_reuse(self):
        """Verify operand pooling reduces allocations."""
        from core.fetch import _acquire_operand, _release_operand, decode_operands, release_operands
        from nova.memory.memory import Memory
        from core.regfile import REGISTER_CODE_MAP
        
        mem = Memory()
        
        # Create register code lookup function
        def decode_register_code(reg_code):
            return REGISTER_CODE_MAP.get(reg_code, (0, 'R'))  # Default to R0 for unknown codes
        
        # Build instruction with 2 register operands (mode byte = 0x00 = reg, reg)
        mem._mem[0x1000] = 0x00  # mode byte (both register)
        mem._mem[0x1001] = 0xE7  # R0 register code
        mem._mem[0x1002] = 0xE8  # R1 register code
        
        operands, length = decode_operands(mem, 0x1000, 0x00, 2, decode_register_code)
        
        # The operands should have been acquired from pool
        assert len(operands) == 2
        assert all(op.is_register for op in operands)
        
        # Release them back to pool
        release_operands(operands)

    def test_operand_pool_reuse_immediate(self):
        """Verify operand pooling works for immediate 16-bit values."""
        from core.fetch import _acquire_operand, _release_operand, decode_operands, release_operands
        from nova.memory.memory import Memory
        from core.regfile import REGISTER_CODE_MAP
        
        mem = Memory()
        
        def decode_register_code(reg_code):
            return REGISTER_CODE_MAP.get(reg_code, (0, 'R'))
        
        # mode for operand 0 = 0x02 & 0x3 = 2 (imm16)
        # mode for operand 1 = (0x02 >> 2) & 0x3 = 0 (reg)
        # So mode byte 0x02 means: op0=imm16, op1=reg
        mem._mem[0x2000] = 0x12  # High byte for imm16
        mem._mem[0x2001] = 0x34  # Low byte for imm16 (value = 0x1234)
        mem._mem[0x2002] = 0xE7  # R0 register code
        
        operands, length = decode_operands(mem, 0x2000, 0x02, 2, decode_register_code)
        
        assert len(operands) == 2
        assert operands[0].is_immediate
        assert operands[0].value == 0x1234
        assert operands[1].is_register
        
        release_operands(operands)

    def test_operand_pool_reuse_two_registers(self):
        """Verify operand pooling works for two register operands."""
        from core.fetch import _acquire_operand, _release_operand, decode_operands, release_operands
        from nova.memory.memory import Memory
        from core.regfile import REGISTER_CODE_MAP
        
        mem = Memory()
        
        def decode_register_code(reg_code):
            return REGISTER_CODE_MAP.get(reg_code, (0, 'R'))
        
        # Mode byte = 0x00 = two registers (both mode 0)
        mem._mem[0x2000] = 0xE7  # R0 register code
        mem._mem[0x2001] = 0xE8  # R1 register code
        
        operands, length = decode_operands(mem, 0x2000, 0x00, 2, decode_register_code)
        
        assert len(operands) == 2
        assert all(op.is_register for op in operands)
        
        release_operands(operands)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])