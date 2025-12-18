# Nova-16 MCP Server - Claude Integration Guide

## Quick Setup for Claude Desktop

### Step 1: Locate Claude Configuration

Claude Desktop stores MCP server configurations in:

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

Usually expands to:
```
C:\Users\YourUsername\AppData\Roaming\Claude\claude_desktop_config.json
```

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

### Step 2: Edit Configuration

Open the file and add this Nova-16 configuration:

```json
{
  "mcpServers": {
    "nova-16": {
      "command": "python",
      "args": [
        "C:\\Code\\Nova\\nova_mcp_server.py"
      ]
    }
  }
}
```

**Important:** Replace `C:\\Code\\Nova` with your actual Nova project path.

### Step 3: Restart Claude

Close and reopen Claude Desktop. The Nova-16 tools should now appear.

### Step 4: Test Connection

Ask Claude:
> What tools are available from the Nova-16 server?

Claude should respond with a list of available tools.

## Example Configuration File

```json
{
  "mcpServers": {
    "nova-16": {
      "command": "python",
      "args": [
        "C:\\Code\\Nova\\nova_mcp_server.py"
      ]
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem@latest",
        "C:\\Code"
      ]
    }
  }
}
```

## Using Nova-16 in Claude

Once configured, you can:

### 1. Load and Run Programs

```
Me: Load asm/very_simple_test.bin and run it

Claude: I'll load the program into the Nova-16 emulator and execute it.
```

### 2. Inspect State

```
Me: What's the current CPU state?

Claude: I'll check the current CPU registers and state.
```

### 3. Debug Programs

```
Me: Can you trace through my program step by step?

Claude: I'll step through and show you each instruction.
```

### 4. Write and Assemble Code

```
Me: Create a program that outputs the pattern AABBCC to graphics

Claude: I'll write the assembly, assemble it, and run it.
```

### 5. Control Emulator

```
Me: Inject the character 'a' and run for 500 cycles

Claude: I'll send the key and execute the program.
```

## Troubleshooting

### Claude doesn't see Nova-16 tools

1. **Check file path**: Ensure the path in config is correct and uses `\\` for Windows
2. **Verify MCP installation**: 
   ```bash
   pip list | grep mcp
   ```
3. **Check permissions**: Ensure Python script is readable
4. **Restart Claude**: Close completely, wait 5 seconds, reopen

### "Python not found" error

Add Python to PATH or use full path:

```json
{
  "mcpServers": {
    "nova-16": {
      "command": "C:\\Users\\YourUsername\\AppData\\Local\\Programs\\Python\\Python312\\python.exe",
      "args": [
        "C:\\Code\\Nova\\nova_mcp_server.py"
      ]
    }
  }
}
```

### Server crashes or hangs

- Check stderr logs in Claude's developer console
- Verify Nova dependencies installed: `pip install numpy pygame mcp`
- Try running server manually: `python nova_mcp_server.py`

### Tools appear but fail

- Ensure current directory is Nova project root
- Check file paths are accessible
- Verify binary/assembly files exist

## Advanced Configuration

### Using with Other MCP Servers

You can configure multiple MCP servers:

```json
{
  "mcpServers": {
    "nova-16": {
      "command": "python",
      "args": ["C:\\Code\\Nova\\nova_mcp_server.py"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem@latest"]
    },
    "postgres": {
      "command": "python",
      "args": ["-m", "mcp_postgres"]
    }
  }
}
```

### Environment Variables

If you need to pass environment variables:

```json
{
  "mcpServers": {
    "nova-16": {
      "command": "python",
      "args": ["C:\\Code\\Nova\\nova_mcp_server.py"],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "NOVA_DEBUG": "0"
      }
    }
  }
}
```

## Complete Workflow Example

### Setup

1. Edit Claude config with Nova-16 server path
2. Restart Claude
3. Test: "Can you list the Nova-16 tools?"

### Interactive Development

```
Me: I have a Nova-16 assembly program that should draw a checkerboard pattern.
Can you help me debug it?

Claude: I'll help debug your program. First, let me see what you have.

Me: Here's my program:
[user provides assembly code]

Claude: 
1. I'll assemble this program
2. Load it into the emulator
3. Run it for a few cycles
4. Check what's on the screen
5. Analyze the results

[Claude uses the MCP tools to:]
- Call assemble(source_path="checkerboard.asm")
- Call load_program(program_path="checkerboard.bin")
- Call cpu_run(cycles=10000)
- Call graphics_get_screen()
- Interprets results and suggests fixes
```

## Documentation Links

- [Full MCP Server Documentation](MCP_SERVER_DOCUMENTATION.md)
- [Nova-16 CPU Architecture](docs/CPU%20Specification.md)
- [Assembly Guide](docs/)

## FAQ

**Q: Can I run the server on a different machine?**
A: The MCP protocol requires stdio connection, so the server must run locally. However, you could use SSH port forwarding for remote execution.

**Q: How many emulator instances can run?**
A: Currently, one per server process. You can run multiple servers by duplicating the configuration with different server names.

**Q: Is my code sandboxed?**
A: Yes - only Nova-16 assembly binaries can execute, preventing arbitrary code execution.

**Q: Can I save/load emulator state?**
A: Currently no, but this could be added as a future enhancement.

**Q: What about GUI graphics?**
A: The server provides pixel-level access but doesn't render a window. You can use the `graphics_get_screen()` tool to retrieve the raw pixel buffer.

## Performance Tips

- Batch operations when possible (multiple memory reads in one call)
- Use `cpu_run` instead of repeated `cpu_step` for large programs
- Use `graphics_get_screen(format="summary")` to avoid transferring large buffers
- Run longer simulations locally with `python nova.py` for GUI when possible

## Getting Help

If you encounter issues:

1. Check MCP_SERVER_DOCUMENTATION.md for detailed tool reference
2. Test server manually: `python nova_mcp_server.py`
3. Check Python environment: `pip list`
4. Review Claude console logs for error messages

---

Happy Nova-16 development with Claude! 🚀
