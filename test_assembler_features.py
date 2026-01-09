#!/usr/bin/env python3
"""Simple test script for assembler features"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from nova_assembler import Assembler

def test_include():
    print("Testing INCLUDE directive...")
    assembler = Assembler()
    success = assembler.assemble("tests/integration/include_test.asm")
    assert success, "Assembly failed"
    assert os.path.exists("tests/integration/include_test.bin")
    assert os.path.exists("tests/integration/include_test.sym")

    with open("tests/integration/include_test.sym", 'r') as f:
        sym_content = f.read()
        assert "SUB_DATA" in sym_content
        assert "SUB_LABEL" in sym_content
        assert "MAIN_DATA" in sym_content
    print("✓ INCLUDE test passed")

def test_conditional():
    print("Testing conditional assembly...")
    assembler = Assembler()
    success = assembler.assemble("tests/integration/conditional_test.asm")
    assert success
    assert os.path.exists("tests/integration/conditional_test.bin")

    with open("tests/integration/conditional_test.sym", 'r') as f:
        sym_content = f.read()
        assert "DEBUG_MSG" in sym_content
        assert "TEST_DATA" in sym_content
    print("✓ Conditional test passed")

def test_ds():
    print("Testing DS directive...")
    assembler = Assembler()
    success = assembler.assemble("tests/integration/ds_test.asm")
    assert success
    assert os.path.exists("tests/integration/ds_test.bin")

    with open("tests/integration/ds_test.bin", 'rb') as f:
        data = f.read()
        assert len(data) == 24
        assert data[:10] == b'\x00' * 10
        assert data[10:13] == b'\x01\x02\x03'
        assert data[13:18] == b'\x00' * 5
    print("✓ DS test passed")

if __name__ == "__main__":
    test_include()
    test_conditional()
    test_ds()
    print("All tests passed!")