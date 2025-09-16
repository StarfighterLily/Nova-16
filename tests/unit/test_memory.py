"""
Unit tests for nova_memory.py - Nova-16 memory system.
"""

import pytest
import numpy as np
from tests.conftest import assert_memory_equals


class TestMemoryInitialization:
    """Test memory initialization and basic properties."""

    def test_memory_size(self, memory):
        """Test that memory has correct size."""
        assert memory.size == 65536  # 64KB
        assert len(memory.memory) == 65536

    def test_memory_initialization(self, memory):
        """Test that memory is initialized to zeros."""
        assert np.all(memory.memory == 0)

    def test_timer_initialization(self, memory):
        """Test timer initialization."""
        assert memory.timer == 0
        assert memory.timer_limit == 256
        assert memory.interrupt_enabled == False


class TestMemoryReadWrite:
    """Test basic read/write operations."""

    def test_write_byte(self, memory):
        """Test single byte write."""
        memory.write_byte(0x1000, 0x42)
        assert memory.read_byte(0x1000) == 0x42

    def test_write_word_big_endian(self, memory):
        """Test 16-bit word write (big-endian)."""
        memory.write_word(0x1000, 0x1234)
        assert memory.read_byte(0x1000) == 0x12  # High byte
        assert memory.read_byte(0x1001) == 0x34  # Low byte
        assert memory.read_word(0x1000) == 0x1234

    def test_read_write_bounds(self, memory):
        """Test read/write operations at memory bounds."""
        # Test last byte
        memory.write_byte(0xFFFF, 0xFF)
        assert memory.read_byte(0xFFFF) == 0xFF

        # Test last word (should handle edge case)
        memory.write_word(0xFFFE, 0xABCD)
        assert memory.read_word(0xFFFE) == 0xABCD

    def test_write_multi_byte(self, memory):
        """Test multi-byte write operations."""
        data = [0x11, 0x22, 0x33, 0x44]
        memory.write(0x2000, 0x11223344, bytes=4)
        actual = memory.read_bytes_direct(0x2000, 4)
        assert actual == data

    def test_read_bounds_checking(self, memory):
        """Test bounds checking for read operations."""
        # Should not raise exception for valid reads
        memory.read_byte(0xFFFF)
        memory.read_word(0xFFFE)

        # Test out of bounds word read - this should work for edge case
        result = memory.read_word(0xFFFF)  # Returns the byte as a word
        assert result == memory.read_byte(0xFFFF)


class TestMemoryLoadSave:
    """Test binary file loading and saving."""

    def test_load_binary_file(self, memory, tmp_path):
        """Test loading binary data from file."""
        test_data = bytes([i % 256 for i in range(100)])
        bin_file = tmp_path / "test.bin"
        bin_file.write_bytes(test_data)

        entry_point = memory.load(str(bin_file))
        assert entry_point == 0x0000  # Default entry point
        loaded_data = memory.memory[:100]
        assert np.array_equal(loaded_data, np.frombuffer(test_data, dtype=np.uint8))

    def test_load_with_org_file(self, memory, tmp_path):
        """Test loading with ORG segment information."""
        # Create test binary
        test_data = bytes([i % 256 for i in range(50)])
        bin_file = tmp_path / "test.bin"
        bin_file.write_bytes(test_data)

        # Create ORG file with segment info
        org_content = "2000 16 0\n3000 16 16\n"
        org_file = tmp_path / "test.org"
        org_file.write_text(org_content)

        entry_point = memory.load_with_org_info(str(bin_file), str(org_file))
        assert entry_point == 0x2000  # First segment start

        # Check first segment loaded correctly
        segment1 = memory.memory[0x2000:0x2010]
        expected1 = np.frombuffer(test_data[:16], dtype=np.uint8)
        assert np.array_equal(segment1, expected1)

        # Check second segment
        segment2 = memory.memory[0x3000:0x3010]
        expected2 = np.frombuffer(test_data[16:32], dtype=np.uint8)
        assert np.array_equal(segment2, expected2)

    def test_save_binary_file(self, memory, tmp_path):
        """Test saving memory to binary file."""
        # Write some test data to memory
        test_data = [i % 256 for i in range(100)]
        memory.memory[:100] = np.array(test_data, dtype=np.uint8)

        save_file = tmp_path / "saved.bin"
        memory.save(str(save_file))

        # Read back and verify
        saved_data = save_file.read_bytes()
        assert saved_data[:100] == bytes(test_data)


class TestMemorySpriteIntegration:
    """Test sprite memory region integration."""

    def test_sprite_memory_write_triggers_dirty_flag(self, memory, graphics):
        """Test that writing to sprite memory marks sprites as dirty."""
        memory.gfx_system = graphics
        graphics.sprites_dirty = False

        # Write to sprite memory region
        memory.write_byte(0xF000, 0x42)
        assert graphics.sprites_dirty == True

    def test_non_sprite_memory_write_no_dirty_flag(self, memory, graphics):
        """Test that writing outside sprite memory doesn't affect dirty flag."""
        memory.gfx_system = graphics
        graphics.sprites_dirty = False

        # Write outside sprite memory
        memory.write_byte(0x1000, 0x42)
        assert graphics.sprites_dirty == False


class TestMemoryDump:
    """Test memory dump functionality."""

    def test_memory_dump(self, memory, capsys):
        """Test memory dump output."""
        # Write some test data
        memory.write_byte(0x0000, 0xAA)
        memory.write_byte(0x0001, 0xBB)
        memory.write_word(0x0010, 0x1234)

        memory.dump()

        captured = capsys.readouterr()
        # Check that output contains expected hex values
        assert "AA" in captured.out
        assert "BB" in captured.out
        assert "12" in captured.out
        assert "34" in captured.out


class TestMemoryRoundTrip:
    """Test round-trip operations (write then read)."""

    def test_byte_round_trip(self, memory):
        """Test byte write/read round trip."""
        test_values = [0x00, 0x42, 0xFF, 0x7F, 0x80]

        for addr in [0x0000, 0x1000, 0xFFFF]:
            for value in test_values:
                memory.write_byte(addr, value)
                assert memory.read_byte(addr) == value

    def test_word_round_trip(self, memory):
        """Test word write/read round trip."""
        test_values = [0x0000, 0x1234, 0xFFFF, 0xABCD, 0x0001]

        for addr in [0x0000, 0x1000, 0xFFFE]:
            for value in test_values:
                memory.write_word(addr, value)
                assert memory.read_word(addr) == value

    def test_multi_byte_round_trip(self, memory):
        """Test multi-byte write/read round trip."""
        test_data = [
            [0x11, 0x22],
            [0xAA, 0xBB, 0xCC, 0xDD],
            list(range(10))
        ]

        for addr in [0x0000, 0x2000]:
            for data in test_data:
                # Write data
                for i, byte in enumerate(data):
                    memory.write_byte(addr + i, byte)

                # Read back and verify
                actual = memory.read_bytes_direct(addr, len(data))
                assert actual == data


class TestMemoryEdgeCases:
    """Aggressive edge case and boundary testing for memory operations."""

    def test_address_boundary_min(self, memory):
        """Test operations at minimum address (0x0000)."""
        # Test byte operations
        memory.write_byte(0x0000, 0xFF)
        assert memory.read_byte(0x0000) == 0xFF

        # Test word operations at boundary
        memory.write_word(0x0000, 0xABCD)
        assert memory.read_word(0x0000) == 0xABCD
        assert memory.read_byte(0x0000) == 0xAB
        assert memory.read_byte(0x0001) == 0xCD

    def test_address_boundary_max(self, memory):
        """Test operations at maximum address (0xFFFF)."""
        # Test byte operations
        memory.write_byte(0xFFFF, 0xEE)
        assert memory.read_byte(0xFFFF) == 0xEE

        # Test word operations near boundary (should handle wraparound)
        memory.write_word(0xFFFE, 0x1234)
        assert memory.read_word(0xFFFE) == 0x1234
        assert memory.read_byte(0xFFFE) == 0x12
        assert memory.read_byte(0xFFFF) == 0x34

    def test_word_boundary_edge_cases(self, memory):
        """Test word operations at edge boundaries."""
        # Word at 0xFFFF should fail (would need 0xFFFF and 0x10000)
        with pytest.raises(IndexError):
            memory.write_word(0xFFFF, 0x1234)

        # Word at 0xFFFE should work
        memory.write_word(0xFFFE, 0x5678)
        assert memory.read_word(0xFFFE) == 0x5678

    def test_invalid_addresses(self, memory):
        """Test operations with invalid addresses."""
        # Negative addresses
        with pytest.raises(IndexError):
            memory.write_byte(-1, 0x42)

        with pytest.raises(IndexError):
            memory.read_byte(-1)

        # Addresses beyond memory size
        with pytest.raises(IndexError):
            memory.write_byte(0x10000, 0x42)

        with pytest.raises(IndexError):
            memory.read_byte(0x10000)

        # Very large addresses
        with pytest.raises(IndexError):
            memory.write_byte(999999, 0x42)

    def test_invalid_values(self, memory):
        """Test operations with invalid values."""
        # Values outside byte range (should be masked)
        memory.write_byte(0x1000, 0x123)  # 291 decimal
        assert memory.read_byte(0x1000) == 0x23  # Should be masked to 8 bits

        memory.write_byte(0x1001, -1)  # Negative value
        assert memory.read_byte(0x1001) == 0xFF  # Should wrap to 255

        # Word values (should be masked to 16 bits)
        memory.write_word(0x1002, 0x12345)  # Too large
        assert memory.read_word(0x1002) == 0x2345  # Should be masked

    def test_zero_length_operations(self, memory):
        """Test operations with zero length."""
        # Zero length read_bytes_direct
        result = memory.read_bytes_direct(0x1000, 0)
        assert result == []

        # Zero length read_bytes_direct at boundary
        result = memory.read_bytes_direct(0xFFFF, 0)
        assert result == []

    def test_large_data_operations(self, memory):
        """Test operations with large amounts of data."""
        # Large sequential write
        large_data = list(range(256)) * 10  # 2560 bytes
        addr = 0x1000

        for i, byte in enumerate(large_data):
            memory.write_byte(addr + i, byte)

        # Verify all data
        for i, expected in enumerate(large_data):
            assert memory.read_byte(addr + i) == (expected & 0xFF)

        # Large block read
        read_data = memory.read_bytes_direct(addr, len(large_data))
        assert read_data == [b & 0xFF for b in large_data]

    def test_memory_wraparound_protection(self, memory):
        """Test that operations don't wrap around memory boundaries."""
        # Try to read beyond memory end
        with pytest.raises(IndexError):
            memory.read_bytes_direct(0xFFFF, 2)

        # Try to write beyond memory end
        with pytest.raises(IndexError):
            memory.write_bytes_direct(0xFFFF, [1, 2])

    def test_sparse_memory_access(self, memory):
        """Test accessing widely separated memory locations."""
        test_addresses = [0x0000, 0x1000, 0x8000, 0xF000, 0xFFFE]
        test_values = [0x11, 0x22, 0x33, 0x44, 0x55]

        # Write to sparse locations
        for addr, val in zip(test_addresses, test_values):
            memory.write_byte(addr, val)

        # Read back and verify
        for addr, expected in zip(test_addresses, test_values):
            assert memory.read_byte(addr) == expected

    def test_memory_pressure_stress(self, memory):
        """Stress test with many small operations."""
        # Perform 1000 random read/write operations
        import random
        random.seed(42)  # For reproducible tests

        operations = []
        for _ in range(1000):
            addr = random.randint(0, 0xFFFF)
            value = random.randint(0, 255)
            operations.append((addr, value))

        # Write phase
        for addr, value in operations:
            memory.write_byte(addr, value)

        # Read phase - verify all writes
        for addr, expected in operations:
            actual = memory.read_byte(addr)
            assert actual == expected

    def test_concurrent_address_access(self, memory):
        """Test accessing same address from different operations."""
        addr = 0x2000

        # Write different values to same address
        memory.write_byte(addr, 0xAA)
        assert memory.read_byte(addr) == 0xAA

        memory.write_word(addr, 0xBBCC)
        assert memory.read_word(addr) == 0xBBCC
        assert memory.read_byte(addr) == 0xBB
        assert memory.read_byte(addr + 1) == 0xCC

        # Overwrite with byte again
        memory.write_byte(addr, 0xDD)
        assert memory.read_byte(addr) == 0xDD
        assert memory.read_byte(addr + 1) == 0xCC  # Should be unchanged


class TestMemoryLoadSaveEdgeCases:
    """Aggressive testing of load/save operations."""

    def test_empty_file_load(self, memory, tmp_path):
        """Test loading an empty file."""
        empty_file = tmp_path / "empty.bin"
        empty_file.write_bytes(b"")

        # Should handle empty file gracefully
        memory.load_with_org_info(str(empty_file))
        # Memory should remain unchanged (all zeros)
        assert np.all(memory.memory == 0)

    def test_corrupted_org_file(self, memory, tmp_path):
        """Test loading file with corrupted ORG data."""
        corrupted_file = tmp_path / "corrupted.org"
        # Write invalid ORG data
        corrupted_file.write_bytes(b"INVALID_ORG_DATA")

        with pytest.raises(ValueError):
            memory.load_with_org_info(str(corrupted_file))

    def test_oversized_file_load(self, memory, tmp_path):
        """Test loading file larger than memory."""
        large_file = tmp_path / "large.bin"
        # Create file larger than 64KB
        large_data = b'\xAA' * (70000)  # 70KB
        large_file.write_bytes(large_data)

        # Should load only up to memory size
        memory.load_with_org_info(str(large_file))
        # First 64KB should be loaded
        assert memory.read_byte(0) == 0xAA
        assert memory.read_byte(0xFFFF) == 0xAA

    def test_zero_org_address(self, memory, tmp_path):
        """Test loading with ORG at address 0."""
        test_file = tmp_path / "zero_org.bin"
        test_data = b'\x11\x22\x33\x44'
        test_file.write_bytes(test_data)

        memory.load_with_org_info(str(test_file), org_address=0)
        assert memory.read_byte(0) == 0x11
        assert memory.read_byte(1) == 0x22
        assert memory.read_byte(2) == 0x33
        assert memory.read_byte(3) == 0x44

    def test_max_org_address(self, memory, tmp_path):
        """Test loading with ORG at maximum address."""
        test_file = tmp_path / "max_org.bin"
        test_data = b'\x55'
        test_file.write_bytes(test_data)

        memory.load_with_org_info(str(test_file), org_address=0xFFFF)
        assert memory.read_byte(0xFFFF) == 0x55

    def test_org_beyond_memory(self, memory, tmp_path):
        """Test loading with ORG address beyond memory size."""
        test_file = tmp_path / "beyond_mem.bin"
        test_data = b'\x77'
        test_file.write_bytes(test_data)

        # Should handle gracefully or raise error
        with pytest.raises(ValueError):
            memory.load_with_org_info(str(test_file), org_address=0x10000)

    def test_save_empty_memory(self, memory, tmp_path):
        """Test saving memory that is all zeros."""
        save_file = tmp_path / "empty_save.bin"
        memory.save(str(save_file))

        # File should exist and be readable
        assert save_file.exists()
        data = save_file.read_bytes()
        assert len(data) == 65536  # Full memory size
        assert all(b == 0 for b in data)

    def test_save_partial_memory(self, memory, tmp_path):
        """Test saving memory with some data."""
        # Write some data
        memory.write_byte(0x1000, 0xAA)
        memory.write_byte(0x2000, 0xBB)
        memory.write_word(0x3000, 0xCCDD)

        save_file = tmp_path / "partial_save.bin"
        memory.save(str(save_file))

        # Verify saved data
        data = save_file.read_bytes()
        assert data[0x1000] == 0xAA
        assert data[0x2000] == 0xBB
        assert data[0x3000] == 0xCC
        assert data[0x3001] == 0xDD

    def test_load_save_roundtrip_complex(self, memory, tmp_path):
        """Complex roundtrip test with multiple ORG sections."""
        # Create test data with multiple ORG sections
        test_data = [
            (0x0000, b'\x01\x02\x03\x04'),
            (0x1000, b'\xAA\xBB\xCC'),
            (0x8000, b'\x55\x66\x77\x88\x99'),
            (0xFFFC, b'\xEE\xFF')  # Near end
        ]

        # Load all sections
        for org_addr, data in test_data:
            temp_file = tmp_path / f"temp_{org_addr}.bin"
            temp_file.write_bytes(data)
            memory.load_with_org_info(str(temp_file), org_address=org_addr)

        # Save and reload
        roundtrip_file = tmp_path / "roundtrip.bin"
        memory.save(str(roundtrip_file))

        # Create new memory and load
        from nova_memory import Memory
        new_memory = Memory()

        new_memory.load_with_org_info(str(roundtrip_file))

        # Verify all data is preserved
        for org_addr, data in test_data:
            for i, expected in enumerate(data):
                assert new_memory.read_byte(org_addr + i) == expected


class TestMemorySpriteIntegrationEdgeCases:
    """Aggressive testing of sprite memory integration."""

    def test_sprite_memory_bounds(self, memory):
        """Test sprite memory access at boundaries."""
        # Sprite memory base is 0xF000, end is 0xF0FF (256 bytes, 16 sprites × 16 bytes)

        # Test writing to sprite memory
        memory.write_byte(0xF000, 0x12)  # Sprite 0, data address high byte
        memory.write_byte(0xF001, 0x34)  # Sprite 0, data address low byte
        assert memory.read_byte(0xF000) == 0x12
        assert memory.read_byte(0xF001) == 0x34

        # Test last sprite
        memory.write_byte(0xF0F0, 0xAA)  # Sprite 15, first byte
        assert memory.read_byte(0xF0F0) == 0xAA

    def test_sprite_memory_overflow(self, memory):
        """Test writing beyond sprite memory bounds."""
        # Should still work as it's regular memory
        memory.write_byte(0xF100, 0xBB)  # Beyond sprite memory
        assert memory.read_byte(0xF100) == 0xBB

    def test_sprite_data_address_edge_cases(self, memory):
        """Test sprite data addresses at memory boundaries."""
        # Set sprite data address to 0x0000
        memory.write_word(0xF000, 0x0000)
        assert memory.read_word(0xF000) == 0x0000

        # Set sprite data address to 0xFFFF
        memory.write_word(0xF010, 0xFFFF)  # Sprite 1
        assert memory.read_word(0xF010) == 0xFFFF

        # Set sprite data address beyond memory
        memory.write_word(0xF020, 0x10000)  # Would be truncated
        assert memory.read_word(0xF020) == 0x0000  # Should wrap or truncate