# Nova-16 MCP Server

A locally-hosted Model Context Protocol server providing LLM control over the Nova-16 16-bit CPU emulator.

## What is This?

This MCP server bridges Claude (and other LLM clients) with the Nova-16 emulator, enabling:

- **Interactive program development** - Write, assemble, and run Nova-16 programs with Claude's help
- **Debugging assistance** - Step through code, inspect memory, analyze state
- **Graphics programming** - Control pixel-level graphics output
- **Audio synthesis** - Generate sound with the Nova-16 sound system
- **System-level control** - Read/write memory, modify registers, inject keyboard input
- **Assembly guidance** - Write and optimize assembly code with AI assistance

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements-mcp.txt
```

Or individually:
```bash
pip install mcp numpy pygame
```

### 2. Configure Claude Desktop

Run the setup helper:
```bash
python setup_mcp_server.py
```

This will:
- Check all dependencies
- Verify Nova-16 modules
- Show you the exact configuration to add to Claude

Alternatively, manually add to Claude's `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "nova-16": {
      "command": "python",
      "args": ["C:\\Code\\Nova\\nova_mcp_server.py"]
    }
  }
}
```

### 3. Restart Claude Desktop

Close and reopen Claude. The Nova-16 tools will now be available.

## Usage Examples

### Example 1: Load and Run a Program

```
You: Load asm/very_simple_test.bin and run it for 1000 cycles

Claude: I'll load the program and execute it for the specified cycles.
[Uses load_program and cpu_run tools]

Result shows:
- Program loaded at entry point 0x0000
- Executed 1000 cycles successfully
- Final CPU state with registers and flags
```

### Example 2: Debug a Program

```
You: I wrote a program to draw a checkerboard pattern but it's not working.
     Can you help debug it?

Claude: I'll analyze your program by:
1. Assembling it
2. Loading it
3. Running it
4. Checking the graphics output
5. Examining memory state

[Uses assemble, load_program, cpu_run, graphics_get_screen, memory_dump tools]

Result identifies the issue with detailed explanation and suggestions
```

### Example 3: Interactive Control

```
You: Run the keyboard input demo and press keys 'a', 'b', 'c'

Claude: I'll execute the program and inject those key presses
[Uses load_program, cpu_run, keyboard_inject_key in sequence]

Result shows how the program responds to each key
```

### Example 4: Real-Time Monitoring

```
You: Step through my program one instruction at a time and show me
     the CPU state after each step

Claude: I'll step through and display state
[Repeatedly uses cpu_step and get_cpu_state]

Result shows each instruction's effect on registers and flags
```

## Available Tools

### CPU Control
- `init_emulator` - Initialize/reset emulator
- `load_program` - Load compiled binary
- `cpu_step` - Execute single or multiple cycles
- `cpu_run` - Run until halt or cycle limit
- `cpu_halt` - Stop execution
- `cpu_reset` - Reset CPU state
- `get_cpu_state` - Read all registers/flags
- `set_register` - Modify single register

### Memory Access
- `read_memory` - Read from any address
- `write_memory` - Write to memory
- `memory_dump` - Formatted hexdump

### Assembly/Disassembly
- `assemble` - Compile .asm to .bin
- `disassemble` - Convert binary back to assembly

### Graphics
- `graphics_get_pixel` - Read pixel color
- `graphics_set_pixel` - Write pixel
- `graphics_get_screen` - Get full screen buffer

### Keyboard
- `keyboard_inject_key` - Send key presses
- `keyboard_get_buffer` - Check input state

### Audio
- `sound_control` - Play/stop/configure sound

### Debugging
- `breakpoint_set` - Set breakpoint address

See [MCP_SERVER_DOCUMENTATION.md](MCP_SERVER_DOCUMENTATION.md) for complete reference.

## Files

- **nova_mcp_server.py** - Main MCP server implementation
- **setup_mcp_server.py** - Installation and setup helper
- **nova_mcp_client_example.py** - Example Python client
- **MCP_SERVER_DOCUMENTATION.md** - Detailed tool reference
- **MCP_CLAUDE_SETUP.md** - Claude configuration guide
- **requirements-mcp.txt** - Python dependencies

## Architecture

```
Claude Desktop
    ↓
MCP Protocol (stdio)
    ↓
nova_mcp_server.py
    ↓
Nova-16 Emulator
├── nova_cpu.py (CPU core)
├── nova_memory.py (64KB memory)
├── nova_gfx.py (Graphics system)
├── nova_sound.py (Audio system)
└── nova_keyboard.py (Input handling)
```

## Key Features

### Full System Control
- Read/write all 64KB of unified memory
- Control 10 8-bit and 10 16-bit registers
- Access 8-layer graphics system
- Control multi-channel sound synthesis
- Inject keyboard input

### Development Integration
- Assemble from source to binary
- Disassemble binary back to readable code
- Step-by-step debugging with memory inspection
- Breakpoint support
- Real-time state monitoring

### LLM-Friendly
- All operations return structured JSON
- Comprehensive error reporting
- Multiple output formats (hex, ASCII, raw, binary)
- Summary and detailed views

## Performance

Typical performance on modern hardware:
- Single CPU cycle: ~1-5ms
- Memory read (256 bytes): ~0.1ms
- Full screen read: ~1-5ms
- Graphics pixel operations: ~0.05ms

## Troubleshooting

### MCP tools not appearing in Claude
1. Ensure `mcp` package installed: `pip install mcp`
2. Verify path in claude_desktop_config.json uses forward or double backslashes
3. Run setup_mcp_server.py to verify configuration
4. Restart Claude completely

### "Python not found" error
Use full path to Python executable in Claude config:
```json
{
  "command": "C:\\Python312\\python.exe",
  "args": ["..."]
}
```

### Server crashes immediately
Check dependencies installed and verify this is run from Nova project directory:
```bash
pip install -r requirements-mcp.txt
cd C:\Code\Nova
python nova_mcp_server.py
```

### Tools fail with file not found
Ensure binary/assembly files exist and use correct paths:
- Relative paths are relative to Nova project root
- Can use absolute paths too

## Development with Claude

### Workflow 1: Write-Compile-Test
1. Ask Claude to write assembly code
2. Claude assembles it with the MCP server
3. Claude loads and runs it
4. Claude inspects results and iterates

### Workflow 2: Guided Debugging
1. You provide broken program
2. Claude analyzes it
3. Claude runs it with instrumentation
4. Claude identifies issue and suggests fix
5. Repeat until working

### Workflow 3: Real-Time Interaction
1. Load interactive program (e.g., keyboard input demo)
2. Run for some cycles
3. Inject key presses
4. Observe output
5. Repeat with different inputs

## Advanced Usage

### Custom Programs
```
You: Write an assembly program that draws a triangle

Claude:
1. Writes complete assembly
2. Saves to file
3. Assembles with MCP
4. Loads and runs
5. Shows graphics result
6. Explains how it works
```

### Performance Analysis
```
You: How many cycles does it take to calculate fibonacci(10)?

Claude:
1. Writes fibonacci program
2. Runs with cycle counter
3. Reports cycle count
4. Suggests optimizations
```

### System Exploration
```
You: Show me what's in memory at 0xF000 (sprite register area)

Claude:
1. Reads and displays memory
2. Interprets register format
3. Explains sprite configuration
4. Suggests modifications
```

## Limitations

- Single emulator instance per server
- No real-time audio playback (sound is parameter-set only)
- Graphics rendered as pixel buffer (no display window)
- Server must run locally (stdio-based MCP protocol)
- No persistent state save/load

## Security

- Only Nova-16 bytecode can execute (safe)
- Arbitrary memory read/write allowed (by design)
- No filesystem access beyond program loading
- Run only in trusted environments

## What's Next?

After setup, try:
1. Ask Claude to explain the Nova-16 architecture
2. Request a simple graphics demo program
3. Ask Claude to write a keyboard input handler
4. Explore the emulator's capabilities interactively

## References

- [Nova-16 CPU Specification](docs/CPU%20Specification.md)
- [Graphics System Documentation](docs/VRAM%20Specification.md)
- [Assembly Guide](docs/)
- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)

## Support

For issues:
1. Check [MCP_SERVER_DOCUMENTATION.md](MCP_SERVER_DOCUMENTATION.md) for tool details
2. Run setup_mcp_server.py to verify installation
3. Test server manually: `python nova_mcp_server.py`
4. Check Python environment: `pip list | grep mcp`

---

**Built for**: Claude + Nova-16 emulator integration  
**License**: Same as Nova-16 project  
**Status**: Production-ready
