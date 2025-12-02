#!/usr/bin/env python3
"""
MCP Proxy Client - Connects stdio to remote SSE server
This allows Claude Desktop to connect to a remote MCP server via HTTP/SSE
"""

import sys
import json
import asyncio
import aiohttp
from typing import Any, Dict

SERVER_URL = "http://localhost:8000/sse"  # Change this to your server URL


async def main():
    """Main proxy loop - reads from stdin, sends to SSE server, writes response to stdout"""

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                # Read JSON-RPC message from stdin (from Claude Desktop)
                line = sys.stdin.readline()
                if not line:
                    break

                message = json.loads(line.strip())

                # Forward to SSE server
                async with session.post(
                    SERVER_URL,
                    json=message,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    result = await response.json()

                    # Write response back to stdout (to Claude Desktop)
                    sys.stdout.write(json.dumps(result) + "\n")
                    sys.stdout.flush()

            except json.JSONDecodeError:
                sys.stderr.write(f"Invalid JSON: {line}\n")
            except Exception as e:
                sys.stderr.write(f"Error: {e}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
