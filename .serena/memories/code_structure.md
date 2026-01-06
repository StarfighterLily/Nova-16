# Code Structure (high level)
- Root Python modules: nova.py (emulator runner), nova_cpu.py, nova_memory.py, nova_gfx.py, nova_sound.py, nova_keyboard.py, nova_assembler.py, nova_debugger.py, nova_disassembler.py, nova_graphics_monitor.py, nova_mcp_server.py.
- NoBASIC: NoBASIC/ directory with compiler (`nobasic_compiler.py`), tests, and .nobasic sources; outputs .asm/.bin.
- ASM examples: asm/ folder with sample assembly programs and .org docs.
- MCP docs: FEATURES_OVERVIEW.md, IMPLEMENTATION_SUMMARY.md, MCP_QUICK_REFERENCE.md, MCP_SERVER_README.md, MCP_DEBUGGER_NOBASIC_FEATURES.md, MCP_INTEGRATION_GUIDE.md, MCP_SERVER_DOCUMENTATION.md.
- Profiling/monitoring: nova_profiler.py, nova_gpu_profiler.py, nova_memory_profiler.py, performance_benchmark_runner.py, GRAPHICS_MONITOR_USAGE.md, NOVA_PROFILER_README.md.
- Tests: tests/ and NoBASIC/tests/ (pytest configuration in pytest.ini).