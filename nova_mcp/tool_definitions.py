"""MCP tool metadata for the Nova-16 server."""

from __future__ import annotations

from mcp.types import Tool


def build_tools() -> list[Tool]:
    """Return the MCP tool definitions exposed by the server."""
    return [
        Tool(
            name="init_emulator",
            description="Initialize or reset the Nova-16 emulator",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="load_program",
            description="Load a Nova-16 binary program into memory",
            inputSchema={
                "type": "object",
                "properties": {
                    "program_path": {
                        "type": "string",
                        "description": "Path to .bin file (absolute or relative to Nova directory)",
                    }
                },
                "required": ["program_path"],
            },
        ),
        Tool(
            name="assemble",
            description="Assemble Nova-16 assembly code to binary",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_path": {"type": "string", "description": "Path to .asm file"},
                    "output_path": {
                        "type": "string",
                        "description": "Path to output .bin file (optional, defaults to .bin variant of source)",
                    },
                },
                "required": ["source_path"],
            },
        ),
        Tool(
            name="cpu_step",
            description="Execute one CPU instruction cycle",
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of cycles to execute (default: 1)",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="cpu_run",
            description="Run CPU for specified number of cycles or until halt",
            inputSchema={
                "type": "object",
                "properties": {
                    "cycles": {
                        "type": "integer",
                        "description": "Number of cycles to run (default: 10000)",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="cpu_halt",
            description="Stop CPU execution",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="cpu_reset",
            description="Reset CPU state (PC, registers, flags)",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="clear_memory",
            description="Clear all memory contents to zero (preserves CPU state)",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="full_reset",
            description="Complete system reset: CPU, memory, graphics, sound, keyboard",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_cpu_state",
            description="Get current CPU state (registers, PC, flags)",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="set_register",
            description="Set CPU register value",
            inputSchema={
                "type": "object",
                "properties": {
                    "register": {
                        "type": "string",
                        "description": "Register name (R0-R9, P0-P9, PC)",
                    },
                    "value": {"type": "integer", "description": "Value to set"},
                },
                "required": ["register", "value"],
            },
        ),
        Tool(
            name="read_memory",
            description="Read data from memory",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {
                        "type": "integer",
                        "description": "Starting address (0x0000-0xFFFF)",
                    },
                    "size": {"type": "integer", "description": "Number of bytes to read"},
                    "format": {
                        "type": "string",
                        "enum": ["hex", "bytes", "ascii", "words"],
                        "description": "Output format (default: hex)",
                    },
                },
                "required": ["address", "size"],
            },
        ),
        Tool(
            name="write_memory",
            description="Write data to memory",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {
                        "type": "integer",
                        "description": "Starting address (0x0000-0xFFFF)",
                    },
                    "data": {
                        "type": "string",
                        "description": "Hex string (e.g., 'DEADBEEF') or ASCII string prefixed with '@' (e.g., '@Hello')",
                    },
                },
                "required": ["address", "data"],
            },
        ),
        Tool(
            name="graphics_get_pixel",
            description="Get pixel color at graphics coordinate",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate (0-255)"},
                    "y": {"type": "integer", "description": "Y coordinate (0-255)"},
                    "layer": {"type": "integer", "description": "Layer (0-8, default: all)"},
                },
                "required": ["x", "y"],
            },
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
                        "description": "Output format (default: summary)",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="graphics_export_png",
            description="Export current screen as base64 PNG",
            inputSchema={
                "type": "object",
                "properties": {
                    "palette": {
                        "type": "string",
                        "description": "Optional palette: 'grayscale' (default) or 'heatmap'",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="graphics_set_blend_mode",
            description="Set graphics blend mode (0=normal,1=add,2=sub,3=mul,4=screen)",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {"type": "integer", "description": "Blend mode (0-4)"}
                },
                "required": ["mode"],
            },
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
                    "layer": {"type": "integer", "description": "Layer (0-8, default: 0)"},
                },
                "required": ["x", "y", "color"],
            },
        ),
        Tool(
            name="keyboard_inject_key",
            description="Inject a key press into the keyboard buffer",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Key code or ASCII character, case-insensitive for named keys (e.g., 'a', 'Enter', 'Space', or hex like '0x41')",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of times to inject (default: 1)",
                    },
                },
                "required": ["key"],
            },
        ),
        Tool(
            name="keyboard_get_buffer",
            description="Get current keyboard input buffer",
            inputSchema={"type": "object", "properties": {}, "required": []},
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
                        "description": "Action to perform",
                    },
                    "address": {"type": "integer", "description": "Sound data address (for play)"},
                    "frequency": {"type": "integer", "description": "Frequency in Hz (for play)"},
                    "volume": {"type": "integer", "description": "Volume 0-255 (for play)"},
                    "waveform": {"type": "integer", "description": "Waveform type 0-3 (for play)"},
                },
                "required": ["action"],
            },
        ),
        Tool(
            name="disassemble",
            description="Disassemble binary back to assembly code",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_addr": {
                        "type": "integer",
                        "description": "Starting address (default: 0x0000)",
                    },
                    "num_instructions": {
                        "type": "integer",
                        "description": "Number of instructions to disassemble (default: 100)",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="memory_dump",
            description="Create a memory dump for debugging",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_addr": {
                        "type": "integer",
                        "description": "Starting address (default: 0x0000)",
                    },
                    "size": {"type": "integer", "description": "Size in bytes (default: 256)"},
                },
                "required": [],
            },
        ),
        Tool(
            name="breakpoint_set",
            description="Set a breakpoint at specific address",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "integer", "description": "Address to set breakpoint"}
                },
                "required": ["address"],
            },
        ),
        Tool(
            name="breakpoint_clear",
            description="Clear a breakpoint at address or all breakpoints",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {
                        "type": "integer",
                        "description": "Address to clear; omit to clear all",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="breakpoint_list",
            description="List all currently set breakpoints",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="cpu_run_until",
            description="Run CPU until PC equals address, halt, or max cycles",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "integer", "description": "Target PC address"},
                    "max_cycles": {
                        "type": "integer",
                        "description": "Cycle cap (default 100000)",
                    },
                },
                "required": ["address"],
            },
        ),
        Tool(
            name="assert_memory",
            description="Assert memory bytes match expected value at address",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "integer", "description": "Start address"},
                    "expected": {
                        "type": "string",
                        "description": "Hex string of expected bytes, e.g., '2A3A'",
                    },
                },
                "required": ["address", "expected"],
            },
        ),
        Tool(
            name="memory_search",
            description="Search memory for a hex pattern",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Hex string pattern (e.g., 'DE AD BE EF')",
                    },
                    "start": {"type": "integer", "description": "Optional start address (default 0x0000)"},
                    "end": {"type": "integer", "description": "Optional end address (default 0xFFFF)"},
                    "max_results": {
                        "type": "integer",
                        "description": "Limit number of matches (default 16)",
                    },
                },
                "required": ["pattern"],
            },
        ),
        Tool(
            name="run_until_memory",
            description="Run CPU until memory at address equals value or timeout",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "integer", "description": "Memory address to watch"},
                    "value": {
                        "type": "string",
                        "description": "Expected hex byte(s), e.g., 'FF' or 'DE AD'",
                    },
                    "max_cycles": {
                        "type": "integer",
                        "description": "Cycle cap (default 100000)",
                    },
                },
                "required": ["address", "value"],
            },
        ),
        Tool(
            name="set_flags",
            description="Set CPU flags (Z,C,S,O,I,T,B,D,P,H,A,E)",
            inputSchema={
                "type": "object",
                "properties": {
                    "flags": {
                        "type": "object",
                        "description": 'Map of flag letter to 0/1, e.g., {"Z":1,"I":0}',
                    }
                },
                "required": ["flags"],
            },
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
                    "TS": {"type": "integer", "description": "Timer speed"},
                },
                "required": [],
            },
        ),
        Tool(
            name="keyboard_type_string",
            description="Inject a full ASCII string as keypresses",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "ASCII text to type"}
                },
                "required": ["text"],
            },
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
                    "exclude_instructions": {"type": "string", "description": "Comma list to exclude"},
                },
                "required": [],
            },
        ),
        Tool(
            name="debugger_init",
            description="Initialize debugger for the loaded program",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="debugger_step",
            description="Step through CPU instructions with debugger enabled",
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of instructions to step (default: 1)",
                    },
                    "show_disasm": {
                        "type": "boolean",
                        "description": "Show disassembly (default: true)",
                    },
                    "show_regs": {
                        "type": "boolean",
                        "description": "Show registers (default: true)",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="debugger_run_until_breakpoint",
            description="Run CPU until a breakpoint is hit or program halts",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_cycles": {
                        "type": "integer",
                        "description": "Maximum cycles to run (default: 100000)",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="debugger_print_state",
            description="Print full debugger state (registers, stack, current instruction)",
            inputSchema={
                "type": "object",
                "properties": {
                    "show_stack": {
                        "type": "boolean",
                        "description": "Show stack contents (default: true)",
                    },
                    "stack_entries": {
                        "type": "integer",
                        "description": "Number of stack entries to show (default: 16)",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="debugger_get_symbol_table",
            description="Get symbol table from loaded program (if .sym file exists)",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="debugger_inspect_instruction",
            description="Get details about the current or specified instruction",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "integer", "description": "Address to inspect (default: PC)"}
                },
                "required": [],
            },
        ),
        Tool(
            name="nobasic_compile",
            description="Compile a NoBASIC source file to assembly and binary",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_path": {
                        "type": "string",
                        "description": "Path to .nobasic source file",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path to output .asm file (optional)",
                    },
                    "verbose": {
                        "type": "boolean",
                        "description": "Enable verbose output (default: false)",
                    },
                    "auto_load": {
                        "type": "boolean",
                        "description": "Automatically load compiled binary (default: false)",
                    },
                },
                "required": ["source_path"],
            },
        ),
    ]