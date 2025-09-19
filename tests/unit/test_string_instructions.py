"""
Unit tests for string instructions in nova_cpu.py - Nova-16 CPU core.
"""

import pytest
from tests.conftest import assert_register_equals, run_cpu_cycles


class TestStringInstructions:
    """Test string operation instructions."""

    def test_strcpy_instruction(self, cpu):
        """Test STRCPY instruction."""
        # Set up source string "Hello"
        source_addr = 0x1000
        cpu.memory.write(source_addr, ord('H'), 1)
        cpu.memory.write(source_addr + 1, ord('e'), 1)
        cpu.memory.write(source_addr + 2, ord('l'), 1)
        cpu.memory.write(source_addr + 3, ord('l'), 1)
        cpu.memory.write(source_addr + 4, ord('o'), 1)
        cpu.memory.write(source_addr + 5, 0, 1)  # null terminator

        dest_addr = 0x2000

        # STRCPY dest, source
        cpu.memory.write_byte(0x0000, 0x71)  # STRCPY opcode
        cpu.memory.write_byte(0x0001, 0x0A)  # Mode byte: both immediate 16-bit
        cpu.memory.write_word(0x0002, dest_addr)  # destination
        cpu.memory.write_word(0x0004, source_addr)  # source

        cpu.step()

        # Verify copy
        assert cpu.memory.read(dest_addr, 1)[0] == ord('H')
        assert cpu.memory.read(dest_addr + 1, 1)[0] == ord('e')
        assert cpu.memory.read(dest_addr + 2, 1)[0] == ord('l')
        assert cpu.memory.read(dest_addr + 3, 1)[0] == ord('l')
        assert cpu.memory.read(dest_addr + 4, 1)[0] == ord('o')
        assert cpu.memory.read(dest_addr + 5, 1)[0] == 0

    def test_strcat_instruction(self, cpu):
        """Test STRCAT instruction."""
        # Set up destination string "Hello"
        dest_addr = 0x1000
        cpu.memory.write(dest_addr, ord('H'), 1)
        cpu.memory.write(dest_addr + 1, ord('e'), 1)
        cpu.memory.write(dest_addr + 2, ord('l'), 1)
        cpu.memory.write(dest_addr + 3, ord('l'), 1)
        cpu.memory.write(dest_addr + 4, ord('o'), 1)
        cpu.memory.write(dest_addr + 5, 0, 1)  # null terminator

        # Set up source string " World"
        source_addr = 0x2000
        cpu.memory.write(source_addr, ord(' '), 1)
        cpu.memory.write(source_addr + 1, ord('W'), 1)
        cpu.memory.write(source_addr + 2, ord('o'), 1)
        cpu.memory.write(source_addr + 3, ord('r'), 1)
        cpu.memory.write(source_addr + 4, ord('l'), 1)
        cpu.memory.write(source_addr + 5, ord('d'), 1)
        cpu.memory.write(source_addr + 6, 0, 1)  # null terminator

        # STRCAT dest, source
        cpu.memory.write_byte(0x0000, 0x72)  # STRCAT opcode
        cpu.memory.write_byte(0x0001, 0x0A)  # Mode byte: both immediate 16-bit
        cpu.memory.write_word(0x0002, dest_addr)  # destination
        cpu.memory.write_word(0x0004, source_addr)  # source

        cpu.step()

        # Verify concatenation
        expected = "Hello World"
        for i, char in enumerate(expected):
            assert cpu.memory.read(dest_addr + i, 1)[0] == ord(char)
        assert cpu.memory.read(dest_addr + len(expected), 1)[0] == 0

    def test_strcmp_instruction_equal(self, cpu):
        """Test STRCMP instruction with equal strings."""
        # Set up string1 "test"
        str1_addr = 0x1000
        cpu.memory.write(str1_addr, ord('t'), 1)
        cpu.memory.write(str1_addr + 1, ord('e'), 1)
        cpu.memory.write(str1_addr + 2, ord('s'), 1)
        cpu.memory.write(str1_addr + 3, ord('t'), 1)
        cpu.memory.write(str1_addr + 4, 0, 1)

        # Set up string2 "test"
        str2_addr = 0x2000
        cpu.memory.write(str2_addr, ord('t'), 1)
        cpu.memory.write(str2_addr + 1, ord('e'), 1)
        cpu.memory.write(str2_addr + 2, ord('s'), 1)
        cpu.memory.write(str2_addr + 3, ord('t'), 1)
        cpu.memory.write(str2_addr + 4, 0, 1)

        # STRCMP str1, str2, length
        cpu.memory.write_byte(0x0000, 0x73)  # STRCMP opcode
        cpu.memory.write_byte(0x0001, 0x2A)  # Mode byte: all immediate 16-bit
        cpu.memory.write_word(0x0002, str1_addr)
        cpu.memory.write_word(0x0004, str2_addr)
        cpu.memory.write_word(0x0006, 10)  # max length

        cpu.step()

        # Result should be 0 (equal)
        assert cpu.Rregisters[0] == 0

    def test_strcmp_instruction_different(self, cpu):
        """Test STRCMP instruction with different strings."""
        # Set up string1 "abc"
        str1_addr = 0x1000
        cpu.memory.write(str1_addr, ord('a'), 1)
        cpu.memory.write(str1_addr + 1, ord('b'), 1)
        cpu.memory.write(str1_addr + 2, ord('c'), 1)
        cpu.memory.write(str1_addr + 3, 0, 1)

        # Set up string2 "abd"
        str2_addr = 0x2000
        cpu.memory.write(str2_addr, ord('a'), 1)
        cpu.memory.write(str2_addr + 1, ord('b'), 1)
        cpu.memory.write(str2_addr + 2, ord('d'), 1)
        cpu.memory.write(str2_addr + 3, 0, 1)

        # STRCMP str1, str2, length
        cpu.memory.write_byte(0x0000, 0x73)  # STRCMP opcode
        cpu.memory.write_byte(0x0001, 0x2A)  # Mode byte: all immediate 16-bit
        cpu.memory.write_word(0x0002, str1_addr)
        cpu.memory.write_word(0x0004, str2_addr)
        cpu.memory.write_word(0x0006, 10)  # max length

        cpu.step()

        # Result should be -1 (str1 < str2)
        assert cpu.Rregisters[0] == 255  # -1 as unsigned byte

    def test_strlen_instruction(self, cpu):
        """Test STRLEN instruction."""
        # Set up string "hello"
        str_addr = 0x1000
        cpu.memory.write(str_addr, ord('h'), 1)
        cpu.memory.write(str_addr + 1, ord('e'), 1)
        cpu.memory.write(str_addr + 2, ord('l'), 1)
        cpu.memory.write(str_addr + 3, ord('l'), 1)
        cpu.memory.write(str_addr + 4, ord('o'), 1)
        cpu.memory.write(str_addr + 5, 0, 1)

        # STRLEN str
        cpu.memory.write_byte(0x0000, 0x74)  # STRLEN opcode
        cpu.memory.write_byte(0x0001, 0x02)  # Mode byte: immediate 16-bit
        cpu.memory.write_word(0x0002, str_addr)

        cpu.step()

        # Length should be 5
        assert cpu.Rregisters[0] == 5

    def test_strupr_instruction(self, cpu):
        """Test STRUPR instruction."""
        # Set up string "Hello"
        str_addr = 0x1000
        cpu.memory.write(str_addr, ord('H'), 1)
        cpu.memory.write(str_addr + 1, ord('e'), 1)
        cpu.memory.write(str_addr + 2, ord('l'), 1)
        cpu.memory.write(str_addr + 3, ord('l'), 1)
        cpu.memory.write(str_addr + 4, ord('o'), 1)
        cpu.memory.write(str_addr + 5, 0, 1)

        # STRUPR str
        cpu.memory.write_byte(0x0000, 0x77)  # STRUPR opcode
        cpu.memory.write_byte(0x0001, 0x02)  # Mode byte: immediate 16-bit
        cpu.memory.write_word(0x0002, str_addr)

        cpu.step()

        # Verify uppercase
        assert cpu.memory.read(str_addr, 1)[0] == ord('H')
        assert cpu.memory.read(str_addr + 1, 1)[0] == ord('E')
        assert cpu.memory.read(str_addr + 2, 1)[0] == ord('L')
        assert cpu.memory.read(str_addr + 3, 1)[0] == ord('L')
        assert cpu.memory.read(str_addr + 4, 1)[0] == ord('O')
        assert cpu.memory.read(str_addr + 5, 1)[0] == 0

    def test_strlwr_instruction(self, cpu):
        """Test STRLWR instruction."""
        # Set up string "HELLO"
        str_addr = 0x1000
        cpu.memory.write(str_addr, ord('H'), 1)
        cpu.memory.write(str_addr + 1, ord('E'), 1)
        cpu.memory.write(str_addr + 2, ord('L'), 1)
        cpu.memory.write(str_addr + 3, ord('L'), 1)
        cpu.memory.write(str_addr + 4, ord('O'), 1)
        cpu.memory.write(str_addr + 5, 0, 1)

        # STRLWR str
        cpu.memory.write_byte(0x0000, 0x78)  # STRLWR opcode
        cpu.memory.write_byte(0x0001, 0x02)  # Mode byte: immediate 16-bit
        cpu.memory.write_word(0x0002, str_addr)

        cpu.step()

        # Verify lowercase
        assert cpu.memory.read(str_addr, 1)[0] == ord('h')
        assert cpu.memory.read(str_addr + 1, 1)[0] == ord('e')
        assert cpu.memory.read(str_addr + 2, 1)[0] == ord('l')
        assert cpu.memory.read(str_addr + 3, 1)[0] == ord('l')
        assert cpu.memory.read(str_addr + 4, 1)[0] == ord('o')
        assert cpu.memory.read(str_addr + 5, 1)[0] == 0

    def test_strrev_instruction(self, cpu):
        """Test STRREV instruction."""
        # Set up string "hello"
        str_addr = 0x1000
        cpu.memory.write(str_addr, ord('h'), 1)
        cpu.memory.write(str_addr + 1, ord('e'), 1)
        cpu.memory.write(str_addr + 2, ord('l'), 1)
        cpu.memory.write(str_addr + 3, ord('l'), 1)
        cpu.memory.write(str_addr + 4, ord('o'), 1)
        cpu.memory.write(str_addr + 5, 0, 1)

        # STRREV str
        cpu.memory.write_byte(0x0000, 0x79)  # STRREV opcode
        cpu.memory.write_byte(0x0001, 0x02)  # Mode byte: immediate 16-bit
        cpu.memory.write_word(0x0002, str_addr)

        cpu.step()

        # Verify reversed
        assert cpu.memory.read(str_addr, 1)[0] == ord('o')
        assert cpu.memory.read(str_addr + 1, 1)[0] == ord('l')
        assert cpu.memory.read(str_addr + 2, 1)[0] == ord('l')
        assert cpu.memory.read(str_addr + 3, 1)[0] == ord('e')
        assert cpu.memory.read(str_addr + 4, 1)[0] == ord('h')
        assert cpu.memory.read(str_addr + 5, 1)[0] == 0

    def test_strfind_instruction_found(self, cpu):
        """Test STRFIND instruction when substring is found."""
        # Set up haystack "hello world"
        haystack_addr = 0x1000
        haystack = "hello world"
        for i, char in enumerate(haystack):
            cpu.memory.write(haystack_addr + i, ord(char), 1)
        cpu.memory.write(haystack_addr + len(haystack), 0, 1)

        # Set up needle "world"
        needle_addr = 0x2000
        needle = "world"
        for i, char in enumerate(needle):
            cpu.memory.write(needle_addr + i, ord(char), 1)
        cpu.memory.write(needle_addr + len(needle), 0, 1)

        # STRFIND haystack, needle
        cpu.memory.write_byte(0x0000, 0x7A)  # STRFIND opcode
        cpu.memory.write_byte(0x0001, 0x0A)  # Mode byte: both immediate 16-bit
        cpu.memory.write_word(0x0002, haystack_addr)
        cpu.memory.write_word(0x0004, needle_addr)

        cpu.step()

        # Should find substring
        assert cpu.Rregisters[0] == 1

    def test_strfind_instruction_not_found(self, cpu):
        """Test STRFIND instruction when substring is not found."""
        # Set up haystack "hello world"
        haystack_addr = 0x1000
        haystack = "hello world"
        for i, char in enumerate(haystack):
            cpu.memory.write(haystack_addr + i, ord(char), 1)
        cpu.memory.write(haystack_addr + len(haystack), 0, 1)

        # Set up needle "xyz"
        needle_addr = 0x2000
        needle = "xyz"
        for i, char in enumerate(needle):
            cpu.memory.write(needle_addr + i, ord(char), 1)
        cpu.memory.write(needle_addr + len(needle), 0, 1)

        # STRFIND haystack, needle
        cpu.memory.write_byte(0x0000, 0x7A)  # STRFIND opcode
        cpu.memory.write_byte(0x0001, 0x0A)  # Mode byte: both immediate 16-bit
        cpu.memory.write_word(0x0002, haystack_addr)
        cpu.memory.write_word(0x0004, needle_addr)

        cpu.step()

        # Should not find substring
        assert cpu.Rregisters[0] == 0

    def test_strfindi_instruction_case_insensitive(self, cpu):
        """Test STRFINDI instruction case-insensitive search."""
        # Set up haystack "Hello World"
        haystack_addr = 0x1000
        haystack = "Hello World"
        for i, char in enumerate(haystack):
            cpu.memory.write(haystack_addr + i, ord(char), 1)
        cpu.memory.write(haystack_addr + len(haystack), 0, 1)

        # Set up needle "world" (lowercase)
        needle_addr = 0x2000
        needle = "world"
        for i, char in enumerate(needle):
            cpu.memory.write(needle_addr + i, ord(char), 1)
        cpu.memory.write(needle_addr + len(needle), 0, 1)

        # STRFINDI haystack, needle
        cpu.memory.write_byte(0x0000, 0x7B)  # STRFINDI opcode
        cpu.memory.write_byte(0x0001, 0x0A)  # Mode byte: both immediate 16-bit
        cpu.memory.write_word(0x0002, haystack_addr)
        cpu.memory.write_word(0x0004, needle_addr)

        cpu.step()

        # Should find substring case-insensitively
        assert cpu.Rregisters[0] == 1