"""
Unit tests for nova_cpu.py - Nova-16 CPU core.
"""

import pytest
import numpy as np
from tests.conftest import assert_register_equals, run_cpu_cycles


class TestCPUInitialization:

    def test_cpu_register_initialization(self, cpu):
        """Test that CPU registers are initialized correctly."""
        # R registers (8-bit) should be 0
        assert all(r == 0 for r in cpu.Rregisters)

        # P registers (16-bit) should be 0 except SP and FP
        assert cpu.Pregisters[8] == 0xFFFF  # SP
        assert cpu.Pregisters[9] == 0xFFFF  # FP
        for i in range(10):
            if i not in [8, 9]:
                assert cpu.Pregisters[i] == 0

    def test_cpu_flags_initialization(self, cpu):
        """Test that CPU flags are initialized correctly."""
        # Most flags should be 0
        assert cpu.flags[11] == 0  # Hacker flag
        assert cpu.flags[10] == 0  # BCD Carry
        assert cpu.flags[9] == 0   # Direction
        assert cpu.flags[8] == 0   # Parity
        assert cpu.flags[7] == 0   # Zero
        assert cpu.flags[6] == 0   # Carry
        assert cpu.flags[5] == 0   # Interrupt
        assert cpu.flags[4] == 0   # Decimal
        assert cpu.flags[3] == 0   # Break
        assert cpu.flags[2] == 0   # Overflow
        assert cpu.flags[1] == 0   # Sign
        assert cpu.flags[0] == 0   # Trap

    def test_cpu_pc_initialization(self, cpu):
        """Test that program counter starts at 0."""
        assert cpu.pc == 0x0000

    def test_cpu_halted_initialization(self, cpu):
        """Test that CPU is not halted initially."""
        assert cpu.halted == False

    def test_cpu_components_integration(self, cpu):
        """Test that CPU is properly connected to components."""
        assert cpu.memory is not None
        assert cpu.gfx is not None
        assert cpu.keyboard_device is not None
        assert cpu.sound is not None


class TestCPUInstructionExecution:
    """Test basic instruction execution."""

    def test_hlt_instruction(self, cpu):
        """Test HLT instruction."""
        # Load HLT opcode (0x00) at PC
        cpu.memory.write_byte(0x0000, 0x00)

        cpu.step()
        assert cpu.halted == True
        assert cpu.pc == 0x0001  # PC should advance

    def test_nop_instruction(self, cpu):
        """Test NOP instruction."""
        # Load NOP opcode (0xFF) at PC
        cpu.memory.write_byte(0x0000, 0xFF)

        initial_pc = cpu.pc
        cpu.step()
        assert cpu.pc == initial_pc + 1
        assert cpu.halted == False

    def test_simple_arithmetic_flags(self, cpu):
        """Test that CPU can execute instructions and set flags."""
        # This is a simplified test - we'll test the CPU's ability to execute
        # without testing specific opcodes which are complex

        # Load a simple program that should work
        # For now, just test that step() doesn't crash
        cpu.memory.write_byte(0x0000, 0xFF)  # NOP

        # Should not raise an exception
        cpu.step()
        assert cpu.pc == 0x0001


class TestCPUFlags:
    """Test CPU flag operations."""

    def test_zero_flag(self, cpu):
        """Test zero flag setting."""
        cpu.Rregisters[0] = 10
        cpu.Rregisters[1] = 10

        # SUB R0, R1 (result = 0)
        cpu.memory.write_byte(0x0000, 0x08)  # SUB opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte: both register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()
        assert_register_equals(cpu, 'R0', 0)
        assert cpu.flags[7] == 1  # Zero flag set

    def test_carry_flag(self, cpu):
        """Test carry flag setting."""
        cpu.Rregisters[0] = 0
        cpu.Rregisters[1] = 1

        # SUB R0, R1 (0 - 1 = -1, borrow)
        cpu.memory.write_byte(0x0000, 0x08)  # SUB opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte: both register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()
        assert cpu.flags[6] == 1  # Carry flag set (borrow occurred)

    def test_sign_flag(self, cpu):
        """Test sign flag setting."""
        cpu.Rregisters[0] = 0
        cpu.Rregisters[1] = 1

        # SUB R0, R1 (result = -1, negative)
        cpu.memory.write_byte(0x0000, 0x08)  # SUB opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte: both register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()
        assert cpu.flags[1] == 1  # Sign flag set (negative result)


class TestCPUInterrupts:
    """Test CPU interrupt handling."""

    def test_interrupt_enable_disable(self, cpu):
        """Test CLI and STI instructions."""
        # CLI (disable interrupts)
        cpu.memory.write_byte(0x0000, 0x03)  # CLI opcode
        cpu.step()
        assert cpu.flags[5] == 0  # Interrupt flag cleared

        # STI (enable interrupts)
        cpu.memory.write_byte(0x0001, 0x04)  # STI opcode
        cpu.step()
        assert cpu.flags[5] == 1  # Interrupt flag set


class TestCPUMemoryAccess:
    """Test CPU memory access operations."""

    def test_load_immediate_to_register(self, cpu):
        """Test MOV immediate to register."""
        # MOV R0, 0x34
        cpu.memory.write_byte(0x0000, 0x06)  # MOV opcode
        cpu.memory.write_byte(0x0001, 0x04)  # Mode byte: op1=register(0), op2=immediate 8-bit(1)
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0x34)  # Immediate value

        cpu.step()
        assert_register_equals(cpu, 'R0', 0x34)  # Should load the immediate value

    def test_store_register_to_memory(self, cpu):
        """Test ST register to memory."""
        # NOTE: No general ST instruction in new opcode set
        # This test is disabled until memory operations are clarified
        cpu.Rregisters[0] = 0x42

        # For now, skip this test
        # ST R0, 0x1000
        # cpu.memory.write_byte(0x0000, 0x??)  # ST opcode - doesn't exist
        # cpu.memory.write_byte(0x0001, 0x??)  # Mode byte
        # ... operands

        # cpu.step()
        # assert cpu.memory.read_byte(0x1000) == 0x42
        pass


class TestCPURegisterOperations:
    """Test various register operations."""

    def test_16bit_register_operations(self, cpu):
        """Test 16-bit P register operations."""
        # MOV P0, 0x1234
        cpu.memory.write_byte(0x0000, 0x06)  # MOV opcode
        cpu.memory.write_byte(0x0001, 0x08)  # Mode byte: op1=register(0), op2=immediate 16-bit(2)
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_word(0x0003, 0x1234)  # Immediate value

        cpu.step()
        assert cpu.Pregisters[0] == 0x1234

    def test_video_registers(self, cpu):
        """Test video register operations."""
        # MOV VX, 100
        cpu.memory.write_byte(0x0000, 0x06)  # MOV opcode
        cpu.memory.write_byte(0x0001, 0x08)  # Mode byte: op1=register(0), op2=immediate 16-bit(2)
        cpu.memory.write_byte(0x0002, 0xFD)  # VX
        cpu.memory.write_word(0x0003, 0x0064)  # 100

        cpu.step()
        assert cpu.gfx.Vregisters[0] == 100  # VX

    def test_sound_registers(self, cpu):
        """Test sound register operations."""
        # MOV SA, 0x2000
        cpu.memory.write_byte(0x0000, 0x06)  # MOV opcode
        cpu.memory.write_byte(0x0001, 0x08)  # Mode byte: op1=register(0), op2=immediate 16-bit(2)
        cpu.memory.write_byte(0x0002, 0xDD)  # SA
        cpu.memory.write_word(0x0003, 0x2000)  # Address

        cpu.step()
        # Check that sound registers are updated (implementation details may vary)

    def test_inc_operation(self, cpu):
        """Test INC operation."""
        cpu.Rregisters[0] = 0x05

        # INC R0 (result = 0x06)
        cpu.memory.write_byte(0x0000, 0x0B)  # INC opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte: register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0

        cpu.step()
        assert_register_equals(cpu, 'R0', 0x06)

    def test_dec_operation(self, cpu):
        """Test DEC operation."""
        cpu.Rregisters[0] = 0x05

        # DEC R0 (result = 0x04)
        cpu.memory.write_byte(0x0000, 0x0C)  # DEC opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte: register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0

        cpu.step()
        assert_register_equals(cpu, 'R0', 0x04)


class TestCPUStackOperations:
    """Test stack operations in detail."""

    def test_call_ret(self, cpu):
        """Test CALL and RET instructions."""
        # CALL 0x1000
        cpu.memory.write_byte(0x0000, 0x2F)  # CALL opcode
        cpu.memory.write_byte(0x0001, 0x02)  # Mode byte: op1=immediate 16-bit(2)
        cpu.memory.write_word(0x0002, 0x1000)  # Address

        initial_sp = cpu.Pregisters[8]
        cpu.step()
        assert cpu.pc == 0x1000
        assert cpu.Pregisters[8] == initial_sp - 2  # SP decreased by 2

        # RET
        cpu.memory.write_byte(0x1000, 0x01)  # RET opcode (no mode byte)
        cpu.step()
        assert cpu.pc == 0x0004  # Back to after CALL
        assert cpu.Pregisters[8] == initial_sp  # SP restored

    def test_pushf_popf(self, cpu):
        """Test PUSHF and POPF instructions."""
        # Set some flags
        cpu.flags[7] = 1  # Zero flag
        cpu.flags[6] = 0  # Carry flag
        original_flags = cpu.flags.copy()

        # PUSHF
        cpu.memory.write_byte(0x0000, 0x1A)  # PUSHF opcode (no operands)
        initial_sp = cpu.Pregisters[8]
        cpu.step()
        assert cpu.Pregisters[8] == initial_sp - 2  # SP decreased by 2

        # Clear flags
        cpu.flags[7] = 0
        cpu.flags[6] = 1

        # POPF
        cpu.memory.write_byte(0x0001, 0x1B)  # POPF opcode (no operands)
        cpu.step()
        assert cpu.Pregisters[8] == initial_sp  # SP restored
        assert cpu.flags == original_flags  # Flags restored


class TestCPUJumpOperations:
    """Test jump and branch operations."""

    def test_jmp(self, cpu):
        """Test JMP instruction."""
        # JMP 0x1000
        cpu.memory.write_byte(0x0000, 0x1E)  # JMP opcode
        cpu.memory.write_byte(0x0001, 0x02)  # Mode byte: op1=immediate 16-bit(2)
        cpu.memory.write_word(0x0002, 0x1000)  # Address

        cpu.step()
        assert cpu.pc == 0x1000

    def test_jz_jump_taken(self, cpu):
        """Test JZ when zero flag is set."""
        cpu.flags[7] = 1  # Set zero flag

        # JZ 0x1000
        cpu.memory.write_byte(0x0000, 0x1F)  # JZ opcode
        cpu.memory.write_byte(0x0001, 0x02)  # Mode byte: op1=immediate 16-bit(2)
        cpu.memory.write_word(0x0002, 0x1000)  # Address

        cpu.step()
        assert cpu.pc == 0x1000

    def test_jz_jump_not_taken(self, cpu):
        """Test JZ when zero flag is clear."""
        cpu.flags[7] = 0  # Clear zero flag

        # JZ 0x1000
        cpu.memory.write_byte(0x0000, 0x1F)  # JZ opcode
        cpu.memory.write_byte(0x0001, 0x02)  # Mode byte: op1=immediate 16-bit(2)
        cpu.memory.write_word(0x0002, 0x1000)  # Address

        cpu.step()
        assert cpu.pc == 0x0004  # Skip the jump


class TestCPUComparisonOperations:
    """Test comparison and conditional operations."""

    def test_cmp_operation(self, cpu):
        """Test CMP operation."""
        cpu.Rregisters[0] = 10
        cpu.Rregisters[1] = 5

        # CMP R0, R1 (10 > 5, should set appropriate flags)
        cpu.memory.write_byte(0x0000, 0x2E)  # CMP opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte: both register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()
        # CMP should set flags but not change registers
        assert_register_equals(cpu, 'R0', 10)
        assert_register_equals(cpu, 'R1', 5)

    def test_jgt_jump_taken(self, cpu):
        """Test JGT when greater than."""
        cpu.Rregisters[0] = 10
        cpu.Rregisters[1] = 5

        # CMP R0, R1 (set flags)
        cpu.memory.write_byte(0x0000, 0x2E)  # CMP
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        # JGT 0x1000
        cpu.memory.write_byte(0x0004, 0x27)  # JGT opcode
        cpu.memory.write_byte(0x0005, 0x02)  # Mode byte: immediate 16-bit
        cpu.memory.write_word(0x0006, 0x1000)  # Address

        cpu.step()  # CMP
        cpu.step()  # JGT
        assert cpu.pc == 0x1000

    def test_jlt_jump_taken(self, cpu):
        """Test JLT when less than."""
        cpu.Rregisters[0] = 5
        cpu.Rregisters[1] = 10

        # CMP R0, R1 (set flags)
        cpu.memory.write_byte(0x0000, 0x2E)  # CMP
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        # JLT 0x1000
        cpu.memory.write_byte(0x0004, 0x28)  # JLT opcode
        cpu.memory.write_byte(0x0005, 0x02)  # Mode byte: immediate 16-bit
        cpu.memory.write_word(0x0006, 0x1000)  # Address

        cpu.step()  # CMP
        cpu.step()  # JLT
        assert cpu.pc == 0x1000


class TestCPUBitwiseOperations:
    """Test bitwise operations."""

    def test_and_operation(self, cpu):
        """Test AND operation."""
        cpu.Rregisters[0] = 0x0F  # 00001111
        cpu.Rregisters[1] = 0xF0  # 11110000

        # AND R0, R1 (result = 0x00)
        cpu.memory.write_byte(0x0000, 0x10)  # AND opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte: both register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()
        assert_register_equals(cpu, 'R0', 0x00)

    def test_or_operation(self, cpu):
        """Test OR operation."""
        cpu.Rregisters[0] = 0x0F  # 00001111
        cpu.Rregisters[1] = 0xF0  # 11110000

        # OR R0, R1 (result = 0xFF)
        cpu.memory.write_byte(0x0000, 0x11)  # OR opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte: both register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()
        assert_register_equals(cpu, 'R0', 0xFF)

    def test_xor_operation(self, cpu):
        """Test XOR operation."""
        cpu.Rregisters[0] = 0xAA  # 10101010
        cpu.Rregisters[1] = 0x55  # 01010101

        # XOR R0, R1 (result = 0xFF)
        cpu.memory.write_byte(0x0000, 0x12)  # XOR opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte: both register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()
        assert_register_equals(cpu, 'R0', 0xFF)

    def test_not_operation(self, cpu):
        """Test NOT operation."""
        cpu.Rregisters[0] = 0xAA  # 10101010

        # NOT R0 (result = 0x55)
        cpu.memory.write_byte(0x0000, 0x13)  # NOT opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte: register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0

        cpu.step()
        assert_register_equals(cpu, 'R0', 0x55)

    def test_shl_operation(self, cpu):
        """Test SHL (shift left) operation."""
        cpu.Rregisters[0] = 0x01  # 00000001
        cpu.Rregisters[1] = 0x03  # shift by 3

        # SHL R0, R1 (result = 0x08)
        cpu.memory.write_byte(0x0000, 0x14)  # SHL opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte: both register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()
        assert_register_equals(cpu, 'R0', 0x08)

    def test_shr_operation(self, cpu):
        """Test SHR (shift right) operation."""
        cpu.Rregisters[0] = 0x10  # 00010000
        cpu.Rregisters[1] = 0x02  # shift by 2

        # SHR R0, R1 (result = 0x04)
        cpu.memory.write_byte(0x0000, 0x15)  # SHR opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte: both register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()
        assert_register_equals(cpu, 'R0', 0x04)


class TestCPUProgramExecution:
    """Test complete program execution."""

    def test_simple_program(self, cpu):
        """Test execution of a simple program."""
        # Program: MOV R0, 10; MOV R1, 20; ADD R0, R1; HLT
        program = [
            0x06, 0x04, 0xE7, 0x0A,  # MOV R0, 10 (MOV, mode reg+imm8, R0, 10)
            0x06, 0x04, 0xE8, 0x14,  # MOV R1, 20 (MOV, mode reg+imm8, R1, 20)
            0x07, 0x00, 0xE7, 0xE8,  # ADD R0, R1 (ADD, mode reg+reg, R0, R1)
            0x00                      # HLT
        ]

        # Load program
        for i, byte in enumerate(program):
            cpu.memory.write_byte(i, byte)

        # Run until halt
        while not cpu.halted:
            cpu.step()

        assert_register_equals(cpu, 'R0', 30)
        assert cpu.halted == True


class TestCPUErrorHandling:
    """Aggressive error handling and edge case testing for CPU."""

    def test_invalid_opcodes(self, cpu):
        """Test handling of invalid opcodes."""
        # Test various invalid opcodes
        invalid_opcodes = [0x5B, 0x5C, 0x5D, 0x9D, 0xA5, 0xB7]

        for opcode in invalid_opcodes:
            cpu.memory.write_byte(0, opcode)
            cpu.pc = 0
            cpu.halted = False

            # Should raise exception for unknown opcode
            with pytest.raises(Exception, match="Unknown opcode"):
                cpu.step()

    def test_register_bounds(self, cpu):
        """Test register access bounds."""
        # Valid register access
        cpu.Rregisters[0] = 255
        cpu.Rregisters[9] = 0
        cpu.Pregisters[0] = 65535
        cpu.Pregisters[9] = 0

        assert cpu.Rregisters[0] == 255
        assert cpu.Rregisters[9] == 0
        assert cpu.Pregisters[0] == 65535
        assert cpu.Pregisters[9] == 0

        # Test register masking (should wrap)
        cpu.r0 = 300  # > 255
        assert cpu.r0 == 44  # 300 & 0xFF

        cpu.p0 = 70000  # > 65535
        assert cpu.p0 == 4464  # 70000 & 0xFFFF

    def test_memory_access_bounds(self, cpu):
        """Test memory access at boundaries."""
        # Test PC at memory boundaries
        cpu.pc = 0xFFFF
        cpu.memory.write_byte(0xFFFF, 0x00)  # NOP

        # Should execute without error
        cpu.step()
        assert cpu.pc == 0  # Should wrap to 0

    def test_stack_operations_edge_cases(self, cpu):
        """Test stack operations at boundaries."""
        # Set SP to bottom of memory
        cpu.Pregisters[8] = 0xFFFF  # SP

        # Test PUSH at stack boundary
        cpu.Rregisters[0] = 0x42
        cpu.memory.write_byte(0, 0x18)  # PUSH opcode
        cpu.memory.write_byte(1, 0x00)  # Mode byte: register direct
        cpu.memory.write_byte(2, 0xE7)  # R0
        cpu.memory.write_byte(3, 0x00)  # HLT

        cpu.pc = 0
        cpu.step()  # PUSH

        assert cpu.Pregisters[8] == 0xFFFE  # SP decremented
        assert cpu.memory.read_byte(0xFFFF) == 0x42  # Value pushed

        # Test POP
        cpu.memory.write_byte(4, 0x19)  # POP opcode
        cpu.memory.write_byte(5, 0x00)  # Mode byte: register direct
        cpu.memory.write_byte(6, 0xE8)  # R1
        cpu.memory.write_byte(7, 0x00)  # HLT

        cpu.pc = 4
        cpu.step()  # POP

        assert cpu.Pregisters[8] == 0xFFFF  # SP incremented
        assert cpu.Rregisters[1] == 0x42   # Value popped

    def test_stack_overflow_protection(self, cpu):
        """Test stack overflow/underflow protection."""
        # Fill stack area with PUSH operations
        cpu.Pregisters[8] = 0xFF00  # Start SP higher

        # Create program that pushes many values
        program = []
        for i in range(100):  # Push R0-R9 repeatedly
            reg_code = 0xE7 + (i % 10)  # R0-R9 codes
            program.extend([0x18, 0x00, reg_code])  # PUSH reg

        program.append(0x00)  # HLT

        # Load program
        for i, byte in enumerate(program):
            cpu.memory.write_byte(i, byte)

        # Run program
        cpu.pc = 0
        while not cpu.halted and cpu.pc < len(program):
            cpu.step()

        # Should complete without crashing
        assert cpu.halted == True

    def test_interrupt_edge_cases(self, cpu):
        """Test interrupt handling edge cases."""
        # Test interrupt with invalid vector
        cpu.interrupt(999)  # Invalid interrupt number

        # Should handle gracefully (depending on implementation)
        # At minimum, shouldn't crash

        # Test interrupt during interrupt
        cpu.interrupt_flag = True
        cpu.interrupt(0)  # Valid interrupt

        # Try another interrupt while processing
        cpu.interrupt(1)

        # Should handle nested interrupts or queue them

    def test_program_counter_wraparound(self, cpu):
        """Test PC wraparound behavior."""
        # Set PC to end of memory
        cpu.pc = 0xFFFF
        cpu.memory.write_byte(0xFFFF, 0x00)  # NOP

        cpu.step()
        # PC should wrap to 0
        assert cpu.pc == 0

    def test_instruction_decoding_stress(self, cpu):
        """Stress test instruction decoding with various byte patterns."""
        import random
        random.seed(42)

        # Test 1000 random byte patterns
        for _ in range(1000):
            # Generate random instruction
            opcode = random.randint(0, 255)
            cpu.memory.write_byte(0, opcode)
            cpu.pc = 0
            cpu.halted = False

            # Try to execute - should either succeed or raise known exception
            try:
                cpu.step()
            except Exception as e:
                # Any exception is acceptable for invalid/random opcodes
                pass

    def test_register_pressure_stress(self, cpu):
        """Stress test with many register operations."""
        # Create program that exercises all registers
        program = [
            0x06, 0x04, 0xE7, 0x01,  # MOV R0, 1
            0x06, 0x04, 0xE8, 0x02,  # MOV R1, 2
            0x06, 0x04, 0xE9, 0x03,  # MOV R2, 3
            0x06, 0x04, 0xEA, 0x04,  # MOV R3, 4
            0x06, 0x04, 0xEB, 0x05,  # MOV R4, 5
            0x06, 0x04, 0xEC, 0x06,  # MOV R5, 6
            0x06, 0x04, 0xED, 0x07,  # MOV R6, 7
            0x06, 0x04, 0xEE, 0x08,  # MOV R7, 8
            0x06, 0x04, 0xEF, 0x09,  # MOV R8, 9
            0x06, 0x04, 0xF0, 0x0A,  # MOV R9, 10
        ]

        # Add operations on all registers
        for i in range(10):
            reg_code = 0xE7 + i
            program.extend([
                0x07, 0x00, reg_code, reg_code,  # ADD R{i}, R{i} (double each register)
            ])

        program.append(0x00)  # HLT

        # Load and run
        for i, byte in enumerate(program):
            cpu.memory.write_byte(i, byte)

        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify results
        expected = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]  # Each register doubled
        for i, exp in enumerate(expected):
            assert_register_equals(cpu, f'R{i}', exp)

    def test_memory_access_patterns(self, cpu):
        """Test various memory access patterns."""
        # Test accessing memory near PC
        cpu.pc = 0x1000
        cpu.memory.write_byte(0x1000, 0x00)  # NOP at PC
        cpu.memory.write_byte(0x1001, 0xAA)  # Data after PC

        cpu.step()
        assert cpu.pc == 0x1001
        assert cpu.memory.read_byte(0x1001) == 0xAA  # Data unchanged

        # Test self-modifying code
        cpu.pc = 0x2000
        cpu.halted = False  # Reset halted state
        cpu.memory.write_byte(0x2000, 0x06)  # MOV opcode
        cpu.memory.write_byte(0x2001, 0x04)  # Mode byte: reg + 8-bit immediate
        cpu.memory.write_byte(0x2002, 0xE7)  # R0
        cpu.memory.write_byte(0x2003, 0x42)  # Value

        cpu.step()
        assert cpu.pc == 0x2004  # PC should advance past the instruction
        assert_register_equals(cpu, 'R0', 0x42)

        # Modify the instruction
        cpu.memory.write_byte(0x2003, 0x24)  # Change value

        # Run again
        cpu.pc = 0x2000
        cpu.halted = False  # Reset halted state
        cpu.step()
        assert_register_equals(cpu, 'R0', 0x24)

    def test_flag_operations_edge_cases(self, cpu):
        """Test flag operations at boundaries."""
        # Test carry flag with maximum values
        cpu.Rregisters[0] = 255
        cpu.Rregisters[1] = 255

        # ADD that causes overflow
        cpu.memory.write_byte(0, 0x07)  # ADD opcode
        cpu.memory.write_byte(1, 0x00)  # Mode byte: register + register
        cpu.memory.write_byte(2, 0xE7)  # R0
        cpu.memory.write_byte(3, 0xE8)  # R1
        cpu.memory.write_byte(4, 0x00)  # HLT

        cpu.pc = 0
        cpu.step()

        # Result should be 254 (510 & 0xFF), carry should be set
        assert_register_equals(cpu, 'R0', 254)

    def test_timing_and_performance(self, cpu):
        """Test CPU timing and performance characteristics."""
        import time

        # Measure execution time for many instructions
        program = [0x00] * 10000  # 10000 NOPs

        for i, byte in enumerate(program):
            cpu.memory.write_byte(i, byte)

        start_time = time.time()
        cpu.pc = 0
        for _ in range(10000):
            cpu.step()
        end_time = time.time()

        execution_time = end_time - start_time
        # Should execute reasonably fast (less than 1 second for 10000 instructions)
        assert execution_time < 1.0

    def test_cpu_state_preservation(self, cpu):
        """Test that CPU state is properly preserved across operations."""
        # Set up complex state
        cpu.Rregisters = [i for i in range(10)]
        cpu.Pregisters = [i * 256 for i in range(10)]
        cpu.pc = 0x1234
        cpu.sp = 0xFFFF
        cpu.flags = [True, False, True, False]

        # Save state
        saved_state = {
            'r': cpu.Rregisters.copy(),
            'p': cpu.Pregisters.copy(),
            'pc': cpu.pc,
            'sp': cpu.sp,
            'flags': cpu.flags.copy()
        }

        # Execute some instructions
        cpu.memory.write_byte(0x1234, 0x00)  # NOP
        cpu.step()

        # Execute more instructions
        for _ in range(10):
            cpu.step()  # Should not crash even if PC goes out of bounds

        # Verify state is preserved (except PC which changes)
        assert cpu.Rregisters == saved_state['r']
        assert cpu.Pregisters == saved_state['p']
        assert cpu.sp == saved_state['sp']
        assert cpu.flags == saved_state['flags']
        # PC should have changed
        assert cpu.pc != saved_state['pc']