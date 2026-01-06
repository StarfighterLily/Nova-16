# Nova-16 MCP / Emulator / NoBASIC
- Purpose: Nova-16 custom 16-bit CPU emulator with unified 64KB memory, graphics/sound/keyboard integration; MCP server exposes emulator control to LLM clients; NoBASIC compiler generates Nova-16 assembly/binaries.
- Platform: Windows (PowerShell). Entry executables are Python scripts.
- Tech stack: Python 3.10, numpy, pygame, MCP protocol (JSON-RPC over stdio).
- Key components: nova_cpu.py (CPU core), nova_memory.py (64KB memory), nova_gfx.py (graphics), nova_sound.py (audio), nova_keyboard.py (input), nova.py (emulator runner), nova_assembler.py (ASM→BIN), nobasic_compiler.py (NoBASIC→ASM→BIN), nova_mcp_server.py (MCP bridge), nova_debugger.py (interactive debugger).
- Docs to skim: FEATURES_OVERVIEW.md, IMPLEMENTATION_SUMMARY.md, MCP_QUICK_REFERENCE.md, MCP_SERVER_README.md, MCP_DEBUGGER_NOBASIC_FEATURES.md, MCP_INTEGRATION_GUIDE.md, GRAPHICS_MONITOR_USAGE.md.