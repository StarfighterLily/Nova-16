import json
from pathlib import Path

import pytest

import nova_mcp_server as mcp


def test_handle_disassemble_returns_assembly_text():
    mcp.initialize_emulator()

    result = json.loads(mcp._handle_disassemble({"start_addr": 0x0000, "num_instructions": 4}))

    assert "assembly" in result
    assert isinstance(result["assembly"], str)
    assert result["assembly"].strip() != ""
    assert result["decoded_instructions"] == 4
    assert "hex" not in result


def test_handle_disassemble_program_uses_complete_args():
    mcp.initialize_emulator()

    binary = Path("asm/gfxtest.bin")
    if not binary.exists():
        pytest.skip("asm/gfxtest.bin not available in workspace")

    load_result = json.loads(mcp._handle_load_program({"program_path": str(binary)}))
    assert "error" not in load_result

    disassemble_result = json.loads(mcp._handle_disassemble_program({}))

    assert "error" not in disassemble_result
    assert "assembly" in disassemble_result
    assert isinstance(disassemble_result["assembly"], str)
    assert disassemble_result["assembly"].strip() != ""
