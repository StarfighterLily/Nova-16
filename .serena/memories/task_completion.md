# Task Completion Checklist
- Run relevant tests: `pytest` (or focused markers) when code changes affect emulator/NoBASIC/assembler.
- If MCP tooling changed, run `python verify_mcp_tools.py` to ensure tools load and register.
- For assembly/NoBASIC changes, assemble/compile and run headless sanity checks: `python nova.py --headless your.bin --cycles 5000`.
- For MCP server changes, consider manual smoke test: `python nova_mcp_server.py` (ensure it starts without import errors).
- Document notable changes/limitations in the associated README or summary file if applicable.
- Avoid destructive git commands; leave workspace state as-is unless user requests otherwise.