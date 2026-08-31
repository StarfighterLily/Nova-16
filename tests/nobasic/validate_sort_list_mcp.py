#!/usr/bin/env python3
"""
Validate SortA list operation using Nova-16 MCP server.
- Loads NoBASIC/test_sort_list.bin
- Runs program to completion
- Asserts first five elements are 1..5 after ascending sort with high sentinel fill

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
BIN = ROOT / "fixtures" / "test_sort_list.bin"

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
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT.parent / "nova_mcp_server.py")]
    )
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            await call(session, "init_emulator", {})
            await call(session, "load_program", {"program_path": str(BIN)})
            await call(session, "cpu_run", {"cycles": 1000000})
            await call(session, "read_memory", {"address": 0x1000, "size": 24, "format": "hex"})
            patterns = [
                ("big", "00 01 00 02 00 03 00 04 00 05 00 FF"),
                ("little", "01 00 02 00 03 00 04 00 05 00 FF 00"),
            ]
            for label, pattern in patterns:
                result = await call(session, "assert_memory", {
                    "address": 0x1000,
                    "expected": pattern
                })
                if result.get("passed"):
                    print(f"SortA validation ({label}-endian) passed.")
                    break
            else:
                print("SortA validation failed (both endian patterns).", file=sys.stderr)
                sys.exit(1)
    print("\nSortA MCP validation complete.\n")

if __name__ == "__main__":
    asyncio.run(main())
