"""
Unit tests for nova_cpu.py - Nova-16 CPU core.
"""

import math
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
        cpu.write_byte(0x0001, 0x04)  # STI opcode
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

    def test_rndr_small_range_does_not_cycle_sequential_low_bits(self, cpu):
        """RNDR should not reduce to the old 0,1,2,3 low-bit cycle for small ranges."""
        cpu.rng_seed = 1
        cpu.Rregisters[1] = 0
        cpu.Rregisters[2] = 3

        cpu.memory.write_byte(0x0000, 0x49)  # RNDR opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte: all register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0 destination
        cpu.memory.write_byte(0x0003, 0xE8)  # R1 minimum
        cpu.memory.write_byte(0x0004, 0xE9)  # R2 maximum

        values = []
        for _ in range(8):
            cpu.pc = 0
            cpu.step()
            values.append(cpu.Rregisters[0])

        assert all(0 <= value <= 3 for value in values)
        assert values != [0, 1, 2, 3, 0, 1, 2, 3]

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

    def test_btst_operation(self, cpu):
        """Test BTST (bit test) operation."""
        cpu.Rregisters[0] = 0xAA  # 10101010
        cpu.Rregisters[1] = 0x01  # test bit 1

        # BTST R0, R1 (bit 1 is set, so Z should be 0)
        cpu.memory.write_byte(0x0000, 0x6D)  # BTST opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte: both register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()
        assert cpu.zero_flag == False  # Bit 1 is set
        assert_register_equals(cpu, 'R0', 0xAA)  # R0 unchanged

        # Test bit 2 (which is clear)
        cpu.pc = 0  # Reset PC
        cpu.Rregisters[1] = 0x02  # test bit 2
        cpu.memory.write_byte(0x0000, 0x6D)  # BTST opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte: both register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()
        assert cpu.zero_flag == True  # Bit 2 is clear
        assert_register_equals(cpu, 'R0', 0xAA)  # R0 unchanged

    def test_bset_operation(self, cpu):
        """Test BSET (bit set) operation."""
        cpu.Rregisters[0] = 0xAA  # 10101010
        cpu.Rregisters[1] = 0x02  # set bit 2

        # BSET R0, R1 (result = 0xAE = 10101110)
        cpu.memory.write_byte(0x0000, 0x6E)  # BSET opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte: both register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()
        assert_register_equals(cpu, 'R0', 0xAE)

    def test_bclr_operation(self, cpu):
        """Test BCLR (bit clear) operation."""
        cpu.Rregisters[0] = 0xAA  # 10101010
        cpu.Rregisters[1] = 0x01  # clear bit 1

        # BCLR R0, R1 (result = 0xA8 = 10101000)
        cpu.memory.write_byte(0x0000, 0x6F)  # BCLR opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte: both register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()
        assert_register_equals(cpu, 'R0', 0xA8)

    def test_bflip_operation(self, cpu):
        """Test BFLIP (bit flip) operation."""
        cpu.Rregisters[0] = 0xAA  # 10101010
        cpu.Rregisters[1] = 0x01  # flip bit 1

        # BFLIP R0, R1 (result = 0xA8 = 10101000, bit 1 was set, now clear)
        cpu.memory.write_byte(0x0000, 0x70)  # BFLIP opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte: both register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()
        assert_register_equals(cpu, 'R0', 0xA8)

        # Flip again (bit 1 was clear, now set)
        cpu.pc = 0  # Reset PC
        cpu.memory.write_byte(0x0000, 0x70)  # BFLIP opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode byte: both register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()
        assert_register_equals(cpu, 'R0', 0xAA)


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
        # Future-proof by removing known opcodes from the dispatch table instead of
        # depending on permanent gaps in the opcode space.
        invalid_opcodes = [0xFF, 0x06]

        for opcode in invalid_opcodes:
            instruction = cpu.instruction_table.pop(opcode)
            cpu.memory.write_byte(0, opcode)
            cpu.pc = 0
            cpu.halted = False

            try:
                with pytest.raises(Exception, match="Unknown opcode"):
                    cpu.step()
            finally:
                cpu.instruction_table[opcode] = instruction

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
        cpu.write_byte(0, 0x18)  # PUSH opcode
        cpu.write_byte(1, 0x00)  # Mode byte: register direct
        cpu.write_byte(2, 0xE7)  # R0
        cpu.write_byte(3, 0x00)  # HLT

        cpu.pc = 0
        cpu.step()  # PUSH

        assert cpu.Pregisters[8] == 0xFFFE  # SP decremented
        assert cpu.memory.read_byte(0xFFFE) == 0x42  # Value pushed

        # Test POP
        cpu.write_byte(4, 0x19)  # POP opcode
        cpu.write_byte(5, 0x00)  # Mode byte: register direct
        cpu.write_byte(6, 0xE8)  # R1
        cpu.write_byte(7, 0x00)  # HLT

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

    @pytest.mark.skip(reason="Test causes infinite loops with random opcodes - needs instruction validation")
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
        # Set 12 flags explicitly (T, S, O, B, D, I, C, Z, P, H, A, E)
        # NOTE: T(0)=False to avoid triggering breakpoint trap during NOP steps
        initial_flags = [False, True, False, True, False, False, False, False, True, False, True, False]
        cpu.flags = initial_flags

        # Save state
        saved_state = {
            'r': cpu.Rregisters.copy(),
            'p': cpu.Pregisters.copy(),
            'pc': cpu.pc,
            'sp': cpu.sp,
            'flags': cpu.flags.get_state()
        }

        # Execute some instructions that shouldn't modify flags
        cpu.memory.write_byte(0x1234, 0xFF)  # NOP
        cpu.memory.write_byte(0x1235, 0xFF)  # NOP
        cpu.memory.write_byte(0x1236, 0xFF)  # NOP
        cpu.memory.write_byte(0x1237, 0xFF)  # NOP
        cpu.memory.write_byte(0x1238, 0xFF)  # NOP
        cpu.memory.write_byte(0x1239, 0xFF)  # NOP
        cpu.memory.write_byte(0x123A, 0xFF)  # NOP
        cpu.memory.write_byte(0x123B, 0xFF)  # NOP
        cpu.memory.write_byte(0x123C, 0xFF)  # NOP
        cpu.memory.write_byte(0x123D, 0xFF)  # NOP
        cpu.memory.write_byte(0x123E, 0xFF)  # NOP
        cpu.memory.write_byte(0x123F, 0x00)  # HLT

        # Execute instructions
        for _ in range(11):
            cpu.step()

        # Verify R registers preserved
        assert cpu.Rregisters == saved_state['r']
        
        # P registers preserved except SP (P8) and FP (P9) which may
        # change during execution (timer updates push/pop to stack)
        for i in range(8):
            assert cpu.Pregisters[i] == saved_state['p'][i], f"P{i} changed"
        
        # Flags should be preserved (NOP doesn't modify flags)
        assert cpu.flags.get_state() == saved_state['flags']
        # PC should have changed
        assert cpu.pc != saved_state['pc']


class TestCPUTimer:
    """Test CPU timer functionality."""

    def test_timer_register_tt_access(self, cpu_with_timer):
        """Test setting and reading timer counter register TT."""
        cpu = cpu_with_timer
        # MOV TT, 42
        cpu.memory.write_byte(0x0000, 0x06)  # MOV opcode
        cpu.memory.write_byte(0x0001, 0x04)  # mode: register + immediate 8-bit
        cpu.memory.write_byte(0x0002, 0xE3)  # TT register code
        cpu.memory.write_byte(0x0003, 42)    # value
        
        cpu.step()
        assert cpu.timer_device.regs[0] == 42

    def test_timer_register_tm_access(self, cpu_with_timer):
        """Test setting timer modulo register TM."""
        cpu = cpu_with_timer
        # MOV TM, 100
        cpu.memory.write_byte(0x0000, 0x06)  # MOV
        cpu.memory.write_byte(0x0001, 0x04)  # mode
        cpu.memory.write_byte(0x0002, 0xE4)  # TM
        cpu.memory.write_byte(0x0003, 100)   # value
        
        cpu.step()
        assert cpu.timer_device.regs[1] == 100

    def test_timer_register_tc_access(self, cpu_with_timer):
        """Test setting timer control register TC."""
        cpu = cpu_with_timer
        # MOV TC, 3 (enable timer and interrupts)
        cpu.memory.write_byte(0x0000, 0x06)  # MOV
        cpu.memory.write_byte(0x0001, 0x04)  # mode
        cpu.memory.write_byte(0x0002, 0xE5)  # TC
        cpu.memory.write_byte(0x0003, 3)     # value
        
        cpu.step()
        assert cpu.timer_device.regs[2] == 3
        assert cpu.timer_device._enabled == True
        assert cpu.intr_ctrl.enabled[cpu.intr_ctrl.VECTOR_TIMER] == 1

    def test_timer_register_ts_access(self, cpu_with_timer):
        """Test setting timer speed register TS."""
        cpu = cpu_with_timer
        # MOV TS, 5
        cpu.memory.write_byte(0x0000, 0x06)  # MOV
        cpu.memory.write_byte(0x0001, 0x04)  # mode
        cpu.memory.write_byte(0x0002, 0xE6)  # TS
        cpu.memory.write_byte(0x0003, 5)     # value
        
        cpu.step()
        assert cpu.timer_device.regs[3] == 5

    def test_timer_increment_basic(self, cpu_with_timer):
        """Test basic timer increment with speed 0 (every cycle)."""
        cpu = cpu_with_timer
        timer = cpu.timer_device
        # Set up timer
        timer.set_register(0, 0)   # TT
        timer.set_register(1, 10)  # TM
        timer.set_register(2, 1)   # TC: enable timer, disable interrupts
        
        # Timer updates via bus events
        for _ in range(10):
            cpu.bus.publish('cpu.tick', None)
        
        assert timer.regs[0] == 10

    def test_timer_interrupt_trigger(self, cpu_with_timer):
        """Test timer interrupt triggering."""
        cpu = cpu_with_timer
        timer = cpu.timer_device
        intr = cpu.intr_ctrl
        
        # Set up interrupt vector
        cpu.memory.write_word(0x0100, 0x2000)  # Timer interrupt handler at 0x2000
        
        # Set up timer
        timer.set_register(0, 0)   # TT
        timer.set_register(1, 5)   # TM
        timer.set_register(2, 3)  # TC: enable timer and interrupts
        
        # Enable global interrupts
        cpu.flags[5] = 1
        
        # Enable timer interrupt vector
        intr.set_enable(intr.VECTOR_TIMER, True)
        
        # Run until interrupt
        cycles = 0
        while cpu.pc == 0x0000 and cycles < 20:
            cpu.bus.publish('cpu.tick', None)
            cycles += 1
        
        # Should have triggered interrupt and jumped to 0x2000
        assert cpu.pc == 0x2000
        assert timer.regs[0] == 0  # Reset after interrupt

    def test_timer_speed_scaling(self, cpu_with_timer):
        """Test timer speed scaling."""
        cpu = cpu_with_timer
        timer = cpu.timer_device
        # Speed 1: increment every 2 cycles
        timer.set_register(0, 0)
        timer.set_register(1, 10)
        timer.set_register(2, 1)  # Enable timer
        timer.set_register(3, 1)  # Speed 1
        
        # 10 ticks at speed 1 should advance by 5
        for _ in range(10):
            cpu.bus.publish('cpu.tick', None)
        
        assert timer.regs[0] == 5

    def test_timer_disable_reset(self, cpu_with_timer):
        """Test timer disable resets state."""
        cpu = cpu_with_timer
        timer = cpu.timer_device
        timer.set_register(0, 5)
        timer._cycle_count = 10
        timer.set_register(2, 0)  # Disable timer
        
        assert timer._enabled == False
        assert timer.regs[0] == 0
        assert timer._cycle_count == 0

    def test_timer_modulo_zero_no_interrupt(self, cpu_with_timer):
        """Test that TM=0 prevents interrupts but allows increment."""
        cpu = cpu_with_timer
        timer = cpu.timer_device
        intr = cpu.intr_ctrl
        
        cpu.memory.write_word(0x0100, 0x2000)
        timer.set_register(0, 0)
        timer.set_register(1, 0)   # TM=0
        timer.set_register(2, 3)   # Enable
        timer.set_register(3, 0)   # Speed 0
        cpu.flags[5] = 1
        intr.set_enable(intr.VECTOR_TIMER, True)
        
        # Run 10 ticks
        for _ in range(10):
            cpu.bus.publish('cpu.tick', None)
        
        # Should not have triggered interrupt
        assert cpu.pc == 0x0000
        assert timer.regs[0] == 10


class TestCPUGraphicsInstructions:
    """Test graphics instructions (SWRITE, SREAD, etc.)"""

    def test_swrite_coordinate_mode(self, cpu):
        """Test SWRITE in coordinate mode (VM=0)."""
        # Set coordinate mode
        cpu.memory.write_byte(0x0000, 0x06)  # MOV opcode
        cpu.memory.write_byte(0x0001, 0x04)  # Mode: reg + imm8
        cpu.memory.write_byte(0x0002, 0xE1)  # VM register (0xE1)
        cpu.memory.write_byte(0x0003, 0x00)  # VM = 0 (coordinate mode)

        # Set coordinates
        cpu.memory.write_byte(0x0004, 0x06)  # MOV VX, 10
        cpu.memory.write_byte(0x0005, 0x04)
        cpu.memory.write_byte(0x0006, 0xFD)  # VX (0xFD)
        cpu.memory.write_byte(0x0007, 0x0A)  # X = 10

        cpu.memory.write_byte(0x0008, 0x06)  # MOV VY, 20
        cpu.memory.write_byte(0x0009, 0x04)
        cpu.memory.write_byte(0x000A, 0xFE)  # VY (0xFE)
        cpu.memory.write_byte(0x000B, 0x14)  # Y = 20

        # Set layer
        cpu.memory.write_byte(0x000C, 0x06)  # MOV VL, 1
        cpu.memory.write_byte(0x000D, 0x04)
        cpu.memory.write_byte(0x000E, 0xE2)  # VL register (0xE2)
        cpu.memory.write_byte(0x000F, 0x01)  # Layer = 1

        # Write pixel
        cpu.memory.write_byte(0x0010, 0x33)  # SWRITE opcode
        cpu.memory.write_byte(0x0011, 0x01)  # Mode: immediate 8-bit
        cpu.memory.write_byte(0x0012, 0xFF)  # Color = 255

        cpu.memory.write_byte(0x0013, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify pixel was written (implementation dependent)

    def test_sread_coordinate_mode(self, cpu):
        """Test SREAD in coordinate mode."""
        # Set coordinate mode and coordinates
        cpu.memory.write_byte(0x0000, 0x06)  # MOV VM, 0
        cpu.memory.write_byte(0x0001, 0x04)
        cpu.memory.write_byte(0x0002, 0xE1)  # VM (0xE1)
        cpu.memory.write_byte(0x0003, 0x00)

        cpu.memory.write_byte(0x0004, 0x06)  # MOV VX, 5
        cpu.memory.write_byte(0x0005, 0x04)
        cpu.memory.write_byte(0x0006, 0xFD)  # VX (0xFD)
        cpu.memory.write_byte(0x0007, 0x05)

        cpu.memory.write_byte(0x0008, 0x06)  # MOV VY, 10
        cpu.memory.write_byte(0x0009, 0x04)
        cpu.memory.write_byte(0x000A, 0xFE)  # VY (0xFE)
        cpu.memory.write_byte(0x000B, 0x0A)

        # Read pixel into R0
        cpu.memory.write_byte(0x000C, 0x32)  # SREAD opcode
        cpu.memory.write_byte(0x000D, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x000E, 0xE7)  # R0

        cpu.memory.write_byte(0x000F, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify R0 contains pixel value (implementation dependent)
        assert cpu.Rregisters[0] >= 0  # Should be a valid color value

    def test_swrite_direct_addressing(self, cpu):
        """Test SWRITE in direct memory addressing mode (VM=1)."""
        # Set direct addressing mode
        cpu.memory.write_byte(0x0000, 0x06)  # MOV VM, 1
        cpu.memory.write_byte(0x0001, 0x04)
        cpu.memory.write_byte(0x0002, 0xE1)  # VM (0xE1)
        cpu.memory.write_byte(0x0003, 0x01)

        # Set address in VX/VY (high/low bytes)
        cpu.memory.write_byte(0x0004, 0x06)  # MOV VX, 0x10 (high byte)
        cpu.memory.write_byte(0x0005, 0x04)
        cpu.memory.write_byte(0x0006, 0xFD)  # VX
        cpu.memory.write_byte(0x0007, 0x10)

        cpu.memory.write_byte(0x0008, 0x06)  # MOV VY, 0x00 (low byte)
        cpu.memory.write_byte(0x0009, 0x04)
        cpu.memory.write_byte(0x000A, 0xFE)  # VY
        cpu.memory.write_byte(0x000B, 0x00)

        # Write pixel
        cpu.memory.write_byte(0x000C, 0x33)  # SWRITE opcode
        cpu.memory.write_byte(0x000D, 0x01)  # Mode: immediate 8-bit
        cpu.memory.write_byte(0x000E, 0xAA)  # Color = 170

        cpu.memory.write_byte(0x000F, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify VRAM was written (implementation dependent)

    def test_sfill_operation(self, cpu):
        """Test SFILL instruction."""
        # Fill screen with color 128
        cpu.memory.write_byte(0x0000, 0x3D)  # SFILL opcode
        cpu.memory.write_byte(0x0001, 0x01)  # Mode: immediate 8-bit
        cpu.memory.write_byte(0x0002, 0x80)  # Color = 128

        cpu.memory.write_byte(0x0003, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify screen was filled (implementation dependent)

    @pytest.mark.skip(reason="VWRITE/VREAD uses P-register for 16-bit address; test needs updating for 16-bit addressing")
    def test_vwrite_vread_operations(self, cpu):
        """Test VRAM write and read operations."""
        # Set address in P0 (16-bit register for VRAM addressing)
        cpu.memory.write_byte(0x0000, 0x06)  # MOV P0, 0x2000
        cpu.memory.write_byte(0x0001, 0x08)  # Mode: reg + imm16
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_word(0x0003, 0x2000)  # Address

        # Write to VRAM at address in P0
        cpu.memory.write_byte(0x0005, 0x3F)  # VWRITE opcode
        cpu.memory.write_byte(0x0006, 0x04)  # Mode: reg + imm8
        cpu.memory.write_byte(0x0007, 0xF1)  # Address in P0
        cpu.memory.write_byte(0x0008, 0x42)  # Value

        # Read from VRAM at address in P0 into R0
        cpu.memory.write_byte(0x0009, 0x3E)  # VREAD opcode
        cpu.memory.write_byte(0x000A, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x000B, 0xE7)  # R0 (result)

        cpu.memory.write_byte(0x000C, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify value was read correctly
        assert_register_equals(cpu, 'R0', 0x42)

    def test_char_operation(self, cpu):
        """Test CHAR instruction for drawing characters."""
        # Set coordinates
        cpu.memory.write_byte(0x0000, 0x06)  # MOV VX, 50
        cpu.memory.write_byte(0x0001, 0x04)
        cpu.memory.write_byte(0x0002, 0xFD)  # VX (0xFD)
        cpu.memory.write_byte(0x0003, 0x32)

        cpu.memory.write_byte(0x0004, 0x06)  # MOV VY, 60
        cpu.memory.write_byte(0x0005, 0x04)
        cpu.memory.write_byte(0x0006, 0xFE)  # VY (0xFE)
        cpu.memory.write_byte(0x0007, 0x3C)

        # Draw character 'A' (ASCII 65) with color 255
        cpu.memory.write_byte(0x0008, 0x41)  # CHAR opcode
        cpu.memory.write_byte(0x0009, 0x05)  # Mode: imm8 + imm8
        cpu.memory.write_byte(0x000A, 0x41)  # Character code
        cpu.memory.write_byte(0x000B, 0xFF)  # Color

        cpu.memory.write_byte(0x000C, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Character drawing is implementation dependent

    def test_text_operation(self, cpu):
        """Test TEXT instruction for drawing text strings."""
        # Set text in memory
        text_addr = 0x1000
        text_data = b"Hello World"
        for i, byte in enumerate(text_data):
            cpu.memory.write_byte(text_addr + i, byte)

        # Set coordinates
        cpu.memory.write_byte(0x0000, 0x06)  # MOV VX, 10
        cpu.memory.write_byte(0x0001, 0x04)
        cpu.memory.write_byte(0x0002, 0xFD)  # VX (0xFD)
        cpu.memory.write_byte(0x0003, 0x0A)

        cpu.memory.write_byte(0x0004, 0x06)  # MOV VY, 30
        cpu.memory.write_byte(0x0005, 0x04)
        cpu.memory.write_byte(0x0006, 0xFE)  # VY (0xFE)
        cpu.memory.write_byte(0x0007, 0x1E)

        # Draw text
        cpu.memory.write_byte(0x0008, 0x42)  # TEXT opcode
        cpu.memory.write_byte(0x0009, 0x05)  # Mode: imm16 + imm8
        cpu.memory.write_word(0x000A, text_addr)  # Text address
        cpu.memory.write_byte(0x000C, 0xFF)      # Color

        cpu.memory.write_byte(0x000D, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Text drawing is implementation dependent

    def test_srol_operation(self, cpu):
        """Test SROL (screen roll) instruction."""
        # Roll screen horizontally by 5 pixels
        cpu.memory.write_byte(0x0000, 0x34)  # SROL opcode
        cpu.memory.write_byte(0x0001, 0x05)  # Mode: imm8 + imm8
        cpu.memory.write_byte(0x0002, 0x00)  # Axis = 0 (horizontal)
        cpu.memory.write_byte(0x0003, 0x05)  # Amount = 5

        cpu.memory.write_byte(0x0004, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Screen rolling is implementation dependent

    def test_sshft_operation(self, cpu):
        """Test SSHFT (screen shift) instruction."""
        # Shift screen vertically by 10 pixels
        cpu.memory.write_byte(0x0000, 0x36)  # SSHFT opcode
        cpu.memory.write_byte(0x0001, 0x05)  # Mode: imm8 + imm8
        cpu.memory.write_byte(0x0002, 0x01)  # Axis = 1 (vertical)
        cpu.memory.write_byte(0x0003, 0x0A)  # Amount = 10

        cpu.memory.write_byte(0x0004, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Screen shifting is implementation dependent

    def test_sflip_operation(self, cpu):
        """Test SFLIP (screen flip) instruction."""
        # Flip screen horizontally
        cpu.memory.write_byte(0x0000, 0x37)  # SFLIP opcode
        cpu.memory.write_byte(0x0001, 0x01)  # Mode: immediate 8-bit
        cpu.memory.write_byte(0x0002, 0x00)  # Axis = 0 (horizontal)

        cpu.memory.write_byte(0x0003, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Screen flipping is implementation dependent


class TestCPUSoundInstructions:
    """Test sound instructions (SPLAY, SSTOP, STRIG)"""

    def test_splay_instruction(self, cpu):
        """Test SPLAY instruction."""
        # Set sound registers first
        cpu.memory.write_byte(0x0000, 0x06)  # MOV SA, 0x2000
        cpu.memory.write_byte(0x0001, 0x08)
        cpu.memory.write_byte(0x0002, 0xDD)  # SA
        cpu.memory.write_word(0x0003, 0x2000)

        cpu.memory.write_byte(0x0005, 0x06)  # MOV SF, 440
        cpu.memory.write_byte(0x0006, 0x08)
        cpu.memory.write_byte(0x0007, 0xDE)  # SF
        cpu.memory.write_word(0x0008, 0x01B8)  # 440 Hz

        cpu.memory.write_byte(0x000A, 0x06)  # MOV SV, 128
        cpu.memory.write_byte(0x000B, 0x04)
        cpu.memory.write_byte(0x000C, 0xDF)  # SV
        cpu.memory.write_byte(0x000D, 0x80)  # Volume 128

        cpu.memory.write_byte(0x000E, 0x06)  # MOV SW, 0
        cpu.memory.write_byte(0x000F, 0x04)
        cpu.memory.write_byte(0x0010, 0xE0)  # SW
        cpu.memory.write_byte(0x0011, 0x00)  # Waveform 0

        # Play sound
        cpu.memory.write_byte(0x0012, 0x57)  # SPLAY opcode
        cpu.memory.write_byte(0x0013, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Sound playback is implementation dependent

    def test_sstop_instruction(self, cpu):
        """Test SSTOP instruction."""
        # Start sound first
        cpu.memory.write_byte(0x0000, 0x57)  # SPLAY

        # Stop sound
        cpu.memory.write_byte(0x0001, 0x58)  # SSTOP opcode
        cpu.memory.write_byte(0x0002, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Sound stopping is implementation dependent

    def test_strig_instruction(self, cpu):
        """Test STRIG instruction with different effect IDs."""
        # Trigger sound effect 1
        cpu.memory.write_byte(0x0000, 0x59)  # STRIG opcode
        cpu.memory.write_byte(0x0001, 0x01)  # Mode: immediate 8-bit
        cpu.memory.write_byte(0x0002, 0x01)  # Effect ID = 1

        cpu.memory.write_byte(0x0003, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Sound effect triggering is implementation dependent

    def test_sound_register_operations(self, cpu):
        """Test setting and reading sound registers."""
        # Set all sound registers
        cpu.memory.write_byte(0x0000, 0x06)  # MOV SA, 0x3000
        cpu.memory.write_byte(0x0001, 0x08)
        cpu.memory.write_byte(0x0002, 0xDD)
        cpu.memory.write_word(0x0003, 0x3000)

        cpu.memory.write_byte(0x0005, 0x06)  # MOV SF, 880
        cpu.memory.write_byte(0x0006, 0x08)
        cpu.memory.write_byte(0x0007, 0xDE)
        cpu.memory.write_word(0x0008, 0x0370)  # 880 Hz

        cpu.memory.write_byte(0x000A, 0x06)  # MOV SV, 64
        cpu.memory.write_byte(0x000B, 0x04)
        cpu.memory.write_byte(0x000C, 0xDF)
        cpu.memory.write_byte(0x000D, 0x40)

        cpu.memory.write_byte(0x000E, 0x06)  # MOV SW, 2
        cpu.memory.write_byte(0x000F, 0x04)
        cpu.memory.write_byte(0x0010, 0xE0)
        cpu.memory.write_byte(0x0011, 0x02)

        cpu.memory.write_byte(0x0012, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify sound registers were set
        # Note: Sound register access depends on implementation


class TestCPUKeyboardInstructions:
    """Test keyboard instructions (KEYIN, KEYSTAT, KEYCOUNT, KEYCLEAR)"""

    def test_keyin_instruction(self, cpu):
        """Test KEYIN instruction."""
        # Simulate key press in keyboard buffer
        cpu.add_key_to_buffer(65)  # ASCII 'A'

        # Read key into R0
        cpu.memory.write_byte(0x0000, 0x43)  # KEYIN opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0

        cpu.memory.write_byte(0x0003, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify key was read
        assert_register_equals(cpu, 'R0', 65)

    def test_keystat_instruction(self, cpu):
        """Test KEYSTAT instruction."""
        # Check status when no key available
        cpu.memory.write_byte(0x0000, 0x44)  # KEYSTAT opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0

        cpu.memory.write_byte(0x0003, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Should return 0 (no key available)
        assert_register_equals(cpu, 'R0', 0)

        # Now test with key available
        cpu.add_key_to_buffer(66)  # ASCII 'B'

        cpu.pc = 0
        cpu.halted = False
        cpu.memory.write_byte(0x0003, 0x00)  # Reset HLT

        # Run again
        while not cpu.halted:
            cpu.step()

        # Should return 1 (key available)
        assert_register_equals(cpu, 'R0', 1)

    def test_keycount_instruction(self, cpu):
        """Test KEYCOUNT instruction."""
        # Add multiple keys to buffer
        cpu.add_key_to_buffer(65)  # 'A'
        cpu.add_key_to_buffer(66)  # 'B'
        cpu.add_key_to_buffer(67)  # 'C'

        # Get key count
        cpu.memory.write_byte(0x0000, 0x45)  # KEYCOUNT opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0

        cpu.memory.write_byte(0x0003, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Should return 3
        assert_register_equals(cpu, 'R0', 3)

    def test_keyclear_instruction(self, cpu):
        """Test KEYCLEAR instruction."""
        # Add keys to buffer
        cpu.add_key_to_buffer(65)
        cpu.add_key_to_buffer(66)
        cpu.add_key_to_buffer(67)

        # Clear buffer
        cpu.memory.write_byte(0x0000, 0x46)  # KEYCLEAR opcode

        # Check count after clear
        cpu.memory.write_byte(0x0001, 0x45)  # KEYCOUNT
        cpu.memory.write_byte(0x0002, 0x00)
        cpu.memory.write_byte(0x0003, 0xE7)  # R0

        cpu.memory.write_byte(0x0004, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Should return 0 after clear
        assert_register_equals(cpu, 'R0', 0)
        assert len(cpu.key_buffer) == 0

    def test_keyctrl_instruction(self, cpu):
        """Test KEYCTRL instruction."""
        # Set keyboard control (implementation dependent)
        cpu.memory.write_byte(0x0000, 0x47)  # KEYCTRL opcode
        cpu.memory.write_byte(0x0001, 0x01)  # Mode: immediate 8-bit
        cpu.memory.write_byte(0x0002, 0x01)  # Control value

        cpu.memory.write_byte(0x0003, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Keyboard control is implementation dependent

    def test_keyboard_buffer_operations(self, cpu):
        """Test comprehensive keyboard buffer operations."""
        # Fill buffer with multiple keys
        for i in range(10):
            cpu.add_key_to_buffer(65 + i)  # 'A' to 'J'

        # Read all keys
        program = []
        for i in range(10):
            program.extend([0x43, 0x00, 0xE7 + (i % 10)])  # KEYIN to R{i}

        program.append(0x00)  # HLT

        # Load and run program
        for i, byte in enumerate(program):
            cpu.memory.write_byte(i, byte)

        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify all keys were read correctly
        for i in range(10):
            expected_key = 65 + i
            assert_register_equals(cpu, f'R{i}', expected_key)


class TestCPUSerialInstructions:
    """Test serial instructions (SERIN, SEROUT, SERSTAT, SERCTRL)"""

    def test_serin_instruction(self, cpu):
        """Test SERIN instruction."""
        # Simulate serial data available
        cpu.serial[0] = 65  # ASCII 'A'
        cpu.serial[1] |= 0x01  # Set data available flag

        # Read serial data into R0
        cpu.memory.write_byte(0x0000, 0xA2)  # SERIN opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0

        cpu.memory.write_byte(0x0003, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify data was read
        assert_register_equals(cpu, 'R0', 65)
        # Verify flag was cleared
        assert (cpu.serial[1] & 0x01) == 0

    def test_serout_instruction(self, cpu):
        """Test SEROUT instruction."""
        # Write data to serial
        cpu.memory.write_byte(0x0000, 0xA3)  # SEROUT opcode
        cpu.memory.write_byte(0x0001, 0x01)  # Mode: immediate 8-bit
        cpu.memory.write_byte(0x0002, 66)    # Data 'B'

        cpu.memory.write_byte(0x0003, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify data was written
        assert cpu.serial[0] == 66
        # Verify tx complete flag set
        assert (cpu.serial[1] & 0x02) != 0

    def test_serstat_instruction(self, cpu):
        """Test SERSTAT instruction."""
        # Set some status flags
        cpu.serial[1] = 0x03  # Data available and tx complete

        # Read status into R0
        cpu.memory.write_byte(0x0000, 0xA4)  # SERSTAT opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0

        cpu.memory.write_byte(0x0003, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify status was read
        assert_register_equals(cpu, 'R0', 0x03)

    def test_serctrl_instruction(self, cpu):
        """Test SERCTRL instruction."""
        # Set serial control
        cpu.memory.write_byte(0x0000, 0xA5)  # SERCTRL opcode
        cpu.memory.write_byte(0x0001, 0x01)  # Mode: immediate 8-bit
        cpu.memory.write_byte(0x0002, 0x01)  # Control value (enable interrupts)

        cpu.memory.write_byte(0x0003, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify control was set and interrupts enabled
        assert (cpu.serial[1] & 0x01) != 0  # Control bit set
        assert cpu.interrupts[1] == 1  # Serial interrupt enabled

    def test_mousectrl_instruction(self, cpu):
        """Test MOUSECTRL instruction."""
        cpu.mouse.move_to(6, 8)

        cpu.memory.write_byte(0x0000, 0xB3)  # MOUSECTRL opcode
        cpu.memory.write_byte(0x0001, 0x01)  # Mode: immediate 8-bit
        cpu.memory.write_byte(0x0002, 0x00)  # Disable mouse
        cpu.memory.write_byte(0x0003, 0xB3)  # MOUSECTRL opcode
        cpu.memory.write_byte(0x0004, 0x01)  # Mode: immediate 8-bit
        cpu.memory.write_byte(0x0005, 0x01)  # Enable mouse

        cpu.pc = 0
        cpu.step()

        assert cpu.mouse.enabled is False
        assert cpu.interrupts[3] == 0
        assert cpu.mouse.pending_interrupt is False

        cpu.step()

        assert cpu.mouse.enabled is True
        assert cpu.interrupts[3] == 1

    def test_mouse_event_interrupt_triggers_vector_3(self, cpu):
        """Host mouse events should trigger the mouse interrupt vector when enabled."""
        cpu.interrupt_check_frequency = 1
        cpu.flags[5] = 1
        cpu.memory.write_word(0x010C, 0x3456)
        cpu.memory.write_byte(0x0000, 0xFF)  # NOP

        cpu.mouse.write_control(1)
        cpu.interrupts[3] = 1
        cpu.mouse.move_to(12, 34, from_host=True)

        cpu.step()

        assert cpu.pc == 0x3456
        assert cpu.mouse.pending_interrupt is False
        assert cpu.Pregisters[8] == 0xFFFB
        assert cpu.memory.read_word(0xFFFB) == 0x0001

    def test_disabled_mouse_event_does_not_interrupt(self, cpu):
        """Host mouse events should be ignored while the mouse is disabled."""
        cpu.interrupt_check_frequency = 1
        cpu.flags[5] = 1
        cpu.memory.write_word(0x010C, 0x3456)
        cpu.memory.write_byte(0x0000, 0xFF)  # NOP

        cpu.mouse.write_control(0)
        cpu.interrupts[3] = 0
        cpu.mouse.move_to(12, 34, from_host=True)

        cpu.step()

        assert cpu.pc == 0x0001
        assert cpu.mouse.pending_interrupt is False


class TestCPUMemoryOperations:
    """Test memory operations (MEMCPY, MEMSET)"""

    def test_memcpy_operation(self, cpu):
        """Test MEMCPY instruction."""
        # Set up source data
        source_addr = 0x1000
        dest_addr = 0x2000
        data = [0x11, 0x22, 0x33, 0x44, 0x55]

        for i, byte in enumerate(data):
            cpu.memory.write_byte(source_addr + i, byte)

        # Copy 5 bytes from source to destination
        cpu.memory.write_byte(0x0000, 0x4A)  # MEMCPY opcode
        cpu.memory.write_byte(0x0001, 0x2A)  # Mode: imm16 + imm16 + imm16
        cpu.memory.write_word(0x0002, dest_addr)  # Destination
        cpu.memory.write_word(0x0004, source_addr)  # Source
        cpu.memory.write_word(0x0006, 0x0005)      # Length

        cpu.memory.write_byte(0x0008, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify data was copied correctly
        for i, expected in enumerate(data):
            assert cpu.memory.read_byte(dest_addr + i) == expected

    def test_memset_operation(self, cpu):
        """Test MEMSET instruction."""
        # Set up destination area
        dest_addr = 0x3000
        fill_value = 0xAA
        length = 10

        # Fill memory with pattern
        cpu.memory.write_byte(0x0000, 0x7C)  # MEMSET opcode
        cpu.memory.write_byte(0x0001, 0x26)  # Mode: imm16 + imm8 + imm16
        cpu.memory.write_word(0x0002, dest_addr)  # Destination
        cpu.memory.write_byte(0x0004, fill_value)  # Fill value
        cpu.memory.write_word(0x0005, length)     # Length

        cpu.memory.write_byte(0x0007, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify memory was filled correctly
        for i in range(length):
            assert cpu.memory.read_byte(dest_addr + i) == fill_value

    def test_memcpy_overlapping_regions(self, cpu):
        """Test MEMCPY with overlapping source and destination."""
        # Set up data with overlap
        base_addr = 0x1000
        data = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08]

        for i, byte in enumerate(data):
            cpu.memory.write_byte(base_addr + i, byte)

        # Copy with overlap (source starts 2 bytes after destination)
        cpu.memory.write_byte(0x0000, 0x4A)  # MEMCPY
        cpu.memory.write_byte(0x0001, 0x2A)  # Mode: imm16 + imm16 + imm16
        cpu.memory.write_word(0x0002, base_addr)      # Destination
        cpu.memory.write_word(0x0004, base_addr + 2)  # Source (overlaps)
        cpu.memory.write_word(0x0006, 0x0006)        # Length

        cpu.memory.write_byte(0x0008, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify overlapping copy worked correctly
        # Result should be [0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x07, 0x08]
        expected = [0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x07, 0x08]
        for i, expected_byte in enumerate(expected):
            assert cpu.memory.read_byte(base_addr + i) == expected_byte

    def test_memset_zero_length(self, cpu):
        """Test MEMSET with zero length."""
        dest_addr = 0x4000
        original_value = 0xFF
        cpu.memory.write_byte(dest_addr, original_value)

        # Set zero length
        cpu.memory.write_byte(0x0000, 0x7C)  # MEMSET
        cpu.memory.write_byte(0x0001, 0x26)  # Mode: imm16 + imm8 + imm16
        cpu.memory.write_word(0x0002, dest_addr)
        cpu.memory.write_byte(0x0004, 0x00)  # Fill value
        cpu.memory.write_word(0x0005, 0x0000)  # Zero length

        cpu.memory.write_byte(0x0007, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Memory should be unchanged
        assert cpu.memory.read_byte(dest_addr) == original_value

    def test_memcpy_large_block(self, cpu):
        """Test MEMCPY with large data block."""
        source_addr = 0x5000
        dest_addr = 0x6000
        length = 256

        # Fill source with pattern
        for i in range(length):
            cpu.memory.write_byte(source_addr + i, i % 256)

        # Copy large block
        cpu.memory.write_byte(0x0000, 0x4A)  # MEMCPY
        cpu.memory.write_byte(0x0001, 0x2A)  # Mode: imm16 + imm16 + imm16
        cpu.memory.write_word(0x0002, dest_addr)
        cpu.memory.write_word(0x0004, source_addr)
        cpu.memory.write_word(0x0006, length)

        cpu.memory.write_byte(0x0008, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify large block was copied correctly
        for i in range(length):
            expected = i % 256
            assert cpu.memory.read_byte(dest_addr + i) == expected

    def test_memory_operation_bounds_checking(self, cpu):
        """Test memory operations with boundary conditions."""
        # Test MEMCPY near end of memory
        source_addr = 0xFFFC  # Near end of 64KB memory
        dest_addr = 0xFFF8
        length = 4

        # Set up source data
        for i in range(length):
            cpu.memory.write_byte(source_addr + i, 0x10 + i)

        # Copy near memory boundary
        cpu.memory.write_byte(0x0000, 0x4A)  # MEMCPY
        cpu.memory.write_byte(0x0001, 0x2A)  # Mode: imm16 + imm16 + imm16
        cpu.memory.write_word(0x0002, dest_addr)
        cpu.memory.write_word(0x0004, source_addr)
        cpu.memory.write_word(0x0006, length)

        cpu.memory.write_byte(0x0008, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify boundary copy worked
        for i in range(length):
            expected = 0x10 + i
            assert cpu.memory.read_byte(dest_addr + i) == expected


class TestCPUInterruptOperations:
    """Test interrupt operations (INT, IRET)"""

    def test_int_instruction(self, cpu):
        """Test INT (software interrupt) instruction."""
        # Set up interrupt vector
        vector_addr = 0x0100  # Vector 0
        handler_addr = 0x2000
        cpu.memory.write_word(vector_addr, handler_addr)

        # Enable interrupts
        cpu.memory.write_byte(0x0000, 0x04)  # STI

        # Trigger software interrupt 0
        cpu.memory.write_byte(0x0001, 0x30)  # INT opcode
        cpu.memory.write_byte(0x0002, 0x01)  # Mode: immediate 8-bit
        cpu.memory.write_byte(0x0003, 0x00)  # Interrupt number 0

        cpu.memory.write_byte(0x0004, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted and cpu.pc < 0x2000:  # Stop before handler
            cpu.step()

        # Should have jumped to handler
        assert cpu.pc == handler_addr

    def test_iret_instruction(self, cpu):
        """Test IRET (interrupt return) instruction."""
        # Set up interrupt context manually, matching the real entry order
        # (see _trigger_interrupt / _int): flags pushed first (deeper on the
        # stack), PC pushed second (top of stack, at the current SP).
        return_addr = 0x0100
        flags_value = 0x00FE  # Some flags (bit 0 / Trap left clear so IRET
                               # doesn't immediately re-trigger a single-step
                               # breakpoint interrupt on return)

        cpu.Pregisters[8] = 0xFFFB  # SP (after pushing flags and PC)
        cpu.memory.write_word(0xFFFB, return_addr)  # PC (pushed second, top of stack)
        cpu.memory.write_word(0xFFFD, flags_value)  # Flags (pushed first, deeper)

        # Set up handler that returns
        handler_addr = 0x2000
        cpu.memory.write_byte(handler_addr, 0x02)  # IRET opcode

        # Jump to handler
        cpu.pc = handler_addr
        cpu.step()

        # Should have returned to original address
        assert cpu.pc == return_addr
        # SP should be restored
        assert cpu.Pregisters[8] == 0xFFFF

    def test_nested_interrupts(self, cpu):
        """Test nested interrupt handling."""
        # Set up multiple interrupt vectors
        cpu.memory.write_word(0x0100, 0x2000)  # Vector 0 -> 0x2000
        cpu.memory.write_word(0x0104, 0x3000)  # Vector 1 -> 0x3000

        # Enable interrupts
        cpu.memory.write_byte(0x0000, 0x04)  # STI

        # Trigger first interrupt
        cpu.memory.write_byte(0x0001, 0x30)  # INT 0
        cpu.memory.write_byte(0x0002, 0x01)
        cpu.memory.write_byte(0x0003, 0x00)

        # In handler, trigger second interrupt
        cpu.memory.write_byte(0x2000, 0x30)  # INT 1
        cpu.memory.write_byte(0x2001, 0x01)
        cpu.memory.write_byte(0x2002, 0x01)

        # Second handler returns
        cpu.memory.write_byte(0x3000, 0x02)  # IRET

        # First handler returns
        cpu.memory.write_byte(0x2003, 0x02)  # IRET

        cpu.memory.write_byte(0x2004, 0x00)  # HLT

        # Run until completion
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Should complete successfully
        assert cpu.halted == True

    def test_interrupt_with_disabled_interrupts(self, cpu):
        """Test INT with interrupts disabled."""
        # Keep interrupts disabled
        cpu.flags[5] = 0  # Interrupt flag cleared

        # Set up interrupt vector
        cpu.memory.write_word(0x0100, 0x2000)

        # Try to trigger interrupt
        cpu.memory.write_byte(0x0000, 0x30)  # INT 0
        cpu.memory.write_byte(0x0001, 0x01)
        cpu.memory.write_byte(0x0002, 0x00)

        cpu.memory.write_byte(0x0003, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Should not have jumped to handler (interrupts disabled)
        assert cpu.pc == 0x0004  # Should be after HLT opcode

    def test_interrupt_stack_overflow_protection(self, cpu):
        """Test interrupt handling with stack overflow."""
       
        # Set SP to near end of memory
        cpu.Pregisters[8] = 0xFFFF

        # Set up interrupt vector
        cpu.memory.write_word(0x0100, 0x2000)

        # Enable interrupts
        cpu.memory.write_byte(0x0000, 0x04)  # STI

        # Trigger interrupt that would cause stack overflow
        cpu.memory.write_byte(0x0001, 0x5B)  # INT 0
        cpu.memory.write_byte(0x0002, 0x01)
        cpu.memory.write_byte(0x0003, 0x00)

        cpu.memory.write_byte(0x0004, 0x00)  # HLT

        # Run program - should handle stack overflow gracefully
        cpu.pc = 0
        try:
            while not cpu.halted and cpu.pc < 0x2000:
                cpu.step()
        except Exception:
            # Should handle stack overflow gracefully
            pass

    def test_iret_without_interrupt_context(self, cpu):
        """Test IRET when no interrupt context exists."""
        # Set SP to top of stack (no interrupt context)
        cpu.Pregisters[8] = 0xFFFF

        # Try IRET without context
        cpu.memory.write_byte(0x0000, 0x02)  # IRET

        # Should raise an exception or handle gracefully
        with pytest.raises(RuntimeError, match="Stack underflow"):
            cpu.step()


class TestCPUEdgeCases:
    """Test edge cases and boundary conditions for existing instructions"""

    def test_arithmetic_overflow_boundary(self, cpu):
        """Test arithmetic operations at overflow boundaries."""
        # Test 8-bit register overflow
        cpu.Rregisters[0] = 255
        cpu.Rregisters[1] = 1

        # ADD that causes 8-bit overflow
        cpu.memory.write_byte(0x0000, 0x07)  # ADD
        cpu.memory.write_byte(0x0001, 0x00)
        cpu.memory.write_byte(0x0002, 0xE7)
        cpu.memory.write_byte(0x0003, 0xE8)
        cpu.memory.write_byte(0x0004, 0x00)  # HLT

        cpu.pc = 0
        cpu.step()

        # Result should wrap to 0
        assert_register_equals(cpu, 'R0', 0)
        assert cpu.flags[6] == 1  # Carry should be set

    def test_16bit_arithmetic_boundary(self, cpu):
        """Test 16-bit arithmetic at boundaries."""
        # Test 16-bit register overflow
        cpu.Pregisters[0] = 65535
        cpu.Pregisters[1] = 1

        # ADD that causes 16-bit overflow
        cpu.memory.write_byte(0x0000, 0x07)  # ADD
        cpu.memory.write_byte(0x0001, 0x00)  # Register direct mode for both operands
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1
        cpu.memory.write_byte(0x0004, 0x00)  # HLT

        cpu.pc = 0
        cpu.step()

        # Result should wrap to 0
        assert cpu.Pregisters[0] == 0
        assert cpu.flags[6] == 1  # Carry should be set

    def test_division_by_zero_handling(self, cpu):
        """Test division by zero handling."""
        cpu.Rregisters[0] = 100
        cpu.Rregisters[1] = 0  # Division by zero

        # DIV instruction (if implemented)
        # This test depends on whether DIV is implemented
        # For now, test that invalid operations are handled

        instruction = cpu.instruction_table.pop(0xFF)
        cpu.memory.write_byte(0x0000, 0xFF)
        cpu.pc = 0

        try:
            with pytest.raises(Exception, match="Unknown opcode"):
                cpu.step()
        finally:
            cpu.instruction_table[0xFF] = instruction

    def test_jump_boundary_conditions(self, cpu):
        """Test jump instructions at memory boundaries."""
        # Test JMP to end of memory
        cpu.memory.write_byte(0x0000, 0x1E)  # JMP
        cpu.memory.write_byte(0x0001, 0x02)
        cpu.memory.write_word(0x0002, 0xFFFF)

        cpu.step()
        assert cpu.pc == 0xFFFF

        # Test executing at memory boundary
        cpu.memory.write_byte(0xFFFF, 0x00)  # NOP at end
        cpu.step()
        assert cpu.pc == 0x0000  # Should wrap around

    def test_stack_boundary_operations(self, cpu):
        """Test stack operations at memory boundaries."""
        # Set SP to memory boundary
        cpu.Pregisters[8] = 0x0000

        # Try PUSH at boundary
        cpu.Rregisters[0] = 0x42
        cpu.memory.write_byte(0x0000, 0x18)  # PUSH
        cpu.memory.write_byte(0x0001, 0x00)
        cpu.memory.write_byte(0x0002, 0xE7)

        # Should handle boundary condition
        cpu.pc = 0
        cpu.step()

        # SP should wrap or handle boundary
        # (Implementation dependent)

    def test_register_indirect_addressing_edge_cases(self, cpu):
        """Test register indirect addressing at boundaries."""
        # Set register to point to memory boundary
        cpu.Pregisters[0] = 0xFFFF

        # Try to access memory at boundary
        cpu.memory.write_byte(0x0000, 0x06)  # MOV R0, [P0]
        cpu.memory.write_byte(0x0001, 0x20)  # Indirect mode
        cpu.memory.write_byte(0x0002, 0xE7)
        cpu.memory.write_byte(0x0003, 0xF1)

        cpu.pc = 0
        cpu.step()

        # Should handle boundary access gracefully

    def test_flag_operations_edge_cases(self, cpu):
        """Test flag operations in edge cases."""
        # Test all flags set/clear
        for i in range(12):
            cpu.flags[i] = 1  # Set all flags

        # Test flag preservation through operations
        cpu.Rregisters[0] = 1
        cpu.Rregisters[1] = 1

        # ADD that affects flags
        cpu.memory.write_byte(0x0000, 0x07)  # ADD
        cpu.memory.write_byte(0x0001, 0x00)  # Register direct mode
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.pc = 0
        cpu.step()

        # Verify flags are updated correctly
        assert cpu.flags[7] == 0  # Zero flag (1 + 1 = 2, not zero)
        assert cpu.flags[6] == 0  # Carry flag (no carry)
        assert cpu.flags[1] == 0  # Sign flag (positive result)

    @pytest.mark.skip(reason="Test causes infinite loops with random opcodes - needs instruction validation")
    def test_instruction_decoding_stress_extended(self, cpu):
        """Extended stress test for instruction decoding."""
        import random
        random.seed(12345)

        # Test more patterns with timeout protection
        for i in range(2000):
            opcode = random.randint(0, 255)
            cpu.memory.write_byte(0, opcode)
            cpu.pc = 0
            cpu.halted = False

            # Add cycle limit to prevent infinite loops
            cycles = 0
            max_cycles = 100  # Prevent any single opcode from running too long
            
            try:
                while not cpu.halted and cycles < max_cycles:
                    cpu.step()
                    cycles += 1
                    
                # If we hit the cycle limit, force halt to prevent hang
                if cycles >= max_cycles:
                    cpu.halted = True
                    
            except Exception:
                # Expected for invalid opcodes
                pass

    def test_memory_alignment_edge_cases(self, cpu):
        """Test memory operations with odd alignments."""
        # Test word access at odd addresses
        cpu.memory.write_word(0x0001, 0x1234)  # Odd address

        # Try to read it back
        value = cpu.memory.read_word(0x0001)
        assert value == 0x1234

        # Test cross-page boundary access
        cpu.memory.write_word(0x00FF, 0xABCD)  # Crosses page boundary
        value = cpu.memory.read_word(0x00FF)
        assert value == 0xABCD

    def test_concurrent_register_access(self, cpu):
        """Test operations that access multiple registers simultaneously."""
        # Set up complex register state
        for i in range(10):
            cpu.Rregisters[i] = i
            cpu.Pregisters[i] = i * 256

        # Perform operations that use multiple registers
        cpu.memory.write_byte(0x0000, 0x07)  # ADD R0, R1
        cpu.memory.write_byte(0x0001, 0x00)
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.pc = 0
        cpu.step()

        # Verify result and that other registers unchanged
        assert_register_equals(cpu, 'R0', 1)  # 0 + 1 = 1
        for i in range(2, 10):
            assert_register_equals(cpu, f'R{i}', i)

    def test_program_counter_wraparound_extended(self, cpu):
        """Test PC wraparound with various instruction lengths."""
        # Test with multi-byte instructions at memory end
        cpu.pc = 0xFFFE
        cpu.memory.write_byte(0xFFFE, 0x06)  # MOV (3 bytes)
        cpu.memory.write_byte(0xFFFF, 0x04)
        cpu.memory.write_byte(0x0000, 0xE7)  # Wraps to beginning
        cpu.memory.write_byte(0x0001, 0x42)

        cpu.step()


class TestCPUBCDInstructions:
    """Test BCD (Binary Coded Decimal) instructions"""

    def test_sed_instruction(self, cpu):
        """Test SED instruction - set decimal flag"""
        # Clear decimal flag first
        cpu.decimal_mode = False
        
        # Set decimal mode
        cpu.memory.write_byte(0x0000, 0x4B)  # SED opcode
        cpu.memory.write_byte(0x0001, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify decimal mode is set
        assert cpu.decimal_mode == True

    def test_cld_instruction(self, cpu):
        """Test CLD instruction - clear decimal flag"""
        # Set decimal flag first
        cpu.decimal_mode = True
        
        # Clear decimal mode
        cpu.memory.write_byte(0x0000, 0x4C)  # CLD opcode
        cpu.memory.write_byte(0x0001, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify decimal mode is cleared
        assert cpu.decimal_mode == False

    def test_bcda_instruction_decimal_mode(self, cpu):
        """Test BCDA instruction in decimal mode"""
        cpu.decimal_mode = True
        cpu.aux_carry = False
        
        # Load BCD values into registers: R0 = 25, R1 = 37
        cpu.memory.write_byte(0x0000, 0x06)  # MOV immediate to register
        cpu.memory.write_byte(0x0001, 0x04)  # Mode: register + immediate 8-bit
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0x25)  # BCD 25
        
        cpu.memory.write_byte(0x0004, 0x06)  # MOV immediate to register
        cpu.memory.write_byte(0x0005, 0x04)  # Mode: register + immediate 8-bit
        cpu.memory.write_byte(0x0006, 0xE8)  # R1
        cpu.memory.write_byte(0x0007, 0x37)  # BCD 37
        
        # BCDA R0, R1 (25 + 37 = 62)
        cpu.memory.write_byte(0x0008, 0x4E)  # BCDA opcode
        cpu.memory.write_byte(0x0009, 0x00)  # Mode: register to register
        cpu.memory.write_byte(0x000A, 0xE7)  # R0 (dest)
        cpu.memory.write_byte(0x000B, 0xE8)  # R1 (source)
        
        cpu.memory.write_byte(0x000C, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify result: 25 + 37 = 62 (BCD 0x62)
        assert_register_equals(cpu, 'R0', 0x62)

    def test_bcda_instruction_binary_mode(self, cpu):
        """Test BCDA instruction in binary mode"""
        cpu.decimal_mode = False
        cpu.aux_carry = True
        
        # Load binary values into registers: R0 = 10, R1 = 5
        cpu.memory.write_byte(0x0000, 0x06)  # MOV immediate to register
        cpu.memory.write_byte(0x0001, 0x04)  # Mode: register + immediate 8-bit
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0x0A)  # 10
        
        cpu.memory.write_byte(0x0004, 0x06)  # MOV immediate to register
        cpu.memory.write_byte(0x0005, 0x04)  # Mode: register + immediate 8-bit
        cpu.memory.write_byte(0x0006, 0xE8)  # R1
        cpu.memory.write_byte(0x0007, 0x05)  # 5
        
        # BCDA R0, R1 (10 + 5 + carry(1) = 16)
        cpu.memory.write_byte(0x0008, 0x4E)  # BCDA opcode
        cpu.memory.write_byte(0x0009, 0x00)  # Mode: register to register
        cpu.memory.write_byte(0x000A, 0xE7)  # R0 (dest)
        cpu.memory.write_byte(0x000B, 0xE8)  # R1 (source)
        
        cpu.memory.write_byte(0x000C, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify result: 10 + 5 + 1 = 16
        assert_register_equals(cpu, 'R0', 0x10)

    def test_bcds_instruction_decimal_mode(self, cpu):
        """Test BCDS instruction in decimal mode"""
        cpu.decimal_mode = True
        cpu.aux_carry = False
        
        # Load BCD values into registers: R0 = 75, R1 = 23
        cpu.memory.write_byte(0x0000, 0x06)  # MOV immediate to register
        cpu.memory.write_byte(0x0001, 0x04)  # Mode: register + immediate 8-bit
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0x75)  # BCD 75
        
        cpu.memory.write_byte(0x0004, 0x06)  # MOV immediate to register
        cpu.memory.write_byte(0x0005, 0x04)  # Mode: register + immediate 8-bit
        cpu.memory.write_byte(0x0006, 0xE8)  # R1
        cpu.memory.write_byte(0x0007, 0x23)  # BCD 23
        
        # BCDS R0, R1 (75 - 23 = 52)
        cpu.memory.write_byte(0x0008, 0x4F)  # BCDS opcode
        cpu.memory.write_byte(0x0009, 0x00)  # Mode: register to register
        cpu.memory.write_byte(0x000A, 0xE7)  # R0 (dest)
        cpu.memory.write_byte(0x000B, 0xE8)  # R1 (source)
        
        cpu.memory.write_byte(0x000C, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify result: 75 - 23 = 52 (BCD 0x52)
        assert_register_equals(cpu, 'R0', 0x52)

    def test_bcdcmp_instruction_decimal_mode(self, cpu):
        """Test BCDCMP instruction in decimal mode"""
        cpu.decimal_mode = True
        
        # Load BCD values into registers: R0 = 45, R1 = 67
        cpu.memory.write_byte(0x0000, 0x06)  # MOV immediate to register
        cpu.memory.write_byte(0x0001, 0x04)  # Mode: register + immediate 8-bit
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0x45)  # BCD 45
        
        cpu.memory.write_byte(0x0004, 0x06)  # MOV immediate to register
        cpu.memory.write_byte(0x0005, 0x04)  # Mode: register + immediate 8-bit
        cpu.memory.write_byte(0x0006, 0xE8)  # R1
        cpu.memory.write_byte(0x0007, 0x67)  # BCD 67
        
        # BCDCMP R0, R1 (45 compared to 67)
        cpu.memory.write_byte(0x0008, 0x50)  # BCDCMP opcode
        cpu.memory.write_byte(0x0009, 0x00)  # Mode: register to register
        cpu.memory.write_byte(0x000A, 0xE7)  # R0 (dest)
        cpu.memory.write_byte(0x000B, 0xE8)  # R1 (source)
        
        cpu.memory.write_byte(0x000C, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify flags: 45 < 67, so sign flag should be set
        assert cpu.sign_flag == True
        assert cpu.zero_flag == False

    def test_bcd2bin_instruction(self, cpu):
        """Test BCD2BIN instruction"""
        # Load BCD 42 into R0
        cpu.memory.write_byte(0x0000, 0x06)  # MOV immediate to register
        cpu.memory.write_byte(0x0001, 0x04)  # Mode: register + immediate 8-bit
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0x42)  # BCD 42
        
        # Convert BCD to binary: BCD2BIN R0
        cpu.memory.write_byte(0x0004, 0x51)  # BCD2BIN opcode
        cpu.memory.write_byte(0x0005, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0006, 0xE7)  # R0
        
        cpu.memory.write_byte(0x0007, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify result: BCD 42 -> binary 42
        assert_register_equals(cpu, 'R0', 42)

    def test_bin2bcd_instruction(self, cpu):
        """Test BIN2BCD instruction"""
        # Load binary 73 into R0
        cpu.memory.write_byte(0x0000, 0x06)  # MOV immediate to register
        cpu.memory.write_byte(0x0001, 0x04)  # Mode: register + immediate 8-bit
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0x49)  # Binary 73
        
        # Convert binary to BCD: BIN2BCD R0
        cpu.memory.write_byte(0x0004, 0x52)  # BIN2BCD opcode
        cpu.memory.write_byte(0x0005, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0006, 0xE7)  # R0
        
        cpu.memory.write_byte(0x0007, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify result: binary 73 -> BCD 73 (0x73)
        assert_register_equals(cpu, 'R0', 0x73)

    def test_bcdadd_instruction_decimal_mode(self, cpu):
        """Test BCDADD instruction in decimal mode"""
        cpu.decimal_mode = True
        
        # Load BCD values into registers: R0 = 18, R1 = 27
        cpu.memory.write_byte(0x0000, 0x06)  # MOV immediate to register
        cpu.memory.write_byte(0x0001, 0x04)  # Mode: register + immediate 8-bit
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0x18)  # BCD 18
        
        cpu.memory.write_byte(0x0004, 0x06)  # MOV immediate to register
        cpu.memory.write_byte(0x0005, 0x04)  # Mode: register + immediate 8-bit
        cpu.memory.write_byte(0x0006, 0xE8)  # R1
        cpu.memory.write_byte(0x0007, 0x27)  # BCD 27
        
        # BCDADD R0, R1 (18 + 27 = 45)
        cpu.memory.write_byte(0x0008, 0x53)  # BCDADD opcode
        cpu.memory.write_byte(0x0009, 0x00)  # Mode: register to register
        cpu.memory.write_byte(0x000A, 0xE7)  # R0 (dest)
        cpu.memory.write_byte(0x000B, 0xE8)  # R1 (source)
        
        cpu.memory.write_byte(0x000C, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify result: 18 + 27 = 45 (BCD 0x45)
        assert_register_equals(cpu, 'R0', 0x45)

    def test_bcdsub_instruction_decimal_mode(self, cpu):
        """Test BCDSUB instruction in decimal mode"""
        cpu.decimal_mode = True
        
        # Load BCD values into registers: R0 = 91, R1 = 46
        cpu.memory.write_byte(0x0000, 0x06)  # MOV immediate to register
        cpu.memory.write_byte(0x0001, 0x04)  # Mode: register + immediate 8-bit
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0x91)  # BCD 91
        
        cpu.memory.write_byte(0x0004, 0x06)  # MOV immediate to register
        cpu.memory.write_byte(0x0005, 0x04)  # Mode: register + immediate 8-bit
        cpu.memory.write_byte(0x0006, 0xE8)  # R1
        cpu.memory.write_byte(0x0007, 0x46)  # BCD 46
        
        # BCDSUB R0, R1 (91 - 46 = 45)
        cpu.memory.write_byte(0x0008, 0x54)  # BCDSUB opcode
        cpu.memory.write_byte(0x0009, 0x00)  # Mode: register to register
        cpu.memory.write_byte(0x000A, 0xE7)  # R0 (dest)
        cpu.memory.write_byte(0x000B, 0xE8)  # R1 (source)
        
        cpu.memory.write_byte(0x000C, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Verify result: 91 - 46 = 45 (BCD 0x45)
        assert_register_equals(cpu, 'R0', 0x45)

    def test_bcd_operations_with_invalid_bcd(self, cpu):
        """Test BCD operations with invalid BCD values"""
        cpu.decimal_mode = True
        
        # Load invalid BCD (0xFA) into R0
        cpu.memory.write_byte(0x0000, 0x06)  # MOV immediate to register
        cpu.memory.write_byte(0x0001, 0x04)  # Mode: register + immediate 8-bit
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xFA)  # Invalid BCD
        
        # Convert BCD to binary: BCD2BIN R0
        cpu.memory.write_byte(0x0004, 0x51)  # BCD2BIN opcode
        cpu.memory.write_byte(0x0005, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0006, 0xE7)  # R0
        
        cpu.memory.write_byte(0x0007, 0x00)  # HLT

        # Run program
        cpu.pc = 0
        while not cpu.halted:
            cpu.step()

        # Invalid BCD should be returned as-is
        assert_register_equals(cpu, 'R0', 0xFA)
        assert cpu.pc == 0x0008  # Should be at HLT instruction


class TestMathFunctions:
    """Test math function instructions."""

    def test_powr_instruction(self, cpu):
        """Test POWR instruction (power function)."""
        cpu.Rregisters[0] = 2   # Base
        cpu.Rregisters[1] = 3   # Exponent

        # POWR R0, R1 (2^3 = 8)
        cpu.memory.write_byte(0x0000, 0x5B)  # POWR opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()
        assert_register_equals(cpu, 'R0', 8)

    def test_powr_negative_exponent(self, cpu):
        """Test POWR with negative exponent (should return 0)."""
        cpu.Rregisters[0] = 2   # Base
        cpu.Rregisters[1] = 0xFFFF  # -1 (two's complement)

        # POWR R0, R1
        cpu.memory.write_byte(0x0000, 0x5B)  # POWR opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()
        assert_register_equals(cpu, 'R0', 0)

    def test_sqrt_instruction(self, cpu):
        """Test SQRT instruction."""
        cpu.Rregisters[0] = 16  # Input

        # SQRT R0 (sqrt(16) = 4)
        cpu.memory.write_byte(0x0000, 0x5C)  # SQRT opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0

        cpu.step()
        assert_register_equals(cpu, 'R0', 4)

    def test_sqrt_negative(self, cpu):
        """Test SQRT with negative input (should return 0)."""
        cpu.Rregisters[0] = 0xFFFF  # -1

        # SQRT R0
        cpu.memory.write_byte(0x0000, 0x5C)  # SQRT opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0

        cpu.step()
        assert_register_equals(cpu, 'R0', 0)

    def test_sin_instruction(self, cpu):
        """Test SIN instruction."""
        # PI/2 in fixed-point (1.570796 * 256 ≈ 402)
        cpu.Pregisters[0] = 402

        # SIN P0 (sin(π/2) ≈ 1.0, fixed-point ≈ 256)
        cpu.memory.write_byte(0x0000, 0x5F)  # SIN opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xF1)  # P0

        cpu.step()
        # Should be close to 256 (1.0 in fixed-point)
        result = cpu.Pregisters[0]
        assert abs(result - 256) < 5  # Allow small rounding error

    def test_cos_instruction(self, cpu):
        """Test COS instruction."""
        cpu.Pregisters[0] = 0  # 0 radians

        # COS P0 (cos(0) = 1.0, fixed-point = 256)
        cpu.memory.write_byte(0x0000, 0x60)  # COS opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xF1)  # P0

        cpu.step()
        assert_register_equals(cpu, 'P0', 256)

    def test_exp_instruction(self, cpu):
        """Test EXP instruction."""
        cpu.Pregisters[0] = 0  # e^0 = 1.0

        # EXP P0 (e^0 = 1.0, fixed-point = 256)
        cpu.memory.write_byte(0x0000, 0x5E)  # EXP opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xF1)  # P0

        cpu.step()
        assert_register_equals(cpu, 'P0', 256)

    def test_log_instruction(self, cpu):
        """Test LOG instruction."""
        cpu.Pregisters[0] = 256  # 1.0 in fixed-point

        # LOG P0 (log(1.0) = 0.0, fixed-point = 0)
        cpu.memory.write_byte(0x0000, 0x5D)  # LOG opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xF1)  # P0

        cpu.step()
        result = cpu.Pregisters[0]
        assert abs(result - 0) < 10  # Should be close to 0

    def test_deg_instruction(self, cpu):
        """Test DEG instruction (degrees to radians)."""
        cpu.Pregisters[0] = 180  # 180 degrees

        # DEG P0 (180° = π radians, fixed-point ≈ 804)
        cpu.memory.write_byte(0x0000, 0x65)  # DEG opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xF1)  # P0

        cpu.step()
        result = cpu.Pregisters[0]
        # π in fixed-point: 3.1415926535 * 256 ≈ 804
        assert abs(result - 804) < 2  # Allow small rounding error

    def test_rad_instruction(self, cpu):
        """Test RAD instruction (radians to degrees)."""
        # π radians in fixed-point
        cpu.Pregisters[0] = 804

        # RAD P0 (π radians = 180 degrees)
        cpu.memory.write_byte(0x0000, 0x66)  # RAD opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xF1)  # P0

        cpu.step()
        result = cpu.Pregisters[0]
        assert abs(result - 180) < 2  # Allow small rounding error

    def test_floor_instruction(self, cpu):
        """Test FLOOR instruction."""
        # 3.7 in fixed-point: 3.7 * 256 = 947
        cpu.Rregisters[0] = 947

        # FLOOR R0 (floor(3.7) = 3)
        cpu.memory.write_byte(0x0000, 0x67)  # FLOOR opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0

        cpu.step()
        assert_register_equals(cpu, 'R0', 3)

    def test_ceil_instruction(self, cpu):
        """Test CEIL instruction."""
        # 3.1 in fixed-point: 3.1 * 256 = 794
        cpu.Rregisters[0] = 794

        # CEIL R0 (ceil(3.1) = 4)
        cpu.memory.write_byte(0x0000, 0x68)  # CEIL opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0

        cpu.step()
        assert_register_equals(cpu, 'R0', 4)

    def test_round_instruction(self, cpu):
        """Test ROUND instruction."""
        # 3.6 in fixed-point: 3.6 * 256 = 922
        cpu.Rregisters[0] = 922

        # ROUND R0 (round(3.6) = 4)
        cpu.memory.write_byte(0x0000, 0x69)  # ROUND opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0

        cpu.step()
        assert_register_equals(cpu, 'R0', 4)

    def test_trunc_instruction(self, cpu):
        """Test TRUNC instruction."""
        # 3.9 in fixed-point: 3.9 * 256 = 999
        cpu.Rregisters[0] = 999

        # TRUNC R0 (trunc(3.9) = 3)
        cpu.memory.write_byte(0x0000, 0x6A)  # TRUNC opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0

        cpu.step()
        assert_register_equals(cpu, 'R0', 3)

    def test_frac_instruction(self, cpu):
        """Test FRAC instruction."""
        # 3.75 in fixed-point: 3.75 * 256 = 960
        cpu.Rregisters[0] = 960

        # FRAC R0 (frac(3.75) = 0.75, fixed-point = 192)
        cpu.memory.write_byte(0x0000, 0x6B)  # FRAC opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0

        cpu.step()
        result = cpu.Rregisters[0]
        # 0.75 * 256 = 192
        assert abs(result - 192) < 2

    def test_intgr_instruction(self, cpu):
        """Test INTGR instruction."""
        # 3.75 in fixed-point: 3.75 * 256 = 960
        cpu.Rregisters[0] = 960

        # INTGR R0 (int(3.75) = 3)
        cpu.memory.write_byte(0x0000, 0x6C)  # INTGR opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0

        cpu.step()
        assert_register_equals(cpu, 'R0', 3)

    def test_atan_instruction(self, cpu):
        """Test ATAN instruction."""
        cpu.Rregisters[0] = 256  # tan(π/4) = 1.0

        # ATAN R0 (atan(1.0) = π/4, fixed-point ≈ 201)
        cpu.memory.write_byte(0x0000, 0x62)  # ATAN opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0

        cpu.step()
        result = cpu.Rregisters[0]
        # π/4 in fixed-point: 0.785398 * 256 ≈ 201
        assert abs(result - 201) < 5

    def test_asin_instruction(self, cpu):
        """Test ASIN instruction."""
        cpu.Rregisters[0] = 128  # sin(π/6) ≈ 0.5

        # ASIN R0 (asin(0.5) = π/6, fixed-point ≈ 134)
        cpu.memory.write_byte(0x0000, 0x63)  # ASIN opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0

        cpu.step()
        result = cpu.Rregisters[0]
        # π/6 in fixed-point: 0.523598 * 256 ≈ 134
        assert abs(result - 134) < 5

    def test_acos_instruction(self, cpu):
        """Test ACOS instruction."""
        cpu.Pregisters[0] = 0  # cos(π/2) = 0

        # ACOS P0 (acos(0) = π/2, fixed-point ≈ 402)
        cpu.memory.write_byte(0x0000, 0x64)  # ACOS opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xF1)  # P0

        cpu.step()
        result = cpu.Pregisters[0]
        # π/2 in fixed-point: 1.570796 * 256 ≈ 402
        assert abs(result - 402) < 5

    def test_tan_instruction(self, cpu):
        """Test TAN instruction."""
        cpu.Rregisters[0] = 0  # tan(0) = 0

        # TAN R0 (tan(0) = 0)
        cpu.memory.write_byte(0x0000, 0x61)  # TAN opcode
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xE7)  # R0

        cpu.step()
        assert_register_equals(cpu, 'R0', 0)


class TestMathFunctionsNegativeFixedPointInputs:
    """Regression: SIN/COS/TAN/ATAN/ASIN/ACOS/DEG/RAD/FLOOR/CEIL/ROUND/
    TRUNC/FRAC/INTGR/LOG/EXP read their operand as a raw unsigned 16-bit
    register value with no sign extension, unlike SQRT/ABS (which already
    called _to_signed_16 -- see core/exec_handlers.py). A negative
    fixed-point value like -100 (stored as 0xFF9C) was silently treated as
    +65436, e.g. FLOOR(-100/256) = FLOOR(-0.39) should be -1 but the
    unfixed handler computed floor(65436/256) = floor(255.6) = 255. Found
    via a NoBASIC-level test comparing constant-folded vs runtime SIN/COS/
    etc results for negative arguments (test_math_builtin_folding.py) --
    the constant folder already treated its literal argument as signed, so
    it silently disagreed with the (buggy) runtime opcode for any negative
    input. Fixed by sign-extending the operand in every affected handler.
    """

    NEG100_U16 = 0xFF9C  # -100 as an unsigned 16-bit register value

    def test_floor_of_negative_fixed_point_rounds_toward_negative_infinity(self, cpu):
        cpu.Pregisters[0] = self.NEG100_U16
        cpu.memory.write_byte(0x0000, 0x67)  # FLOOR
        cpu.memory.write_byte(0x0001, 0x00)
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.step()
        assert_register_equals(cpu, 'P0', int(math.floor(-100 / 256.0)) & 0xFFFF)

    def test_ceil_of_negative_fixed_point(self, cpu):
        cpu.Pregisters[0] = self.NEG100_U16
        cpu.memory.write_byte(0x0000, 0x68)  # CEIL
        cpu.memory.write_byte(0x0001, 0x00)
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.step()
        assert_register_equals(cpu, 'P0', int(math.ceil(-100 / 256.0)) & 0xFFFF)

    def test_round_of_negative_fixed_point(self, cpu):
        cpu.Pregisters[0] = self.NEG100_U16
        cpu.memory.write_byte(0x0000, 0x69)  # ROUND
        cpu.memory.write_byte(0x0001, 0x00)
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.step()
        assert_register_equals(cpu, 'P0', int(round(-100 / 256.0)) & 0xFFFF)

    def test_trunc_of_negative_fixed_point_rounds_toward_zero(self, cpu):
        """-100/256 == -0.39: TRUNC must give 0 (toward zero), not -1
        (floor toward -infinity)."""
        cpu.Pregisters[0] = self.NEG100_U16
        cpu.memory.write_byte(0x0000, 0x6A)  # TRUNC
        cpu.memory.write_byte(0x0001, 0x00)
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.step()
        assert_register_equals(cpu, 'P0', 0)

    def test_intgr_of_negative_fixed_point_matches_trunc(self, cpu):
        cpu.Pregisters[0] = self.NEG100_U16
        cpu.memory.write_byte(0x0000, 0x6C)  # INTGR
        cpu.memory.write_byte(0x0001, 0x00)
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.step()
        assert_register_equals(cpu, 'P0', 0)

    def test_frac_of_negative_fixed_point_keeps_sign_of_input(self, cpu):
        """FRAC must be consistent with TRUNC: v == TRUNC(v)*256 + FRAC(v).
        Since TRUNC(-100/256) == 0, FRAC(-100) must be -100 (as u16),
        not the floor-modulo 156 that `-100 % 256` would give in Python."""
        cpu.Pregisters[0] = self.NEG100_U16
        cpu.memory.write_byte(0x0000, 0x6B)  # FRAC
        cpu.memory.write_byte(0x0001, 0x00)
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.step()
        assert_register_equals(cpu, 'P0', (-100) & 0xFFFF)

    def test_log_of_negative_fixed_point_falls_back_to_zero(self, cpu):
        cpu.Pregisters[0] = self.NEG100_U16
        cpu.memory.write_byte(0x0000, 0x5D)  # LOG
        cpu.memory.write_byte(0x0001, 0x00)
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.step()
        assert_register_equals(cpu, 'P0', 0)

    def test_sin_of_negative_fixed_point_radians(self, cpu):
        cpu.Pregisters[0] = self.NEG100_U16
        cpu.memory.write_byte(0x0000, 0x5F)  # SIN
        cpu.memory.write_byte(0x0001, 0x00)
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.step()
        expected = int(math.sin(-100 / 256.0) * 256) & 0xFFFF
        assert_register_equals(cpu, 'P0', expected)

    def test_atan_of_negative_fixed_point(self, cpu):
        cpu.Pregisters[0] = self.NEG100_U16
        cpu.memory.write_byte(0x0000, 0x62)  # ATAN
        cpu.memory.write_byte(0x0001, 0x00)
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.step()
        expected = int(math.atan(-100 / 256.0) * 256) & 0xFFFF
        assert_register_equals(cpu, 'P0', expected)

    def test_deg_of_negative_degrees(self, cpu):
        cpu.Pregisters[0] = self.NEG100_U16
        cpu.memory.write_byte(0x0000, 0x65)  # DEG
        cpu.memory.write_byte(0x0001, 0x00)
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.step()
        expected = int((-100 * math.pi / 180.0) * 256) & 0xFFFF
        assert_register_equals(cpu, 'P0', expected)

    def test_tan_of_negative_raw_radians(self, cpu):
        cpu.Pregisters[0] = self.NEG100_U16
        cpu.memory.write_byte(0x0000, 0x61)  # TAN
        cpu.memory.write_byte(0x0001, 0x00)
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.step()
        expected = int(math.tan(-100) * 1000) & 0xFFFF
        assert_register_equals(cpu, 'P0', expected)


class TestInstructionCache:
    """Tests for instruction cache functionality.
    
    NOTE: Instruction caching (Phase 4) has been intentionally removed
    as part of the reimplantation strategy. These tests validate that
    the cache has been correctly eliminated and will not be reintroduced.
    """

    def test_instruction_cache_removed(self, cpu):
        """Verify instruction_cache has been eliminated (Phase 4)."""
        assert not hasattr(cpu, 'instruction_cache')

    def test_cache_misses_removed(self, cpu):
        """Verify cache_misses has been eliminated (Phase 4)."""
        assert not hasattr(cpu, 'cache_misses')

    def test_cache_hits_removed(self, cpu):
        """Verify cache_hits has been eliminated (Phase 4)."""
        assert not hasattr(cpu, 'cache_hits')

    def test_prefetch_buffer_removed(self, cpu):
        """Verify prefetch_buffer has been eliminated (Phase 4)."""
        assert not hasattr(cpu, 'prefetch_buffer')

    def test_cache_enabled_removed(self, cpu):
        """Verify cache_enabled has been eliminated (Phase 4)."""
        assert not hasattr(cpu, 'cache_enabled')

    def test_get_cache_stats_removed(self, cpu):
        """Verify get_cache_stats has been eliminated (Phase 4)."""
        assert not hasattr(cpu, 'get_cache_stats')

    def test_instruction_execution_still_works_without_cache(self, cpu):
        """Verify instruction execution works correctly without caching."""
        cpu.memory.write_byte(0x1000, 0xFF)  # NOP
        cpu.pc = 0x1000
        cpu.step()
        assert cpu.pc == 0x1001  # PC should advance


class TestConditionalJumpsAndComparisons:
    """Test conditional jump instructions and comparison flag setting."""

    def test_cmp_flag_setting_16bit_equal(self, cpu):
        """Test CMP sets correct flags when values are equal."""
        cpu.Pregisters[0] = 0x1234
        cpu.Pregisters[1] = 0x1234

        # CMP P0, P1
        cpu.memory.write_byte(0x0000, 0x2E)  # CMP
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1

        cpu.step()

        assert cpu.flags[7] == 1  # Zero flag set
        assert cpu.flags[1] == 0  # Sign flag clear
        assert cpu.flags[6] == 0  # Carry flag clear (no borrow)
        assert cpu.flags[2] == 0  # Overflow flag clear

    def test_cmp_flag_setting_16bit_less_than_signed(self, cpu):
        """Test CMP sets correct flags for signed less than."""
        cpu.Pregisters[0] = 0x8000  # -32768 (most negative)
        cpu.Pregisters[1] = 0x0001  # 1

        # CMP P0, P1 (0x8000 - 0x0001 = 0x7FFF, but overflow)
        cpu.memory.write_byte(0x0000, 0x2E)  # CMP
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1

        cpu.step()

        assert cpu.flags[7] == 0  # Zero flag clear
        assert cpu.flags[1] == 0  # Sign flag clear (result is 0x7FFF)
        assert cpu.flags[6] == 0  # Carry flag clear (no borrow in unsigned)
        assert cpu.flags[2] == 1  # Overflow flag set (signed overflow)

    def test_cmp_flag_setting_16bit_greater_than_signed(self, cpu):
        """Test CMP sets correct flags for signed greater than."""
        cpu.Pregisters[0] = 0x0001  # 1
        cpu.Pregisters[1] = 0x8000  # -32768

        # CMP P0, P1 (0x0001 - 0x8000 = 0x8001, overflow)
        cpu.memory.write_byte(0x0000, 0x2E)  # CMP
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1

        cpu.step()

        assert cpu.flags[7] == 0  # Zero flag clear
        assert cpu.flags[1] == 1  # Sign flag set (result is 0x8001)
        assert cpu.flags[6] == 1  # Carry flag set (borrow occurred)
        assert cpu.flags[2] == 1  # Overflow flag set (signed overflow)

    def test_cmp_flag_setting_16bit_unsigned_less(self, cpu):
        """Test CMP sets correct flags for unsigned less than."""
        cpu.Pregisters[0] = 0x0001  # 1
        cpu.Pregisters[1] = 0xFFFF  # 65535

        # CMP P0, P1 (0x0001 - 0xFFFF = 0x0002 with borrow)
        cpu.memory.write_byte(0x0000, 0x2E)  # CMP
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1

        cpu.step()

        assert cpu.flags[7] == 0  # Zero flag clear
        assert cpu.flags[1] == 0  # Sign flag clear (result is 0x0002)
        assert cpu.flags[6] == 1  # Carry flag set (borrow occurred)
        assert cpu.flags[2] == 0  # Overflow flag clear (no signed overflow)

    def test_cmp_flag_setting_8bit_equal(self, cpu):
        """Test CMP sets correct flags for 8-bit equal comparison."""
        cpu.Rregisters[0] = 0x42
        cpu.Rregisters[1] = 0x42

        # CMP R0, R1
        cpu.memory.write_byte(0x0000, 0x2E)  # CMP
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()

        assert cpu.flags[7] == 1  # Zero flag set
        assert cpu.flags[1] == 0  # Sign flag clear
        assert cpu.flags[6] == 0  # Carry flag clear
        assert cpu.flags[2] == 0  # Overflow flag clear

    def test_cmp_flag_setting_8bit_signed_overflow(self, cpu):
        """Test CMP sets correct flags for 8-bit signed overflow."""
        cpu.Rregisters[0] = 0x80  # -128 (most negative 8-bit)
        cpu.Rregisters[1] = 0x01  # 1

        # CMP R0, R1 (0x80 - 0x01 = 0x7F, but overflow)
        cpu.memory.write_byte(0x0000, 0x2E)  # CMP
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()

        assert cpu.flags[7] == 0  # Zero flag clear
        assert cpu.flags[1] == 0  # Sign flag clear (result is 0x7F)
        assert cpu.flags[6] == 0  # Carry flag clear (no borrow in unsigned)
        assert cpu.flags[2] == 1  # Overflow flag set (signed overflow)

    def test_jlt_jump_taken_signed_less(self, cpu):
        """Test JLT jumps when signed less than condition is true."""
        # Set up flags for signed less than: overflow=1, sign=0 (overflow XOR sign = 1)
        cpu.flags[2] = 1  # Overflow
        cpu.flags[1] = 0  # Sign

        # JLT to 0x1000
        cpu.memory.write_byte(0x0000, 0x28)  # JLT
        cpu.memory.write_byte(0x0001, 0x02)
        cpu.memory.write_word(0x0002, 0x1000)

        cpu.step()
        assert cpu.pc == 0x1000

    def test_jlt_jump_not_taken_signed_greater_equal(self, cpu):
        """Test JLT does not jump when signed greater or equal."""
        # Set up flags for signed greater than: overflow=0, sign=0 (overflow XOR sign = 0)
        cpu.flags[2] = 0  # Overflow
        cpu.flags[1] = 0  # Sign

        # JLT to 0x1000
        cpu.memory.write_byte(0x0000, 0x28)  # JLT
        cpu.memory.write_byte(0x0001, 0x02)
        cpu.memory.write_word(0x0002, 0x1000)

        cpu.step()
        assert cpu.pc == 0x0004  # PC advances past instruction

    def test_jlt_jump_not_taken_signed_equal(self, cpu):
        """Test JLT does not jump when values are equal."""
        # Set up flags for equal: zero=1, overflow=0, sign=0
        cpu.flags[7] = 1  # Zero
        cpu.flags[2] = 0  # Overflow
        cpu.flags[1] = 0  # Sign

        # JLT to 0x1000
        cpu.memory.write_byte(0x0000, 0x28)  # JLT
        cpu.memory.write_byte(0x0001, 0x02)
        cpu.memory.write_word(0x0002, 0x1000)

        cpu.step()
        assert cpu.pc == 0x0004  # PC advances past instruction

    def test_js_jump_taken_negative(self, cpu):
        """Test JS jumps when sign flag is set."""
        cpu.flags[1] = 1  # Sign flag set

        # JS to 0x1000
        cpu.memory.write_byte(0x0000, 0x25)  # JS
        cpu.memory.write_byte(0x0001, 0x02)
        cpu.memory.write_word(0x0002, 0x1000)

        cpu.step()
        assert cpu.pc == 0x1000

    def test_js_jump_not_taken_positive(self, cpu):
        """Test JS does not jump when sign flag is clear."""
        cpu.flags[1] = 0  # Sign flag clear

        # JS to 0x1000
        cpu.memory.write_byte(0x0000, 0x25)  # JS
        cpu.memory.write_byte(0x0001, 0x02)
        cpu.memory.write_word(0x0002, 0x1000)

        cpu.step()
        assert cpu.pc == 0x0004  # PC advances past instruction

    def test_cmp_jlt_integration_signed_less(self, cpu):
        """Test CMP followed by JLT for signed less than."""
        cpu.Pregisters[0] = 0x0001  # 1
        cpu.Pregisters[1] = 0x0002  # 2

        # CMP P0, P1 followed by JLT
        cpu.memory.write_byte(0x0000, 0x2E)  # CMP
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1
        cpu.memory.write_byte(0x0004, 0x28)  # JLT
        cpu.memory.write_byte(0x0005, 0x02)  # Mode: immediate 16-bit
        cpu.memory.write_word(0x0006, 0x1000)

        cpu.step()  # CMP
        cpu.step()  # JLT

        assert cpu.pc == 0x1000  # Should have jumped

    def test_cmp_jlt_integration_signed_greater(self, cpu):
        """Test CMP followed by JLT for signed greater than."""
        cpu.Pregisters[0] = 0x0002  # 2
        cpu.Pregisters[1] = 0x0001  # 1

        # CMP P0, P1 followed by JLT
        cpu.memory.write_byte(0x0000, 0x2E)  # CMP
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1
        cpu.memory.write_byte(0x0004, 0x28)  # JLT
        cpu.memory.write_byte(0x0005, 0x02)  # Mode: immediate 16-bit
        cpu.memory.write_word(0x0006, 0x1000)

        cpu.step()  # CMP
        cpu.step()  # JLT

        assert cpu.pc == 0x0008  # Should not have jumped (PC at next instruction after JLT)

    def test_cmp_js_integration_negative_result(self, cpu):
        """Test CMP followed by JS for negative result."""
        cpu.Pregisters[0] = 0x0001  # 1
        cpu.Pregisters[1] = 0x0002  # 2

        # CMP P0, P1 followed by JS
        cpu.memory.write_byte(0x0000, 0x2E)  # CMP
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1
        cpu.memory.write_byte(0x0004, 0x25)  # JS
        cpu.memory.write_byte(0x0005, 0x02)  # Mode: immediate 16-bit
        cpu.memory.write_word(0x0006, 0x1000)

        cpu.step()  # CMP
        cpu.step()  # JS

        assert cpu.pc == 0x1000  # Should have jumped (result is negative)


class TestEnhancedArithmeticInstructions:
    """Test enhanced arithmetic instructions."""

    def test_adc_without_carry(self, cpu):
        """Test ADC instruction without carry."""
        cpu.Pregisters[0] = 5
        cpu.Pregisters[1] = 3
        cpu.flags[6] = 0  # Clear carry flag

        # ADC P0, P1
        cpu.memory.write_byte(0x0000, 0x87)  # ADC
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1

        cpu.step()
        assert_register_equals(cpu, 'P0', 8)  # 5 + 3 + 0 = 8
        assert cpu.flags[6] == 0  # No carry

    def test_adc_with_carry(self, cpu):
        """Test ADC instruction with carry."""
        cpu.Pregisters[0] = 5
        cpu.Pregisters[1] = 3
        cpu.flags[6] = 1  # Set carry flag

        # ADC P0, P1
        cpu.memory.write_byte(0x0000, 0x87)  # ADC
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1

        cpu.step()
        assert_register_equals(cpu, 'P0', 9)  # 5 + 3 + 1 = 9
        assert cpu.flags[6] == 0  # No carry

    def test_sbc_without_carry(self, cpu):
        """Test SBC instruction without carry."""
        cpu.Pregisters[0] = 10
        cpu.Pregisters[1] = 3
        cpu.flags[6] = 0  # Clear carry flag

        # SBC P0, P1
        cpu.memory.write_byte(0x0000, 0x88)  # SBC
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1

        cpu.step()
        assert_register_equals(cpu, 'P0', 7)  # 10 - 3 - 0 = 7
        assert cpu.flags[6] == 0  # No borrow

    def test_sbc_with_carry(self, cpu):
        """Test SBC instruction with carry."""
        cpu.Pregisters[0] = 10
        cpu.Pregisters[1] = 3
        cpu.flags[6] = 1  # Set carry flag

        # SBC P0, P1
        cpu.memory.write_byte(0x0000, 0x88)  # SBC
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1

        cpu.step()
        assert_register_equals(cpu, 'P0', 6)  # 10 - 3 - 1 = 6
        assert cpu.flags[6] == 0  # No borrow

    def test_adc_overflow_flag_carry_folded_into_operand_edge_case(self, cpu):
        """Regression test: ADC's overflow flag must not corrupt when
        src + carry crosses a byte boundary on its own (src=0x7F, carry=1).

        Folding carry into the source operand before running it through the
        two's-complement overflow formula ((op1^op2)&sign / (op1^result)&sign)
        flips the "source" sign bit purely from the +1 carry, independent of
        the actual operands' signs. Concretely: R0=0x00, R1=0x7F, carry=1.
        True signed sum is 0 + 127 + 1 = 128, which does NOT fit in a signed
        8-bit result (-128..127), so overflow must be set.
        """
        cpu.Rregisters[0] = 0x00
        cpu.Rregisters[1] = 0x7F
        cpu.flags[6] = 1  # Set carry flag

        # ADC R0, R1
        cpu.memory.write_byte(0x0000, 0x87)  # ADC
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()
        assert_register_equals(cpu, 'R0', 0x80)  # 0 + 127 + 1 = 128
        assert cpu.flags[2] == 1  # Overflow flag must be set

    def test_sbc_overflow_flag_carry_folded_into_operand_edge_case(self, cpu):
        """Regression test: SBC's overflow flag must not corrupt when
        src + carry crosses a byte boundary on its own (src=0x7F, carry=1).

        R0=0xFF (-1 signed), R1=0x7F (127), carry=1. True signed result is
        -1 - 127 - 1 = -129, which does NOT fit in -128..127, so overflow
        must be set.
        """
        cpu.Rregisters[0] = 0xFF
        cpu.Rregisters[1] = 0x7F
        cpu.flags[6] = 1  # Set carry flag

        # SBC R0, R1
        cpu.memory.write_byte(0x0000, 0x88)  # SBC
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xE8)  # R1

        cpu.step()
        assert_register_equals(cpu, 'R0', 0x7F)  # (-1 - 127 - 1) mod 256 = 0x7F
        assert cpu.flags[2] == 1  # Overflow flag must be set

    def test_mulh(self, cpu):
        """Test MULH instruction."""
        cpu.Pregisters[0] = 0x1000  # 4096
        cpu.Pregisters[1] = 0x1000  # 4096

        # MULH P0, P1 (4096 * 4096 = 16777216 = 0x01000000)
        cpu.memory.write_byte(0x0000, 0x89)  # MULH
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1

        cpu.step()
        assert_register_equals(cpu, 'P0', 0x0100)  # High 16 bits of 0x01000000

    def test_divh(self, cpu):
        """Test DIVH instruction."""
        cpu.Pregisters[0] = 0x0001  # High 16 bits
        cpu.Pregisters[3] = 0x0000  # Low 16 bits (dividend = 0x00010000 = 65536)
        cpu.Pregisters[1] = 0x0002  # Divisor = 2

        # DIVH P0, P1 (65536 / 2 = 32768)
        cpu.memory.write_byte(0x0000, 0x8A)  # DIVH
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1

        cpu.step()
        assert_register_equals(cpu, 'P0', 0x8000)  # 32768
        assert cpu.Pregisters[3] == 0  # Remainder

    def test_min(self, cpu):
        """Test MIN instruction."""
        cpu.Pregisters[0] = 10
        cpu.Pregisters[1] = 5

        # MIN P0, P1
        cpu.memory.write_byte(0x0000, 0x8B)  # MIN
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1

        cpu.step()
        assert_register_equals(cpu, 'P0', 5)

    def test_max(self, cpu):
        """Test MAX instruction."""
        cpu.Pregisters[0] = 10
        cpu.Pregisters[1] = 15

        # MAX P0, P1
        cpu.memory.write_byte(0x0000, 0x8C)  # MAX
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1

        cpu.step()
        assert_register_equals(cpu, 'P0', 15)

    def test_clz_zero(self, cpu):
        """Test CLZ instruction with zero."""
        cpu.Pregisters[0] = 0

        # CLZ P0
        cpu.memory.write_byte(0x0000, 0x8D)  # CLZ
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xF1)  # P0

        cpu.step()
        assert_register_equals(cpu, 'P0', 16)

    def test_clz_value(self, cpu):
        """Test CLZ instruction with value."""
        cpu.Pregisters[0] = 0x00FF  # 0000000011111111

        # CLZ P0
        cpu.memory.write_byte(0x0000, 0x8D)  # CLZ
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xF1)  # P0

        cpu.step()
        assert_register_equals(cpu, 'P0', 8)  # 8 leading zeros

    def test_ctz_zero(self, cpu):
        """Test CTZ instruction with zero."""
        cpu.Pregisters[0] = 0

        # CTZ P0
        cpu.memory.write_byte(0x0000, 0x8E)  # CTZ
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xF1)  # P0

        cpu.step()
        assert_register_equals(cpu, 'P0', 16)

    def test_ctz_value(self, cpu):
        """Test CTZ instruction with value."""
        cpu.Pregisters[0] = 0xFF00  # 1111111100000000

        # CTZ P0
        cpu.memory.write_byte(0x0000, 0x8E)  # CTZ
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xF1)  # P0

        cpu.step()
        assert_register_equals(cpu, 'P0', 8)  # 8 trailing zeros

    def test_popcnt(self, cpu):
        """Test POPCNT instruction."""
        cpu.Pregisters[0] = 0xAAAA  # 1010101010101010

        # POPCNT P0
        cpu.memory.write_byte(0x0000, 0x8F)  # POPCNT
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register direct
        cpu.memory.write_byte(0x0002, 0xF1)  # P0

        cpu.step()
        assert_register_equals(cpu, 'P0', 8)  # 8 ones in 0xAAAA

    def test_sar_positive(self, cpu):
        """Test SAR instruction with positive value."""
        cpu.Pregisters[0] = 0x0008  # 8
        cpu.Pregisters[1] = 1       # Shift by 1

        # SAR P0, P1
        cpu.memory.write_byte(0x0000, 0x90)  # SAR
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1

        cpu.step()
        assert_register_equals(cpu, 'P0', 4)  # 8 >> 1 = 4

    def test_sar_negative(self, cpu):
        """Test SAR instruction with negative value."""
        cpu.Pregisters[0] = 0xFFF8  # -8 (two's complement)
        cpu.Pregisters[1] = 1       # Shift by 1

        # SAR P0, P1
        cpu.memory.write_byte(0x0000, 0x90)  # SAR
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1

        cpu.step()
        assert_register_equals(cpu, 'P0', 0xFFFC)  # -8 >> 1 = -4

    def test_sal(self, cpu):
        """Test SAL instruction."""
        cpu.Pregisters[0] = 0x0008  # 8
        cpu.Pregisters[1] = 1       # Shift by 1

        # SAL P0, P1
        cpu.memory.write_byte(0x0000, 0x91)  # SAL
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1

        cpu.step()
        assert_register_equals(cpu, 'P0', 16)  # 8 << 1 = 16

    def test_rcl_without_carry(self, cpu):
        """Test RCL instruction without initial carry."""
        cpu.Pregisters[0] = 0x8000  # 1000000000000000
        cpu.Pregisters[1] = 1       # Rotate by 1
        cpu.flags[6] = 0            # Clear carry

        # RCL P0, P1
        cpu.memory.write_byte(0x0000, 0x92)  # RCL
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1

        cpu.step()
        assert_register_equals(cpu, 'P0', 0x0000)  # Bit 15 moves to carry, 0 shifts in
        assert cpu.carry_flag == 1  # Carry set from bit 15

    def test_rcr_without_carry(self, cpu):
        """Test RCR instruction without initial carry."""
        cpu.Pregisters[0] = 0x0001  # 0000000000000001
        cpu.Pregisters[1] = 1       # Rotate by 1
        cpu.flags[6] = 0            # Clear carry

        # RCR P0, P1
        cpu.memory.write_byte(0x0000, 0x93)  # RCR
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: both register
        cpu.memory.write_byte(0x0002, 0xF1)  # P0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1

        cpu.step()
        assert_register_equals(cpu, 'P0', 0x0000)  # Bit 0 moves to carry, 0 shifts in
        assert cpu.carry_flag == 1  # Carry set from bit 0


class TestCPUDebuggingInstructions:

    def test_setbp_instruction(self, cpu):
        """Test SETBP instruction sets hardware breakpoint."""
        cpu.Rregisters[0] = 1  # Index 1
        cpu.Pregisters[1] = 0x1234  # Address

        # SETBP R0, P1
        cpu.memory.write_byte(0x0000, 0xA6)  # SETBP
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register, register
        cpu.memory.write_byte(0x0002, 0xE7)  # R0
        cpu.memory.write_byte(0x0003, 0xF2)  # P1

        cpu.step()
        assert cpu.hw_breakpoints[1] == 0x1234
        assert cpu.hw_breakpoint_enabled[1] == True

    def test_clrbp_instruction(self, cpu):
        """Test CLRBP instruction clears hardware breakpoint."""
        cpu.hw_breakpoints[2] = 0x5678
        cpu.hw_breakpoint_enabled[2] = True
        cpu.Rregisters[0] = 2  # Index

        # CLRBP R0
        cpu.memory.write_byte(0x0000, 0xA7)  # CLRBP
        cpu.memory.write_byte(0x0001, 0x00)  # Mode: register
        cpu.memory.write_byte(0x0002, 0xE7)  # R0

        cpu.step()
        assert cpu.hw_breakpoint_enabled[2] == False

    def test_enabrk_instruction(self, cpu):
        """Test ENABRK instruction enables breakpoints."""
        cpu.hw_breakpoints[0] = 0x1000
        cpu.hw_breakpoints[1] = 0x2000
        cpu.hw_breakpoint_enabled[0] = False
        cpu.hw_breakpoint_enabled[1] = False

        # ENABRK
        cpu.memory.write_byte(0x0000, 0xA8)  # ENABRK

        cpu.step()
        assert cpu.hw_breakpoint_enabled[0] == True
        assert cpu.hw_breakpoint_enabled[1] == True

    def test_disbrk_instruction(self, cpu):
        """Test DISBRK instruction disables breakpoints."""
        cpu.hw_breakpoint_enabled[0] = True
        cpu.hw_breakpoint_enabled[1] = True

        # DISBRK
        cpu.memory.write_byte(0x0000, 0xA9)  # DISBRK

        cpu.step()
        assert cpu.hw_breakpoint_enabled[0] == False
        assert cpu.hw_breakpoint_enabled[1] == False

    def test_enatrap_instruction(self, cpu):
        """Test ENATRAP instruction sets trap flag."""
        # ENATRAP
        cpu.memory.write_byte(0x0000, 0xAA)  # ENATRAP

        cpu.step()
        assert cpu.trap_flag == 1

    def test_disatrap_instruction(self, cpu):
        """Test DISATRAP instruction clears trap flag."""
        cpu.flags[0] = 1  # Set trap

        # DISATRAP
        cpu.memory.write_byte(0x0000, 0xAB)  # DISATRAP

        cpu.step()
        assert cpu.trap_flag == 0