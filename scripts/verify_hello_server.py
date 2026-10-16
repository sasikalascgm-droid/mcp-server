"""Verification script for Day 2 Hello MCP Server.

Connects to hello_server.py via stdio transport, checks tools/list,
and performs tools/call for say_hello.
"""

import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PYTHON_EXE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".venv", "Scripts", "python.exe")
)
SERVER_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "hello_server.py")
)


async def main():
    server_params = StdioServerParameters(
        command=PYTHON_EXE,
        args=[SERVER_PATH],
        env=None,
    )

    print("=" * 65)
    print("DAY 2: HELLO MCP SERVER VERIFICATION")
    print("=" * 65)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("\n[Protocol Status] Initialized stdio session successfully.")

            # 1. tools/list verification
            tools_result = await session.list_tools()
            print("\n[Exchange: tools/list]")
            for tool in tools_result.tools:
                print(f"  - Tool: {tool.name}")
                print(f"    Description: {tool.description}")
                print(f"    Input Schema: {tool.input_schema}")

            # 2. tools/call verification with name='Sasikala'
            print("\n[Exchange: tools/call -> say_hello(name='Sasikala')]")
            call_res = await session.call_tool(
                "say_hello", arguments={"name": "Sasikala"}
            )
            print(f"  Response: {call_res.content[0].text}")

            # 3. tools/call verification with default/empty name
            print("\n[Exchange: tools/call -> say_hello(name='')]")
            empty_res = await session.call_tool("say_hello", arguments={"name": ""})
            print(f"  Response: {empty_res.content[0].text}")

    print("\n" + "=" * 65)
    print("HELLO MCP SERVER TEST PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
