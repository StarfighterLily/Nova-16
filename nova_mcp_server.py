#!/usr/bin/env python3
"""Nova-16 MCP server compatibility facade."""

from __future__ import annotations

import asyncio
import json
import traceback
from typing import Any

from mcp.server import Server
from mcp.server.lowlevel.server import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import ServerCapabilities, TextContent, ToolsCapability
import mcp.types as types

from nova_mcp.handlers_debugger import (
    handle_debugger_get_symbol_table,
    handle_debugger_init,
    handle_debugger_inspect_instruction,
    handle_debugger_print_state,
    handle_debugger_run_until_breakpoint,
    handle_debugger_step,
)
from nova_mcp.handlers_media import (
    handle_graphics_export_png,
    handle_graphics_get_pixel,
    handle_graphics_get_screen,
    handle_graphics_set_blend_mode,
    handle_graphics_set_pixel,
    handle_keyboard_get_buffer,
    handle_keyboard_inject_key,
    handle_keyboard_type_string,
    handle_sound_control,
)
from nova_mcp.handlers_nobasic import handle_nobasic_compile
from nova_mcp.handlers_system import (
    handle_assemble,
    handle_assert_memory,
    handle_breakpoint_clear,
    handle_breakpoint_list,
    handle_breakpoint_set,
    handle_clear_memory,
    handle_cpu_halt,
    handle_cpu_reset,
    handle_cpu_run,
    handle_cpu_run_until,
    handle_cpu_step,
    handle_disassemble,
    handle_disassemble_program,
    handle_full_reset,
    handle_get_cpu_state,
    handle_init_emulator,
    handle_load_program,
    handle_memory_dump,
    handle_memory_search,
    handle_read_memory,
    handle_run_until_memory,
    handle_set_flags,
    handle_set_register,
    handle_timer_control,
    handle_write_memory,
)
from nova_mcp.runtime import (
    Image,
    ROOT_DIR,
    _HAS_NOBASIC,
    _HAS_PIL,
    _emulator_state,
    cleanup_emulator,
    compile_nobasic,
    ensure_emulator,
    initialize_emulator,
    nova_assembler,
    nova_debugger,
    nova_disassembler,
)
from nova_mcp.tool_definitions import build_tools

server = Server("nova-16-mcp")

TOOL_HANDLER_NAMES = {
    "init_emulator": "_handle_init_emulator",
    "load_program": "_handle_load_program",
    "assemble": "_handle_assemble",
    "cpu_step": "_handle_cpu_step",
    "cpu_run": "_handle_cpu_run",
    "cpu_halt": "_handle_cpu_halt",
    "cpu_reset": "_handle_cpu_reset",
    "clear_memory": "_handle_clear_memory",
    "full_reset": "_handle_full_reset",
    "get_cpu_state": "_handle_get_cpu_state",
    "set_register": "_handle_set_register",
    "read_memory": "_handle_read_memory",
    "write_memory": "_handle_write_memory",
    "graphics_get_pixel": "_handle_graphics_get_pixel",
    "graphics_get_screen": "_handle_graphics_get_screen",
    "graphics_export_png": "_handle_graphics_export_png",
    "graphics_set_blend_mode": "_handle_graphics_set_blend_mode",
    "graphics_set_pixel": "_handle_graphics_set_pixel",
    "keyboard_inject_key": "_handle_keyboard_inject_key",
    "keyboard_get_buffer": "_handle_keyboard_get_buffer",
    "sound_control": "_handle_sound_control",
    "disassemble": "_handle_disassemble",
    "memory_dump": "_handle_memory_dump",
    "breakpoint_set": "_handle_breakpoint_set",
    "breakpoint_clear": "_handle_breakpoint_clear",
    "breakpoint_list": "_handle_breakpoint_list",
    "cpu_run_until": "_handle_cpu_run_until",
    "assert_memory": "_handle_assert_memory",
    "memory_search": "_handle_memory_search",
    "run_until_memory": "_handle_run_until_memory",
    "set_flags": "_handle_set_flags",
    "timer_control": "_handle_timer_control",
    "keyboard_type_string": "_handle_keyboard_type_string",
    "disassemble_program": "_handle_disassemble_program",
    "debugger_init": "_handle_debugger_init",
    "debugger_step": "_handle_debugger_step",
    "debugger_run_until_breakpoint": "_handle_debugger_run_until_breakpoint",
    "debugger_print_state": "_handle_debugger_print_state",
    "debugger_get_symbol_table": "_handle_debugger_get_symbol_table",
    "debugger_inspect_instruction": "_handle_debugger_inspect_instruction",
    "nobasic_compile": "_handle_nobasic_compile",
}


def _handle_init_emulator() -> str:
    return handle_init_emulator(initialize_emulator=initialize_emulator, state=_emulator_state)


def _handle_load_program(args: dict[str, Any]) -> str:
    return handle_load_program(args, ensure_emulator=ensure_emulator, state=_emulator_state, base_dir=ROOT_DIR)


def _handle_assemble(args: dict[str, Any]) -> str:
    return handle_assemble(args, ensure_emulator=ensure_emulator, assembler_module=nova_assembler, base_dir=ROOT_DIR)


def _handle_cpu_step(args: dict[str, Any]) -> str:
    return handle_cpu_step(args, ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_cpu_run(args: dict[str, Any]) -> str:
    return handle_cpu_run(args, ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_cpu_halt() -> str:
    return handle_cpu_halt(ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_cpu_reset() -> str:
    return handle_cpu_reset(ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_clear_memory() -> str:
    return handle_clear_memory(ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_full_reset() -> str:
    return handle_full_reset(ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_get_cpu_state() -> str:
    return handle_get_cpu_state(ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_set_register(args: dict[str, Any]) -> str:
    return handle_set_register(args, ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_read_memory(args: dict[str, Any]) -> str:
    return handle_read_memory(args, ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_write_memory(args: dict[str, Any]) -> str:
    return handle_write_memory(args, ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_graphics_get_pixel(args: dict[str, Any]) -> str:
    return handle_graphics_get_pixel(args, ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_graphics_get_screen(args: dict[str, Any]) -> str:
    return handle_graphics_get_screen(args, ensure_emulator=ensure_emulator, state=_emulator_state, has_pil=_HAS_PIL, image_cls=Image)


def _handle_graphics_export_png(args: dict[str, Any]) -> str:
    return handle_graphics_export_png(args, ensure_emulator=ensure_emulator, state=_emulator_state, has_pil=_HAS_PIL, image_cls=Image)


def _handle_graphics_set_blend_mode(args: dict[str, Any]) -> str:
    return handle_graphics_set_blend_mode(args, ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_graphics_set_pixel(args: dict[str, Any]) -> str:
    return handle_graphics_set_pixel(args, ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_keyboard_inject_key(args: dict[str, Any]) -> str:
    return handle_keyboard_inject_key(args, ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_keyboard_get_buffer() -> str:
    return handle_keyboard_get_buffer(ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_sound_control(args: dict[str, Any]) -> str:
    return handle_sound_control(args, ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_disassemble(args: dict[str, Any]) -> str:
    return handle_disassemble(args, ensure_emulator=ensure_emulator, state=_emulator_state, disassembler_module=nova_disassembler)


def _handle_memory_dump(args: dict[str, Any]) -> str:
    return handle_memory_dump(args, ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_breakpoint_set(args: dict[str, Any]) -> str:
    return handle_breakpoint_set(args, ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_breakpoint_clear(args: dict[str, Any]) -> str:
    return handle_breakpoint_clear(args, ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_breakpoint_list() -> str:
    return handle_breakpoint_list(ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_cpu_run_until(args: dict[str, Any]) -> str:
    return handle_cpu_run_until(args, ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_assert_memory(args: dict[str, Any]) -> str:
    return handle_assert_memory(args, ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_memory_search(args: dict[str, Any]) -> str:
    return handle_memory_search(args, ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_run_until_memory(args: dict[str, Any]) -> str:
    return handle_run_until_memory(args, ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_set_flags(args: dict[str, Any]) -> str:
    return handle_set_flags(args, ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_timer_control(args: dict[str, Any]) -> str:
    return handle_timer_control(args, ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_keyboard_type_string(args: dict[str, Any]) -> str:
    return handle_keyboard_type_string(args, ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_disassemble_program(args: dict[str, Any]) -> str:
    return handle_disassemble_program(args, ensure_emulator=ensure_emulator, state=_emulator_state, disassembler_module=nova_disassembler)


def _handle_debugger_init() -> str:
    return handle_debugger_init(ensure_emulator=ensure_emulator, state=_emulator_state, debugger_module=nova_debugger)


def _handle_debugger_step(args: dict[str, Any]) -> str:
    return handle_debugger_step(args, ensure_emulator=ensure_emulator, state=_emulator_state, disassembler_module=nova_disassembler, debugger_module=nova_debugger)


def _handle_debugger_run_until_breakpoint(args: dict[str, Any]) -> str:
    return handle_debugger_run_until_breakpoint(args, ensure_emulator=ensure_emulator, state=_emulator_state, debugger_module=nova_debugger)


def _handle_debugger_print_state(args: dict[str, Any]) -> str:
    return handle_debugger_print_state(args, ensure_emulator=ensure_emulator, state=_emulator_state, disassembler_module=nova_disassembler)


def _handle_debugger_get_symbol_table() -> str:
    return handle_debugger_get_symbol_table(ensure_emulator=ensure_emulator, state=_emulator_state)


def _handle_debugger_inspect_instruction(args: dict[str, Any]) -> str:
    return handle_debugger_inspect_instruction(args, ensure_emulator=ensure_emulator, state=_emulator_state, disassembler_module=nova_disassembler, debugger_module=nova_debugger)


def _handle_nobasic_compile(args: dict[str, Any]) -> str:
    return handle_nobasic_compile(
        args,
        has_nobasic=_HAS_NOBASIC,
        compile_nobasic=compile_nobasic,
        assembler_module=nova_assembler,
        ensure_emulator=ensure_emulator,
        state=_emulator_state,
        base_dir=ROOT_DIR,
    )


@server.list_tools()
async def handle_list_tools() -> types.ListToolsResult:
    return types.ListToolsResult(tools=build_tools())


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None):
    args = arguments or {}
    try:
        handler_name = TOOL_HANDLER_NAMES.get(name)
        if handler_name is None:
            result_text = json.dumps({"error": f"Unknown tool: {name}"})
        else:
            handler = globals()[handler_name]
            result_text = handler(args) if args else handler()
        return [TextContent(type="text", text=result_text)]
    except SystemExit as exc:
        error_text = json.dumps({"error": f"Tool exited with code {exc.code}", "traceback": traceback.format_exc()})
        return [TextContent(type="text", text=error_text)]
    except Exception as exc:
        error_text = json.dumps({"error": str(exc), "traceback": traceback.format_exc()})
        return [TextContent(type="text", text=error_text)]


async def main() -> None:
    initialize_emulator()
    async with stdio_server() as (read_stream, write_stream):
        init_options = InitializationOptions(
            server_name="Nova-16 MCP",
            server_version="1.0.0",
            capabilities=ServerCapabilities(tools=ToolsCapability()),
        )
        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())
