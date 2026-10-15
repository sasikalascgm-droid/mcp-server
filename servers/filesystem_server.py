"""Restricted Filesystem MCP Server (Python implementation).

Provides safe, boundary-restricted file operations within a dedicated test folder.
Prevents directory traversal attacks by validating all canonical file paths.
"""

import os
import sys
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except (ImportError, ModuleNotFoundError):
    from mcp.server.mcpserver import MCPServer as FastMCP

# Define the allowed folder boundary
DEFAULT_TEST_FOLDER = os.environ.get(
    "MCP_FILESYSTEM_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test_folder")),
)

mcp = FastMCP("Restricted Filesystem Server")


def _resolve_safe_path(requested_path: str) -> Path:
    """Resolves path and enforces strict confinement to DEFAULT_TEST_FOLDER."""
    root_path = Path(DEFAULT_TEST_FOLDER).resolve()
    # If path is relative, resolve relative to root
    if not os.path.isabs(requested_path):
        target = (root_path / requested_path).resolve()
    else:
        target = Path(requested_path).resolve()

    # Boundary check (path traversal prevention)
    if not str(target).startswith(str(root_path)):
        raise PermissionError(
            f"Access denied: Path '{requested_path}' resolves outside allowed test folder '{root_path}'."
        )
    return target


@mcp.tool(
    name="list_directory",
    description="List files and directories inside the allowed test folder.",
)
def list_directory(relative_path: str = ".") -> str:
    """Lists files and folders inside the restricted test directory."""
    try:
        target = _resolve_safe_path(relative_path)
        if not target.exists() or not target.is_dir():
            return f"Directory '{relative_path}' does not exist or is not a directory."

        entries = os.listdir(target)
        if not entries:
            return f"Directory '{relative_path}' is empty."

        lines = [f"Contents of '{relative_path}':"]
        for entry in sorted(entries):
            entry_path = target / entry
            kind = "DIR" if entry_path.is_dir() else "FILE"
            lines.append(f"- [{kind}] {entry}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool(
    name="read_file",
    description="Read the text content of a file located within the allowed test folder.",
)
def read_file(file_path: str) -> str:
    """Reads content from a file inside the restricted test directory."""
    try:
        target = _resolve_safe_path(file_path)
        if not target.exists() or not target.is_file():
            return f"Error: File '{file_path}' does not exist."

        content = target.read_text(encoding="utf-8")
        return content
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool(
    name="write_file",
    description="Write content to a file inside the allowed test folder.",
)
def write_file(file_path: str, content: str) -> str:
    """Writes content to a file strictly within the restricted test directory."""
    try:
        target = _resolve_safe_path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to '{file_path}'."
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool(
    name="get_file_info",
    description="Get metadata (size, last modified) for a file inside the allowed test folder.",
)
def get_file_info(file_path: str) -> str:
    """Retrieves file size and modification time inside the restricted test folder."""
    try:
        target = _resolve_safe_path(file_path)
        if not target.exists():
            return f"Error: File '{file_path}' does not exist."

        stat = target.stat()
        return (
            f"File: {target.name}\n"
            f"Size: {stat.st_size} bytes\n"
            f"Is Directory: {target.is_dir()}"
        )
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    os.makedirs(DEFAULT_TEST_FOLDER, exist_ok=True)
    mcp.run(transport="stdio")
