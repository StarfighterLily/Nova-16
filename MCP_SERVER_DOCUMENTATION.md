# Nova-16 MCP Server Documentation

## Overview

The Nova-16 MCP (Model Context Protocol) Server provides a locally-hosted interface for LLM control over the Nova-16 CPU emulator. This enables Claude and other MCP-compatible clients to:

- **Execute programs** on the emulated CPU
- **Inspect and modify** CPU state (registers, flags, PC)
- **Read/write memory** directly
- **Control graphics** (get/set pixels, retrieve screen state)
- **Inject keyboard input** for interactive programs
- **Control audio** synthesis
- **Assemble and disassemble** code
- **Debug** programs with breakpoints and memory inspection

## Installation

### Prerequisites

```bash
pip install mcp
pip install numpy pygame  # Nova-16 dependencies
```

### Setup

The MCP server runs as a subprocess and communicates via stdio.

## Quick Start

### 1. Starting the Server

```bash
python nova_mcp_server.py
```

The server runs indefinitely, listening for MCP protocol messages on stdin and writing responses to stdout.

### 2. Connecting with Claude (Desktop)

In your Claude settings, add this MCP server:

```json
{
  "type": "command",
  "command": "python",
  "args": ["path/to/nova_mcp_server.py"]
}
```

### 3. Running Programs

Once connected, you can:

```
Me: Load the program asm/very_simple_test.bin

Claude: I'll load the program into the Nova-16 emulator.
[Uses load_program tool]

Me: Run it for 1000 cycles

Claude: I'll execute the program.
[Uses cpu_run tool with cycles=1000]

Me: What's in memory at 0x1000?

Claude: I'll read that memory region.
[Uses read_memory tool]
```

## Tool Reference

### CPU Control

#### `init_emulator`
Initialize or reset the emulator to a clean state.

**Returns:**
- Memory size (64KB)
- Screen dimensions (320×200)
- Register configuration

#### `load_program`
Load a compiled Nova-16 binary into memory.

**Parameters:**
- `program_path` (string): Path to .bin file

**Returns:**
- Entry point address
- Initial PC value

#### `assemble`
Convert assembly source to binary.

**Parameters:**
- `source_path` (string): Path to .asm file
- `output_path` (string, optional): Output .bin path

**Returns:**
- Assembled file path

#### `cpu_step`
Execute one or more CPU instruction cycles.

**Parameters:**
- `count` (integer, optional): Cycles to execute (default: 1)

**Returns:**
- Old and new PC values
- Halted status
- Total cycle count

#### `cpu_run`
Run CPU for specified cycles or until halt.

**Parameters:**
- `cycles` (integer, optional): Cycles to run (default: 10000)

**Returns:**
- Cycles executed
- Final PC
- Halted status

#### `cpu_halt`
Stop CPU execution immediately.

#### `cpu_reset`
Reset CPU to clean state (PC=0, all registers=0, SP=0xFFFF).

#### `get_cpu_state`
Read all CPU state including registers, flags, and PC.

**Returns:**
```json
{
  "pc": "0x0000",
  "halted": false,
  "r_registers": ["0x00", "0x00", ...],
  "p_registers": ["0x0000", "0x0000", ...],
  "flags": {
    "Z": false,
    "C": false,
    "S": false,
    "O": false,
    "I": false
  }
}
```

#### `set_register`
Set a CPU register to a specific value.

**Parameters:**
- `register` (string): R0-R9, P0-P9, or PC
- `value` (integer): Value to set

### Memory Access

#### `read_memory`
Read data from memory at a specific address.

**Parameters:**
- `address` (integer): Starting address (0x0000-0xFFFF)
- `size` (integer): Bytes to read
- `format` (string): Output format
  - `hex`: Hex string (default)
  - `bytes`: Array of integers
  - `ascii`: Printable ASCII
  - `words`: 16-bit words

**Returns:**
- Address and size
- Data in requested format

**Example:**
```
read_memory(address=0x1000, size=16, format="hex")
→ {"address": "0x1000", "data": "48656C6C6F20576F726C64"}
```

#### `write_memory`
Write data to memory.

**Parameters:**
- `address` (integer): Starting address
- `data` (string): Hex string (e.g., "DEADBEEF") or ASCII string prefixed with '@'

**Returns:**
- Status, address, and size written

**Examples:**
```
write_memory(address=0x1000, data="DEADBEEF")
write_memory(address=0x1000, data="@Hello, World!")
```

#### `memory_dump`
Create a formatted hexdump of memory.

**Parameters:**
- `start_addr` (integer, optional): Starting address (default: 0x0000)
- `size` (integer, optional): Size in bytes (default: 256)

**Returns:**
- Formatted hexdump with hex and ASCII columns

### Graphics

#### `graphics_get_pixel`
Read pixel color at a coordinate.

**Parameters:**
- `x` (integer): X coordinate (0-319)
- `y` (integer): Y coordinate (0-199)
- `layer` (integer, optional): Layer (0-7)

**Returns:**
- Color value (0-255)

#### `graphics_set_pixel`
Write a pixel to the screen.

**Parameters:**
- `x` (integer): X coordinate
- `y` (integer): Y coordinate
- `color` (integer): Color value (0-255)
- `layer` (integer, optional): Layer (default: 0)

#### `graphics_get_screen`
Retrieve screen buffer state.

**Parameters:**
- `format` (string): Output format
  - `summary`: Pixel count (fastest)
  - `raw`: Base64-encoded image data
  - `base64`: Same as raw

**Returns:**
- Screen dimensions
- Pixel data or summary

### Keyboard Input

#### `keyboard_inject_key`
Send a key press to the keyboard input buffer.

**Parameters:**
- `key` (string): Key as character or special name
  - Character: 'a', 'A', '0', etc.
  - Special: "Enter", "Space", "Escape"
  - Hex: "0x41" for key code 0x41
- `count` (integer, optional): Number of times to inject

**Returns:**
- Key code that was injected
- Count injected

#### `keyboard_get_buffer`
Check keyboard input buffer state.

**Returns:**
- Current buffer size
- Buffer capacity

### Sound

#### `sound_control`
Control audio playback.

**Parameters:**
- `action` (string): "play", "stop", or "get_state"
- `frequency` (integer): Frequency in Hz (for play)
- `volume` (integer): Volume 0-255 (for play)
- `waveform` (integer): Waveform type 0-3 (for play)

**Returns:**
- Current sound state or playback confirmation

### Debugging

#### `disassemble`
Convert binary memory back to assembly code.

**Parameters:**
- `start_addr` (integer, optional): Starting address (default: 0x0000)
- `num_instructions` (integer, optional): Instructions to disassemble (default: 100)

**Returns:**
- Assembly code with addresses and hex opcodes

#### `breakpoint_set`
Set a breakpoint at an address.

**Parameters:**
- `address` (integer): Address for breakpoint

**Returns:**
- Breakpoint confirmation
- Total breakpoints set

## Example Workflows

### Workflow 1: Load and Run a Simple Program

```
User: Load asm/test_add.bin and run it for 500 cycles

Claude:
1. Calls load_program(program_path="asm/test_add.bin")
2. Calls cpu_run(cycles=500)
3. Calls get_cpu_state()
   
Returns: Final state with register values after execution
```

### Workflow 2: Debugging a Program

```
User: Debug why my program isn't producing graphics output

Claude:
1. Calls get_cpu_state() → Check current PC
2. Calls disassemble(start_addr=0x0000, num_instructions=20)
   → Show first 20 instructions
3. Calls graphics_get_screen(format="summary")
   → Check if any pixels are drawn
4. Calls read_memory(address=0xF000, size=64)
   → Check graphics registers
```

### Workflow 3: Interactive Program Control

```
User: Run the keyboard demo and press 'a' then Enter

Claude:
1. Calls load_program(program_path="asm/kbd_sprite.bin")
2. Calls cpu_run(cycles=1000)
3. Calls keyboard_inject_key(key="a")
4. Calls cpu_run(cycles=100)
5. Calls keyboard_inject_key(key="Enter")
6. Calls cpu_run(cycles=500)
7. Calls graphics_get_screen(format="summary")
```

## Advanced Usage

### Custom Assembly Development

```
User: Create a program that draws a diagonal line
1. User provides assembly code
2. Claude saves to new_line.asm
3. Calls assemble(source_path="new_line.asm")
4. Calls load_program(program_path="new_line.bin")
5. Calls cpu_run(cycles=10000)
6. Calls graphics_get_screen() to verify
```

### Memory Introspection

```
User: What's at address 0x1000?

Claude:
1. Calls read_memory(address=0x1000, size=256, format="hex")
2. Optionally calls read_memory(..., format="ascii")
3. Returns interpreted data
```

### Real-time Program Monitoring

```
User: Step through my program and show me the CPU state after each instruction

Claude:
1. Calls cpu_step(count=1)
2. Calls get_cpu_state()
3. Displays state
4. Repeats until halt or user stops
```

## Architecture

### Process Model

```
┌─────────────────────────┐
│   MCP Client (Claude)   │
│   via stdio transport   │
└──────────────┬──────────┘
               │
         (JSON-RPC messages)
               │
┌──────────────▼──────────┐
│   nova_mcp_server.py    │
│  (Tool handler dispatch)│
└──────────────┬──────────┘
               │
┌──────────────▼──────────────┐
│   Nova-16 Emulator Core     │
│  ├─ nova_cpu.py            │
│  ├─ nova_memory.py         │
│  ├─ nova_gfx.py            │
│  ├─ nova_sound.py          │
│  ├─ nova_keyboard.py       │
│  └─ nova_assembler.py      │
└────────────────────────────┘
```

### Shared Memory Model

All emulator components share a single memory reference for integrated control:

```python
mem = Memory()
cpu = CPU(mem, gfx, kbd, sound)
```

## Error Handling

All tool invocations return JSON with either:

**Success:**
```json
{
  "status": "ok",
  "data": {...}
}
```

**Error:**
```json
{
  "error": "Description of what went wrong",
  "traceback": "Python traceback if available"
}
```

## Performance Considerations

- **cpu_step**: ~1-5ms per cycle
- **read_memory**: ~0.1ms for 256 bytes
- **graphics_get_screen**: ~1-5ms depending on format
- **graphics_set_pixel**: ~0.05ms per pixel

For best performance:
- Use `cpu_run` for long executions instead of repeated `cpu_step`
- Use `format="summary"` for graphics queries instead of raw data
- Batch memory operations when possible

## Limitations

1. **No real-time audio**: Sound operations set parameters but don't generate audio
2. **Single instance**: Only one emulator per server process
3. **No networking**: Server must run locally due to MCP protocol
4. **Memory consistency**: Graphics/sound registers must be accessed through memory interface

## Troubleshooting

### Server won't start
- Check Python version (3.8+ required)
- Verify mcp package installed: `pip install mcp`
- Check Nova modules are accessible

### Tools not appearing in Claude
- Verify MCP server is running (check stderr output)
- Check Claude's MCP settings
- Restart Claude to re-sync tool list

### Program not producing output
- Check entry point: Use `get_cpu_state()` to verify PC
- Check memory: Use `memory_dump()` to inspect values
- Check graphics: Use `graphics_get_screen(format="summary")` to see pixel count

## Security Notes

- This server allows arbitrary memory read/write
- It can only run Nova-16 binaries (safe bytecode)
- No filesystem access beyond program loading
- Run only in trusted environments

## Future Enhancements

Potential additions:
- Real-time graphics rendering preview
- Audio synthesis with waveform generation
- Profiling and performance analysis tools
- Interactive debugging with step-over/breakpoints
- Program validation and sandboxing
- Memory protection and access control
