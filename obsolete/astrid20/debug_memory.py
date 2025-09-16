#!/usr/bin/env python3
"""
Debug the memory function issue specifically
"""

import os
import sys

# Add the src directory to the path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from astrid2.builtin.system import SystemBuiltins

def test_memory_functions():
    """Test the memory builtin functions directly."""
    
    system = SystemBuiltins()
    
    try:
        # Test with integer values (should work)
        print("Testing memory_write with integer values:")
        result = system._memory_write(0x2000, 123)
        print(result)
        
        print("\nTesting memory_read with integer values:")
        result = system._memory_read(0x2000)
        print(result)
        
        # Test with string values (should fail)
        print("\nTesting memory_write with string values:")
        result = system._memory_write("0x2000", "123")  # This should fail
        print(result)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_memory_functions()
