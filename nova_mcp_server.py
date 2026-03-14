#!/usr/bin/env python3
"""
MCP Server for Nova-16 Emulator

This MCP server provides tools for LLM control over the Nova-16 CPU emulator,
including CPU execution, memory access, graphics, sound, keyboard, and debugging.

To use with Claude or other MCP clients:
1. Install mcp package: pip install mcp
2. Configure client with stdio transport pointing to this script
3. Invoke tools via the MCP protocol
"""

import sys
import json
import traceback
import contextlib
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal
import base64
import struct
import os
import io

# Suppress pygame output before importing
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import logging
logging.getLogger('pygame').setLevel(logging.ERROR)

# Add Nova project to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import nova_cpu as cpu_module
    import nova_memory as memory_module
    import nova_gfx as gfx_module
    import nova_sound as sound_module
    import nova_keyboard as keyboard_module
    import nova_assembler
    import nova_disassembler
    import nova_debugger
except ImportError as e:
    print(f"Error importing Nova modules: {e}", file=sys.stderr)
    sys.exit(1)

# Try to import NoBASIC compiler
try:
    sys.path.insert(0, str(Path(__file__).parent / "NoBASIC"))
    from nobasic_compiler import compile_nobasic
    _HAS_NOBASIC = True
except ImportError:
    _HAS_NOBASIC = False

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.types as types
from typing import TypedDict

# Optional image export support
try:
    from PIL import Image
    _HAS_PIL = True
except Exception:
    _HAS_PIL = False

# Global emulator state
_emulator_state = {
    "cpu": None,
    "memory": None,
    "gfx": None,
    "kbd": None,
    "sound": None,
    "program_path": None,
    "running": False,
    "cycle_count": 0,
    "debugger": None,
}


def _parse_int_arg(value: Any, name: str, *, minimum: Optional[int] = None, maximum: Optional[int] = None) -> int:
    """Parse an integer argument with optional bounds checks."""
    try:
        parsed = int(value, 0) if isinstance(value, str) else int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be an integer")

    if minimum is not None and parsed < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    if maximum is not None and parsed > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return parsed


def _parse_register_arg(value: Any) -> tuple[str, Optional[int]]:
    """Normalize a register argument and validate supported register names."""
    if not isinstance(value, str):
        raise ValueError("register must be a string")

    register = value.strip().upper()
    if register == "PC":
        return register, None

    if len(register) >= 2 and register[0] in {"R", "P"} and register[1:].isdigit():
        index = int(register[1:])
        if 0 <= index <= 9:
            return register, index

    raise ValueError(f"Unknown register: {register}")


def _normalize_keyboard_key_arg(value: Any, key_mapping: Dict[str, int]) -> tuple[str, Optional[int]]:
    """Normalize MCP keyboard input to a Nova key name or raw scan code."""
    if not isinstance(value, str):
        raise ValueError("key must be a string")

    raw_key = value.strip()
    if not raw_key:
        raise ValueError("key must not be empty")

    if raw_key.lower().startswith("0x"):
        scan_code = _parse_int_arg(raw_key, "key", minimum=0, maximum=0xFF)
        return f"0x{scan_code:02X}", scan_code

    if len(raw_key) == 1:
        return raw_key, None

    normalized = raw_key.lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "return": "enter",
        "esc": "escape",
        "space": " ",
        "arrowleft": "left",
        "arrowright": "right",
        "arrowup": "up",
        "arrowdown": "down",
        "left_arrow": "left",
        "right_arrow": "right",
        "up_arrow": "up",
        "down_arrow": "down",
    }
    normalized = aliases.get(normalized, normalized)

    if normalized in {"shift", "ctrl", "alt"} or normalized in key_mapping:
        return normalized, None

    raise ValueError(f"Unknown key: {raw_key}")


def _parse_hex_bytes_arg(value: Any, name: str) -> tuple[str, bytes]:
    """Parse a required hex string argument, allowing embedded spaces."""
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")

    normalized = value.replace(" ", "").strip()
    if not normalized:
        raise ValueError(f"{name} must not be empty")

    try:
        return normalized.upper(), bytes.fromhex(normalized)
    except ValueError as e:
        raise ValueError(f"Invalid hex {name}: {e}") from e

def cleanup_emulator():
    """Explicitly clean up emulator resources before reinitialization"""
    import gc
    
    # Clean up sound system first (pygame mixer resources)
    if _emulator_state["sound"] is not None:
        try:
            _emulator_state["sound"].cleanup()
        except Exception as e:
            print(f"[MCP] Error cleaning up sound: {e}", file=sys.stderr)
    
    # Stop any running debugger
    if _emulator_state["debugger"] is not None:
        _emulator_state["debugger"] = None
    
    # Clear all references to allow garbage collection
    _emulator_state.update({
        "cpu": None,
        "memory": None,
        "gfx": None,
        "kbd": None,
        "sound": None,
        "program_path": None,
        "running": False,
        "cycle_count": 0,
        "debugger": None,
    })
    
    # Force garbage collection to free numpy arrays and other resources
    gc.collect()
    print("[MCP] Emulator resources cleaned up", file=sys.stderr)

def initialize_emulator(force_clean=True):
    """Initialize all Nova-16 system components with optional cleanup"""
    # Clean up existing resources if requested
    if force_clean and _emulator_state["cpu"] is not None:
        cleanup_emulator()
    
    mem = memory_module.Memory()
    gfx = gfx_module.GFX(256, 256)
    kbd = keyboard_module.NovaKeyboard()
    snd = sound_module.NovaSound()
    
    proc = cpu_module.CPU(mem, gfx, kbd, snd)
    kbd.cpu = proc
    mem.gfx_system = gfx
    
    _emulator_state.update({
        "cpu": proc,
        "memory": mem,
        "gfx": gfx,
        "kbd": kbd,
        "sound": snd,
        "program_path": None,
        "running": False,
        "cycle_count": 0,
        "debugger": None,
    })
    
    print("[MCP] Emulator initialized", file=sys.stderr)
    
    return proc, mem, gfx, kbd, snd

def ensure_emulator():
    """Ensure emulator is initialized"""
    if _emulator_state["cpu"] is None:
        initialize_emulator()

# Create MCP server
server = Server("nova-16-mcp")

@server.list_tools()
async def handle_list_tools() -> types.ListToolsResult:
    """List all available Nova-16 control tools"""
    print(f"[MCP] Listing tools...", file=sys.stderr)
    tools = [
        Tool(
            name="init_emulator",
            description="Initialize or reset the Nova-16 emulator",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="load_program",
            description="Load a Nova-16 binary program into memory",
            inputSchema={
                "type": "object",
                "properties": {
                    "program_path": {
                        "type": "string",
                        "description": "Path to .bin file (absolute or relative to Nova directory)"
                    }
                },
                "required": ["program_path"]
            }
        ),
        Tool(
            name="assemble",
            description="Assemble Nova-16 assembly code to binary",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_path": {
                        "type": "string",
                        "description": "Path to .asm file"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path to output .bin file (optional, defaults to .bin variant of source)"
                    }
                },
                "required": ["source_path"]
            }
        ),
        Tool(
            name="cpu_step",
            description="Execute one CPU instruction cycle",
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of cycles to execute (default: 1)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="cpu_run",
            description="Run CPU for specified number of cycles or until halt",
            inputSchema={
                "type": "object",
                "properties": {
                    "cycles": {
                        "type": "integer",
                        "description": "Number of cycles to run (default: 10000)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="cpu_halt",
            description="Stop CPU execution",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="cpu_reset",
            description="Reset CPU state (PC, registers, flags)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="clear_memory",
            description="Clear all memory contents to zero (preserves CPU state)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="full_reset",
            description="Complete system reset: CPU, memory, graphics, sound, keyboard",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_cpu_state",
            description="Get current CPU state (registers, PC, flags)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="set_register",
            description="Set CPU register value",
            inputSchema={
                "type": "object",
                "properties": {
                    "register": {
                        "type": "string",
                        "description": "Register name (R0-R9, P0-P9, PC)"
                    },
                    "value": {
                        "type": "integer",
                        "description": "Value to set"
                    }
                },
                "required": ["register", "value"]
            }
        ),
        Tool(
            name="read_memory",
            description="Read data from memory",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {
                        "type": "integer",
                        "description": "Starting address (0x0000-0xFFFF)"
                    },
                    "size": {
                        "type": "integer",
                        "description": "Number of bytes to read"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["hex", "bytes", "ascii", "words"],
                        "description": "Output format (default: hex)"
                    }
                },
                "required": ["address", "size"]
            }
        ),
        Tool(
            name="write_memory",
            description="Write data to memory",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {
                        "type": "integer",
                        "description": "Starting address (0x0000-0xFFFF)"
                    },
                    "data": {
                        "type": "string",
                        "description": "Hex string (e.g., 'DEADBEEF') or ASCII string prefixed with '@' (e.g., '@Hello')"
                    }
                },
                "required": ["address", "data"]
            }
        ),
        Tool(
            name="graphics_get_pixel",
            description="Get pixel color at graphics coordinate",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate (0-255)"},
                    "y": {"type": "integer", "description": "Y coordinate (0-255)"},
                    "layer": {"type": "integer", "description": "Layer (0-8, default: all)"}
                },
                "required": ["x", "y"]
            }
        ),
        Tool(
            name="graphics_get_screen",
            description="Get entire screen buffer as base64-encoded PNG or raw data",
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "enum": ["base64", "png", "raw", "summary"],
                        "description": "Output format (default: summary)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="graphics_export_png",
            description="Export current screen as base64 PNG",
            inputSchema={
                "type": "object",
                "properties": {
                    "palette": {
                        "type": "string",
                        "description": "Optional palette: 'grayscale' (default) or 'heatmap'"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="graphics_set_blend_mode",
            description="Set graphics blend mode (0=normal,1=add,2=sub,3=mul,4=screen)",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {"type": "integer", "description": "Blend mode (0-4)"}
                },
                "required": ["mode"]
            }
        ),
        Tool(
            name="graphics_set_pixel",
            description="Set pixel color in graphics buffer",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate (0-255)"},
                    "y": {"type": "integer", "description": "Y coordinate (0-255)"},
                    "color": {"type": "integer", "description": "Color value (0-255)"},
                    "layer": {"type": "integer", "description": "Layer (0-8, default: 0)"}
                },
                "required": ["x", "y", "color"]
            }
        ),
        Tool(
            name="keyboard_inject_key",
            description="Inject a key press into the keyboard buffer",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Key code or ASCII character, case-insensitive for named keys (e.g., 'a', 'Enter', 'Space', or hex like '0x41')"
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of times to inject (default: 1)"
                    }
                },
                "required": ["key"]
            }
        ),
        Tool(
            name="keyboard_get_buffer",
            description="Get current keyboard input buffer",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="sound_control",
            description="Control sound playback",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["play", "stop", "get_state"],
                        "description": "Action to perform"
                    },
                    "address": {"type": "integer", "description": "Sound data address (for play)"},
                    "frequency": {"type": "integer", "description": "Frequency in Hz (for play)"},
                    "volume": {"type": "integer", "description": "Volume 0-255 (for play)"},
                    "waveform": {"type": "integer", "description": "Waveform type 0-3 (for play)"}
                },
                "required": ["action"]
            }
        ),
        Tool(
            name="disassemble",
            description="Disassemble binary back to assembly code",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_addr": {
                        "type": "integer",
                        "description": "Starting address (default: 0x0000)"
                    },
                    "num_instructions": {
                        "type": "integer",
                        "description": "Number of instructions to disassemble (default: 100)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="memory_dump",
            description="Create a memory dump for debugging",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_addr": {
                        "type": "integer",
                        "description": "Starting address (default: 0x0000)"
                    },
                    "size": {
                        "type": "integer",
                        "description": "Size in bytes (default: 256)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="breakpoint_set",
            description="Set a breakpoint at specific address",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {
                        "type": "integer",
                        "description": "Address to set breakpoint"
                    }
                },
                "required": ["address"]
            }
        ),
        Tool(
            name="breakpoint_clear",
            description="Clear a breakpoint at address or all breakpoints",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {
                        "type": "integer",
                        "description": "Address to clear; omit to clear all"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="breakpoint_list",
            description="List all currently set breakpoints",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="cpu_run_until",
            description="Run CPU until PC equals address, halt, or max cycles",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "integer", "description": "Target PC address"},
                    "max_cycles": {"type": "integer", "description": "Cycle cap (default 100000)"}
                },
                "required": ["address"]
            }
        ),
        Tool(
            name="assert_memory",
            description="Assert memory bytes match expected value at address",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "integer", "description": "Start address"},
                    "expected": {"type": "string", "description": "Hex string of expected bytes, e.g., '2A3A'"}
                },
                "required": ["address", "expected"]
            }
        ),
        Tool(
            name="memory_search",
            description="Search memory for a hex pattern",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Hex string pattern (e.g., 'DE AD BE EF')"},
                    "start": {"type": "integer", "description": "Optional start address (default 0x0000)"},
                    "end": {"type": "integer", "description": "Optional end address (default 0xFFFF)"},
                    "max_results": {"type": "integer", "description": "Limit number of matches (default 16)"}
                },
                "required": ["pattern"]
            }
        ),
        Tool(
            name="run_until_memory",
            description="Run CPU until memory at address equals value or timeout",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "integer", "description": "Memory address to watch"},
                    "value": {"type": "string", "description": "Expected hex byte(s), e.g., 'FF' or 'DE AD'"},
                    "max_cycles": {"type": "integer", "description": "Cycle cap (default 100000)"}
                },
                "required": ["address", "value"]
            }
        ),
        Tool(
            name="set_flags",
            description="Set CPU flags (Z,C,S,O,I,T,B,D,P,H,A,E)",
            inputSchema={
                "type": "object",
                "properties": {
                    "flags": {"type": "object", "description": "Map of flag letter to 0/1, e.g., {\"Z\":1,\"I\":0}"}
                },
                "required": ["flags"]
            }
        ),
        Tool(
            name="timer_control",
            description="Configure timer registers TT, TM, TC, TS",
            inputSchema={
                "type": "object",
                "properties": {
                    "TT": {"type": "integer", "description": "Timer counter (0-65535)"},
                    "TM": {"type": "integer", "description": "Timer modulo (0-65535)"},
                    "TC": {"type": "integer", "description": "Timer control"},
                    "TS": {"type": "integer", "description": "Timer speed"}
                },
                "required": []
            }
        ),
        Tool(
            name="keyboard_type_string",
            description="Inject a full ASCII string as keypresses",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "ASCII text to type"}
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="disassemble_program",
            description="Disassemble the currently loaded program using the advanced disassembler",
            inputSchema={
                "type": "object",
                "properties": {
                    "start": {"type": "integer", "description": "Optional start address"},
                    "end": {"type": "integer", "description": "Optional end address"},
                    "show_hex": {"type": "boolean", "description": "Include hex bytes"},
                    "show_addresses": {"type": "boolean", "description": "Include addresses"},
                    "filter_instructions": {"type": "string", "description": "Comma list to include"},
                    "exclude_instructions": {"type": "string", "description": "Comma list to exclude"}
                },
                "required": []
            }
        ),
        Tool(
            name="debugger_init",
            description="Initialize debugger for the loaded program",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="debugger_step",
            description="Step through CPU instructions with debugger enabled",
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Number of instructions to step (default: 1)"},
                    "show_disasm": {"type": "boolean", "description": "Show disassembly (default: true)"},
                    "show_regs": {"type": "boolean", "description": "Show registers (default: true)"}
                },
                "required": []
            }
        ),
        Tool(
            name="debugger_run_until_breakpoint",
            description="Run CPU until a breakpoint is hit or program halts",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_cycles": {"type": "integer", "description": "Maximum cycles to run (default: 100000)"}
                },
                "required": []
            }
        ),
        Tool(
            name="debugger_print_state",
            description="Print full debugger state (registers, stack, current instruction)",
            inputSchema={
                "type": "object",
                "properties": {
                    "show_stack": {"type": "boolean", "description": "Show stack contents (default: true)"},
                    "stack_entries": {"type": "integer", "description": "Number of stack entries to show (default: 16)"}
                },
                "required": []
            }
        ),
        Tool(
            name="debugger_get_symbol_table",
            description="Get symbol table from loaded program (if .sym file exists)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="debugger_inspect_instruction",
            description="Get details about the current or specified instruction",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "integer", "description": "Address to inspect (default: PC)"}
                },
                "required": []
            }
        ),
        Tool(
            name="nobasic_compile",
            description="Compile a NoBASIC source file to assembly and binary",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_path": {"type": "string", "description": "Path to .nobasic source file"},
                    "output_path": {"type": "string", "description": "Path to output .asm file (optional)"},
                    "verbose": {"type": "boolean", "description": "Enable verbose output (default: false)"},
                    "auto_load": {"type": "boolean", "description": "Automatically load compiled binary (default: false)"}
                },
                "required": ["source_path"]
            }
        ),
    ]
    print(f"[MCP] Returning {len(tools)} tools", file=sys.stderr)
    return types.ListToolsResult(tools=tools)

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]):
    """Handle tool invocations"""
    try:
        result_text: str
        if name == "init_emulator":
            result_text = _handle_init_emulator()
        elif name == "load_program":
            result_text = _handle_load_program(arguments)
        elif name == "assemble":
            result_text = _handle_assemble(arguments)
        elif name == "cpu_step":
            result_text = _handle_cpu_step(arguments)
        elif name == "cpu_run":
            result_text = _handle_cpu_run(arguments)
        elif name == "cpu_halt":
            result_text = _handle_cpu_halt()
        elif name == "cpu_reset":
            result_text = _handle_cpu_reset()
        elif name == "clear_memory":
            result_text = _handle_clear_memory()
        elif name == "full_reset":
            result_text = _handle_full_reset()
        elif name == "get_cpu_state":
            result_text = _handle_get_cpu_state()
        elif name == "set_register":
            result_text = _handle_set_register(arguments)
        elif name == "read_memory":
            result_text = _handle_read_memory(arguments)
        elif name == "write_memory":
            result_text = _handle_write_memory(arguments)
        elif name == "graphics_get_pixel":
            result_text = _handle_graphics_get_pixel(arguments)
        elif name == "graphics_get_screen":
            result_text = _handle_graphics_get_screen(arguments)
        elif name == "graphics_export_png":
            result_text = _handle_graphics_export_png(arguments)
        elif name == "graphics_set_blend_mode":
            result_text = _handle_graphics_set_blend_mode(arguments)
        elif name == "graphics_set_pixel":
            result_text = _handle_graphics_set_pixel(arguments)
        elif name == "keyboard_inject_key":
            result_text = _handle_keyboard_inject_key(arguments)
        elif name == "keyboard_get_buffer":
            result_text = _handle_keyboard_get_buffer()
        elif name == "sound_control":
            result_text = _handle_sound_control(arguments)
        elif name == "disassemble":
            result_text = _handle_disassemble(arguments)
        elif name == "memory_dump":
            result_text = _handle_memory_dump(arguments)
        elif name == "breakpoint_set":
            result_text = _handle_breakpoint_set(arguments)
        elif name == "breakpoint_clear":
            result_text = _handle_breakpoint_clear(arguments)
        elif name == "breakpoint_list":
            result_text = _handle_breakpoint_list()
        elif name == "cpu_run_until":
            result_text = _handle_cpu_run_until(arguments)
        elif name == "assert_memory":
            result_text = _handle_assert_memory(arguments)
        elif name == "memory_search":
            result_text = _handle_memory_search(arguments)
        elif name == "run_until_memory":
            result_text = _handle_run_until_memory(arguments)
        elif name == "set_flags":
            result_text = _handle_set_flags(arguments)
        elif name == "timer_control":
            result_text = _handle_timer_control(arguments)
        elif name == "keyboard_type_string":
            result_text = _handle_keyboard_type_string(arguments)
        elif name == "disassemble_program":
            result_text = _handle_disassemble_program(arguments)
        elif name == "debugger_init":
            result_text = _handle_debugger_init()
        elif name == "debugger_step":
            result_text = _handle_debugger_step(arguments)
        elif name == "debugger_run_until_breakpoint":
            result_text = _handle_debugger_run_until_breakpoint(arguments)
        elif name == "debugger_print_state":
            result_text = _handle_debugger_print_state(arguments)
        elif name == "debugger_get_symbol_table":
            result_text = _handle_debugger_get_symbol_table()
        elif name == "debugger_inspect_instruction":
            result_text = _handle_debugger_inspect_instruction(arguments)
        elif name == "nobasic_compile":
            result_text = _handle_nobasic_compile(arguments)
        else:
            result_text = json.dumps({"error": f"Unknown tool: {name}"})
            
        return [TextContent(type="text", text=result_text)]
    except SystemExit as e:
        error_text = json.dumps({
            "error": f"Tool exited with code {e.code}",
            "traceback": traceback.format_exc()
        })
        return [TextContent(type="text", text=error_text)]
    except Exception as e:
        error_text = json.dumps({
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        return [TextContent(type="text", text=error_text)]

# Tool handlers

def _handle_init_emulator():
    """Initialize the emulator"""
    initialize_emulator()
    memory = _emulator_state["memory"]
    gfx = _emulator_state["gfx"]
    return json.dumps({
        "status": "initialized",
        "memory_size": memory.size,
        "screen_width": gfx.width,
        "screen_height": gfx.height,
        "registers": "R0-R9 (8-bit), P0-P9 (16-bit)"
    })

def _handle_load_program(args):
    """Load a program into memory"""
    ensure_emulator()
    program_path = args["program_path"]
    
    # Handle relative paths
    if not Path(program_path).is_absolute():
        program_path = Path(__file__).parent / program_path
    
    if not Path(program_path).exists():
        return json.dumps({"error": f"File not found: {program_path}"})
    
    try:
        entry_point = _emulator_state["memory"].load(str(program_path))
        _emulator_state["program_path"] = program_path
        _emulator_state["cpu"].pc = entry_point
        _emulator_state["cycle_count"] = 0
        
        return json.dumps({
            "status": "loaded",
            "program_path": str(program_path),
            "entry_point": f"0x{entry_point:04X}",
            "pc": f"0x{_emulator_state['cpu'].pc:04X}"
        })
    except Exception as e:
        return json.dumps({"error": f"Failed to load program: {str(e)}"})

def _handle_assemble(args):
    """Assemble assembly source to binary"""
    ensure_emulator()
    source_path = Path(args["source_path"])
    output_path = args.get("output_path")
    
    # Handle relative paths
    if not source_path.is_absolute():
        source_path = Path(__file__).parent / source_path
    
    if not source_path.exists():
        return json.dumps({"error": f"File not found: {source_path}"})
    
    if output_path is None:
        output_path = source_path.with_suffix(".bin")
    elif not Path(output_path).is_absolute():
        output_path = Path(__file__).parent / output_path
    else:
        output_path = Path(output_path)
    
    try:
        assembler = nova_assembler.Assembler()
        success = assembler.assemble(str(source_path))
        if not success:
            return json.dumps({"error": "Assembly failed - check syntax"})

        generated_output = source_path.with_suffix(".bin")
        generated_org = source_path.with_suffix(".org")
        generated_sym = source_path.with_suffix(".sym")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        if generated_output.resolve() != output_path.resolve():
            shutil.move(str(generated_output), str(output_path))

        output_org = output_path.with_suffix(".org")
        output_sym = output_path.with_suffix(".sym")
        if generated_org.exists() and generated_org.resolve() != output_org.resolve():
            shutil.move(str(generated_org), str(output_org))
        if generated_sym.exists() and generated_sym.resolve() != output_sym.resolve():
            shutil.move(str(generated_sym), str(output_sym))

        return json.dumps({
            "status": "assembled",
            "source": str(source_path),
            "output": str(output_path)
        })
    except Exception as e:
        import traceback
        return json.dumps({
            "error": f"Assembly failed: {str(e)}",
            "traceback": traceback.format_exc()
        })

def _handle_cpu_step(args):
    """Step CPU execution"""
    ensure_emulator()
    try:
        count = _parse_int_arg(args.get("count", 1), "count", minimum=0)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    
    cpu = _emulator_state["cpu"]
    old_pc = cpu.pc
    
    for _ in range(count):
        if cpu.halted:
            break
        cpu.step()
        _emulator_state["cycle_count"] += 1
    
    return json.dumps({
        "status": "stepped",
        "cycles": count,
        "old_pc": f"0x{old_pc:04X}",
        "new_pc": f"0x{cpu.pc:04X}",
        "halted": cpu.halted,
        "total_cycles": _emulator_state["cycle_count"]
    })

def _handle_cpu_run(args):
    """Run CPU for specified cycles"""
    ensure_emulator()
    try:
        cycles = _parse_int_arg(args.get("cycles", 10000), "cycles", minimum=0)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    
    cpu = _emulator_state["cpu"]
    old_pc = cpu.pc
    cycle_count = 0
    
    for _ in range(cycles):
        if cpu.halted:
            break
        cpu.step()
        cycle_count += 1
        _emulator_state["cycle_count"] += 1
    
    return json.dumps({
        "status": "ran",
        "cycles_executed": cycle_count,
        "old_pc": f"0x{old_pc:04X}",
        "final_pc": f"0x{cpu.pc:04X}",
        "halted": cpu.halted,
        "total_cycles": _emulator_state["cycle_count"]
    })

def _handle_cpu_halt():
    """Halt CPU"""
    ensure_emulator()
    _emulator_state["cpu"].halted = True
    return json.dumps({"status": "halted"})

def _handle_cpu_reset():
    """Reset CPU"""
    ensure_emulator()
    cpu = _emulator_state["cpu"]
    cpu.pc = 0x0000
    cpu.halted = False
    for i in range(10):
        cpu.Rregisters[i] = 0
        cpu.Pregisters[i] = 0
    cpu.Pregisters[8] = 0xFFFF  # SP
    cpu.Pregisters[9] = 0xFFFF  # FP
    _emulator_state["cycle_count"] = 0
    
    return json.dumps({"status": "reset", "pc": "0x0000"})

def _handle_clear_memory():
    """Clear all memory contents to zero"""
    ensure_emulator()
    mem = _emulator_state["memory"]
    
    # Clear main memory
    mem.memory.fill(0)
    
    # Clear caches
    mem.zero_page_cache.fill(0)
    mem.zero_page_dirty = False
    mem.interrupt_vector_cache.fill(0)
    mem.interrupt_vector_dirty = False
    mem.lru_cache.clear()
    
    # Reset cache statistics
    mem.cache_hits = 0
    mem.cache_misses = 0
    
    return json.dumps({
        "status": "memory cleared",
        "size": mem.size,
        "bytes_cleared": mem.size
    })

def _handle_full_reset():
    """Completely reset the emulator to initial state"""
    ensure_emulator()
    
    # Reset CPU state
    cpu = _emulator_state["cpu"]
    cpu.pc = 0x0000
    cpu.halted = False
    for i in range(10):
        cpu.Rregisters[i] = 0
        cpu.Pregisters[i] = 0
    cpu.Pregisters[8] = 0xFFFF  # SP
    cpu.Pregisters[9] = 0xFFFF  # FP
    for i in range(12):
        cpu.flags[i] = 0
    
    # Clear memory
    mem = _emulator_state["memory"]
    mem.memory.fill(0)
    mem.zero_page_cache.fill(0)
    mem.zero_page_dirty = False
    mem.interrupt_vector_cache.fill(0)
    mem.interrupt_vector_dirty = False
    mem.lru_cache.clear()
    mem.cache_hits = 0
    mem.cache_misses = 0
    
    # Clear graphics
    gfx = _emulator_state["gfx"]
    gfx._screen.fill(0)
    gfx.layer_0.fill(0)
    for layer in gfx.background_layers:
        layer.fill(0)
    for layer in gfx.sprite_layers:
        layer.fill(0)
    gfx.layers_dirty = False
    gfx.sprites_dirty = False
    
    # Reset sound
    sound = _emulator_state["sound"]
    try:
        sound.sstop()  # Stop all channels
        # Reset sound registers
        sound.SA = 0
        sound.SF = 0
        sound.SV = 0
        sound.SW = 0
        for i in range(len(sound.sound_registers)):
            sound.sound_registers[i] = 0
    except Exception as e:
        print(f"[MCP] Warning during sound reset: {e}", file=sys.stderr)
    
    # Clear keyboard
    kbd = _emulator_state["kbd"]
    if kbd.cpu:
        kbd.cpu.key_buffer.clear()
    for i in range(4):
        cpu.keyboard[i] = 0
    
    # Reset emulator state tracking
    _emulator_state["cycle_count"] = 0
    _emulator_state["program_path"] = None
    _emulator_state["running"] = False
    
    return json.dumps({
        "status": "full system reset complete",
        "components_reset": ["cpu", "memory", "graphics", "sound", "keyboard"],
        "pc": "0x0000",
        "sp": "0xFFFF",
        "memory_cleared": mem.size
    })

def _handle_get_cpu_state():
    """Get current CPU state"""
    ensure_emulator()
    cpu = _emulator_state["cpu"]
    
    return json.dumps({
        "pc": f"0x{cpu.pc:04X}",
        "halted": cpu.halted,
        "cycles": _emulator_state["cycle_count"],
        "r_registers": [f"0x{r:02X}" for r in cpu.Rregisters[:10]],
        "p_registers": [f"0x{p:04X}" for p in cpu.Pregisters[:10]],
        "flags": {
            "Z": bool(cpu.flags[7]),
            "C": bool(cpu.flags[6]),
            "S": bool(cpu.flags[1]),
            "O": bool(cpu.flags[2]),
            "I": bool(cpu.flags[5])
        },
        "sp": f"0x{cpu.Pregisters[8]:04X}",
        "fp": f"0x{cpu.Pregisters[9]:04X}"
    })

def _handle_set_register(args):
    """Set CPU register"""
    ensure_emulator()
    try:
        register, index = _parse_register_arg(args["register"])
        value = _parse_int_arg(args["value"], "value")
    except (KeyError, ValueError) as e:
        return json.dumps({"error": str(e)})
    
    cpu = _emulator_state["cpu"]
    
    if register == "PC":
        cpu.pc = value & 0xFFFF
    elif register.startswith("R"):
        cpu.Rregisters[index] = value & 0xFF
    else:
        cpu.Pregisters[index] = value & 0xFFFF
    
    return json.dumps({
        "status": "set",
        "register": register,
        "value": f"0x{value & 0xFFFF:04X}" if register in {"PC"} or register.startswith("P") else f"0x{value & 0xFF:02X}"
    })

def _handle_read_memory(args):
    """Read from memory"""
    ensure_emulator()
    memory = _emulator_state["memory"]

    try:
        address = _parse_int_arg(args.get("address"), "address", minimum=0, maximum=memory.size - 1)
        size = _parse_int_arg(args.get("size"), "size", minimum=0, maximum=memory.size)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    if address + size > memory.size:
        return json.dumps({"error": "address + size exceeds memory bounds"})

    format_type = args.get("format", "hex")
    data = [memory.read_byte(address + i) for i in range(size)]
    
    if format_type == "hex":
        hex_str = "".join(f"{b:02X}" for b in data)
        return json.dumps({"address": f"0x{address:04X}", "size": size, "data": hex_str})
    elif format_type == "bytes":
        return json.dumps({"address": f"0x{address:04X}", "size": size, "data": data})
    elif format_type == "ascii":
        ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in data)
        return json.dumps({"address": f"0x{address:04X}", "size": size, "data": ascii_str})
    elif format_type == "words":
        words = []
        for i in range(0, len(data), 2):
            if i + 1 < len(data):
                word = data[i] | (data[i + 1] << 8)
                words.append(f"0x{word:04X}")
        return json.dumps({"address": f"0x{address:04X}", "data": words})
    else:
        return json.dumps({"error": f"Unknown format: {format_type}"})

def _handle_write_memory(args):
    """Write to memory"""
    ensure_emulator()
    memory = _emulator_state["memory"]

    try:
        address = _parse_int_arg(args.get("address"), "address", minimum=0, maximum=memory.size - 1)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    data_str = args.get("data")
    if not isinstance(data_str, str):
        return json.dumps({"error": "data must be a string"})
    
    try:
        if data_str.startswith("@"):
            data = data_str[1:].encode("ascii")
        else:
            data = bytes.fromhex(data_str)
    except UnicodeEncodeError:
        return json.dumps({"error": "ASCII data must contain only ASCII characters"})
    except ValueError as e:
        return json.dumps({"error": f"Invalid data payload: {e}"})

    if address + len(data) > memory.size:
        return json.dumps({"error": "address + data size exceeds memory bounds"})
    
    for i, byte in enumerate(data):
        memory.write(address + i, byte)
    
    return json.dumps({
        "status": "written",
        "address": f"0x{address:04X}",
        "size": len(data),
        "data": data_str[:50] + ("..." if len(data_str) > 50 else "")
    })

def _handle_graphics_get_pixel(args):
    """Get pixel color"""
    ensure_emulator()
    try:
        x = _parse_int_arg(args["x"], "x")
        y = _parse_int_arg(args["y"], "y")
        layer_value = args.get("layer")
        layer = None if layer_value is None else _parse_int_arg(layer_value, "layer", minimum=0, maximum=8)
    except (KeyError, ValueError) as e:
        return json.dumps({"error": str(e)})
    
    gfx = _emulator_state["gfx"]
    in_bounds = 0 <= x < gfx.width and 0 <= y < gfx.height
    
    if layer is not None:
        # Access layer arrays directly
        if layer == 0:
            color = int(gfx.layer_0[y, x]) if in_bounds else 0
        elif 1 <= layer <= 4:
            color = int(gfx.background_layers[layer - 1][y, x]) if in_bounds else 0
        else:
            color = int(gfx.sprite_layers[layer - 5][y, x]) if in_bounds else 0
    else:
        color = int(gfx.screen[y, x]) if in_bounds else 0
    
    return json.dumps({"x": x, "y": y, "color": color, "layer": layer})

def _handle_graphics_get_screen(args):
    """Get screen buffer"""
    ensure_emulator()
    format_type = args.get("format", "summary")
    
    gfx = _emulator_state["gfx"]
    screen = gfx.screen
    
    if format_type == "summary":
        non_zero = int((screen != 0).sum())
        return json.dumps({
            "width": gfx.width,
            "height": gfx.height,
            "non_black_pixels": non_zero,
            "format": "RGBA indexed"
        })
    elif format_type == "raw":
        # Flatten and base64 encode
        data = screen.flatten().tobytes()
        b64 = base64.b64encode(data).decode("ascii")
        return json.dumps({
            "width": gfx.width,
            "height": gfx.height,
            "data_base64": b64,
            "encoding": "raw uint8"
        })
    elif format_type in {"base64", "png"}:
        # Export as PNG (grayscale palette) if PIL available
        try:
            if not _HAS_PIL:
                raise RuntimeError("Pillow not installed")
            img = Image.fromarray(screen.astype('uint8'), mode='L')
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            b64 = base64.b64encode(buf.getvalue()).decode('ascii')
            return json.dumps({
                "width": gfx.width,
                "height": gfx.height,
                "encoding": "png_base64",
                "png_base64": b64
            })
        except Exception as e:
            return json.dumps({"error": f"PNG export failed: {e}"})
    else:
        return json.dumps({"error": f"Unknown format: {format_type}"})

def _handle_graphics_set_pixel(args):
    """Set pixel color"""
    ensure_emulator()
    try:
        x = _parse_int_arg(args.get("x"), "x")
        y = _parse_int_arg(args.get("y"), "y")
        color = _parse_int_arg(args.get("color"), "color", minimum=0, maximum=0xFF)
        layer = _parse_int_arg(args.get("layer", 0), "layer", minimum=0, maximum=8)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    
    gfx = _emulator_state["gfx"]
    # Set the layer register and use the internal method
    old_vl = gfx.VL
    gfx.VL = layer
    if 0 <= x < gfx.width and 0 <= y < gfx.height:
        gfx._set_pixel_to_layer(x, y, color)
    gfx.VL = old_vl
    
    return json.dumps({"status": "set", "x": x, "y": y, "color": color, "layer": layer})

def _handle_keyboard_inject_key(args):
    """Inject keyboard input"""
    ensure_emulator()
    kbd = _emulator_state["kbd"]

    try:
        key, scan_code = _normalize_keyboard_key_arg(args.get("key"), kbd.key_mapping)
        count = _parse_int_arg(args.get("count", 1), "count", minimum=0)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    kbd = _emulator_state["kbd"]
    
    for _ in range(count):
        if scan_code is not None:
            _emulator_state["cpu"].add_key_to_buffer(scan_code)
        else:
            kbd.press_key(key)
    
    response = {
        "status": "injected",
        "key": key,
        "count": count
    }
    if scan_code is not None:
        response["scan_code"] = f"0x{scan_code:02X}"

    return json.dumps(response)

def _handle_keyboard_get_buffer():
    """Get keyboard buffer state"""
    ensure_emulator()
    kbd = _emulator_state["kbd"]
    status = {}
    try:
        status = kbd.get_buffer_status() if hasattr(kbd, "get_buffer_status") else {}
    except Exception:
        status = {}
    return json.dumps({
        "status": status
    })

def _handle_graphics_export_png(args):
    """Export screen as base64 PNG with optional palette"""
    ensure_emulator()
    palette = (args.get("palette") or "grayscale").lower()
    gfx = _emulator_state["gfx"]
    screen = gfx.screen.astype('uint8')
    try:
        if not _HAS_PIL:
            raise RuntimeError("Pillow not installed")
        if palette == "grayscale":
            img = Image.fromarray(screen, mode='L')
        elif palette == "heatmap":
            # Simple heatmap mapping using three channels
            import numpy as np
            s = screen
            r = np.clip(s * 2, 0, 255).astype('uint8')
            g = np.clip(255 - np.abs(s - 128) * 2, 0, 255).astype('uint8')
            b = (255 - s).astype('uint8')
            rgb = np.dstack((r, g, b))
            img = Image.fromarray(rgb, mode='RGB')
        else:
            img = Image.fromarray(screen, mode='L')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        b64 = base64.b64encode(buf.getvalue()).decode('ascii')
        return json.dumps({"png_base64": b64, "palette": palette})
    except Exception as e:
        return json.dumps({"error": f"PNG export failed: {e}"})

def _handle_graphics_set_blend_mode(args):
    ensure_emulator()
    try:
        mode = _parse_int_arg(args.get("mode"), "mode", minimum=0, maximum=4)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    gfx = _emulator_state["gfx"]
    gfx.blend_mode = mode
    return json.dumps({"status": "blend_set", "mode": gfx.blend_mode})

def _handle_sound_control(args):
    """Control sound system"""
    ensure_emulator()
    action = args["action"]
    
    sound = _emulator_state["sound"]
    
    if action == "play":
        address = int(args.get("address", 0x2000))
        frequency_reg = int(args.get("frequency", 220)) & 0xFF
        volume_reg = int(args.get("volume", 128)) & 0xFF
        waveform_reg = int(args.get("waveform", 1)) & 0xFF
        # Update registers and attempt to play via NovaSound
        if hasattr(sound, "update_registers"):
            sound.update_registers(sa=address, sf=frequency_reg, sv=volume_reg, sw=waveform_reg | 0x80)
        # Try to play on default channel derived from SW
        played = sound.splay() if hasattr(sound, "splay") else False
        return json.dumps({
            "status": "playing" if played else "play_failed",
            "frequency_reg": frequency_reg,
            "volume_reg": volume_reg,
            "waveform_reg": waveform_reg
        })
    elif action == "stop":
        stopped = sound.sstop() if hasattr(sound, "sstop") else False
        return json.dumps({"status": "stopped" if stopped else "stop_failed"})
    elif action == "get_state":
        return json.dumps({
            "frequency": sound.get_register("SF") if hasattr(sound, "get_register") else 0,
            "volume": sound.get_register("SV") if hasattr(sound, "get_register") else 0,
            "waveform": sound.get_register("SW") if hasattr(sound, "get_register") else 0,
        })
    else:
        return json.dumps({"error": f"Unknown action: {action}"})

def _handle_disassemble(args):
    """Disassemble memory into Nova-16 assembly text."""
    ensure_emulator()

    def _parse_int(value, default=0):
        if value is None:
            return default
        if isinstance(value, str):
            return int(value, 0)
        return int(value)

    start_addr = _parse_int(args.get("start_addr", 0x0000), 0x0000) & 0xFFFF
    num_instructions = max(1, _parse_int(args.get("num_instructions", 100), 100))

    memory = _emulator_state["memory"]
    bytecode = bytes(memory.read_byte(i) for i in range(0x10000))
    opcode_map, register_map = nova_disassembler.create_reverse_maps()

    lines: List[str] = []
    pc = start_addr

    for _ in range(num_instructions):
        if pc >= len(bytecode):
            break

        opcode = bytecode[pc]

        if opcode in opcode_map:
            mnemonic, operands, size = nova_disassembler.disassemble_instruction_new(
                bytecode,
                pc,
                opcode_map,
                register_map,
            )
            size = max(1, int(size))
            instruction_bytes = bytecode[pc:pc + size]
            hex_dump = " ".join(f"{b:02X}" for b in instruction_bytes)
            operand_str = ", ".join(operands) if operands else ""
            asm_text = f"{mnemonic} {operand_str}".strip()
            lines.append(f"{pc:04X}: {hex_dump:<15} {asm_text}")
            pc += size
        else:
            lines.append(f"{pc:04X}: {opcode:02X}              DB 0x{opcode:02X}")
            pc += 1

        if pc >= 0x10000:
            break

    return json.dumps({
        "start_addr": f"0x{start_addr:04X}",
        "num_instructions": num_instructions,
        "decoded_instructions": len(lines),
        "assembly": "\n".join(lines)
    })

def _handle_memory_dump(args):
    """Create memory dump"""
    ensure_emulator()
    start_addr = args.get("start_addr", 0x0000)
    size = args.get("size", 256)
    
    memory = _emulator_state["memory"]
    dump = []
    
    for i in range(0, size, 16):
        addr = start_addr + i
        line_data = [memory.read_byte(addr + j) for j in range(16) if addr + j < 0x10000]
        hex_part = " ".join(f"{b:02X}" for b in line_data)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in line_data)
        dump.append(f"0x{addr:04X}: {hex_part:<48} {ascii_part}")
    
    return json.dumps({
        "start_addr": f"0x{start_addr:04X}",
        "size": size,
        "dump": "\n".join(dump)
    })

def _handle_breakpoint_set(args):
    """Set breakpoint (stored in CPU state)"""
    ensure_emulator()
    try:
        address = _parse_int_arg(args["address"], "address", minimum=0, maximum=0xFFFF)
    except (KeyError, ValueError) as e:
        return json.dumps({"error": str(e)})
    
    cpu = _emulator_state["cpu"]
    if not hasattr(cpu, "breakpoints"):
        cpu.breakpoints = set()
    
    cpu.breakpoints.add(address)
    
    return json.dumps({
        "status": "breakpoint_set",
        "address": f"0x{address:04X}",
        "total_breakpoints": len(cpu.breakpoints)
    })

def _handle_breakpoint_clear(args):
    """Clear a single breakpoint or all"""
    ensure_emulator()
    cpu = _emulator_state["cpu"]
    addr = args.get("address")
    if not hasattr(cpu, "breakpoints"):
        cpu.breakpoints = set()
    if addr is None:
        cpu.breakpoints.clear()
        return json.dumps({"status": "breakpoints_cleared", "total_breakpoints": 0})
    else:
        try:
            address = _parse_int_arg(addr, "address", minimum=0, maximum=0xFFFF)
        except ValueError as e:
            return json.dumps({"error": str(e)})
        cpu.breakpoints.discard(address)
        return json.dumps({
            "status": "breakpoint_cleared",
            "address": f"0x{address:04X}",
            "total_breakpoints": len(cpu.breakpoints)
        })

def _handle_breakpoint_list():
    ensure_emulator()
    cpu = _emulator_state["cpu"]
    bps = sorted([f"0x{bp:04X}" for bp in getattr(cpu, "breakpoints", set())])
    return json.dumps({"breakpoints": bps, "count": len(bps)})

def _handle_cpu_run_until(args):
    """Run until PC equals address, halt, or max cycles"""
    ensure_emulator()
    try:
        target = _parse_int_arg(args.get("address"), "address", minimum=0, maximum=0xFFFF)
        max_cycles = _parse_int_arg(args.get("max_cycles", 100000), "max_cycles", minimum=0)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    cpu = _emulator_state["cpu"]
    cycles = 0
    start_pc = cpu.pc
    while cycles < max_cycles and not cpu.halted and cpu.pc != target:
        cpu.step()
        cycles += 1
        _emulator_state["cycle_count"] += 1
        # Honor stored breakpoints if CPU implements PC check externally
        if hasattr(cpu, "breakpoints") and cpu.pc in cpu.breakpoints:
            break
    return json.dumps({
        "status": "ran_until",
        "start_pc": f"0x{start_pc:04X}",
        "final_pc": f"0x{cpu.pc:04X}",
        "cycles": cycles,
        "halted": cpu.halted,
        "hit_breakpoint": bool(getattr(cpu, "breakpoints", set()) and cpu.pc in cpu.breakpoints),
        "reached_target": cpu.pc == target
    })

def _handle_assert_memory(args):
    """Assert memory matches expected bytes"""
    ensure_emulator()
    memory = _emulator_state["memory"]

    try:
        address = _parse_int_arg(args.get("address"), "address", minimum=0, maximum=memory.size - 1)
        expected_hex, expected_bytes = _parse_hex_bytes_arg(args.get("expected"), "expected")
    except ValueError as e:
        return json.dumps({"error": str(e)})

    if address + len(expected_bytes) > memory.size:
        return json.dumps({"error": "address + expected size exceeds memory bounds"})

    actual = bytes(memory.read_byte(address + i) for i in range(len(expected_bytes)))
    passed = actual == expected_bytes
    diff = [
        {
            "offset": i,
            "expected": f"{expected_bytes[i]:02X}",
            "actual": f"{actual[i]:02X}"
        }
        for i in range(len(expected_bytes)) if expected_bytes[i] != actual[i]
    ]
    return json.dumps({
        "status": "assert_memory",
        "address": f"0x{address:04X}",
        "length": len(expected_bytes),
        "passed": passed,
        "diff": diff
    })

def _handle_memory_search(args):
    ensure_emulator()
    mem = _emulator_state["memory"]

    try:
        pattern_hex, pat = _parse_hex_bytes_arg(args.get("pattern"), "pattern")
        start = _parse_int_arg(args.get("start", 0), "start", minimum=0, maximum=mem.size - 1)
        end = _parse_int_arg(args.get("end", mem.size - 1), "end", minimum=0, maximum=mem.size - 1)
        max_results = _parse_int_arg(args.get("max_results", 16), "max_results", minimum=1)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    if end < start:
        return json.dumps({"error": "end must be >= start"})

    data = bytes(int(mem.read(i)) for i in range(start, end + 1))
    matches: List[int] = []
    idx = 0
    while idx <= len(data) - len(pat) and len(matches) < max_results:
        if data[idx:idx + len(pat)] == pat:
            matches.append(start + idx)
            idx += len(pat)
        else:
            idx += 1
    return json.dumps({
        "pattern": pattern_hex.upper(),
        "start": f"0x{start:04X}",
        "end": f"0x{end:04X}",
        "matches": [f"0x{m:04X}" for m in matches]
    })

def _handle_run_until_memory(args):
    ensure_emulator()
    mem = _emulator_state["memory"]

    try:
        address = _parse_int_arg(args.get("address"), "address", minimum=0, maximum=mem.size - 1)
        _, expected = _parse_hex_bytes_arg(args.get("value"), "value")
        max_cycles = _parse_int_arg(args.get("max_cycles", 100000), "max_cycles", minimum=0)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    if address + len(expected) > mem.size:
        return json.dumps({"error": "address + value size exceeds memory bounds"})

    cpu = _emulator_state["cpu"]
    cycles = 0
    start_pc = cpu.pc

    def read_slice(addr, n):
        return bytes(int(mem.read(addr + i)) for i in range(n))

    while cycles < max_cycles and not cpu.halted:
        if read_slice(address, len(expected)) == expected:
            break
        cpu.step()
        cycles += 1
        _emulator_state["cycle_count"] += 1
    return json.dumps({
        "status": "ran_until_memory",
        "start_pc": f"0x{start_pc:04X}",
        "final_pc": f"0x{cpu.pc:04X}",
        "cycles": cycles,
        "matched": read_slice(address, len(expected)) == expected
    })

def _handle_set_flags(args):
    ensure_emulator()
    flags_map = args.get("flags", {})
    cpu = _emulator_state["cpu"]
    letter_to_index = {
        "E": 11, "A": 10, "H": 9, "P": 8, "Z": 7, "C": 6,
        "I": 5, "D": 4, "B": 3, "O": 2, "S": 1, "T": 0
    }
    updated = {}
    for k, v in flags_map.items():
        kk = str(k).upper()
        if kk in letter_to_index:
            idx = letter_to_index[kk]
            cpu.flags[idx] = 1 if int(v) != 0 else 0
            updated[kk] = cpu.flags[idx]
    return json.dumps({"status": "flags_set", "updated": updated})

def _handle_timer_control(args):
    ensure_emulator()
    cpu = _emulator_state["cpu"]
    try:
        parsed_values = {
            name: _parse_int_arg(args[name], name, minimum=0, maximum=0xFFFF)
            for name in ("TT", "TM", "TC", "TS")
            if name in args
        }
    except ValueError as e:
        return json.dumps({"error": str(e)})

    for name, idx in [("TT", 0), ("TM", 1), ("TC", 2), ("TS", 3)]:
        if name in parsed_values:
            cpu.timer[idx] = parsed_values[name]

    return json.dumps({"status": "timer_set", "timer": {
        "TT": cpu.timer[0], "TM": cpu.timer[1], "TC": cpu.timer[2], "TS": cpu.timer[3]
    }})

def _handle_keyboard_type_string(args):
    ensure_emulator()
    text = args.get("text")
    if not isinstance(text, str):
        return json.dumps({"error": "text must be a string"})

    try:
        text.encode("ascii")
    except UnicodeEncodeError:
        return json.dumps({"error": "text must contain only ASCII characters"})

    kbd = _emulator_state["kbd"]
    kbd.type_string(text)
    return json.dumps({"status": "typed", "length": len(text)})

def _handle_disassemble_program(args):
    ensure_emulator()
    prog = _emulator_state.get("program_path")
    if not prog:
        return json.dumps({"error": "No program loaded"})

    def _parse_optional_int(value):
        if value is None:
            return None
        if isinstance(value, str):
            return int(value, 0)
        return int(value)

    def _parse_bool(value, default):
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    # Build a minimal arg namespace
    class _Args:
        def __init__(self, d):
            self.start = _parse_optional_int(d.get("start"))
            self.end = _parse_optional_int(d.get("end"))
            self.show_hex = _parse_bool(d.get("show_hex"), True)
            self.show_addresses = _parse_bool(d.get("show_addresses"), True)
            self.filter_instructions = d.get("filter_instructions")
            self.exclude_instructions = d.get("exclude_instructions")
            self.format = "text"
            self.output = None
            self.quiet = True
            self.interactive = False
            self.analyze_dataflow = False
            self.analyze_liveness = False
            self.analyze_functions = False
            self.analyze_loops = False
            self.analyze_deadcode = False
            self.analyze_security = False
            self.analyze_patterns = False

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            nova_disassembler.disassemble(str(prog), _Args(args))
    except Exception as e:
        return json.dumps({"error": f"Disassembly failed: {e}"})

    return json.dumps({"assembly": buf.getvalue()[:100000]})

# Debugger tool handlers

def _handle_debugger_init():
    """Initialize debugger for loaded program"""
    ensure_emulator()
    cpu = _emulator_state["cpu"]
    mem = _emulator_state["memory"]
    gfx = _emulator_state["gfx"]
    snd = _emulator_state["sound"]
    prog = _emulator_state.get("program_path")
    
    if not prog:
        return json.dumps({"error": "No program loaded. Load a program first with load_program."})
    
    dbg = nova_debugger.NovaDebugger(cpu, mem, gfx, snd, str(prog))
    _emulator_state["debugger"] = dbg
    
    return json.dumps({
        "status": "debugger_initialized",
        "program": str(prog),
        "pc": f"0x{cpu.pc:04X}",
        "symbols_loaded": len(dbg.symbol_table) > 0,
        "symbol_count": len(dbg.symbol_table)
    })

def _handle_debugger_step(args):
    """Step through instructions with debugger enabled"""
    ensure_emulator()
    count = args.get("count", 1)
    show_disasm = args.get("show_disasm", True)
    show_regs = args.get("show_regs", True)
    
    cpu = _emulator_state["cpu"]
    dbg = _emulator_state.get("debugger")
    mem = _emulator_state["memory"]
    
    if not dbg:
        # Auto-initialize debugger if not already done
        _handle_debugger_init()
        dbg = _emulator_state.get("debugger")
        if not dbg:
            return json.dumps({"error": "Failed to initialize debugger"})
    
    result = {
        "status": "stepped",
        "steps": count,
        "instructions": []
    }
    
    for i in range(count):
        if cpu.halted:
            result["halted"] = True
            break
        
        old_pc = cpu.pc
        cpu.step()
        _emulator_state["cycle_count"] += 1
        
        step_info = {"pc": f"0x{old_pc:04X}"}
        
        if show_disasm:
            try:
                opcode = mem.memory[old_pc]
                if opcode in dbg.opcode_map:
                    mnemonic, operands, size = nova_disassembler.disassemble_instruction_new(
                        mem.memory, old_pc, dbg.opcode_map, dbg.register_map
                    )
                    operand_str = ', '.join(operands) if operands else ""
                    step_info["instruction"] = f"{mnemonic} {operand_str}".strip()
            except Exception:
                pass
        
        result["instructions"].append(step_info)
    
    if show_regs:
        result["registers"] = {
            "pc": f"0x{cpu.pc:04X}",
            "r": [f"0x{r:02X}" for r in cpu.Rregisters[:10]],
            "p": [f"0x{p:04X}" for p in cpu.Pregisters[:10]]
        }
    
    return json.dumps(result)

def _handle_debugger_run_until_breakpoint(args):
    """Run until breakpoint or halt"""
    ensure_emulator()
    max_cycles = args.get("max_cycles", 100000)
    
    cpu = _emulator_state["cpu"]
    dbg = _emulator_state.get("debugger")
    
    if not dbg:
        _handle_debugger_init()
        dbg = _emulator_state.get("debugger")
    
    if not dbg:
        return json.dumps({"error": "Failed to initialize debugger"})
    
    start_pc = cpu.pc
    cycles = 0
    breakpoint_hit = None
    
    while cycles < max_cycles and not cpu.halted:
        if cpu.pc in dbg.breakpoints:
            breakpoint_hit = f"0x{cpu.pc:04X}"
            break
        
        cpu.step()
        cycles += 1
        _emulator_state["cycle_count"] += 1
    
    return json.dumps({
        "status": "ran_until_breakpoint",
        "start_pc": f"0x{start_pc:04X}",
        "final_pc": f"0x{cpu.pc:04X}",
        "cycles": cycles,
        "halted": cpu.halted,
        "breakpoint_hit": breakpoint_hit
    })

def _handle_debugger_print_state(args):
    """Print full debugger state"""
    ensure_emulator()
    show_stack = args.get("show_stack", True)
    stack_entries = args.get("stack_entries", 16)
    
    cpu = _emulator_state["cpu"]
    mem = _emulator_state["memory"]
    dbg = _emulator_state.get("debugger")
    
    if not dbg:
        return json.dumps({"error": "Debugger not initialized. Call debugger_init first."})
    
    result = {
        "pc": f"0x{cpu.pc:04X}",
        "halted": cpu.halted,
        "cycles": _emulator_state["cycle_count"],
        "r_registers": [f"0x{r:02X}" for r in cpu.Rregisters[:10]],
        "p_registers": [f"0x{p:04X}" for p in cpu.Pregisters[:10]],
        "flags": {
            "Z": int(cpu.flags[7]),
            "C": int(cpu.flags[6]),
            "S": int(cpu.flags[1]),
            "O": int(cpu.flags[2]),
            "I": int(cpu.flags[5]),
            "D": int(cpu.flags[4]),
            "B": int(cpu.flags[3])
        }
    }
    
    # Current instruction
    try:
        opcode = mem.memory[cpu.pc]
        if opcode in dbg.opcode_map:
            mnemonic, operands, size = nova_disassembler.disassemble_instruction_new(
                mem.memory, cpu.pc, dbg.opcode_map, dbg.register_map
            )
            operand_str = ', '.join(operands) if operands else ""
            result["current_instruction"] = f"{mnemonic} {operand_str}".strip()
            result["instruction_size"] = size
    except Exception:
        pass
    
    # Stack contents
    if show_stack:
        sp = cpu.Pregisters[8]
        stack_data = []
        for i in range(stack_entries):
            addr = (int(sp) + i * 2) & 0xFFFF
            try:
                val = mem.read_word(addr)
                stack_data.append({
                    "offset": i,
                    "address": f"0x{addr:04X}",
                    "value": f"0x{val:04X}"
                })
            except Exception:
                break
        result["stack"] = stack_data
    
    return json.dumps(result)

def _handle_debugger_get_symbol_table():
    """Get symbol table from loaded program"""
    ensure_emulator()
    dbg = _emulator_state.get("debugger")
    
    if not dbg:
        return json.dumps({"error": "Debugger not initialized. Call debugger_init first."})
    
    symbols = {k: v for k, v in dbg.symbol_table.items()}
    reverse_symbols = {f"0x{k:04X}": v for k, v in dbg.reverse_symbol_table.items()}
    
    return json.dumps({
        "symbols": symbols,
        "reverse_symbols": reverse_symbols,
        "total": len(dbg.symbol_table)
    })

def _handle_debugger_inspect_instruction(args):
    """Inspect an instruction at a given address"""
    ensure_emulator()
    address = args.get("address")
    
    cpu = _emulator_state["cpu"]
    mem = _emulator_state["memory"]
    dbg = _emulator_state.get("debugger")
    
    if not dbg:
        _handle_debugger_init()
        dbg = _emulator_state.get("debugger")
    
    if address is None:
        address = cpu.pc
    
    address = int(address) & 0xFFFF
    
    if address >= len(mem.memory):
        return json.dumps({"error": f"Address 0x{address:04X} is beyond memory bounds"})
    
    result = {"address": f"0x{address:04X}"}
    
    try:
        opcode = mem.memory[address]
        
        # Check for string data
        from nova_disassembler import is_string_data, format_string_data
        is_string, str_length = is_string_data(mem.memory, address)
        
        if is_string and str_length > 1:
            result["type"] = "string"
            result["length"] = str_length
            result["directive"] = format_string_data(mem.memory, address, str_length)
        elif opcode in dbg.opcode_map:
            mnemonic, operands, size = nova_disassembler.disassemble_instruction_new(
                mem.memory, address, dbg.opcode_map, dbg.register_map
            )
            result["type"] = "instruction"
            result["mnemonic"] = mnemonic
            result["operands"] = operands
            result["size"] = size
            result["hex"] = ' '.join(f'{mem.memory[address + i]:02X}' for i in range(size))
        else:
            result["type"] = "data"
            result["byte_value"] = f"0x{opcode:02X}"
            result["hex"] = f"{opcode:02X}"
        
        # Symbol information
        if address in dbg.reverse_symbol_table:
            result["symbol"] = dbg.reverse_symbol_table[address]
    
    except Exception as e:
        result["error"] = str(e)
    
    return json.dumps(result)

# NoBASIC compiler handlers

def _handle_nobasic_compile(args):
    """Compile NoBASIC source to binary"""
    if not _HAS_NOBASIC:
        return json.dumps({"error": "NoBASIC compiler not available. Check installation in NoBASIC/ directory."})
    
    source_path_arg = args["source_path"]
    output_path_arg = args.get("output_path")
    verbose = args.get("verbose", False)
    auto_load = args.get("auto_load", False)
    
    # Handle relative paths
    if not Path(source_path_arg).is_absolute():
        source_path = Path(__file__).parent / source_path_arg
    else:
        source_path = Path(source_path_arg)
    
    if not source_path.exists():
        return json.dumps({"error": f"Source file not found: {source_path}"})
    
    if source_path.suffix.lower() != '.nobasic':
        return json.dumps({"error": "Source file must have .nobasic extension"})
    
    if output_path_arg is None:
        output_path = source_path.with_suffix('.asm')
    elif not Path(output_path_arg).is_absolute():
        output_path = Path(__file__).parent / output_path_arg
    else:
        output_path = Path(output_path_arg)
    
    try:
        # Compile NoBASIC to assembly
        compile_nobasic(str(source_path), str(output_path), verbose)
        
        # Binary file should be created automatically
        binary_path = output_path.with_suffix('.bin')
        
        if not binary_path.exists():
            return json.dumps({
                "error": f"Binary file not created at {binary_path}",
                "assembly_created": str(output_path)
            })
        
        result = {
            "status": "compiled",
            "source": str(source_path),
            "assembly": str(output_path),
            "binary": str(binary_path)
        }
        
        # Auto-load if requested
        if auto_load:
            ensure_emulator()
            try:
                entry_point = _emulator_state["memory"].load(binary_path)
                _emulator_state["program_path"] = binary_path
                _emulator_state["cpu"].pc = entry_point
                _emulator_state["cycle_count"] = 0
                _emulator_state["debugger"] = None  # Reset debugger
                result["auto_loaded"] = True
                result["entry_point"] = f"0x{entry_point:04X}"
            except Exception as e:
                result["auto_load_error"] = str(e)
        
        return json.dumps(result)
    except SystemExit as e:
        return json.dumps({
            "error": f"Compilation failed with exit code {e.code}",
            "exit_code": e.code,
            "source": str(source_path),
            "assembly": str(output_path)
        })
    except Exception as e:
        import traceback
        return json.dumps({
            "error": f"Compilation failed: {str(e)}",
            "traceback": traceback.format_exc()
        })

if __name__ == "__main__":
    import asyncio
    
    # Initialize emulator on startup
    initialize_emulator()
    
    # Start MCP server with stdio transport
    from mcp.server.stdio import stdio_server
    from mcp.server.lowlevel.server import InitializationOptions
    from mcp.types import ServerCapabilities, ToolsCapability
    
    async def main():
        async with stdio_server() as (read_stream, write_stream):
            # Create proper initialization options with server capabilities
            init_options = InitializationOptions(
                server_name="Nova-16 MCP",
                server_version="1.0.0",
                capabilities=ServerCapabilities(
                    tools=ToolsCapability()
                )
            )
            await server.run(read_stream, write_stream, init_options)
    
    asyncio.run(main())
