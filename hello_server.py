"""Hello MCP Server - Day 2 Task.

A simple, beginner-friendly Model Context Protocol (MCP) server in Python
that provides a 'say_hello' tool over stdio transport.
"""

import sys

# Support both MCP SDK 1.x (FastMCP) and 2.x (MCPServer)
try:
    from mcp.server.fastmcp import FastMCP
except (ImportError, ModuleNotFoundError):
    from mcp.server.mcpserver import MCPServer as FastMCP

# Initialize the Hello MCP server
mcp = FastMCP("Hello MCP Server")


@mcp.tool(
    name="say_hello",
    description="Returns a friendly, personalized greeting for a given name.",
)
def say_hello(name: str = "World") -> str:
    """Generates a warm greeting message.

    Args:
        name: The name of the person to greet (defaults to 'World').

    Returns:
        A friendly greeting string.
    """
    clean_name = (name or "").strip()
    if not clean_name:
        return "Hello! Welcome to the Model Context Protocol (MCP). Nice to meet you!"

    return f"Hello, {clean_name}! Welcome to the Model Context Protocol (MCP). It's great to connect with you!"


if __name__ == "__main__":
    # Run the server over standard input/output transport
    mcp.run(transport="stdio")
