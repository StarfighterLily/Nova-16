"""
Nova-16 Memory — 64KB unified memory with single hot-region view.

Phase 5 of the reimplantation strategy:
- Removes zero_page_cache, interrupt_vector_cache, LRU cache
- Single numpy view ``self._hot = self.memory[0:0x0120]`` for hot region
- Event-bus notification for SCB (sprite control block) writes
- No dirty-tracking, no writeback logic, no cache invalidation

Optimization Phase (Performance):
- Added read_byte_fast() / write_byte_fast() — skip bounds checking
- Added read_word_fast() / write_word_fast() — fast-path word access
- Optimized existing methods with local references
- Added simple instruction cache for recently fetched opcodes
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional

import numpy as np

if TYPE_CHECKING:
    from nova.bus.eventbus import EventBus


class Memory:
    """64KB unified memory with single hot-region view.

    The hot region (0x0000-0x011F) covers:
      - Zero page (0x0000-0x00FF) — fast access for frequently used variables
      - Interrupt vectors (0x0100-0x011F) — 8 vectors × 4 bytes each

    It is implemented as a numpy *view* into the main array — zero-copy and
    auto-synchronising.

    The Sprite Control Block region (0xF000-0xF0FF) is monitored: any write
    to that region publishes a ``memory.scb_written`` event on the bus so
    the graphics subsystem can update its sprite state.
    """

    SIZE = 65536          # 64 KB
    HOT_END = 0x0120      # zero page (256) + IVT (32)
    SCB_START = 0xF000
    SCB_END = 0xF100

    # Instruction cache size (number of entries)
    ICACHE_SIZE = 64

    def __init__(self, bus: Optional[EventBus] = None):
        self.bus = bus
        self.size = self.SIZE
        self.memory = np.zeros(self.size, dtype=np.uint8)

        # Single hot-region view — zero-copy, auto-synchronising with memory
        self._hot = self.memory[0:self.HOT_END]

        # Local references for fast-path access (avoid attribute lookups)
        self._mem = self.memory
        self._hot_end = self.HOT_END
        self._scb_start = self.SCB_START
        self._scb_end = self.SCB_END

        # Simple instruction cache: maps address -> opcode byte
        # Only caches opcode fetches (not operand reads)
        self._icache = {}
        self._icache_max = self.ICACHE_SIZE

    # ── Byte reads ─────────────────────────────────────────────────────

    def read_byte(self, address: int) -> int:
        """O(1) single-byte read — fast path via hot view."""
        if address < 0 or address >= self.size:
            raise IndexError(f"Address out of bounds: 0x{address:04X}")

        if address < self._hot_end:
            return int(self._hot[address])
        return int(self._mem[address])

    def read_byte_fast(self, address: int) -> int:
        """Fast-path single-byte read — no bounds checking.
        
        Caller MUST ensure address is in range 0..SIZE-1.
        """
        if address < self._hot_end:
            return int(self._hot[address])
        return int(self._mem[address])

    def read_bytes_direct(self, address: int, count: int) -> list:
        """Read *count* bytes starting at *address* as a list of ints."""
        if address < 0:
            raise IndexError(f"Read address out of bounds: 0x{address:04X}")
        if count < 0:
            raise ValueError(f"Read count must be non-negative: {count}")
        if address + count > self.size:
            raise IndexError(
                f"Read beyond memory bounds: 0x{address + count:04X} > "
                f"0x{self.size:04X}"
            )

        return self._mem[address:address + count].tolist()

    # ── Word reads (big-endian) ─────────────────────────────────────────

    def read_word(self, address: int) -> int:
        """O(1) 16-bit big-endian read."""
        if address < 0:
            raise IndexError(f"Address out of bounds for word read: 0x{address:04X}")
        if address >= self.size - 1:
            if address == self.size - 1:
                return int(self._mem[address]) & 0xFF
            raise IndexError(f"Address out of bounds for word read: 0x{address:04X}")

        high = self.read_byte(address)
        low = self.read_byte(address + 1)
        return (high << 8) | low

    def read_word_fast(self, address: int) -> int:
        """Fast-path 16-bit big-endian read — no bounds checking.
        
        Caller MUST ensure address is in range 0..SIZE-2.
        """
        high = self.read_byte_fast(address)
        low = self.read_byte_fast(address + 1)
        return (high << 8) | low

    # ── Byte writes ─────────────────────────────────────────────────────

    def write_byte(self, address: int, value: int):
        """O(1) single-byte write — hot region auto-updates via shared view.

        Publishes ``memory.scb_written`` if the write targets the SCB region
        (0xF000-0xF0FF). Invalidates instruction cache entry.
        """
        if address < 0 or address >= self.size:
            raise IndexError(f"Address out of bounds: 0x{address:04X}")

        val = int(value) & 0xFF
        self._mem[address] = val

        # Invalidate instruction cache for this address (it may have been cached)
        if address in self._icache:
            del self._icache[address]

        # Notify SCB region writes via event bus
        if self.bus and self._scb_start <= address < self._scb_end:
            self.bus.publish('memory.scb_written', address)

    def write_byte_fast(self, address: int, value: int):
        """Fast-path single-byte write — no bounds check, no SCB notification.
        
        Caller MUST ensure address is in range 0..SIZE-1 and that the write
        does NOT target the SCB region (0xF000-0xF0FF).
        """
        self._mem[address] = value & 0xFF

    def write_bytes_direct(self, address: int, data):
        """Write multiple bytes directly to memory.

        Args:
            address: Starting address.
            data: Iterable of byte values.
        """
        if address < 0 or address + len(data) > self.size:
            raise IndexError(
                f"Write beyond memory bounds: 0x{address + len(data):04X} > "
                f"0x{self.size:04X}"
            )
        if not data:
            return

        byte_array = np.fromiter(
            ((int(byte) & 0xFF) for byte in data),
            dtype=np.uint8, count=len(data),
        )
        self._mem[address:address + len(data)] = byte_array

        # Invalidate instruction cache for the written range
        for addr in range(address, address + len(data)):
            if addr in self._icache:
                del self._icache[addr]

        # Notify SCB region writes
        if self.bus and address < self._scb_end and address + len(data) > self._scb_start:
            notify_start = max(address, self._scb_start)
            notify_end = min(address + len(data), self._scb_end)
            for addr in range(notify_start, notify_end):
                self.bus.publish('memory.scb_written', addr)

    # ── Word writes (big-endian) ────────────────────────────────────────

    def write_word(self, address: int, value: int):
        """O(1) 16-bit big-endian write."""
        if address < 0 or address >= self.size - 1:
            raise IndexError(f"Address out of bounds for word write: 0x{address:04X}")

        val = int(value) & 0xFFFF

        # Notify SCB region writes via bus
        if self.bus and self._scb_start <= address < self._scb_end:
            self.bus.publish('memory.scb_written', address)
            if (address + 1) < self._scb_end:
                self.bus.publish('memory.scb_written', address + 1)

        # Big-endian: high byte first, low byte second
        self._mem[address] = (val >> 8) & 0xFF
        self._mem[address + 1] = val & 0xFF

    def write_word_fast(self, address: int, value: int):
        """Fast-path 16-bit big-endian write — no bounds check, no SCB notification.
        
        Caller MUST ensure address is in range 0..SIZE-2 and that the write
        does NOT target the SCB region.
        """
        val = int(value) & 0xFFFF
        self._mem[address] = int((val >> 8) & 0xFF)
        self._mem[address + 1] = int(val & 0xFF)

    # ── Instruction cache ───────────────────────────────────────────────

    def fetch_opcode(self, address: int) -> int:
        """Fetch an opcode byte with simple instruction caching."""
        # Check instruction cache first
        cached = self._icache.get(address)
        if cached is not None:
            return cached

        # Cache miss — read from memory
        opcode = self.read_byte_fast(address)

        # Add to cache (simple FIFO eviction if full)
        if len(self._icache) >= self._icache_max:
            # Remove oldest entry (dict preserves insertion order in Python 3.7+)
            self._icache.pop(next(iter(self._icache)))
        self._icache[address] = opcode

        return opcode

    def invalidate_icache(self):
        """Clear the instruction cache (call when PC jumps non-sequentially)."""
        self._icache.clear()

    # ── Legacy aliases ──────────────────────────────────────────────────

    def write(self, address: int, value: int, bytes: int = 1):
        """Legacy write alias — delegates to write_byte / write_word."""
        if bytes == 1:
            self.write_byte(address, value)
        elif bytes == 2:
            self.write_word(address, value)
        else:
            for i in range(bytes):
                shift = 8 * (bytes - 1 - i)
                self.write_byte(address + i, (value >> shift) & 0xFF)

    def read(self, address: int, bytes: int = 1):
        """Legacy read alias — returns numpy array."""
        if address < 0 or address + bytes > self.size:
            raise IndexError(f"Read address out of bounds: 0x{address:04X}")

        if bytes == 1:
            return np.array([self.read_byte(address)])
        else:
            result = [self.read_byte(address + i) for i in range(bytes)]
            return np.array(result)

    # ── Binary loading (with ORG support) ───────────────────────────────

    def load(self, file_path: str) -> int:
        """Load a binary file into memory.

        If a corresponding ``.org`` file exists, segment-aware loading is
        performed.  Returns the entry point address (first ORG segment's
        start address, or 0x0000 if no .org file).
        """
        if not file_path:
            return 0x0000
        file_path = str(file_path)

        # Check if there's a corresponding .org file with segment information
        org_file_path = file_path.replace('.bin', '.org')
        try:
            with open(org_file_path, 'r') as org_file:
                return self.load_with_org_info(file_path, org_file_path)
        except FileNotFoundError:
            pass

        # Legacy loading: load binary starting at address 0x0000
        with open(file_path, 'rb') as file:
            data = file.read()
            load_size = min(len(data), self.size)
            if load_size:
                self._mem[:load_size] = np.frombuffer(
                    data[:load_size], dtype=np.uint8
                )

        # Notify about SCB region writes
        if self.bus and load_size > 0 and 0x0000 < self._scb_end:
            notify_end = min(load_size, self._scb_end)
            for addr in range(max(0x0000, self._scb_start), notify_end):
                if self._scb_start <= addr < self._scb_end:
                    self.bus.publish('memory.scb_written', addr)

        return 0x0000

    def load_with_org_info(self, bin_file_path: str, org_file_path: str) -> int:
        """Load a binary file using ORG segment information.

        The ``.org`` file contains lines with::

            <start_address> <length> <offset_in_bin_file>

        Returns the entry point (first segment's start address).
        """
        print(f"Loading {bin_file_path} with ORG information from {org_file_path}")

        with open(bin_file_path, 'rb') as bin_file:
            bin_data = bin_file.read()

        entry_point = 0x0000
        first_segment = True

        with open(org_file_path, 'r', encoding='utf-8') as org_file:
            for line_num, line in enumerate(org_file, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                try:
                    parts = line.split()
                    if len(parts) != 3:
                        raise ValueError(
                            f"Invalid format in {org_file_path} line "
                            f"{line_num}: {line}"
                        )

                    start_addr = int(parts[0], 16)
                    length = int(parts[1])
                    bin_offset = int(parts[2])

                    if first_segment:
                        entry_point = start_addr
                        first_segment = False

                    if start_addr + length > self.size:
                        raise ValueError(
                            f"Segment at 0x{start_addr:04X} extends beyond "
                            f"memory size"
                        )
                    if bin_offset + length > len(bin_data):
                        raise ValueError(
                            f"Binary offset {bin_offset} + {length} exceeds "
                            f"binary file size"
                        )

                    segment_data = bin_data[bin_offset:bin_offset + length]
                    if length:
                        self._mem[start_addr:start_addr + length] = \
                            np.frombuffer(segment_data, dtype=np.uint8)

                    # Notify about SCB region writes
                    if (self.bus and start_addr < self._scb_end
                            and start_addr + length > self._scb_start):
                        notify_start = max(start_addr, self._scb_start)
                        notify_end = min(start_addr + length, self._scb_end)
                        for addr in range(notify_start, notify_end):
                            self.bus.publish('memory.scb_written', addr)

                    print(
                        f"Loaded {length} bytes at 0x{start_addr:04X} "
                        f"from binary offset {bin_offset}"
                    )

                except ValueError as e:
                    raise ValueError(
                        f"Error parsing {org_file_path} line {line_num}: {e}"
                    )
                except Exception as e:
                    raise ValueError(
                        f"Unexpected error loading segment from line "
                        f"{line_num}: {e}"
                    )

        return entry_point

    def load_binary(self, binary_data, address: int = 0x0000) -> int:
        """Load binary data directly into memory at *address*.

        Accepts a file path (str) or raw bytes.  Returns the load address.
        """
        if isinstance(binary_data, str):
            with open(binary_data, 'rb') as f:
                binary_data = f.read()

        if address < 0 or address > self.size:
            raise IndexError(f"Load address out of bounds: 0x{address:04X}")

        load_size = min(len(binary_data), self.size - address)
        if load_size:
            self._mem[address:address + load_size] = np.frombuffer(
                binary_data[:load_size], dtype=np.uint8
            )

            # Notify about SCB region writes
            if (self.bus and address < self._scb_end
                    and address + load_size > self._scb_start):
                notify_start = max(address, self._scb_start)
                notify_end = min(address + load_size, self._scb_end)
                for addr in range(notify_start, notify_end):
                    self.bus.publish('memory.scb_written', addr)

        return address

    def load_program(self, program_data, address: int = 0x0000) -> int:
        """Load program data (list of bytes) into memory at *address*.

        Used for unit testing with raw instruction bytes.
        """
        if isinstance(program_data, list):
            program_data = bytes(program_data)

        if address < 0 or address > self.size:
            raise IndexError(f"Load address out of bounds: 0x{address:04X}")

        load_size = min(len(program_data), self.size - address)
        if load_size:
            self._mem[address:address + load_size] = np.frombuffer(
                program_data[:load_size], dtype=np.uint8
            )

            # Notify about SCB region writes
            if (self.bus and address < self._scb_end
                    and address + load_size > self._scb_start):
                notify_start = max(address, self._scb_start)
                notify_end = min(address + load_size, self._scb_end)
                for addr in range(notify_start, notify_end):
                    self.bus.publish('memory.scb_written', addr)

        return address

    # ── Dump / save / reset ─────────────────────────────────────────────

    def dump(self):
        """Hex dump the full memory contents (debug helper)."""
        for i in range(0, self.size, 16):
            hex_bytes = ' '.join(f"{byte:02X}" for byte in self._mem[i:i + 16])
            print(f"{i:04X}: {hex_bytes}")

    def save(self, file_path: str = None):
        """Save memory contents to a binary file.

        If *file_path* is None, opens a file-save dialog (tkinter).
        """
        if not file_path:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            file_path = filedialog.asksaveasfilename(
                filetypes=[("Binary files", "*.bin")]
            )
            root.destroy()
        if not file_path:
            return
        with open(file_path, 'wb') as file:
            file.write(bytes(self._mem))

    def reset(self):
        """Clear backing memory and publish ``memory.reset`` event."""
        self._mem.fill(0)
        self._icache.clear()
        if self.bus:
            self.bus.publish('memory.reset')

    # ── Legacy cache stubs (no-ops — caches eliminated in Phase 4) ──────

    def flush_cache(self):
        pass

    def ensure_memory_consistency(self):
        pass

    def get_cache_stats(self) -> dict:
        return {
            'cache_hits': 0,
            'cache_misses': 0,
            'total_cache_accesses': 0,
            'cache_hit_rate': 0,
            'zero_page_dirty': False,
            'interrupt_vector_dirty': False,
            'pending_write_back_count': 0,
            'lru_cache_size': 0,
        }