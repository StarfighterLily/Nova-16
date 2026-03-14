import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import nova_mcp_server as mcp


def setup_function():
    mcp.initialize_emulator()


def test_init_emulator_reports_actual_dimensions():
    result = json.loads(mcp._handle_init_emulator())

    assert result["status"] == "initialized"
    assert result["memory_size"] == mcp._emulator_state["memory"].size
    assert result["screen_width"] == mcp._emulator_state["gfx"].width
    assert result["screen_height"] == mcp._emulator_state["gfx"].height


def test_assemble_honors_custom_output_path(tmp_path):
    source = tmp_path / "program.asm"
    output = tmp_path / "out" / "custom.bin"
    source.write_text("ORG 0x0000\nMOV R0, 42\nHLT\n", encoding="ascii")

    result = json.loads(mcp._handle_assemble({
        "source_path": str(source),
        "output_path": str(output),
    }))

    assert result["status"] == "assembled"
    assert Path(result["output"]) == output
    assert output.exists()
    assert output.with_suffix(".org").exists()
    assert output.with_suffix(".sym").exists()
    assert not source.with_suffix(".bin").exists()


def test_set_register_sets_supported_registers_and_validates_names():
    p9_result = json.loads(mcp._handle_set_register({"register": "P9", "value": 0x1234}))
    assert p9_result["status"] == "set"
    assert mcp._emulator_state["cpu"].Pregisters[9] == 0x1234

    pc_result = json.loads(mcp._handle_set_register({"register": "pc", "value": "0x3456"}))
    assert pc_result["status"] == "set"
    assert mcp._emulator_state["cpu"].pc == 0x3456

    invalid_result = json.loads(mcp._handle_set_register({"register": "R10", "value": 1}))
    assert invalid_result["error"] == "Unknown register: R10"


def test_breakpoint_handlers_parse_and_validate_addresses():
    set_result = json.loads(mcp._handle_breakpoint_set({"address": "0x1234"}))
    assert set_result["status"] == "breakpoint_set"
    assert "0x1234" in json.loads(mcp._handle_breakpoint_list())["breakpoints"]

    clear_result = json.loads(mcp._handle_breakpoint_clear({"address": "0x1234"}))
    assert clear_result["status"] == "breakpoint_cleared"
    assert clear_result["address"] == "0x1234"

    invalid_clear = json.loads(mcp._handle_breakpoint_clear({"address": "not-an-address"}))
    assert invalid_clear["error"] == "address must be an integer"


def test_graphics_get_pixel_uses_actual_gfx_dimensions():
    mcp._handle_graphics_set_pixel({"x": 255, "y": 255, "color": 77, "layer": 0})

    result = json.loads(mcp._handle_graphics_get_pixel({"x": 255, "y": 255, "layer": 0}))

    assert result["color"] == 77
    assert result["x"] == 255
    assert result["y"] == 255


def test_graphics_get_screen_accepts_png_alias():
    result = json.loads(mcp._handle_graphics_get_screen({"format": "png"}))

    if "error" in result:
        assert result["error"] == "PNG export failed: Pillow not installed"
    else:
        assert result["encoding"] == "png_base64"
        assert isinstance(result["png_base64"], str)
        assert result["png_base64"]


def test_list_tools_advertises_png_screen_format():
    tools = asyncio.run(mcp.handle_list_tools()).tools
    graphics_get_screen = next(tool for tool in tools if tool.name == "graphics_get_screen")

    assert "png" in graphics_get_screen.inputSchema["properties"]["format"]["enum"]


def test_memory_search_rejects_empty_pattern():
    result = json.loads(mcp._handle_memory_search({"pattern": "   "}))

    assert result["error"] == "pattern must not be empty"


def test_memory_search_validates_range_arguments():
    result = json.loads(mcp._handle_memory_search({"pattern": "AA", "start": 10, "end": 9}))

    assert result["error"] == "end must be >= start"


def test_cpu_run_rejects_negative_cycle_count():
    result = json.loads(mcp._handle_cpu_run({"cycles": -1}))

    assert result["error"] == "cycles must be >= 0"


def test_cpu_run_until_validates_address_and_cycle_count():
    invalid_address = json.loads(mcp._handle_cpu_run_until({"address": "bad"}))
    assert invalid_address["error"] == "address must be an integer"

    invalid_cycles = json.loads(mcp._handle_cpu_run_until({"address": 0x10, "max_cycles": -1}))
    assert invalid_cycles["error"] == "max_cycles must be >= 0"


def test_memory_handlers_validate_arguments_and_bounds():
    invalid_read = json.loads(mcp._handle_read_memory({"address": "0x10", "size": "bad"}))
    assert invalid_read["error"] == "size must be an integer"

    invalid_format = json.loads(mcp._handle_read_memory({"address": 0, "size": 1, "format": "binary"}))
    assert invalid_format["error"] == "Unknown format: binary"

    invalid_write = json.loads(mcp._handle_write_memory({"address": 0, "data": "GG"}))
    assert invalid_write["error"].startswith("Invalid data payload:")

    out_of_bounds_write = json.loads(mcp._handle_write_memory({"address": 0xFFFF, "data": "ABCD"}))
    assert out_of_bounds_write["error"] == "address + data size exceeds memory bounds"


def test_graphics_set_pixel_validates_numeric_ranges():
    invalid_coordinate = json.loads(mcp._handle_graphics_set_pixel({"x": "bad", "y": 0, "color": 1}))
    assert invalid_coordinate["error"] == "x must be an integer"

    invalid_color = json.loads(mcp._handle_graphics_set_pixel({"x": 0, "y": 0, "color": 256}))
    assert invalid_color["error"] == "color must be <= 255"

    invalid_layer = json.loads(mcp._handle_graphics_set_pixel({"x": 0, "y": 0, "color": 1, "layer": 9}))
    assert invalid_layer["error"] == "layer must be <= 8"


def test_graphics_set_blend_mode_validates_range():
    invalid_mode = json.loads(mcp._handle_graphics_set_blend_mode({"mode": 5}))

    assert invalid_mode["error"] == "mode must be <= 4"


def test_keyboard_inject_key_supports_aliases_hex_and_count_validation():
    alias_result = json.loads(mcp._handle_keyboard_inject_key({"key": "Enter", "count": "2"}))
    assert alias_result["status"] == "injected"
    assert alias_result["key"] == "enter"
    assert alias_result["count"] == 2
    assert mcp._emulator_state["cpu"].key_buffer == [0x0A, 0x0A]

    hex_result = json.loads(mcp._handle_keyboard_inject_key({"key": "0x41"}))
    assert hex_result["status"] == "injected"
    assert hex_result["key"] == "0x41"
    assert hex_result["scan_code"] == "0x41"
    assert mcp._emulator_state["cpu"].key_buffer[-1] == 0x41

    invalid_count = json.loads(mcp._handle_keyboard_inject_key({"key": "a", "count": -1}))
    assert invalid_count["error"] == "count must be >= 0"


def test_keyboard_type_string_supports_control_characters_and_ascii_validation():
    result = json.loads(mcp._handle_keyboard_type_string({"text": "A\n\t\b"}))

    assert result["status"] == "typed"
    assert result["length"] == 4
    assert mcp._emulator_state["cpu"].key_buffer == [0x61, 0x0A, 0x09, 0x08]

    invalid_text = json.loads(mcp._handle_keyboard_type_string({"text": "cafe\u00e9"}))
    assert invalid_text["error"] == "text must contain only ASCII characters"


def test_assert_memory_and_run_until_memory_validate_bounds_and_payloads():
    invalid_expected = json.loads(mcp._handle_assert_memory({"address": 0, "expected": "   "}))
    assert invalid_expected["error"] == "expected must not be empty"

    out_of_bounds_assert = json.loads(mcp._handle_assert_memory({"address": 0xFFFF, "expected": "AA BB"}))
    assert out_of_bounds_assert["error"] == "address + expected size exceeds memory bounds"

    invalid_value = json.loads(mcp._handle_run_until_memory({"address": 0, "value": "   "}))
    assert invalid_value["error"] == "value must not be empty"

    out_of_bounds_value = json.loads(mcp._handle_run_until_memory({"address": 0xFFFF, "value": "AA BB"}))
    assert out_of_bounds_value["error"] == "address + value size exceeds memory bounds"


def test_timer_control_validates_ranges():
    invalid_timer = json.loads(mcp._handle_timer_control({"TT": 0x1_0000}))

    assert invalid_timer["error"] == "TT must be <= 65535"


def test_handle_nobasic_compile_accepts_case_insensitive_extensions_and_uses_suffix_binary(tmp_path, monkeypatch):
    source = tmp_path / "program.NoBasic"
    source.write_text("Pause\n", encoding="ascii")
    output = tmp_path / "build" / "CUSTOM.ASM"

    monkeypatch.setattr(mcp, "_HAS_NOBASIC", True)

    def fake_compile(source_file, output_file, verbose):
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("HLT\n", encoding="ascii")
        output_path.with_suffix(".bin").write_bytes(b"\x00")

    monkeypatch.setattr(mcp, "compile_nobasic", fake_compile)

    result = json.loads(mcp._handle_nobasic_compile({
        "source_path": str(source),
        "output_path": str(output),
    }))

    assert result["status"] == "compiled"
    assert Path(result["assembly"]) == output
    assert Path(result["binary"]) == output.with_suffix(".bin")
    assert output.exists()
    assert output.with_suffix(".bin").exists()


def test_handle_nobasic_compile_returns_error_when_compiler_exits(tmp_path, monkeypatch):
    source = tmp_path / "broken.nobasic"
    source.write_text("Pause\n", encoding="ascii")

    monkeypatch.setattr(mcp, "_HAS_NOBASIC", True)

    def fake_compile(source_file, output_file, verbose):
        raise SystemExit(1)

    monkeypatch.setattr(mcp, "compile_nobasic", fake_compile)

    result = json.loads(mcp._handle_nobasic_compile({"source_path": str(source)}))

    assert result["error"] == "Compilation failed with exit code 1"
    assert result["exit_code"] == 1
    assert Path(result["source"]) == source
    assert Path(result["assembly"]) == source.with_suffix(".asm")


def test_handle_call_tool_catches_system_exit_and_returns_json_error(monkeypatch):
    def fake_handler(arguments):
        raise SystemExit(3)

    monkeypatch.setattr(mcp, "_handle_nobasic_compile", fake_handler)

    result = asyncio.run(mcp.handle_call_tool("nobasic_compile", {"source_path": "ignored.nobasic"}))

    assert len(result) == 1
    payload = json.loads(result[0].text)
    assert payload["error"] == "Tool exited with code 3"
    assert "SystemExit: 3" in payload["traceback"]