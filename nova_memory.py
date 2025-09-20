import numpy as np

class Memory:
    def __init__( self, size = 65536 ):
        self.size = size
        self.memory = np.zeros( self.size, dtype=np.uint8 )
        self.timer = 0
        self.timer_limit = 256
        self.interrupt_enabled = False
        
        # Sprite system hook - will be set by CPU during initialization
        self.gfx_system = None

    def write( self, address, value, bytes=1 ):
        # Check bounds
        if address < 0 or address + bytes > self.size:
            raise IndexError(f"Write address out of bounds: {address}")
        
        # Check if writing to sprite memory region (0xF000-0xF0FF)
        if 0xF000 <= address <= 0xF0FF and self.gfx_system:
            self.gfx_system.sprites_dirty = True  # Mark sprites as needing re-render
        
        if bytes == 1:
            self.memory[ address ] = value & 0xFF
        elif bytes == 2:
            # Big-endian for Nova-16: store high byte first, then low byte
            self.memory[ address ] = ( value >> 8 ) & 0xFF
            self.memory[ address + 1 ] = value & 0xFF
        else:
            # For multi-byte writes, store in big-endian order
            for i in range( bytes ):
                self.memory[ address + i ] = ( value >> ( 8 * (bytes - 1 - i) ) ) & 0xFF

    def read( self, address, bytes=1 ):
        address = int(address)
        bytes = int(bytes)
        if address < 0 or address + bytes > self.size:
            raise IndexError(f"Read address out of bounds: {address}")
        return self.memory[ address:address + bytes ]
    
    # ========================================
    # OPTIMIZED MEMORY ACCESS METHODS - Phase 1
    # ========================================
    
    def read_byte(self, address):
        """Optimized single byte read without array overhead"""
        addr = int(address)
        if addr < 0 or addr >= self.size:
            raise IndexError(f"Address out of bounds: {addr}")
        return int(self.memory[addr]) & 0xFF
    
    def read_word(self, address):
        """Optimized 16-bit read without array overhead (big-endian for Nova-16)"""
        addr = int(address)
        if addr < 0:
            raise IndexError(f"Address out of bounds for word read: {addr}")
        if addr >= self.size - 1:
            # For edge case where we're at the last byte, return just that byte as a word
            if addr == self.size - 1:
                return int(self.memory[addr]) & 0xFF
            else:
                raise IndexError(f"Address out of bounds for word read: {addr}")
        
        high_byte = int(self.memory[addr]) & 0xFF
        low_byte = int(self.memory[addr + 1]) & 0xFF
        return (high_byte << 8) | low_byte
    
    def write_byte(self, address, value):
        """Optimized single byte write without method overhead"""
        addr = int(address) & 0xFFFF  # Ensure address is within 16-bit bounds
        
        # Check if writing to sprite memory region (0xF000-0xF0FF)
        if 0xF000 <= addr <= 0xF0FF and self.gfx_system:
            self.gfx_system.sprites_dirty = True
            
        self.memory[addr] = int(value) & 0xFF
    
    def write_word(self, address, value):
        """Optimized 16-bit write without method overhead (big-endian for Nova-16)"""
        addr = int(address)
        if addr < 0 or addr >= self.size - 1:
            raise IndexError(f"Address out of bounds for word write: {addr}")
        
        # Check if writing to sprite memory region (0xF000-0xF0FF)
        if 0xF000 <= addr <= 0xF0FF and self.gfx_system:
            self.gfx_system.sprites_dirty = True
            
        val = int(value) & 0xFFFF  # Ensure value is within 16-bit bounds
        self.memory[addr] = (val >> 8) & 0xFF      # High byte first
        self.memory[addr + 1] = val & 0xFF         # Low byte second
    
    def read_bytes_direct(self, address, count):
        """Optimized multi-byte read returning list of ints"""
        if address + count > self.size:
            raise IndexError(f"Read beyond memory bounds: {address + count} > {self.size}")
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
        return 0x0000
    
    def load_with_org_info(self, bin_file_path, org_file_path):
        """
        Loads a binary file using ORG segment information.
        The .org file contains lines with: <start_address> <length> <offset_in_bin_file>
        Returns the entry point (first segment's start address).
        """
        print(f"Loading {bin_file_path} with ORG information from {org_file_path}")
        
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
                    print(f"Error parsing {org_file_path} line {line_num}: {e}")
                except Exception as e:
                    print(f"Unexpected error loading segment from line {line_num}: {e}")
        
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

    def write_bytes_direct(self, address, data):
        """Write multiple bytes directly to memory"""
        if address + len(data) > self.size:
            raise IndexError(f"Write beyond memory bounds: {address + len(data)} > {self.size}")
        for i, byte in enumerate(data):
            self.memory[address + i] = byte & 0xFF