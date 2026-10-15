"""Book Library MCP Server.

Provides tools, resources, and prompts for AI applications to interact with
a persistent local SQLite book library using the Model Context Protocol (MCP).
"""

import os
import sys

# Support both MCP SDK 1.x (FastMCP) and 2.x (MCPServer)
try:
    from mcp.server.fastmcp import FastMCP
except (ImportError, ModuleNotFoundError):
    from mcp.server.mcpserver import MCPServer as FastMCP

import database

# Initialize the MCP Server instance
mcp = FastMCP("Book Library")

# Ensure database is initialized when server module is loaded
database.init_db()


# ---------------------------------------------------------------------------
# Tool 1: search_books
# ---------------------------------------------------------------------------
@mcp.tool(
    name="search_books",
    description="Search books by title or author keywords. Returns matching books with ID, title, author, and availability status.",
)
def search_books(query: str) -> str:
    """Searches the library catalogue for books matching the given query string.

    Args:
        query: Search term to match against book titles or authors.

    Returns:
        A human-readable list of matching books or a helpful status message.
    """
    clean_query = (query or "").strip()
    if not clean_query:
        return "Search input is empty. Please provide a search term (e.g., author name like 'Orwell' or title keyword like 'Code')."

    results = database.search_books(clean_query)
    if not results:
        return f"No books found matching '{clean_query}'. Use the 'library://catalog' resource or try searching with another keyword."

    lines = [f"Found {len(results)} book(s) matching '{clean_query}':"]
    for book in results:
        lines.append(
            f"- [ID: {book['id']}] \"{book['title']}\" by {book['author']} | Status: {book['status']}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 2: add_book
# ---------------------------------------------------------------------------
@mcp.tool(
    name="add_book",
    description="Add a new book to the library catalog with a title and author. Validates input and prevents duplicate entries.",
)
def add_book(title: str, author: str) -> str:
    """Adds a new book record into the SQLite database.

    Args:
        title: The full title of the book.
        author: The author or authors of the book.

    Returns:
        A confirmation message with the new book ID, or an explanatory error message.
    """
    success, message, book = database.add_book(title=title, author=author)
    if not success:
        return f"Failed to add book: {message}"

    return (
        f"Success: {message}\n"
        f"Details: [ID: {book['id']}] \"{book['title']}\" by {book['author']} (Status: Available)"
    )


# ---------------------------------------------------------------------------
# Tool 3: borrow_book
# ---------------------------------------------------------------------------
@mcp.tool(
    name="borrow_book",
    description="Borrow an available book from the library using its numeric book ID. Returns an error if not found or already borrowed.",
)
def borrow_book(book_id: int) -> str:
    """Marks a book as borrowed in the library database.

    Args:
        book_id: The unique integer ID of the book to borrow.

    Returns:
        A success confirmation or a specific reason why the borrow operation could not be completed.
    """
    success, message, book = database.borrow_book(book_id=book_id)
    if not success:
        return f"Borrow failed: {message}"

    return f"Success: {message}"


# ---------------------------------------------------------------------------
# Resource: library://catalog
# ---------------------------------------------------------------------------
@mcp.resource("library://catalog")
def get_catalog() -> str:
    """Returns the complete library book catalog, including book IDs, titles, authors, and availability status."""
    books = database.get_all_books()
    if not books:
        return "The library catalog is currently empty."

    lines = [
        f"=== Library Book Catalog ({len(books)} total books) ===",
        f"{'ID':<6} {'Status':<12} {'Title':<35} {'Author'}",
        "-" * 75,
    ]
    for b in books:
        lines.append(f"{b['id']:<6} {b['status']:<12} {b['title']:<35} {b['author']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompt: recommend-a-book
# ---------------------------------------------------------------------------
@mcp.prompt("recommend-a-book")
def recommend_book(topic_or_genre: str = "general reading") -> str:
    """Provides a prompt template guiding the AI to recommend books strictly from the verified library catalog."""
    books = database.get_all_books()
    available_books = [b for b in books if not b["is_borrowed"]]
    borrowed_books = [b for b in books if b["is_borrowed"]]

    available_summary = (
        "\n".join(
            [
                f"- [ID: {b['id']}] '{b['title']}' by {b['author']}"
                for b in available_books
            ]
        )
        or "None currently available."
    )

    borrowed_summary = (
        "\n".join(
            [
                f"- [ID: {b['id']}] '{b['title']}' by {b['author']} (Currently Borrowed)"
                for b in borrowed_books
            ]
        )
        or "None."
    )

    prompt_text = f"""You are a helpful and knowledgeable library assistant.
A reader is seeking a book recommendation based on the following topic or interest:
"{topic_or_genre}"

Here is the current, real catalog from our library database:

AVAILABLE FOR IMMEDIATE BORROWING:
{available_summary}

CURRENTLY BORROWED (Collection reference only):
{borrowed_summary}

CRITICAL RULES:
1. ONLY recommend books that are explicitly listed in the catalog above. Do NOT hallucinate or suggest books not in this list.
2. Recommend the best matching available book first, mentioning its ID so the user can easily borrow it with the 'borrow_book' tool.
3. If an interested book is currently borrowed, politely inform the user that it exists in the library but is currently checked out.
4. Explain clearly and concisely why the recommended book fits their stated interest: "{topic_or_genre}".
"""
    return prompt_text


if __name__ == "__main__":
    # Ensure database is initialized before serving requests
    database.init_db()
    # Run the server over stdio transport
    mcp.run(transport="stdio")
