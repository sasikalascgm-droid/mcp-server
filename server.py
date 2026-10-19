
"""Book Library MCP Server with confirmation checks for write operations."""

try:
    from mcp.server.fastmcp import FastMCP
except (ImportError, ModuleNotFoundError):
    from mcp.server.mcpserver import MCPServer as FastMCP

import database

mcp = FastMCP("Book Library")
database.init_db()


@mcp.tool(
    name="search_books",
    description=(
        "Read-only tool. Search books by title or author keywords. "
        "This tool does not modify the library."
    ),
)
def search_books(query: str) -> str:
    """Search books without modifying the database."""
    clean_query = (query or "").strip()

    if not clean_query:
        return "Search input is empty. Please provide a title or author."

    results = database.search_books(clean_query)

    if not results:
        return f"No books found matching '{clean_query}'."

    lines = [f"Found {len(results)} book(s):"]

    for book in results:
        lines.append(
            f"- [ID: {book['id']}] \"{book['title']}\" by "
            f"{book['author']} | Status: {book['status']}"
        )

    return "\n".join(lines)


@mcp.tool(
    name="add_book",
    description=(
        "Write operation: add one book using its title and author. "
        "Requires confirmation='ADD BOOK'. The client should ask the "
        "user for approval before making the confirmed tool call."
    ),
)
def add_book(
    title: str,
    author: str,
    confirmation: str = "",
) -> str:
    """Add a book only when the required confirmation is supplied."""
    if confirmation != "ADD BOOK":
        return (
            "Confirmation required. Ask the user to approve adding "
            "this book before retrying with confirmation='ADD BOOK'. "
            "No changes were made."
        )

    success, message, book = database.add_book(
        title=title,
        author=author,
    )

    if not success:
        return f"Failed to add book: {message}"

    return (
        f"Success: {message}\n"
        f"Details: [ID: {book['id']}] \"{book['title']}\" by "
        f"{book['author']} (Status: Available)"
    )


@mcp.tool(
    name="borrow_book",
    description=(
        "Write operation: borrow one available book using its numeric ID. "
        "Requires confirmation='BORROW BOOK'. The client should ask the "
        "user for approval before making the confirmed tool call."
    ),
)
def borrow_book(
    book_id: int,
    confirmation: str = "",
) -> str:
    """Borrow a book only when the required confirmation is supplied."""
    if confirmation != "BORROW BOOK":
        return (
            "Confirmation required. Ask the user to approve borrowing "
            "this book before retrying with confirmation='BORROW BOOK'. "
            "No changes were made."
        )

    success, message, book = database.borrow_book(book_id=book_id)

    if not success:
        return f"Borrow failed: {message}"

    return f"Success: {message}"


@mcp.resource("library://catalog")
def get_catalog() -> str:
    """Return a read-only view of the library catalog."""
    books = database.get_all_books()

    if not books:
        return "The library catalog is currently empty."

    lines = [
        f"=== Library Book Catalog ({len(books)} total books) ===",
        f"{'ID':<6} {'Status':<12} {'Title':<35} {'Author'}",
        "-" * 75,
    ]

    for book in books:
        lines.append(
            f"{book['id']:<6} {book['status']:<12} "
            f"{book['title']:<35} {book['author']}"
        )

    return "\n".join(lines)


@mcp.prompt("recommend-a-book")
def recommend_book(
    topic_or_genre: str = "general reading",
) -> str:
    """Generate a recommendation prompt from the real catalog."""
    books = database.get_all_books()

    available_books = [
        book for book in books if not book["is_borrowed"]
    ]
    borrowed_books = [
        book for book in books if book["is_borrowed"]
    ]

    available_summary = "\n".join(
        f"- [ID: {book['id']}] '{book['title']}' by {book['author']}"
        for book in available_books
    ) or "None currently available."

    borrowed_summary = "\n".join(
        f"- [ID: {book['id']}] '{book['title']}' by {book['author']} "
        "(Currently Borrowed)"
        for book in borrowed_books
    ) or "None."

    return f"""You are a helpful library assistant.

Reader interest: "{topic_or_genre}"

AVAILABLE BOOKS:
{available_summary}

CURRENTLY BORROWED:
{borrowed_summary}

CRITICAL RULES:
1. Recommend only books listed in this catalog.
2. Include the book ID and explain why it matches the reader's interest.
3. Clearly identify books that are currently borrowed.
4. Never invent books or claim that an unavailable book is available.
"""


if __name__ == "__main__":
    mcp.run(transport="stdio")
