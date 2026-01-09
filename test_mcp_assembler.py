#!/usr/bin/env python3
"""
Test script for Nova-16 MCP server assembler tool
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from nova_mcp_server import _handle_assemble

def test_assembler_success():
    """Test successful assembly"""
    # Create a simple valid assembly file
    with open('test_success.asm', 'w') as f:
        f.write('ORG 0x0000\nMOV R0, 42\nHLT\n')

    result = _handle_assemble({"source_path": "test_success.asm"})
    print("Success test result:", result)

    # Clean up
    os.remove('test_success.asm')
    if os.path.exists('test_success.bin'):
        os.remove('test_success.bin')
    if os.path.exists('test_success.org'):
        os.remove('test_success.org')
    if os.path.exists('test_success.sym'):
        os.remove('test_success.sym')

def test_assembler_failure():
    """Test failed assembly"""
    # Create a failing assembly file
    with open('test_failure.asm', 'w') as f:
        f.write('ORG 0x0000\nINVALID_INSTRUCTION R0, R1\nHLT\n')

    result = _handle_assemble({"source_path": "test_failure.asm"})
    print("Failure test result:", result)

    # Clean up
    os.remove('test_failure.asm')
    # Don't remove .bin/.org/.sym as they might not be created on failure

if __name__ == "__main__":
    print("Testing Nova-16 MCP server assembler tool...")

    # Initialize emulator (required for _handle_assemble)
    from nova_mcp_server import initialize_emulator
    initialize_emulator()

    test_assembler_success()
    test_assembler_failure()

    print("Tests completed.")