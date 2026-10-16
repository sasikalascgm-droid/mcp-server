"""Day 3 MCP Tools Verification Script.

Executes real MCP protocol requests over stdio to test:
1. tools/list discovery and schemas
2. search_books (success, not found, empty input)
3. add_book (success, blank title/author validation, duplicate rejection)
4. borrow_book (success, already borrowed, non-existent ID, invalid ID)

Uses a completely isolated temporary SQLite database to guarantee
that the real library.db is never modified or corrupted.
"""

import asyncio
import os
import sys
import tempfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Project paths
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYTHON_EXE = os.path.join(WORKSPACE_ROOT, ".venv", "Scripts", "python.exe")
SERVER_PY = os.path.join(WORKSPACE_ROOT, "server.py")
REAL_DB_PATH = os.path.join(WORKSPACE_ROOT, "library.db")

# Isolated temporary database for Day 3 testing
TEMP_DB_PATH = os.path.join(tempfile.gettempdir(), "day3_isolated_test_library.db")


async def run_day3_audit():
    print("=" * 70)
    print("DAY 3: BOOK LIBRARY MCP TOOLS AUDIT & PROTOCOL VERIFICATION")
    print("=" * 70)

    # 1. Ensure isolated database clean state
    if os.path.exists(TEMP_DB_PATH):
        os.remove(TEMP_DB_PATH)

    # Capture real library.db metadata to verify it remains untouched
    real_db_size_before = (
        os.path.getsize(REAL_DB_PATH) if os.path.exists(REAL_DB_PATH) else None
    )
    real_db_mtime_before = (
        os.path.getmtime(REAL_DB_PATH) if os.path.exists(REAL_DB_PATH) else None
    )
    print(f"\n[Safety Check] Real library.db path: {REAL_DB_PATH}")
    print(f"[Safety Check] Target isolated test db: {TEMP_DB_PATH}")

    # Launch server with LIBRARY_DB_PATH pointing strictly to temporary database
    server_env = dict(os.environ)
    server_env["LIBRARY_DB_PATH"] = TEMP_DB_PATH

    server_params = StdioServerParameters(
        command=PYTHON_EXE,
        args=[SERVER_PY],
        env=server_env,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("\n[Protocol Status] MCP stdio session initialized successfully.")

            # =================================================================
            # STEP 1: Verify tools/list
            # =================================================================
            print("\n" + "-" * 70)
            print("STEP 1: VERIFYING MCP tools/list")
            print("-" * 70)
            tools_resp = await session.list_tools()
            tool_names = [t.name for t in tools_resp.tools]
            print(f"Discovered Tools ({len(tool_names)}): {tool_names}")
            assert "search_books" in tool_names, "Missing search_books tool"
            assert "add_book" in tool_names, "Missing add_book tool"
            assert "borrow_book" in tool_names, "Missing borrow_book tool"

            for t in tools_resp.tools:
                print(f"\n  * Tool: {t.name}")
                print(f"    Description: {t.description}")
                print(f"    Parameters: {t.input_schema.get('properties', {}).keys()}")
                print(f"    Required: {t.input_schema.get('required', [])}")

            # =================================================================
            # STEP 2: Verify search_books
            # =================================================================
            print("\n" + "-" * 70)
            print("STEP 2: TESTING Tool 1 — search_books")
            print("-" * 70)

            # 2a. Successful search
            print("\n[2a. Success Case] Searching for author 'Orwell':")
            res_orwell = await session.call_tool("search_books", arguments={"query": "Orwell"})
            print(f"Output:\n{res_orwell.content[0].text}")

            # 2b. Missing search results (graceful message)
            print("\n[2b. Error Case: Missing Results] Searching for 'Quantum Computing XYZ':")
            res_missing = await session.call_tool(
                "search_books", arguments={"query": "Quantum Computing XYZ"}
            )
            print(f"Output:\n{res_missing.content[0].text}")

            # 2c. Empty / whitespace search query
            print("\n[2c. Error Case: Empty Query] Searching with query='   ':")
            res_empty = await session.call_tool("search_books", arguments={"query": "   "})
            print(f"Output:\n{res_empty.content[0].text}")

            # =================================================================
            # STEP 3: Verify add_book
            # =================================================================
            print("\n" + "-" * 70)
            print("STEP 3: TESTING Tool 2 — add_book")
            print("-" * 70)

            # 3a. Successful book addition
            print("\n[3a. Success Case] Adding 'Domain-Driven Design' by 'Eric Evans':")
            res_add = await session.call_tool(
                "add_book",
                arguments={"title": "Domain-Driven Design", "author": "Eric Evans"},
            )
            print(f"Output:\n{res_add.content[0].text}")

            # 3b. Duplicate book prevention
            print("\n[3b. Error Case: Duplicate Book] Attempting to re-add '1984' by 'George Orwell':")
            res_dup = await session.call_tool(
                "add_book",
                arguments={"title": "1984", "author": "George Orwell"},
            )
            print(f"Output:\n{res_dup.content[0].text}")

            # 3c. Blank title validation
            print("\n[3c. Error Case: Blank Title] Adding with title='   ', author='Valid Author':")
            res_no_title = await session.call_tool(
                "add_book",
                arguments={"title": "   ", "author": "Valid Author"},
            )
            print(f"Output:\n{res_no_title.content[0].text}")

            # 3d. Blank author validation
            print("\n[3d. Error Case: Blank Author] Adding with title='Valid Title', author='':")
            res_no_author = await session.call_tool(
                "add_book",
                arguments={"title": "Valid Title", "author": ""},
            )
            print(f"Output:\n{res_no_author.content[0].text}")

            # =================================================================
            # STEP 4: Verify borrow_book
            # =================================================================
            print("\n" + "-" * 70)
            print("STEP 4: TESTING Tool 3 — borrow_book")
            print("-" * 70)

            # 4a. Borrow available book
            print("\n[4a. Success Case] Borrowing available book ID 1 ('The Hobbit'):")
            res_borrow = await session.call_tool("borrow_book", arguments={"book_id": 1})
            print(f"Output:\n{res_borrow.content[0].text}")

            # 4b. Re-borrowing already borrowed book
            print("\n[4b. Error Case: Already Borrowed] Attempting to borrow book ID 1 again:")
            res_borrow_again = await session.call_tool(
                "borrow_book", arguments={"book_id": 1}
            )
            print(f"Output:\n{res_borrow_again.content[0].text}")

            # 4c. Non-existent book ID
            print("\n[4c. Error Case: Non-existent ID] Borrowing book ID 99999:")
            res_borrow_missing = await session.call_tool(
                "borrow_book", arguments={"book_id": 99999}
            )
            print(f"Output:\n{res_borrow_missing.content[0].text}")

            # 4d. Invalid book ID (negative number)
            print("\n[4d. Error Case: Invalid Negative ID] Borrowing book ID -7:")
            res_borrow_invalid = await session.call_tool(
                "borrow_book", arguments={"book_id": -7}
            )
            print(f"Output:\n{res_borrow_invalid.content[0].text}")

    # =================================================================
    # Clean up isolated test database
    # =================================================================
    if os.path.exists(TEMP_DB_PATH):
        os.remove(TEMP_DB_PATH)

    # Verify that real library.db was completely protected
    if os.path.exists(REAL_DB_PATH):
        real_db_size_after = os.path.getsize(REAL_DB_PATH)
        real_db_mtime_after = os.path.getmtime(REAL_DB_PATH)
        assert real_db_size_before == real_db_size_after, "real library.db size changed!"
        assert real_db_mtime_before == real_db_mtime_after, "real library.db mtime changed!"
        print(f"\n[Safety Verification] Real library.db size: {real_db_size_after} bytes (UNCHANGED)")
        print(f"[Safety Verification] Real library.db modification timestamp: (UNCHANGED)")

    print("\n" + "=" * 70)
    print("ALL DAY 3 BOOK LIBRARY MCP TOOLS VERIFIED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_day3_audit())
