"""
Unit tests for Nova-16 bit instructions.
"""

import pytest
import numpy as np
from tests.conftest import assert_register_equals, run_cpu_cycles


class TestBitInstructions:
    """Test bit manipulation instructions."""

    def test_and_instruction(self, cpu, memory):
        """Test AND instruction with register operands."""
        # Load test program: MOV R0, 0xAA; MOV R1, 0x55; AND R0, R1
        program = [
            0x06, 0x08, 0xE7, 0x00, 0xAA,  # MOV R0, 0xAA
            0x06, 0x04, 0xE8, 0x55,        # MOV R1, 0x55
            0x10, 0x00, 0xE7, 0xE8,        # AND R0, R1
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        
        # R0 should be 0xAA & 0x55 = 0x00
        assert cpu.Rregisters[0] == 0x00
        assert cpu.zero_flag == True

    def test_or_instruction(self, cpu, memory):
        """Test OR instruction with register operands."""
        # Load test program: MOV R0, 0xAA; MOV R1, 0x55; OR R0, R1
        program = [
            0x06, 0x08, 0xE7, 0x00, 0xAA,  # MOV R0, 0xAA
            0x06, 0x04, 0xE8, 0x55,        # MOV R1, 0x55
            0x11, 0x00, 0xE7, 0xE8,        # OR R0, R1
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        
        # R0 should be 0xAA | 0x55 = 0xFF
        assert cpu.Rregisters[0] == 0xFF
        assert cpu.zero_flag == False

    def test_xor_instruction(self, cpu, memory):
        """Test XOR instruction with register operands."""
        # Load test program: MOV R0, 0xAA; MOV R1, 0x55; XOR R0, R1
        program = [
            0x06, 0x08, 0xE7, 0x00, 0xAA,  # MOV R0, 0xAA
            0x06, 0x04, 0xE8, 0x55,        # MOV R1, 0x55
            0x12, 0x00, 0xE7, 0xE8,        # XOR R0, R1
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        
        # R0 should be 0xAA ^ 0x55 = 0xFF
        assert cpu.Rregisters[0] == 0xFF
        assert cpu.zero_flag == False

    def test_not_instruction(self, cpu, memory):
        """Test NOT instruction."""
        # Load test program: MOV R0, 0xAA; NOT R0
        program = [
            0x06, 0x08, 0xE7, 0x00, 0xAA,  # MOV R0, 0xAA
            0x13, 0x00, 0xE7,              # NOT R0
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 3)
        
        # R0 should be ~0xAA = 0x55 (8-bit)
        assert cpu.Rregisters[0] == 0x55
        assert cpu.zero_flag == False

    def test_shl_instruction(self, cpu, memory):
        """Test SHL instruction."""
        # Load test program: MOV R0, 0x0F; MOV R1, 4; SHL R0, R1
        program = [
            0x06, 0x04, 0xE7, 0x0F,        # MOV R0, 0x0F
            0x06, 0x04, 0xE8, 0x04,        # MOV R1, 4
            0x14, 0x00, 0xE7, 0xE8,        # SHL R0, R1
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        
        # R0 should be 0x0F << 4 = 0xF0
        assert cpu.Rregisters[0] == 0xF0
        assert cpu.zero_flag == False

    def test_shr_instruction(self, cpu, memory):
        """Test SHR instruction."""
        # Load test program: MOV R0, 0xF0; MOV R1, 4; SHR R0, R1
        program = [
            0x06, 0x08, 0xE7, 0x00, 0xF0,  # MOV R0, 0xF0
            0x06, 0x04, 0xE8, 0x04,        # MOV R1, 4
            0x15, 0x00, 0xE7, 0xE8,        # SHR R0, R1
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        
        # R0 should be 0xF0 >> 4 = 0x0F
        assert cpu.Rregisters[0] == 0x0F
        assert cpu.zero_flag == False

    def test_rol_instruction(self, cpu, memory):
        """Test ROL instruction."""
        # Load test program: MOV R0, 0xAA; MOV R1, 1; ROL R0, R1
        program = [
            0x06, 0x08, 0xE7, 0x00, 0xAA,  # MOV R0, 0xAA
            0x06, 0x04, 0xE8, 0x01,        # MOV R1, 1
            0x16, 0x00, 0xE7, 0xE8,        # ROL R0, R1
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        
        # R0 should be ROL(0xAA, 1) = 0x55 (8-bit rotate)
        assert cpu.Rregisters[0] == 0x55
        assert cpu.zero_flag == False

    def test_ror_instruction(self, cpu, memory):
        """Test ROR instruction."""
        # Load test program: MOV R0, 0x55; MOV R1, 2; ROR R0, R1
        program = [
            0x06, 0x04, 0xE7, 0x55,        # MOV R0, 0x55
            0x06, 0x04, 0xE8, 0x02,        # MOV R1, 2
            0x17, 0x00, 0xE7, 0xE8,        # ROR R0, R1
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        
        # R0 should be ROR(0x55, 2) = 0x55 (8-bit rotate)
        assert cpu.Rregisters[0] == 0x55
        assert cpu.zero_flag == False

    def test_btst_instruction(self, cpu, memory):
        """Test BTST instruction."""
        # Load test program: MOV R0, 0xAA; BTST R0, 1
        program = [
            0x06, 0x08, 0xE7, 0x00, 0xAA,  # MOV R0, 0xAA
            0x6D, 0x04, 0xE7, 0x01,        # BTST R0, 1
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 3)
        
        # Bit 1 of 0xAA (10101010) is 1, so Z should be 0
        assert cpu.zero_flag == False

    def test_bset_instruction(self, cpu, memory):
        """Test BSET instruction."""
        # Load test program: MOV R0, 0x00; MOV R1, 0; BSET R0, R1
        program = [
            0x06, 0x04, 0xE7, 0x00,        # MOV R0, 0x00
            0x06, 0x04, 0xE8, 0x00,        # MOV R1, 0
            0x6E, 0x00, 0xE7, 0xE8,        # BSET R0, R1
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        
        # R0 should be 0x01 (bit 0 set)
        assert cpu.Rregisters[0] == 0x01
        assert cpu.zero_flag == False

    def test_bclr_instruction(self, cpu, memory):
        """Test BCLR instruction."""
        # Load test program: MOV R0, 0xFF; MOV R1, 0; BCLR R0, R1
        program = [
            0x06, 0x08, 0xE7, 0x00, 0xFF,  # MOV R0, 0xFF
            0x06, 0x04, 0xE8, 0x00,        # MOV R1, 0
            0x6F, 0x00, 0xE7, 0xE8,        # BCLR R0, R1
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        
        # R0 should be 0xFE (bit 0 cleared)
        assert cpu.Rregisters[0] == 0xFE
        assert cpu.zero_flag == False

    def test_bflip_instruction(self, cpu, memory):
        """Test BFLIP instruction."""
        # Load test program: MOV R0, 0xAA; MOV R1, 0; BFLIP R0, R1
        program = [
            0x06, 0x08, 0xE7, 0x00, 0xAA,  # MOV R0, 0xAA
            0x06, 0x04, 0xE8, 0x00,        # MOV R1, 0
            0x70, 0x00, 0xE7, 0xE8,        # BFLIP R0, R1
            0x00                             # HLT
        ]
        memory.load_program(program)
        run_cpu_cycles(cpu, 4)
        
        # R0 should be 0xAB (bit 0 of 0xAA flipped from 0 to 1)
        assert cpu.Rregisters[0] == 0xAB
        assert cpu.zero_flag == False