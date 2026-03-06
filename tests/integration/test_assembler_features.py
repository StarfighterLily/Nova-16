import pytest
import os
import tempfile
from nova_assembler import Assembler


@pytest.mark.assembler
def test_include_directive():
    """Test INCLUDE directive"""
    assembler = Assembler()
    success = assembler.assemble("tests/integration/include_test.asm")
    assert success
    assert os.path.exists("tests/integration/include_test.bin")
    assert os.path.exists("tests/integration/include_test.sym")

    # Check symbol table contains symbols from included file
    with open("tests/integration/include_test.sym", 'r') as f:
        sym_content = f.read()
        assert "SUB_DATA" in sym_content
        assert "SUB_LABEL" in sym_content
        assert "MAIN_DATA" in sym_content


@pytest.mark.assembler
def test_conditional_assembly():
    """Test conditional assembly directives"""
    assembler = Assembler()
    success = assembler.assemble("tests/integration/conditional_test.asm")
    assert success
    assert os.path.exists("tests/integration/conditional_test.bin")

    # Check that DEBUG_MSG is included since DEBUG is defined
    with open("tests/integration/conditional_test.sym", 'r') as f:
        sym_content = f.read()
        assert "DEBUG_MSG" in sym_content
        assert "TEST_DATA" in sym_content  # Since RELEASE not defined


@pytest.mark.assembler
def test_ds_directive():
    """Test DS directive for defining space"""
    assembler = Assembler()
    success = assembler.assemble("tests/integration/ds_test.asm")
    assert success
    assert os.path.exists("tests/integration/ds_test.bin")

    # Check binary size: 10 (DS) + 3 (DB) + 5 (DS) + 5 (MOV R0, BUFFER) + 1 (HLT) = 24 bytes
    with open("tests/integration/ds_test.bin", 'rb') as f:
        data = f.read()
        assert len(data) == 24
        # First 10 bytes should be 0 (DS 10)
        assert data[:10] == b'\x00' * 10
        # Next 3 bytes: 1,2,3
        assert data[10:13] == b'\x01\x02\x03'
        # Next 5 bytes: 0 (DS 5)
        assert data[13:18] == b'\x00' * 5