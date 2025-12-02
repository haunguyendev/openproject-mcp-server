#!/usr/bin/env python3
"""
OpenProject MCP Server - SSE Transport Entry Point

This is the entry point for SSE transport (FastMCP Cloud).
FastMCP-based implementation with automatic tool registration.
"""

from src.server import mcp
import os

if __name__ == "__main__":
    # Force h11 protocol to avoid httptools issues with Python 3.13+
    os.environ.setdefault("UVICORN_HTTP_PROTOCOL", "h11")

    # Run with SSE transport (for FastMCP Cloud deployment)
    mcp.run(transport="sse")
