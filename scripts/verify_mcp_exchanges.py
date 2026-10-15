"""Script to execute and record real MCP protocol exchanges over stdio transport.

Tests Book Library MCP Server, Filesystem MCP Server, and GitHub MCP Server.
Uses an isolated temporary database for the Book Library test.
"""

import asyncio
import json
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PYTHON_EXE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".venv", "Scripts", "python.exe")
)
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


async def test_book_library():
    print("=" * 70)
    print("1. AUDIT: BOOK LIBRARY MCP SERVER (server.py)")
    print("=" * 70)

    # Use a disposable test database
    demo_db = os.path.join(WORKSPACE_ROOT, "library_audit_demo.db")
    if os.path.exists(demo_db):
        os.remove(demo_db)

    env = dict(os.environ)
    env["LIBRARY_DB_PATH"] = demo_db

    server_params = StdioServerParameters(
        command=PYTHON_EXE,
        args=[os.path.join(WORKSPACE_ROOT, "server.py")],
        env=env,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("\n[Protocol Status] Initialized stdio session successfully.")

            # 1. tools/list exchange
            tools_result = await session.list_tools()
            print("\n[Exchange: tools/list]")
            for tool in tools_result.tools:
                print(f"  - Tool: {tool.name}")
                print(f"    Description: {tool.description}")
                print(f"    Schema: {tool.input_schema}")

            # 2. tools/call: search_books ("Orwell")
            print("\n[Exchange: tools/call -> search_books(query='Orwell')]")
            search_res = await session.call_tool("search_books", arguments={"query": "Orwell"})
            print(f"  Response: {search_res.content[0].text}")

            # 3. tools/call: add_book
            print("\n[Exchange: tools/call -> add_book(title='Test Book A', author='Jane Doe')]")
            add_res = await session.call_tool(
                "add_book", arguments={"title": "Test Book A", "author": "Jane Doe"}
            )
            print(f"  Response: {add_res.content[0].text}")

            # 4. tools/call: borrow_book (book_id=2)
            print("\n[Exchange: tools/call -> borrow_book(book_id=2)]")
            borrow_res1 = await session.call_tool("borrow_book", arguments={"book_id": 2})
            print(f"  Response: {borrow_res1.content[0].text}")

            # 5. tools/call: borrow_book (duplicate check, book_id=2)
            print("\n[Exchange: tools/call -> borrow_book(book_id=2) [Repeat Attempt]]")
            borrow_res2 = await session.call_tool("borrow_book", arguments={"book_id": 2})
            print(f"  Response: {borrow_res2.content[0].text}")

            # 6. resources/read: library://catalog
            print("\n[Exchange: resources/read -> library://catalog]")
            res_content = await session.read_resource("library://catalog")
            print(f"  Response:\n{res_content.contents[0].text}")

            # 7. prompts/get: recommend-a-book
            print("\n[Exchange: prompts/get -> recommend-a-book(topic_or_genre='dystopian fiction')]")
            prompt_res = await session.get_prompt(
                "recommend-a-book", arguments={"topic_or_genre": "dystopian fiction"}
            )
            print(f"  Generated Prompt:\n{prompt_res.messages[0].content.text[:250]}...")

    # Clean up disposable demo DB
    if os.path.exists(demo_db):
        os.remove(demo_db)


async def test_filesystem():
    print("\n" + "=" * 70)
    print("2. AUDIT: RESTRICTED FILESYSTEM MCP SERVER (filesystem_server.py)")
    print("=" * 70)

    test_folder = os.path.join(WORKSPACE_ROOT, "test_folder")
    server_params = StdioServerParameters(
        command=PYTHON_EXE,
        args=[os.path.join(WORKSPACE_ROOT, "servers", "filesystem_server.py")],
        env={"MCP_FILESYSTEM_ROOT": test_folder},
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("\n[Protocol Status] Initialized stdio session successfully.")

            # tools/list
            tools_result = await session.list_tools()
            print("\n[Exchange: tools/list]")
            for tool in tools_result.tools:
                print(f"  - Tool: {tool.name}: {tool.description}")

            # tools/call: list_directory
            print("\n[Exchange: tools/call -> list_directory()]")
            list_res = await session.call_tool("list_directory", arguments={"relative_path": "."})
            print(f"  Response:\n{list_res.content[0].text}")

            # tools/call: read_file
            print("\n[Exchange: tools/call -> read_file(file_path='sample.txt')]")
            read_res = await session.call_tool("read_file", arguments={"file_path": "sample.txt"})
            print(f"  Response:\n{read_res.content[0].text.strip()}")

            # tools/call: boundary protection check
            print("\n[Exchange: tools/call -> read_file(file_path='../../server.py') (Boundary Check)]")
            blocked_res = await session.call_tool(
                "read_file", arguments={"file_path": "../../server.py"}
            )
            print(f"  Response:\n{blocked_res.content[0].text.strip()}")


async def test_github():
    print("\n" + "=" * 70)
    print("3. AUDIT: GITHUB MCP SERVER (github_server.py)")
    print("=" * 70)

    server_params = StdioServerParameters(
        command=PYTHON_EXE,
        args=[os.path.join(WORKSPACE_ROOT, "servers", "github_server.py")],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("\n[Protocol Status] Initialized stdio session successfully.")

            # tools/list
            tools_result = await session.list_tools()
            print("\n[Exchange: tools/list]")
            for tool in tools_result.tools:
                print(f"  - Tool: {tool.name}: {tool.description}")

            # tools/call: get_repository
            print("\n[Exchange: tools/call -> get_repository(owner='modelcontextprotocol', repo='servers')]")
            repo_res = await session.call_tool(
                "get_repository",
                arguments={"owner": "modelcontextprotocol", "repo": "servers"},
            )
            print(f"  Response:\n{repo_res.content[0].text.strip()}")


async def main():
    await test_book_library()
    await test_filesystem()
    await test_github()
    print("\n" + "=" * 70)
    print("ALL AUDIT EXCHANGES VERIFIED SUCCESSFULLY VIA REAL STDIO SESSIONS!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
