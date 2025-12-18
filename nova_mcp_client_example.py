#!/usr/bin/env python3
"""
Example MCP Client for Nova-16 Emulator

This demonstrates how to connect to the Nova-16 MCP server
and execute commands programmatically.
"""

import asyncio
import sys
from pathlib import Path

# Example usage with mcp library
try:
    from mcp import ClientSession
    from mcp.client.stdio import StdioClientTransport
except ImportError:
    print("Please install mcp library: pip install mcp")
    sys.exit(1)

async def main():
    """Example: Connect to Nova-16 MCP server and run a program"""
    
    # Start the MCP server as a subprocess
    import subprocess
    
    server_process = subprocess.Popen(
        [sys.executable, str(Path(__file__).parent / "nova_mcp_server.py")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Create client session
    transport = StdioClientTransport(
        server_process.stdout,
        server_process.stdin,
    )
    
    async with ClientSession(transport) as session:
        await session.initialize()
        
        # List available tools
        tools = await session.list_tools()
        print(f"Available tools: {len(tools.tools)}")
        
        # Initialize emulator
        print("\n1. Initializing emulator...")
        result = await session.call_tool("init_emulator", {})
        print(result.content[0].text)
        
        # Load a program (example - replace with actual program)
        print("\n2. Loading program...")
        try:
            result = await session.call_tool("load_program", {
                "program_path": "asm/very_simple_test.bin"
            })
            print(result.content[0].text)
        except Exception as e:
            print(f"Could not load program: {e}")
        
        # Get CPU state
        print("\n3. Getting CPU state...")
        result = await session.call_tool("get_cpu_state", {})
        print(result.content[0].text)
        
        # Step CPU a few times
        print("\n4. Stepping CPU...")
        result = await session.call_tool("cpu_step", {"count": 5})
        print(result.content[0].text)
        
        # Read memory
        print("\n5. Reading memory...")
        result = await session.call_tool("read_memory", {
            "address": 0x0000,
            "size": 32,
            "format": "hex"
        })
        print(result.content[0].text)
    
    server_process.terminate()

if __name__ == "__main__":
    asyncio.run(main())
