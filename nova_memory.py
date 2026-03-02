import numpy as np
from collections import OrderedDict

class Memory:
    def __init__( self, size = 65536 ):
        self.size = size
        self.memory = np.zeros( self.size, dtype=np.uint8 )
        self.timer = 0
        self.timer_limit = 256
        self.interrupt_enabled = False
        
        # Sprite system hook - will be set by CPU during initialization
        self.gfx_system = None

        # ========================================
        # MEMORY CACHING OPTIMIZATIONS - Phase 2
        # ========================================
        
        # Zero page cache (0x0000-0x00FF) - frequently accessed variables
        self.zero_page_cache = np.zeros(256, dtype=np.uint8)
        self.zero_page_dirty = False  # Track if cache needs sync to main memory
        
        # Interrupt vector cache (0x0100-0x011F) - 8 vectors × 4 bytes each
        self.interrupt_vector_cache = np.zeros(32, dtype=np.uint8)
        self.interrupt_vector_dirty = False
        
        # General purpose LRU cache for hot memory locations
        self.lru_cache = OrderedDict()  # {address: value}
        self.lru_cache_max_size = 512  # Cache up to 512 recently accessed bytes
        
        # Cache write-back optimization
        self.write_back_batch_size = 16  # Batch write operations
        self.pending_write_back = set()  # Addresses that need write-back
        
        # Cache statistics for performance monitoring
        self.cache_hits = 0
        self.cache_misses = 0

    # ========================================
    # CACHE MANAGEMENT METHODS
    # ========================================
    
    def _sync_zero_page_to_memory(self):
        """Sync zero page cache to main memory"""
        if self.zero_page_dirty:
            self.memory[0:256] = self.zero_page_cache
            self.zero_page_dirty = False
    
    def _sync_zero_page_from_memory(self):
        """Sync zero page cache from main memory"""
        self.zero_page_cache[:] = self.memory[0:256]
        self.zero_page_dirty = False
    
    def _sync_interrupt_vectors_to_memory(self):
        """Sync interrupt vector cache to main memory"""
        if self.interrupt_vector_dirty:
            self.memory[0x100:0x120] = self.interrupt_vector_cache
            self.interrupt_vector_dirty = False
    
    def _sync_interrupt_vectors_from_memory(self):
        """Sync interrupt vector cache from main memory"""
        self.interrupt_vector_cache[:] = self.memory[0x100:0x120]
        self.interrupt_vector_dirty = False
    
    def _lru_cache_get(self, address):
        """Get value from LRU cache if present"""
        if address in self.lru_cache:
            # Move to end (most recently used)
            self.lru_cache.move_to_end(address)
            self.cache_hits += 1
            return self.lru_cache[address]
        self.cache_misses += 1
        return None
    
    def _lru_cache_put(self, address, value):
        """Put value in LRU cache"""
        if address in self.lru_cache:
            self.lru_cache.move_to_end(address)
        else:
            if len(self.lru_cache) >= self.lru_cache_max_size:
                # Remove least recently used
                self.lru_cache.popitem(last=False)
        self.lru_cache[address] = value
    
    def _lru_cache_invalidate(self, address):
        """Remove address from LRU cache"""
        if address in self.lru_cache:
            del self.lru_cache[address]
    
    def _sync_caches_after_load(self):
        """Sync caches with main memory after loading a program"""
        # Sync zero page cache
        self.zero_page_cache[:] = self.memory[0:256]
        self.zero_page_dirty = False
        
        # Sync interrupt vector cache
        self.interrupt_vector_cache[:] = self.memory[0x100:0x120]
        self.interrupt_vector_dirty = False
        
        # Clear LRU cache since memory content has changed
        self.lru_cache.clear()
        self.pending_write_back.clear()
    
    def _lazy_write_back(self):
        """Perform lazy write-back of dirty cache lines to main memory"""
        # Write back zero page if dirty
        if self.zero_page_dirty:
            self.memory[0:256] = self.zero_page_cache
            self.zero_page_dirty = False
        
        # Write back interrupt vectors if dirty
        if self.interrupt_vector_dirty:
            self.memory[0x100:0x120] = self.interrupt_vector_cache
            self.interrupt_vector_dirty = False
        
        # Write back pending LRU cache entries
        for addr in list(self.pending_write_back):
            if addr in self.lru_cache:
                self.memory[addr] = self.lru_cache[addr]
        
        self.pending_write_back.clear()
    
    def _check_write_back_needed(self):
        """Check if write-back is needed based on batch size"""
        if len(self.pending_write_back) >= self.write_back_batch_size:
            self._lazy_write_back()
    
    def flush_cache(self):
        """Force write-back of all dirty cache lines"""
        self._lazy_write_back()
    
    def ensure_memory_consistency(self):
        """Ensure memory consistency by flushing all caches before critical operations"""
        self.flush_cache()

    def write( self, address, value, bytes=1 ):
        # Check bounds
        if address < 0 or address + bytes > self.size:
            raise IndexError(f"Write address out of bounds: {address}")
        
        # Check if writing to sprite memory region (0xF000-0xF0FF)
        if 0xF000 <= address <= 0xF0FF and self.gfx_system:
            self.gfx_system.sprites_dirty = True  # Mark sprites as needing re-render
        
        if bytes == 1:
            self.write_byte(address, value, invalidate_cpu_cache=False)
        elif bytes == 2:
            # Big-endian for Nova-16: store high byte first, then low byte
            self.write_byte(address, (value >> 8) & 0xFF, invalidate_cpu_cache=False)
            self.write_byte(address + 1, value & 0xFF, invalidate_cpu_cache=False)
        else:
            # For multi-byte writes, store in big-endian order
            for i in range( bytes ):
                self.write_byte(address + i, (value >> (8 * (bytes - 1 - i))) & 0xFF, invalidate_cpu_cache=False)

        # Invalidate instruction cache and prefetch once per write operation
        if hasattr(self, 'cpu') and self.cpu:
            self.cpu.invalidate_instruction_cache()
            self.cpu.invalidate_prefetch()

    def read( self, address, bytes=1 ):
        address = int(address)
        bytes = int(bytes)
        if address < 0 or address + bytes > self.size:
            raise IndexError(f"Read address out of bounds: {address}")
        
        # For multi-byte reads, use the optimized byte-by-byte method for cache consistency
        if bytes == 1:
            return np.array([self.read_byte(address)])
        else:
            result = []
            for i in range(bytes):
                result.append(self.read_byte(address + i))
            return np.array(result)
    
    # ========================================
    # OPTIMIZED MEMORY ACCESS METHODS - Phase 1
    # ========================================
    
    def read_byte(self, address):
        """Optimized single byte read with lazy write-back caching"""
        addr = int(address)
        if addr < 0 or addr >= self.size:
            raise IndexError(f"Address out of bounds: {addr}")
        
        # Check zero page cache (0x0000-0x00FF)
        if 0 <= addr <= 0xFF:
            return int(self.zero_page_cache[addr])
        
        # Check interrupt vector cache (0x0100-0x011F)
        elif 0x100 <= addr <= 0x11F:
            return int(self.interrupt_vector_cache[addr - 0x100])
        
        # Check LRU cache first
        cached_value = self._lru_cache_get(addr)
        if cached_value is not None:
            return cached_value
        
        # Read from main memory and cache it
        value = int(self.memory[addr])
        self._lru_cache_put(addr, value)
        return value
    
    def read_word(self, address):
        """Optimized 16-bit read with caching (big-endian for Nova-16)"""
        addr = int(address)
        if addr < 0:
            raise IndexError(f"Address out of bounds for word read: {addr}")
        if addr >= self.size - 1:
            # For edge case where we're at the last byte, return just that byte as a word
            if addr == self.size - 1:
                return int(self.memory[addr]) & 0xFF
            else:
                raise IndexError(f"Address out of bounds for word read: {addr}")
        
        # For cached regions, read byte by byte to maintain cache consistency
        high_byte = self.read_byte(addr)
        low_byte = self.read_byte(addr + 1)
        return (high_byte << 8) | low_byte
    
    def write_byte(self, address, value, invalidate_cpu_cache=True):
        """Optimized single byte write with lazy write-back caching"""
        addr = int(address)
        if addr < 0 or addr >= self.size:
            raise IndexError(f"Address out of bounds: {addr}")
        
        val = int(value) & 0xFF
        
        # Check if writing to sprite memory region (0xF000-0xF0FF)
        if 0xF000 <= addr <= 0xF0FF and self.gfx_system:
            self.gfx_system.sprites_dirty = True
        
        # Update zero page cache (0x0000-0x00FF) - lazy write-back
        if 0 <= addr <= 0xFF:
            self.zero_page_cache[addr] = val
            self.zero_page_dirty = True
        
        # Update interrupt vector cache (0x0100-0x011F) - lazy write-back
        elif 0x100 <= addr <= 0x11F:
            self.interrupt_vector_cache[addr - 0x100] = val
            self.interrupt_vector_dirty = True
        
        else:
            # For non-cached regions, write directly to main memory
            self.memory[addr] = val
        
        # Update LRU cache and mark for lazy write-back
        self._lru_cache_put(addr, val)
        self.pending_write_back.add(addr)
        
        # Check if we need to do write-back
        self._check_write_back_needed()
        
        # Invalidate instruction cache and prefetch if CPU exists (for self-modifying code)
        if invalidate_cpu_cache and hasattr(self, 'cpu') and self.cpu:
            self.cpu.invalidate_instruction_cache()
            self.cpu.invalidate_prefetch()
    
    def write_word(self, address, value):
        """Optimized 16-bit write with caching (big-endian for Nova-16)"""
        addr = int(address)
        if addr < 0 or addr >= self.size - 1:
            raise IndexError(f"Address out of bounds for word write: {addr}")
        
        # Check if writing to sprite memory region (0xF000-0xF0FF)
        if 0xF000 <= addr <= 0xF0FF and self.gfx_system:
            self.gfx_system.sprites_dirty = True
            
        val = int(value) & 0xFFFF  # Ensure value is within 16-bit bounds
        
        # Write byte by byte to maintain cache consistency
        self.write_byte(addr, (val >> 8) & 0xFF, invalidate_cpu_cache=False)      # High byte first
        self.write_byte(addr + 1, val & 0xFF, invalidate_cpu_cache=False)         # Low byte second

        # Invalidate instruction cache and prefetch once per write operation
        if hasattr(self, 'cpu') and self.cpu:
            self.cpu.invalidate_instruction_cache()
            self.cpu.invalidate_prefetch()
    
    def read_bytes_direct(self, address, count):
        """Optimized multi-byte read returning list of ints"""
        if address + count > self.size:
            raise IndexError(f"Read beyond memory bounds: {address + count} > {self.size}")
        
        # Ensure cache consistency for direct reads
        self.flush_cache()
        
        return [int(self.memory[address + i]) for i in range(count)]

    def dump( self ):
        for i in range( 0, self.size, 16 ):
            hex_bytes = ' '.join( f"{byte:02X}" for byte in self.memory[i:i+16] )
            print( f"{i:04X}: {hex_bytes}" )

    def load( self, file_path ):
        """
        Loads a binary file into memory from the given file path.
        If a corresponding .org file exists, uses that for ORG-aware loading.
        Returns the entry point address (first ORG address, or 0x0000 if none).
        """
        if not file_path:
            return 0x0000
            
        # Clear LRU cache before loading new program
        self.lru_cache.clear()
        
        # Check if there's a corresponding .org file with segment information
        org_file_path = file_path.replace('.bin', '.org')
        try:
            with open(org_file_path, 'r') as org_file:
                return self.load_with_org_info(file_path, org_file_path)
        except FileNotFoundError:
            # Fall back to legacy loading
            pass
            
        # Legacy loading: load binary starting at address 0x0000
        with open( file_path, 'rb' ) as file:
            data = file.read()
            # Determine how much data to load to avoid buffer overflows
            load_size = min( len( data ), self.size )
            # Convert bytes to numpy array and copy to memory
            for i in range(load_size):
                self.memory[i] = data[i]
        
        # Sync caches after loading
        self._sync_caches_after_load()
        
        return 0x0000
    
    def load_with_org_info(self, bin_file_path, org_file_path):
        """
        Loads a binary file using ORG segment information.
        The .org file contains lines with: <start_address> <length> <offset_in_bin_file>
        Returns the entry point (first segment's start address).
        """
        print(f"Loading {bin_file_path} with ORG information from {org_file_path}")
        
        # Clear LRU cache before loading new program
        self.lru_cache.clear()
        
        # Read the binary data
        with open(bin_file_path, 'rb') as bin_file:
            bin_data = bin_file.read()
        
        entry_point = 0x0000
        first_segment = True
        
        # Read the ORG segment information
        with open(org_file_path, 'r', encoding='utf-8') as org_file:
            for line_num, line in enumerate(org_file, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                try:
                    parts = line.split()
                    if len(parts) != 3:
                        raise ValueError(f"Invalid format in {org_file_path} line {line_num}: {line}")
                        
                    start_addr = int(parts[0], 16)
                    length = int(parts[1])
                    bin_offset = int(parts[2])
                    
                    # First segment becomes the entry point
                    if first_segment:
                        entry_point = start_addr
                        first_segment = False
                    
                    # Validate bounds
                    if start_addr + length > self.size:
                        raise ValueError(f"Segment at 0x{start_addr:04X} extends beyond memory size")
                        
                    if bin_offset + length > len(bin_data):
                        raise ValueError(f"Binary offset {bin_offset} + {length} exceeds binary file size")
                    
                    # Load this segment
                    segment_data = bin_data[bin_offset:bin_offset + length]
                    # Use a more reliable method to copy the data
                    for i in range(length):
                        self.memory[start_addr + i] = segment_data[i]
                    
                    print(f"Loaded {length} bytes at 0x{start_addr:04X} from binary offset {bin_offset}")
                    
                except ValueError as e:
                    raise ValueError(f"Error parsing {org_file_path} line {line_num}: {e}")
                except Exception as e:
                    raise ValueError(f"Unexpected error loading segment from line {line_num}: {e}")
        
        # Sync caches after loading
        self._sync_caches_after_load()
        
        return entry_point


    def save( self, file_path ):
        # This part still uses a file dialog if no path is given.
        # For consistency, you might refactor it like the load function.
        if not file_path:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            file_path = filedialog.asksaveasfilename( filetypes=[ ( "Binary files", "*.bin" ) ] )
            root.destroy()
        if not file_path:
            return
        with open( file_path, 'wb' ) as file:
            file.write( bytes( self.memory ) )

    def load_binary(self, binary_data, address=0x0000):
        """
        Load binary data directly into memory at the specified address.
        Used for loading assembled programs from assembler output.
        """
        if isinstance(binary_data, str):
            # If it's a string, assume it's a file path
            with open(binary_data, 'rb') as f:
                binary_data = f.read()
        
        # Ensure we don't overflow memory
        load_size = min(len(binary_data), self.size - address)
        self.memory[address:address + load_size] = binary_data[:load_size]
        return address

    def load_program(self, program_data, address=0x0000):
        """
        Load program data (list of bytes) into memory at the specified address.
        Used for unit testing with raw instruction bytes.
        """
        if isinstance(program_data, list):
            program_data = bytes(program_data)
        
        # Ensure we don't overflow memory
        load_size = min(len(program_data), self.size - address)
        self.memory[address:address + load_size] = np.frombuffer(program_data[:load_size], dtype=np.uint8)
        
        # Sync caches after loading
        self._sync_caches_after_load()
        
        return address

    def get_cache_stats(self):
        """Get cache performance statistics"""
        total_accesses = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_accesses * 100) if total_accesses > 0 else 0
        
        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'total_cache_accesses': total_accesses,
            'cache_hit_rate': hit_rate,
            'zero_page_dirty': self.zero_page_dirty,
            'interrupt_vector_dirty': self.interrupt_vector_dirty,
            'pending_write_back_count': len(self.pending_write_back),
            'lru_cache_size': len(self.lru_cache)
        }

    def write_bytes_direct(self, address, data):
        """Write multiple bytes directly to memory"""
        if address + len(data) > self.size:
            raise IndexError(f"Write beyond memory bounds: {address + len(data)} > {self.size}")
        for i, byte in enumerate(data):
            self.memory[address + i] = byte & 0xFF