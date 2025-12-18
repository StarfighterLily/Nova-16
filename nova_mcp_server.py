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
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal
import base64
import struct

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
except ImportError as e:
    print(f"Error importing Nova modules: {e}", file=sys.stderr)
    sys.exit(1)

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.types as types

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
}

def initialize_emulator():
    """Initialize all Nova-16 system components"""
    mem = memory_module.Memory()
    gfx = gfx_module.GFX()
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
    })
    
    return proc, mem, gfx, kbd, snd

def ensure_emulator():
    """Ensure emulator is initialized"""
    if _emulator_state["cpu"] is None:
        initialize_emulator()

# Create MCP server
server = Server("nova-16-mcp")

@server.list_tools()
async def handle_list_tools():
    """List all available Nova-16 control tools"""
    return [
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
                    "x": {"type": "integer", "description": "X coordinate (0-319)"},
                    "y": {"type": "integer", "description": "Y coordinate (0-199)"},
                    "layer": {"type": "integer", "description": "Layer (0-7, default: all)"}
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
                        "enum": ["base64", "raw", "summary"],
                        "description": "Output format (default: summary)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="graphics_set_pixel",
            description="Set pixel color in graphics buffer",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate (0-319)"},
                    "y": {"type": "integer", "description": "Y coordinate (0-199)"},
                    "color": {"type": "integer", "description": "Color value (0-255)"},
                    "layer": {"type": "integer", "description": "Layer (0-7, default: 0)"}
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
                        "description": "Key code or ASCII character (e.g., 'a', 'Enter', 'Space', or hex like '0x41')"
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
    ]

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
        else:
            result_text = json.dumps({"error": f"Unknown tool: {name}"})
            
        return [TextContent(type="text", text=result_text)]
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
    return json.dumps({
        "status": "initialized",
        "memory_size": 65536,
        "screen_width": 320,
        "screen_height": 200,
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
    source_path = args["source_path"]
    output_path = args.get("output_path")
    
    # Handle relative paths
    if not Path(source_path).is_absolute():
        source_path = Path(__file__).parent / source_path
    
    if not Path(source_path).exists():
        return json.dumps({"error": f"File not found: {source_path}"})
    
    if output_path is None:
        output_path = str(source_path).replace(".asm", ".bin")
    elif not Path(output_path).is_absolute():
        output_path = Path(__file__).parent / output_path
    
    try:
        nova_assembler.assemble_file(str(source_path), str(output_path))
        return json.dumps({
            "status": "assembled",
            "source": str(source_path),
            "output": str(output_path)
        })
    except Exception as e:
        return json.dumps({"error": f"Assembly failed: {str(e)}"})

def _handle_cpu_step(args):
    """Step CPU execution"""
    ensure_emulator()
    count = args.get("count", 1)
    
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
    cycles = args.get("cycles", 10000)
    
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
    register = args["register"].upper()
    value = args["value"]
    
    cpu = _emulator_state["cpu"]
    
    if register == "PC":
        cpu.pc = value & 0xFFFF
    elif register.startswith("R"):
        idx = int(register[1])
        cpu.Rregisters[idx] = value & 0xFF
    elif register.startswith("P"):
        idx = int(register[1])
        cpu.Pregisters[idx] = value & 0xFFFF
    else:
        return json.dumps({"error": f"Unknown register: {register}"})
    
    return json.dumps({
        "status": "set",
        "register": register,
        "value": f"0x{value:04X}" if register.startswith("P") else f"0x{value:02X}"
    })

def _handle_read_memory(args):
    """Read from memory"""
    ensure_emulator()
    address = args["address"]
    size = args["size"]
    format_type = args.get("format", "hex")
    
    memory = _emulator_state["memory"]
    data = [memory.read(address + i) for i in range(size)]
    
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

def _handle_write_memory(args):
    """Write to memory"""
    ensure_emulator()
    address = args["address"]
    data_str = args["data"]
    
    memory = _emulator_state["memory"]
    
    if data_str.startswith("@"):
        # ASCII string
        data = data_str[1:].encode("ascii")
    else:
        # Hex string
        data = bytes.fromhex(data_str)
    
    for i, byte in enumerate(data):
        if address + i < 0x10000:
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
    x = args["x"]
    y = args["y"]
    layer = args.get("layer")
    
    gfx = _emulator_state["gfx"]
    
    if layer is not None:
        color = gfx.get_pixel_layer(x, y, layer)
    else:
        color = gfx.screen[y, x] if 0 <= y < 200 and 0 <= x < 320 else 0
    
    return json.dumps({"x": x, "y": y, "color": color})

def _handle_graphics_get_screen(args):
    """Get screen buffer"""
    ensure_emulator()
    format_type = args.get("format", "summary")
    
    gfx = _emulator_state["gfx"]
    screen = gfx.screen
    
    if format_type == "summary":
        non_zero = int((screen != 0).sum())
        return json.dumps({
            "width": 320,
            "height": 200,
            "non_black_pixels": non_zero,
            "format": "RGBA indexed"
        })
    elif format_type == "raw":
        # Flatten and base64 encode
        data = screen.flatten().tobytes()
        b64 = base64.b64encode(data).decode("ascii")
        return json.dumps({
            "width": 320,
            "height": 200,
            "data_base64": b64,
            "encoding": "raw uint8"
        })
    else:
        return json.dumps({"error": f"Unknown format: {format_type}"})

def _handle_graphics_set_pixel(args):
    """Set pixel color"""
    ensure_emulator()
    x = args["x"]
    y = args["y"]
    color = args["color"]
    layer = args.get("layer", 0)
    
    gfx = _emulator_state["gfx"]
    gfx.set_pixel_layer(x, y, color, layer)
    
    return json.dumps({"status": "set", "x": x, "y": y, "color": color, "layer": layer})

def _handle_keyboard_inject_key(args):
    """Inject keyboard input"""
    ensure_emulator()
    key = args["key"]
    count = args.get("count", 1)
    
    kbd = _emulator_state["kbd"]
    
    # Convert key to key code
    if key.lower().startswith("0x"):
        key_code = int(key, 16)
    elif len(key) == 1:
        key_code = ord(key)
    elif key == "Enter":
        key_code = 0x0D
    elif key == "Space":
        key_code = 0x20
    elif key == "Escape":
        key_code = 0x1B
    else:
        # Try as raw ASCII
        key_code = ord(key[0])
    
    for _ in range(count):
        kbd.inject_key(key_code)
    
    return json.dumps({
        "status": "injected",
        "key_code": f"0x{key_code:02X}",
        "count": count
    })

def _handle_keyboard_get_buffer():
    """Get keyboard buffer state"""
    ensure_emulator()
    kbd = _emulator_state["kbd"]
    
    buffer_size = len(kbd.buffer) if hasattr(kbd, "buffer") else 0
    
    return json.dumps({
        "buffer_size": buffer_size,
        "buffer_capacity": 16 if hasattr(kbd, "buffer_size") else "unknown"
    })

def _handle_sound_control(args):
    """Control sound system"""
    ensure_emulator()
    action = args["action"]
    
    sound = _emulator_state["sound"]
    
    if action == "play":
        address = args.get("address", 0x2000)
        frequency = args.get("frequency", 440)
        volume = args.get("volume", 128)
        waveform = args.get("waveform", 0)
        
        sound.set_register("SA", address)
        sound.set_register("SF", frequency)
        sound.set_register("SV", volume)
        sound.set_register("SW", waveform)
        # sound.play() if hasattr(sound, 'play') else None
        
        return json.dumps({
            "status": "playing",
            "frequency": frequency,
            "volume": volume,
            "waveform": waveform
        })
    elif action == "stop":
        sound.set_register("SV", 0)
        return json.dumps({"status": "stopped"})
    elif action == "get_state":
        return json.dumps({
            "frequency": sound.get_register("SF") if hasattr(sound, "get_register") else 0,
            "volume": sound.get_register("SV") if hasattr(sound, "get_register") else 0,
            "waveform": sound.get_register("SW") if hasattr(sound, "get_register") else 0,
        })
    else:
        return json.dumps({"error": f"Unknown action: {action}"})

def _handle_disassemble(args):
    """Disassemble instructions"""
    ensure_emulator()
    start_addr = args.get("start_addr", 0x0000)
    num_instructions = args.get("num_instructions", 100)
    
    memory = _emulator_state["memory"]
    
    try:
        disassembly = nova_disassembler.disassemble(
            memory, start_addr, num_instructions
        )
        return json.dumps({
            "start_addr": f"0x{start_addr:04X}",
            "count": num_instructions,
            "disassembly": disassembly
        })
    except Exception as e:
        return json.dumps({"error": f"Disassembly failed: {str(e)}"})

def _handle_memory_dump(args):
    """Create memory dump"""
    ensure_emulator()
    start_addr = args.get("start_addr", 0x0000)
    size = args.get("size", 256)
    
    memory = _emulator_state["memory"]
    dump = []
    
    for i in range(0, size, 16):
        addr = start_addr + i
        line_data = [memory.read(addr + j) for j in range(16) if addr + j < 0x10000]
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
    address = args["address"]
    
    cpu = _emulator_state["cpu"]
    if not hasattr(cpu, "breakpoints"):
        cpu.breakpoints = set()
    
    cpu.breakpoints.add(address)
    
    return json.dumps({
        "status": "breakpoint_set",
        "address": f"0x{address:04X}",
        "total_breakpoints": len(cpu.breakpoints)
    })

if __name__ == "__main__":
    import asyncio
    
    # Initialize emulator on startup
    initialize_emulator()
    print("Nova-16 MCP Server initialized", file=sys.stderr)
    
    # Start MCP server with async main
    asyncio.run(server.run())
