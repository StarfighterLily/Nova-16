#!/usr/bin/env python3
"""
Test file I/O functionality in FORTH
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from forth.forth_interpreter import ForthInterpreter

def test_file_io():
    """Test file I/O operations"""
    forth = ForthInterpreter()
    
    print("Testing FORTH File I/O...")
    
    # Test opening a file for reading
    print("\n1. Testing OPEN-FILE for reading...")
    forth.interpret('S" test_file.txt"')
    
    # Check what S" pushed
    length = forth.pop_param()
    addr = forth.pop_param()
    print(f"S\" pushed: addr={addr}, length={length}")
    
    # Read the string
    filename = ""
    for i in range(length):
        char = forth.memory.read_byte(addr + i)
        filename += chr(char)
    print(f"Filename from memory: '{filename}'")
    
    # Now push back and call OPEN-FILE
    forth.push_param(addr)
    forth.push_param(length)
    forth.push_param(0)  # fam = read
    forth.word_open_file()
    
    # Check stack
    ior = forth.pop_param()
    fileid = forth.pop_param()
    print(f"OPEN-FILE result: fileid={fileid}, ior={ior}")
    
    if ior == 0:
        print("File opened successfully")
        
        # Test reading from file
        print("\n2. Testing READ-FILE...")
        # Allocate buffer in memory
        buffer_addr = forth.here
        forth.here += 100  # 100 byte buffer
        
        forth.push_param(buffer_addr)  # c-addr
        forth.push_param(50)  # u1 (read up to 50 bytes)
        forth.push_param(fileid)  # fileid
        forth.word_read_file()
        
        ior = forth.pop_param()
        bytes_read = forth.pop_param()
        print(f"READ-FILE result: bytes_read={bytes_read}, ior={ior}")
        
        if ior == 0 and bytes_read > 0:
            # Read the data from memory
            data = ""
            for i in range(bytes_read):
                char = forth.memory.read_byte(buffer_addr + i)
                data += chr(char)
            print(f"Data read: '{data}'")
        
        # Test closing file
        print("\n3. Testing CLOSE-FILE...")
        forth.push_param(fileid)
        forth.word_close_file()
        ior = forth.pop_param()
        print(f"CLOSE-FILE result: ior={ior}")
        
    else:
        print("Failed to open file")
    
    # Test writing to a file
    print("\n4. Testing WRITE-FILE...")
    forth.interpret('S" output.txt" 1 OPEN-FILE')  # Open for writing
    
    ior = forth.pop_param()
    fileid = forth.pop_param()
    print(f"OPEN-FILE for writing: fileid={fileid}, ior={ior}")
    
    if ior == 0:
        # Write some data
        test_data = "Hello from FORTH!"
        data_addr = forth.here
        
        # Store test data in memory
        for i, char in enumerate(test_data):
            forth.memory.write_byte(data_addr + i, ord(char))
        
        forth.push_param(data_addr)  # c-addr
        forth.push_param(len(test_data))  # u
        forth.push_param(fileid)  # fileid
        forth.word_write_file()
        
        ior = forth.pop_param()
        print(f"WRITE-FILE result: ior={ior}")
        
        # Close file
        forth.push_param(fileid)
        forth.word_close_file()
        print("File closed after writing")
    
    print("\nFile I/O test completed!")

if __name__ == "__main__":
    test_file_io()
