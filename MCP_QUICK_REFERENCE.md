# Nova-16 MCP Server - Quick Reference

## What You Now Have

A complete MCP server for controlling Nova-16 from Claude AI.

```
┌──────────────────────────────────────────────────────────┐
│           Claude Desktop AI                               │
│  "Load program and run it"                               │
└────────────────────┬─────────────────────────────────────┘
                     │ MCP Protocol (JSON-RPC over stdio)
                     ↓
┌──────────────────────────────────────────────────────────┐
│         nova_mcp_server.py (Running Process)             │
│  - Listens on stdin for MCP requests                    │
│  - Calls Nova-16 emulator functions                      │
│  - Returns JSON responses                                │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ↓
┌──────────────────────────────────────────────────────────┐
│          Nova-16 Emulator System                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │
│  │   CPU        │ │   Memory     │ │  Graphics    │     │
│  │  (Registers) │ │   (64KB)     │ │  (320x200)   │     │
│  └──────────────┘ └──────────────┘ └──────────────┘     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │
│  │   Sound      │ │  Keyboard    │ │ Assembler    │     │
│  │  (8-channel) │ │  (Input buf) │ │ (ASM→Binary) │     │
│  └──────────────┘ └──────────────┘ └──────────────┘     │
└──────────────────────────────────────────────────────────┘
```

## Installation Checklist

- [x] Installed `mcp` package
- [x] Installed `numpy` and `pygame`
- [x] Created `nova_mcp_server.py`
- [x] Created setup helpers and documentation
- [x] Verified all imports work
- [ ] **Next: Configure Claude (see below)**

## Configure Claude (2 Steps)

### Step 1: Find Configuration File

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
C:\Users\YourName\AppData\Roaming\Claude\claude_desktop_config.json
```

### Step 2: Add This Section

Open `claude_desktop_config.json` and add to the `mcpServers` object:

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

**Replace** `C:\\Code\\Nova` with your actual path.

### Step 3: Restart Claude

Close Claude completely, wait 5 seconds, reopen it.

### Step 4: Verify (Ask Claude)

```
"What Nova-16 tools are available?"
```

Claude should list 20+ tools!

## Available Tools (Quick Reference)

### 🔧 CPU Control
- `init_emulator` - Reset everything
- `load_program` - Load .bin file
- `cpu_step` - Execute 1+ cycles
- `cpu_run` - Run many cycles
- `get_cpu_state` - Show all registers
- `set_register` - Change register value

### 💾 Memory
- `read_memory` - Read bytes
- `write_memory` - Write bytes
- `memory_dump` - Hex dump

### 🎨 Graphics
- `graphics_get_pixel` - Read color
- `graphics_set_pixel` - Write color
- `graphics_get_screen` - Get screen buffer

### ⌨️ Input
- `keyboard_inject_key` - Send key press
- `keyboard_get_buffer` - Check buffer

### 🔊 Sound
- `sound_control` - Play/stop audio

### 🔧 Development
- `assemble` - Compile .asm → .bin
- `disassemble` - Decompile .bin → asm
- `breakpoint_set` - Set breakpoint

## Usage Patterns

### Pattern 1: Program Development
```
1. Ask Claude to write assembly
2. Claude uses assemble tool
3. Claude uses load_program tool
4. Claude uses cpu_run tool
5. Claude shows results
6. Iterate based on feedback
```

### Pattern 2: Debugging
```
1. You provide broken program
2. Claude uses disassemble tool
3. Claude uses memory_dump tool
4. Claude uses cpu_step tool (in loop)
5. Claude identifies issue
6. Claude suggests fix
```

### Pattern 3: Interactive
```
1. Load keyboard input program
2. Claude runs for cycles
3. Claude injects keys
4. Claude runs more cycles
5. Claude reads graphics
6. Show interactive results
```

## Example Conversations

### Conversation 1: Simple Program

**You:**
```
Load asm/very_simple_test.bin and run it for 500 cycles.
Show me the final CPU state.
```

**Claude:**
- Loads program with `load_program`
- Runs with `cpu_run`
- Gets state with `get_cpu_state`
- Shows registers and flags

### Conversation 2: Write a Program

**You:**
```
Write an assembly program that counts from 0 to 10
and stores the result in memory at 0x1000.
```

**Claude:**
- Writes assembly code
- Saves to file
- Uses `assemble` tool
- Uses `load_program` tool
- Uses `cpu_run` tool
- Uses `read_memory` tool to verify
- Shows results

### Conversation 3: Debug Graphics

**You:**
```
I'm trying to draw a diagonal line but it's not working.
Can you debug my program?
```

**Claude:**
- Uses `disassemble` to review code
- Uses `graphics_get_screen` to check output
- Uses `memory_dump` to inspect graphics registers
- Uses `cpu_step` to trace execution
- Identifies the bug
- Suggests fix

## File Locations

| File | Purpose |
|------|---------|
| `nova_mcp_server.py` | Main server (run this) |
| `setup_mcp_server.py` | Installation helper |
| `MCP_SERVER_README.md` | Main documentation |
| `MCP_SERVER_DOCUMENTATION.md` | Complete reference |
| `MCP_CLAUDE_SETUP.md` | Setup guide |
| `MCP_INSTALLATION_SUMMARY.md` | This summary |
| `requirements-mcp.txt` | Dependencies |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Tools don't appear | Restart Claude (after config change) |
| "Python not found" | Use full path in config |
| Server crashes | Run `pip install -r requirements-mcp.txt` |
| Permission denied | Check file isn't read-only |

## Performance Tips

- Use `cpu_run` instead of many `cpu_step` calls
- Use `format="summary"` for graphics queries
- Batch memory operations when possible
- Run long programs headless (no GUI overhead)

## What This Enables

✅ Write assembly with Claude's help  
✅ Test programs in seconds  
✅ Debug interactively  
✅ Learn Nova-16 through experimentation  
✅ Prototype graphics and sound  
✅ Get AI suggestions for optimizations  

## Common Tasks

### Task: Load a program and see what happens
```
Claude: "Load asm/starfield.bin and run for 5000 cycles"
→ Uses: load_program, cpu_run, get_cpu_state
```

### Task: Check memory contents
```
Claude: "What's at memory address 0x1000?"
→ Uses: read_memory
```

### Task: Draw a pixel
```
Claude: "Draw a red pixel at (100, 100)"
→ Uses: graphics_set_pixel
```

### Task: Trace through code
```
Claude: "Step through my program 10 times and show me the CPU state each time"
→ Uses: cpu_step (loop), get_cpu_state (loop)
```

### Task: Create a graphics program
```
Claude: "Write a program that draws a checkerboard pattern"
→ Uses: assemble, load_program, cpu_run, graphics_get_screen
```

## Next Steps

1. ✅ Installation done
2. ⬜ Edit Claude config (2 minutes)
3. ⬜ Restart Claude (1 minute)
4. ⬜ Start building programs with Claude! (unlimited fun)

## Quick Start Command

After configuring Claude, just ask:

```
"Can you help me write and test a Nova-16 program?"
```

Claude will handle the rest!

---

**Setup Status**: ✅ Complete  
**Configuration Status**: ⏳ Awaiting Claude config  
**Ready to Use**: Once you configure and restart Claude  

Enjoy developing with Nova-16 and Claude! 🚀
