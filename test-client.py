#!/usr/bin/env python3
"""
Simple test client for MCP server via stdio transport
This connects to the Docker container and tests if tools are working
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    """Test the MCP server"""

    # For local testing: connect to Python script directly
    # For Docker: we'll need to use docker exec

    server_params = StdioServerParameters(
        command="python",
        args=["openproject-mcp-sse.py"],
        env=None
    )

    print("🔌 Connecting to MCP server...")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            print("📡 Initializing session...")
            await session.initialize()

            # List available tools
            print("\n📋 Listing available tools...")
            tools = await session.list_tools()

            print(f"\n✅ Found {len(tools.tools)} tools:")
            for tool in tools.tools[:10]:  # Show first 10
                print(f"   - {tool.name}: {tool.description[:60]}...")

            if len(tools.tools) > 10:
                print(f"   ... and {len(tools.tools) - 10} more tools")

            # Test a simple tool call
            print("\n🧪 Testing 'test_connection' tool...")
            result = await session.call_tool("test_connection", arguments={})

            print(f"\n✅ Tool response:")
            for content in result.content:
                if hasattr(content, 'text'):
                    print(content.text)

            print("\n✨ All tests passed!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
