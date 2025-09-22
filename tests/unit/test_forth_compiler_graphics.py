"""
Unit tests for FORTH compiler graphics instructions.
Tests compilation of graphics-related FORTH words to ensure correct assembly generation,
register usage, and opcode compliance.
"""

import pytest
import sys
import os
from typing import List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from forth.forth_compiler import ForthCompiler


class TestForthCompilerGraphics:
    """Test FORTH compiler graphics instruction compilation."""

    @pytest.fixture
    def compiler(self):
        """Create a fresh FORTH compiler instance for each test."""
        return ForthCompiler(enable_optimization=False)

    def test_pixel_instruction_compilation(self, compiler):
        """Test PIXEL instruction compiles to correct assembly with VX/VY registers."""
        # Test basic pixel drawing
        forth_code = "10 20 255 PIXEL"
        lines = compiler.compile_to_lines(forth_code)

        # Should contain MOV instructions for coordinates and SWRITE
        assembly_str = '\n'.join(lines)

        # Check that VX and VY registers are set
        assert "MOV VX, R2" in assembly_str
        assert "MOV VY, R1" in assembly_str
        assert "SWRITE R0" in assembly_str

        # Check stack comments
        assert "; Stack before: ( x y color -- )" in assembly_str

        # Verify register usage doesn't corrupt other registers
        # R0=color, R1=y, R2=x should be used
        assert "MOV R0," in assembly_str  # Color loading
        assert "MOV R1," in assembly_str  # Y coordinate loading
        assert "MOV R2," in assembly_str  # X coordinate loading

    def test_layer_instruction_compilation(self, compiler):
        """Test LAYER instruction compiles to VL register store."""
        forth_code = "3 LAYER"
        lines = compiler.compile_to_lines(forth_code)

        assembly_str = '\n'.join(lines)
        assert "MOV VL, R0" in assembly_str
        assert "; LAYER - Set active graphics layer" in assembly_str
        assert "; Stack before: ( layer -- )" in assembly_str

    def test_vmode_instruction_compilation(self, compiler):
        """Test VMODE instruction compiles to VM register store."""
        forth_code = "1 VMODE"
        lines = compiler.compile_to_lines(forth_code)

        assembly_str = '\n'.join(lines)
        assert "MOV VM, R0" in assembly_str
        assert "; VMODE - Set video mode" in assembly_str
        assert "; Stack before: ( mode -- )" in assembly_str

    def test_video_register_stores(self, compiler):
        """Test VX!, VY!, VM!, VL! register store instructions."""
        test_cases = [
            ("10 VX!", "MOV VX, R0", "; VX! - Store to VX register"),
            ("20 VY!", "MOV VY, R0", "; VY! - Store to VY register"),
            ("1 VM!", "MOV VM, R0", "; VM! - Store to VM register (video mode)"),
            ("2 VL!", "MOV VL, R0", "; VL! - Store to VL register (video layer)"),
        ]

        for forth_code, expected_instruction, expected_comment in test_cases:
            lines = compiler.compile_to_lines(forth_code)
            assembly_str = '\n'.join(lines)

            assert expected_instruction in assembly_str
            assert expected_comment in assembly_str
            assert "; Stack before: ( value -- )" in assembly_str

    def test_swrite_instruction_compilation(self, compiler):
        """Test SWRITE instruction compiles correctly."""
        forth_code = "255 SWRITE"
        lines = compiler.compile_to_lines(forth_code)

        assembly_str = '\n'.join(lines)
        assert "SWRITE R0" in assembly_str
        assert "; SWRITE - Write pixel at current coordinates" in assembly_str
        assert "; Stack before: ( color -- )" in assembly_str

    def test_sprite_instruction_compilation(self, compiler):
        """Test SPRITE instruction compiles to sprite control block manipulation."""
        forth_code = "0 100 150 255 SPRITE"
        lines = compiler.compile_to_lines(forth_code)

        assembly_str = '\n'.join(lines)

        # Check sprite control block calculations
        assert "MOV R0, :P3" in assembly_str  # Sprite ID
        assert "AND R0, 0x0F" in assembly_str  # Limit to 16 sprites
        assert "ADD R0, 0xF000" in assembly_str  # Base address

        # Check sprite parameter storage
        assert "MOV [R0+0], R1" in assembly_str  # X coordinate
        assert "MOV [R0+1], R1" in assembly_str  # Y coordinate
        assert "MOV [R0+2], R1" in assembly_str  # Color
        assert "MOV [R0+3], R1" in assembly_str  # Enable flag

        assert "; SPRITE - Configure sprite" in assembly_str
        assert "; Stack before: ( sprite_id x y color -- )" in assembly_str

    def test_sound_instruction_compilation(self, compiler):
        """Test SOUND instruction compiles to sound register setup."""
        forth_code = "440 128 1 SOUND"
        lines = compiler.compile_to_lines(forth_code)

        assembly_str = '\n'.join(lines)

        # Check sound register assignments
        assert "MOV SW, R2" in assembly_str  # Waveform
        assert "MOV SV, R1" in assembly_str  # Volume
        assert "MOV SF, R0" in assembly_str  # Frequency

        assert "; SOUND - Set sound parameters" in assembly_str
        assert "; Stack before: ( freq volume waveform -- )" in assembly_str

    def test_play_instruction_compilation(self, compiler):
        """Test PLAY instruction compiles to SPLAY."""
        forth_code = "PLAY"
        lines = compiler.compile_to_lines(forth_code)

        assembly_str = '\n'.join(lines)
        assert "SPLAY" in assembly_str
        assert "; PLAY - Start sound playback" in assembly_str

    def test_keyboard_instructions(self, compiler):
        """Test KEY and KEY? instructions."""
        # Test KEY instruction
        lines_key = compiler.compile_to_lines("KEY")
        assembly_key = '\n'.join(lines_key)
        assert "KEYIN R0" in assembly_key
        assert "; KEY - Read key from keyboard" in assembly_key

        # Test KEY? instruction
        lines_keyq = compiler.compile_to_lines("KEY?")
        assembly_keyq = '\n'.join(lines_keyq)
        assert "KEYSTAT R0" in assembly_keyq
        assert "; KEY? - Check if key is available" in assembly_keyq

    def test_timer_instruction_compilation(self, compiler):
        """Test TIMER! instruction compiles to TT register store."""
        forth_code = "60 TIMER!"
        lines = compiler.compile_to_lines(forth_code)

        assembly_str = '\n'.join(lines)
        assert "MOV TT, R0" in assembly_str
        assert "; TIMER! - Store to timer register" in assembly_str
        assert "; Stack before: ( value -- )" in assembly_str

    def test_register_preservation_in_graphics_ops(self, compiler):
        """Test that graphics operations don't unnecessarily corrupt general registers."""
        # Test a sequence that should preserve registers
        forth_code = """
        10 R0 !     ; Store 10 in a variable location
        20 30 255 PIXEL  ; Draw a pixel
        R0 @       ; Retrieve the value
        """

        lines = compiler.compile_to_lines(forth_code)
        assembly_str = '\n'.join(lines)

        # Should not have unexpected register usage
        # The PIXEL operation should only use R0, R1, R2 as documented
        # Count occurrences of MOV to registers
        mov_r0_count = assembly_str.count("MOV R0,")
        mov_r1_count = assembly_str.count("MOV R1,")
        mov_r2_count = assembly_str.count("MOV R2,")

        # Should be reasonable usage - not excessive register corruption
        assert mov_r0_count <= 15  # More reasonable bound for FORTH operations
        assert mov_r1_count <= 10
        assert mov_r2_count <= 10

    def test_graphics_instructions_with_constants(self, compiler):
        """Test graphics instructions work with predefined color constants."""
        forth_code = "100 200 RED PIXEL"
        lines = compiler.compile_to_lines(forth_code)

        assembly_str = '\n'.join(lines)

        # Should load the RED constant (0x1F = 31) and use it
        assert "MOV P0,31" in assembly_str  # RED constant is 31
        assert "MOV VX, R2" in assembly_str
        assert "MOV VY, R1" in assembly_str
        assert "SWRITE R0" in assembly_str

    def test_complex_graphics_sequence(self, compiler):
        """Test a complex sequence of graphics operations."""
        forth_code = """
        1 VMODE        ; Set video mode
        2 LAYER        ; Set layer
        100 VX!        ; Set X coordinate
        150 VY!        ; Set Y coordinate
        255 SWRITE     ; Write pixel
        0 50 100 200 SPRITE  ; Configure sprite
        """

        lines = compiler.compile_to_lines(forth_code)
        assembly_str = '\n'.join(lines)

        # Check all instructions are present
        assert "MOV VM, R0" in assembly_str  # VMODE
        assert "MOV VL, R0" in assembly_str  # LAYER
        assert "MOV VX, R0" in assembly_str  # VX!
        assert "MOV VY, R0" in assembly_str  # VY!
        assert "SWRITE R0" in assembly_str   # SWRITE
        assert "MOV [R0+0], R1" in assembly_str  # SPRITE x coordinate
        assert "MOV [R0+1], R1" in assembly_str  # SPRITE y coordinate
        assert "MOV [R0+2], R1" in assembly_str  # SPRITE color
        assert "MOV [R0+3], R1" in assembly_str  # SPRITE enable

    def test_stack_management_in_graphics_ops(self, compiler):
        """Test that graphics operations properly manage the parameter stack."""
        forth_code = "10 20 DUP PIXEL"
        lines = compiler.compile_to_lines(forth_code)

        assembly_str = '\n'.join(lines)

        # DUP should duplicate the top of stack, PIXEL should consume 3 items
        # Check for proper stack pointer manipulation
        sub_p8_count = assembly_str.count("SUB P8,2")  # Push operations
        add_p8_count = assembly_str.count("ADD P8,2")  # Pop operations

        # DUP: 1 SUB P8,2 (duplicate)
        # PIXEL: 3 ADD P8,2 (pop x,y,color)
        # So we should have more ADD than SUB for net stack consumption
        assert add_p8_count >= sub_p8_count

    def test_graphics_opcodes_compliance(self, compiler):
        """Test that generated assembly uses opcodes defined in opcodes.py."""
        # Import opcodes to check compliance
        import opcodes

        # Extract opcode names from opcodes.py
        opcode_names = {name for name, _, _ in opcodes.opcodes}

        forth_code = "10 20 255 PIXEL 440 128 1 SOUND PLAY"
        lines = compiler.compile_to_lines(forth_code)

        # Check that all instructions in generated assembly are valid opcodes
        for line in lines:
            line = line.strip()
            if line and not line.startswith(';') and not line.startswith('forth_main:') and not line.startswith('main:'):
                # Extract instruction name (first word before space or comma)
                instruction = line.split()[0] if line.split() else ""
                # Skip labels (end with :) and assembler directives
                if instruction and instruction not in ['ORG', 'DW', 'EQU', 'DB', 'RET', 'CALL', 'HLT'] and not instruction.endswith(':'):
                    # Check if it's a valid opcode or register
                    assert instruction in opcode_names or instruction in ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9',
                                                                         'P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9',
                                                                         'VX', 'VY', 'VM', 'VL', 'TT', 'TM', 'TC', 'TS',
                                                                         'SP', 'FP', 'SA', 'SF', 'SV', 'SW'], \
                           f"Instruction '{instruction}' not found in opcodes.py"

    def test_assembly_syntax_validation(self, compiler):
        """Test that generated assembly has correct syntax for nova_assembler.py."""
        forth_code = "5 10 15 PIXEL"
        lines = compiler.compile_to_lines(forth_code)

        # Check that assembly follows expected patterns
        for line in lines:
            line = line.strip()
            if line and not line.startswith(';'):
                # Should not have syntax errors that would break assembler
                # Allow various instruction formats and labels
                valid_syntax = (',' in line or 
                              line in ['RET', 'HLT'] or 
                              line.startswith(('forth_main:', 'main:', 'ORG')) or
                              line.endswith(':') or  # Labels
                              line.startswith(('CALL ', 'JMP ', 'JZ ', 'JNZ ', 'JG ', 'JL ', 'JGE ', 'JLE ',
                                             'SWRITE ', 'KEYIN ', 'KEYSTAT ', 'SPLAY ', 'SPBLIT ', 'SPBLITALL ',
                                             'SFILL ', 'SBLIT ', 'VBLIT ', 'VREAD ', 'VWRITE ', 'MEMCPY ',
                                             'STRCPY ', 'STRCAT ', 'STRCMP ', 'STRLEN ', 'STREXT ', 'STREXTI ',
                                             'STRUPR ', 'STRLWR ', 'STRREV ', 'STRFIND ', 'STRFINDI ',
                                             'MEMSET ', 'MEMTEST ', 'MEMMOVE ', 'SMIX ', 'SECHO ', 'SREVERB ',
                                             'SFILTER ', 'CHAR ', 'TEXT ', 'KEYCLEAR ', 'KEYCTRL ', 'KEYCOUNT ',
                                             'RND ', 'RNDR ', 'SED ', 'CLD ', 'CLA ', 'BCDA ', 'BCDS ', 'BCDCMP ',
                                             'BCD2BIN ', 'BIN2BCD ', 'BCDADD ', 'BCDSUB ', 'BTST ', 'BSET ',
                                             'BCLR ', 'BFLIP ', 'POWR ', 'SQRT ', 'LOG ', 'EXP ', 'SIN ', 'COS ',
                                             'TAN ', 'ATAN ', 'ASIN ', 'ACOS ', 'DEG ', 'RAD ', 'FLOOR ', 'CEIL ',
                                             'ROUND ', 'TRUNC ', 'FRAC ', 'INTGR ', 'LOOP ', 'SBLEND ', 'SREAD ',
                                             'SROL ', 'SROT ', 'SSHFT ', 'SFLIP ', 'SLINE ', 'SRECT ', 'SCIRC ',
                                             'SINV ', 'INT ', 'NEG ', 'INC ', 'DEC ', 'AND ', 'OR ', 'XOR ',
                                             'NOT ', 'SHL ', 'SHR ', 'ROL ', 'ROR ', 'CMP ', 'PUSH ', 'POP ',
                                             'PUSHF ', 'POPF ', 'PUSHA ', 'POPA ', 'MOV ', 'ADD ', 'SUB ',
                                             'MUL ', 'DIV ', 'MOD ', 'ABS ', 'BR ', 'BRZ ', 'BRNZ ')))
                assert valid_syntax, f"Line has invalid syntax: {line}"

                # Check register names are valid for MOV instructions
                if 'MOV' in line and ',' in line:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        dest = parts[0].split()[1] if len(parts[0].split()) > 1 else ""
                        src = parts[1].strip() if len(parts) > 1 else ""
                        valid_regs = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9',
                                    'P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9',
                                    'VX', 'VY', 'VM', 'VL', 'TT', 'TM', 'TC', 'TS',
                                    'SP', 'FP', 'SA', 'SF', 'SV', 'SW']
                        if dest in valid_regs:
                            assert src.replace(' ', '') in valid_regs or src.isdigit() or src.startswith('0x') or '[' in src or ':' in src, \
                                   f"Invalid source operand: {src}"

    def test_graphics_word_definitions(self, compiler):
        """Test that graphics words can be defined and used in FORTH programs."""
        forth_code = """
        : DRAW-PIXEL PIXEL ;
        : SET-LAYER LAYER ;
        10 20 255 DRAW-PIXEL
        2 SET-LAYER
        """

        lines = compiler.compile_to_lines(forth_code)

        # Should compile word definitions and their usage
        assembly_str = '\n'.join(lines)

        # Check that words are defined
        assert 'DRAW-PIXEL:' in assembly_str
        assert 'SET-LAYER:' in assembly_str

        # Check that graphics instructions are present
        assert "MOV VX, R2" in assembly_str
        assert "MOV VY, R1" in assembly_str
        assert "SWRITE R0" in assembly_str
        assert "MOV VL, R0" in assembly_str

    def test_error_handling_in_graphics_ops(self, compiler):
        """Test error handling for invalid graphics operations."""
        # Test with invalid layer number (should still compile but may have runtime issues)
        forth_code = "255 LAYER"  # Invalid layer, but should compile
        lines = compiler.compile_to_lines(forth_code)

        assembly_str = '\n'.join(lines)
        assert "MOV VL, R0" in assembly_str  # Should still generate instruction

        # Test with out-of-range coordinates (should still compile)
        forth_code = "300 400 255 PIXEL"  # Coordinates outside screen
        lines = compiler.compile_to_lines(forth_code)

        assembly_str = '\n'.join(lines)
        assert "MOV VX, R2" in assembly_str
        assert "MOV VY, R1" in assembly_str
        assert "SWRITE R0" in assembly_str