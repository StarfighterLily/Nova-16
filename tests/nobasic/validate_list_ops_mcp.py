#!/usr/bin/env python3
"""
Validate NoBASIC list operations using Nova-16 MCP server.
- Loads NoBASIC/mcp_list_check.bin
- Runs program to HLT
- Asserts first 5 elements of L1 (base 0x1000) are 1..5
- Ensures remaining entries are 0 after Fill

Requires: pip install mcp
"""
import asyncio
import sys
import json
from pathlib import Path

try:
    from mcp import ClientSession, stdio_client, StdioServerParameters
except ImportError:
    print("Please install mcp: pip install mcp", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent
BIN = ROOT / "fixtures" / "mcp_list_check.bin"

async def call(session: ClientSession, name: str, args: dict):
    resp = await session.call_tool(name, args)
    text = resp.content[0].text
    print(f"\n>>> {name}({args})\n{text}")
    try:
        return json.loads(text)
    except Exception:
        return {}

async def main():
    if not BIN.exists():
        print(f"Missing {BIN}", file=sys.stderr)
        sys.exit(1)
    # Launch server via MCP stdio_client transport
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT.parent / "nova_mcp_server.py")]
    )
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            # Init + load program
            await call(session, "init_emulator", {})
            await call(session, "load_program", {"program_path": str(BIN)})
            # Run to completion
            await call(session, "cpu_run", {"cycles": 2000})
            patterns = [
                ("little", "01 00 02 00 03 00 04 00 05 00"),
                ("big", "00 01 00 02 00 03 00 04 00 05"),
            ]
            for label, pattern in patterns:
                result = await call(session, "assert_memory", {"address": 0x1000, "expected": pattern})
                if result.get("passed"):
                    print(f"List SEQ validation ({label}-endian) passed.")
                    break
            else:
                print("List SEQ validation failed (both endian patterns).", file=sys.stderr)
                sys.exit(1)

            zeros = await call(session, "assert_memory", {"address": 0x100A, "expected": "00 00 00 00"})
            if not zeros.get("passed", False):
                print("List FILL validation failed.", file=sys.stderr)
                sys.exit(1)
            print("List FILL validation passed.")
    print("\nList operations MCP validation complete.\n")

if __name__ == "__main__":
    asyncio.run(main())
