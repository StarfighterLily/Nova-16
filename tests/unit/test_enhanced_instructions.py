"""
Unit tests for Nova-16 enhanced instructions (0x94-0xA1).
"""

import pytest
import numpy as np
from tests.conftest import assert_register_equals, run_cpu_cycles


class TestEnhancedDataMovement:
    """Test enhanced data movement instructions."""

    def test_swap_instruction(self, cpu, memory):
        """Test SWAP instruction - swap bytes."""
        # Load t    # def test_while_loop(self, cpu, memory):
    #     """Test WHILE instruction - while condition != 0."""
    #     # WHILE P0; DEC P0; (simplified)
    #     program = [
    #         0x06, 0x08, 0xF1, 0x01, 0x00,  # MOV P0, 1
    #         0xA1, 0x00, 0xF1,              # WHILE P0 (register)
    #         0x0C, 0x00, 0xF1,              # DEC P0
    #         0x00                             # HLT
    #     ]
    #     memory.load_program(program)
    #     run_cpu_cycles(cpu, 4)
    #     
    #     # Should have executed WHILE, then DEC, P0=0
    #     assert cpu.Pregisters[0] == 0V P0, 0xABCD; SWAP P0
        program = [
            0x06, 0x08, 0xF1, 0xAB, 0xCD,  # MOV P0, 0xABCD
            0x94, 0x00, 0xF1,              # SWAP P0
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 3)
        
        # MOV loaded 0xABCD, SWAP should swap to 0xCDAB
        assert cpu.Pregisters[0] == 0xCDAB

    def test_xchng_instruction(self, cpu, memory):
        """Test XCHNG instruction - exchange operands."""
        # Load test program: MOV P0, 0x1234; MOV P1, 0x5678; XCHNG P0, P1
        program = [
            0x06, 0x08, 0xF1, 0x34, 0x12,  # MOV P0, 0x1234 (loads as 0x3412)
            0x06, 0x08, 0xF2, 0x78, 0x56,  # MOV P1, 0x5678 (loads as 0x7856)
            0x95, 0x00, 0xF1, 0xF2,        # XCHNG P0, P1
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        
        # P0 should be 0x7856, P1 should be 0x3412
        assert cpu.Pregisters[0] == 0x7856
        assert cpu.Pregisters[1] == 0x3412

    def test_movz_instruction_move_when_zero(self, cpu, memory):
        """Test MOVZ instruction - move when zero flag is set."""
        # Load test program: MOV P0, 0x1111; MOV P1, 0x2222; CMP P0, P0; MOVZ P1, P0
        program = [
            0x06, 0x08, 0xF1, 0x11, 0x11,  # MOV P0, 0x1111
            0x06, 0x08, 0xF2, 0x22, 0x22,  # MOV P1, 0x2222
            0x2E, 0x00, 0xF1, 0xF1,        # CMP P0, P0 (sets zero flag)
            0x96, 0x00, 0xF2, 0xF1,        # MOVZ P1, P0
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 5)
        
        # P1 should be 0x1111 (moved because zero flag was set)
        assert cpu.Pregisters[1] == 0x1111

    def test_movz_instruction_no_move_when_not_zero(self, cpu, memory):
        """Test MOVZ instruction - don't move when zero flag is not set."""
        # Load test program: MOV P0, 0x1111; MOV P1, 0x2222; MOV P2, 0x3333; CMP P0, P2; MOVZ P1, P0
        program = [
            0x06, 0x08, 0xF1, 0x11, 0x11,  # MOV P0, 0x1111
            0x06, 0x08, 0xF2, 0x22, 0x22,  # MOV P1, 0x2222
            0x06, 0x08, 0xF3, 0x33, 0x33,  # MOV P2, 0x3333
            0x2E, 0x00, 0xF1, 0xF3,        # CMP P0, P2 (clears zero flag)
            0x96, 0x00, 0xF2, 0xF1,        # MOVZ P1, P0
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 6)
        
        # P1 should still be 0x2222 (not moved because zero flag was not set)
        assert cpu.Pregisters[1] == 0x2222


class TestEnhancedMemoryOperations:
    """Test enhanced memory operations."""

    def test_memcmp_instruction_equal(self, cpu, memory):
        """Test MEMCMP instruction - compare equal memory regions."""
        # Setup memory: 0x1000-0x1002 = [1, 2, 3], 0x1100-0x1102 = [1, 2, 3]
        memory.write_byte(0x1000, 1)
        memory.write_byte(0x1001, 2)
        memory.write_byte(0x1002, 3)
        memory.write_byte(0x1100, 1)
        memory.write_byte(0x1101, 2)
        memory.write_byte(0x1102, 3)
        
        # Load test program: MOV P1, 0x1000; MOV P2, 0x1100; MOV P3, 3; MEMCMP P0, P1, P2, P3
        program = [
            0x06, 0x08, 0xF2, 0x10, 0x00,  # MOV P1, 0x1000
            0x06, 0x08, 0xF3, 0x11, 0x00,  # MOV P2, 0x1100
            0x06, 0x04, 0xF4, 0x03,        # MOV P3, 3
            0x99, 0x00, 0xF1, 0xF2, 0xF3, 0xF4,  # MEMCMP P0, P1, P2, P3
            0x00                                 # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 5)
        
        # P0 should be 0 (equal)
        assert cpu.Pregisters[0] == 0

    def test_memcmp_instruction_greater(self, cpu, memory):
        """Test MEMCMP instruction - first region greater."""
        # Setup memory: 0x1000-0x1002 = [2, 2, 3], 0x1100-0x1102 = [1, 2, 3]
        memory.write_byte(0x1000, 2)
        memory.write_byte(0x1001, 2)
        memory.write_byte(0x1002, 3)
        memory.write_byte(0x1100, 1)
        memory.write_byte(0x1101, 2)
        memory.write_byte(0x1102, 3)

        # Load test program: MOV P1, 0x1000; MOV P2, 0x1100; MOV P3, 3; MEMCMP P0, P1, P2, P3
        program = [
            0x06, 0x08, 0xF2, 0x10, 0x00,  # MOV P1, 0x1000
            0x06, 0x08, 0xF3, 0x11, 0x00,  # MOV P2, 0x1100
            0x06, 0x04, 0xF4, 0x03,        # MOV P3, 3
            0x99, 0x00, 0xF1, 0xF2, 0xF3, 0xF4,  # MEMCMP P0, P1, P2, P3
            0x00                                 # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 5)

        # P0 should be 1 (first > second)
        assert cpu.Pregisters[0] == 1

    def test_memswap_instruction(self, cpu, memory):
        """Test MEMSWAP instruction - swap memory regions."""
        # Setup memory: 0x1000-0x1002 = [1, 2, 3], 0x1100-0x1102 = [4, 5, 6]
        memory.write_byte(0x1000, 1)
        memory.write_byte(0x1001, 2)
        memory.write_byte(0x1002, 3)
        memory.write_byte(0x1100, 4)
        memory.write_byte(0x1101, 5)
        memory.write_byte(0x1102, 6)
        
        # Load test program: MOV P0, 0x1000; MOV P1, 0x1100; MEMSWAP P0, P1, 3
        program = [
            0x06, 0x08, 0xF1, 0x10, 0x00,  # MOV P0, 0x1000
            0x06, 0x08, 0xF2, 0x11, 0x00,  # MOV P1, 0x1100
            0x9A, 0x10, 0xF1, 0xF2, 0x03,  # MEMSWAP P0, P1, 3
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        
        # Check swapped values
        assert memory.read_byte(0x1000) == 4
        assert memory.read_byte(0x1001) == 5
        assert memory.read_byte(0x1002) == 6
        assert memory.read_byte(0x1100) == 1
        assert memory.read_byte(0x1101) == 2
        assert memory.read_byte(0x1102) == 3


class TestEnhancedControlFlow:
    """Test enhanced control flow instructions."""


class TestStackFrameInstructions:
    """Test stack frame management instructions."""

    def test_enter_instruction(self, cpu, memory):
        """Test ENTER instruction - create stack frame."""
        # Load test program: MOV P0, 10; ENTER P0
        program = [
            0x06, 0x04, 0xF1, 0x0A,        # MOV P0, 10
            0x9B, 0x00, 0xF1,              # ENTER P0
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 3)
        
        # Check stack frame setup
        # SP should be decreased by frame size (10)
        assert cpu.Pregisters[8] == 0xFFFF - 2 - 10  # Initial SP - old FP - frame size
        # FP should point to old FP location
        assert cpu.Pregisters[9] == 0xFFFF - 2

    def test_leave_instruction(self, cpu, memory):
        """Test LEAVE instruction - destroy stack frame."""
        # First setup a stack frame
        cpu.Pregisters[8] = 0xFFFF - 2 - 10  # Simulate SP after ENTER
        cpu.Pregisters[9] = 0xFFFF - 2       # Simulate FP
        memory.write_word(0xFFFF - 2, 0xFFFF)  # Old FP on stack(0xFFFF - 2, 0xFFFF)  # Old FP on stack
        
        # Load test program: LEAVE
        program = [
            0x9C,                           # LEAVE
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 2)
        
        # SP should be restored to original position (after popping old FP)
        assert cpu.Pregisters[8] == 0xFFFD
        # FP should be restored from stack
        assert cpu.Pregisters[9] == 0xFFFF


class TestFlagInstructions:
    """Test flag manipulation instructions."""

    @pytest.mark.skip(reason="STC (Set Carry) instruction not in official opcode spec - 0x9F is RETN")
    def test_stc_instruction(self, cpu, memory):
        """Test STC instruction - set carry flag."""
        # Clear carry flag first
        cpu.carry_flag = False
        
        # Load test program: STC
        program = [
            0x9F,                           # STC (not in spec - 0x9F is RETN)
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 2)
        
        assert cpu.carry_flag == True

    @pytest.mark.skip(reason="CLC (Clear Carry) instruction not in official opcode spec - 0xA0 is LOOPZ")
    def test_clc_instruction(self, cpu, memory):
        """Test CLC instruction - clear carry flag."""
        # Set carry flag first
        cpu.carry_flag = True
        
        # Load test program: CLC
        program = [
            0xA0,                           # CLC (not in spec - 0xA0 is LOOPZ)
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 2)
        
        assert cpu.carry_flag == False

    @pytest.mark.skip(reason="CMC (Complement Carry) instruction not in official opcode spec - 0xA1 is WHILE")
    def test_cmc_instruction(self, cpu, memory):
        """Test CMC instruction - complement carry flag."""
        # Set carry flag first, then complement it
        cpu.carry_flag = True
        
        # Load test program: CMC
        program = [
            0xA1,                           # CMC (not in spec - 0xA1 is WHILE)
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 2)
        
        assert cpu.carry_flag == False


class TestAdvancedControlFlow:
    """Test advanced control flow instructions."""

    def test_callz_call_when_zero(self, cpu, memory):
        """Test CALLZ instruction - call when zero flag is set."""
        # Load test program: MOV P0, 0; CMP P0, P0; CALLZ subroutine
        # Subroutine: MOV P1, 0x1234; RET
        program = [
            0x06, 0x08, 0xF1, 0x00, 0x00,  # MOV P0, 0
            0x2E, 0x00, 0xF1, 0xF1,        # CMP P0, P0 (sets zero)
            0x9D, 0x02, 0x00, 0x0E,        # CALLZ 0x000E (imm16)
            0x00,                           # HLT
            # Subroutine at 0x000C
            0x06, 0x08, 0xF2, 0x12, 0x34,  # MOV P1, 0x1234
            0x01                             # RET
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 5)
        
        # Should have called subroutine, P1 = 0x1234
        assert cpu.Pregisters[1] == 0x1234

    def test_callz_no_call_when_not_zero(self, cpu, memory):
        """Test CALLZ instruction - no call when zero flag is not set."""
        # Load test program: MOV P0, 1; MOV P1, 0; CMP P0, P1; CALLZ subroutine
        program = [
            0x06, 0x08, 0xF1, 0x01, 0x00,  # MOV P0, 1
            0x06, 0x08, 0xF2, 0x00, 0x00,  # MOV P1, 0
            0x2E, 0x00, 0xF1, 0xF2,        # CMP P0, P1 (1 != 0, not zero)
            0x9D, 0x02, 0x00, 0x13,        # CALLZ 0x0013 (imm16)
            0x00,                           # HLT
            # Subroutine
            0x06, 0x08, 0xF3, 0x12, 0x34,  # MOV P2, 0x1234
            0x01                             # RET
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 5)
        
        # Should not have called, P1 remains 0
        assert cpu.Pregisters[1] == 0

    def test_retn_return_with_value(self, cpu, memory):
        """Test RETN instruction - return with value."""
        # Load test program: CALL subroutine; MOV P1, R0
        # Subroutine: MOV R0, 0xAB; RETN R0
        program = [
            0x2F, 0x02, 0x00, 0x09,        # CALL 0x0009 (imm16)
            0x06, 0x00, 0xF2, 0xE0,        # MOV P1, R0
            0x00,                           # HLT
            # Subroutine
            0x06, 0x04, 0xE0, 0xAB,  # MOV R0, 0xAB (8-bit)
            0x9F, 0x00, 0xE0                # RETN R0 (register)
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 5)
        
        # R0 should be 0xAB, P1 should be 0xAB
        assert cpu.Rregisters[0] == 0xAB
        assert cpu.Pregisters[1] == 0x00AB

    def test_loopz_loop_while_zero(self, cpu, memory):
        """Test LOOPZ instruction - loop while counter != 0."""
        # Simple loop: MOV P0, 3; loop: DEC P0; LOOPZ P0, loop
        program = [
            0x06, 0x04, 0xF1, 0x03,        # MOV P0, 3
            0x2E, 0x00, 0xF1, 0xF1,        # CMP P0, P0 (sets Z flag)
            0xA0, 0x04, 0xF1, 0x04,        # LOOPZ P0, 0x0004 (jump back to CMP)
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 10)  # Should loop 3 times
        
        # P0 should be 0 after looping
        assert cpu.Pregisters[0] == 0

    def test_while_loop(self, cpu, memory):
        """Test WHILE instruction - while condition != 0."""
        # WHILE P0; DEC P0; ENDWHILE or something, but simplified
        # For now, test basic
        program = [
            0x06, 0x04, 0xF1, 0x01,        # MOV P0, 1 (8-bit)
            0xA1, 0x00, 0xF1,              # WHILE P0
            0x0C, 0x00, 0xF1,              # DEC P0
            0x00                             # HLT (simplified, no endwhile)
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        
        # Should have executed WHILE, then DEC, P0=0
        assert cpu.Pregisters[0] == 0
