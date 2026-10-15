"""Automated test suite for Book Library MCP Server.

Covers:
- Searching for books (positive, not found, empty input)
- Adding valid books
- Input validation and duplicate rejection
- Borrowing available books
- Handling unknown IDs and already borrowed books
- Reading MCP resource catalog and prompt generation

Uses pytest and temporary isolated SQLite databases.
"""

import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import database
import server


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Sets up an isolated, temporary SQLite database for each test."""
    test_db_path = str(tmp_path / "test_library.db")
    # Patch default db path in both database and server modules
    monkeypatch.setattr(database, "DEFAULT_DB_PATH", test_db_path)
    monkeypatch.setenv("LIBRARY_DB_PATH", test_db_path)
    # Initialize the test database with sample books
    database.init_db(test_db_path)
    yield test_db_path


def test_search_books():
    """Test searching books by title, author, non-matching keyword, and empty query."""
    # 1. Search by title keyword
    results_title = database.search_books("Hobbit")
    assert len(results_title) == 1
    assert results_title[0]["title"] == "The Hobbit"
    assert results_title[0]["status"] == "Available"

    # 2. Search by author keyword
    results_author = database.search_books("Orwell")
    assert len(results_author) == 1
    assert results_author[0]["title"] == "1984"

    # 3. Search non-existent book
    results_none = database.search_books("Quantum Physics In A Nutshell")
    assert len(results_none) == 0

    # 4. Search with empty / whitespace query returns empty list
    results_empty = database.search_books("   ")
    assert results_empty == []

    # 5. Test through the MCP tool function
    tool_output = server.search_books("1984")
    assert "Found 1 book(s)" in tool_output
    assert "George Orwell" in tool_output


def test_add_valid_book():
    """Test adding a valid book and verifying it persists."""
    success, message, new_book = database.add_book(
        title="Design Patterns", author="Erich Gamma et al."
    )
    assert success is True
    assert "Successfully added" in message
    assert new_book is not None
    assert new_book["id"] > 0
    assert new_book["title"] == "Design Patterns"

    # Verify through search that the newly added book is present
    search_res = database.search_books("Design Patterns")
    assert len(search_res) == 1
    assert search_res[0]["author"] == "Erich Gamma et al."

    # Test MCP tool interface
    tool_res = server.add_book(
        title="Refactoring", author="Martin Fowler"
    )
    assert "Success" in tool_res
    assert "Martin Fowler" in tool_res


def test_add_invalid_input_and_duplicates():
    """Test rejection of blank titles, blank authors, and duplicate entries."""
    # Blank title
    ok, msg, book = database.add_book(title="  ", author="Valid Author")
    assert ok is False
    assert "title cannot be empty" in msg

    # Blank author
    ok, msg, book = database.add_book(title="Valid Title", author="")
    assert ok is False
    assert "author cannot be empty" in msg

    # Duplicate check: '1984' by 'George Orwell' is already in the seed data
    ok_dup, msg_dup, book_dup = database.add_book(
        title="1984", author="George Orwell"
    )
    assert ok_dup is False
    assert "Duplicate entry" in msg_dup

    # Verify duplicate rejection through MCP tool
    tool_msg = server.add_book(title="1984", author="George Orwell")
    assert "Failed to add book: Duplicate entry" in tool_msg


def test_borrow_available_book():
    """Test borrowing an available book successfully updates its state."""
    # Find an available book ID
    books = database.get_all_books()
    book_to_borrow = books[0]
    book_id = book_to_borrow["id"]
    assert book_to_borrow["is_borrowed"] is False

    # Borrow the book
    ok, msg, updated = database.borrow_book(book_id)
    assert ok is True
    assert "Successfully borrowed" in msg
    assert updated["is_borrowed"] is True
    assert updated["status"] == "Borrowed"

    # Verify catalog reflects the new borrowed state
    all_books = database.get_all_books()
    borrowed_in_catalog = next(b for b in all_books if b["id"] == book_id)
    assert borrowed_in_catalog["is_borrowed"] is True


def test_borrow_unknown_or_already_borrowed():
    """Test borrow failure for invalid ID and already borrowed books."""
    # Non-existent ID
    ok_missing, msg_missing, _ = database.borrow_book(99999)
    assert ok_missing is False
    assert "not found" in msg_missing

    # Invalid ID (negative or 0)
    ok_invalid, msg_invalid, _ = database.borrow_book(-5)
    assert ok_invalid is False
    assert "positive integer" in msg_invalid

    # Borrow once
    ok1, _, _ = database.borrow_book(1)
    assert ok1 is True

    # Attempt to borrow the same book again
    ok2, msg2, _ = database.borrow_book(1)
    assert ok2 is False
    assert "already borrowed" in msg2

    # Verify through MCP tool
    tool_err = server.borrow_book(1)
    assert "Borrow failed: Borrow error: 'The Hobbit' (ID: 1) is already borrowed" in tool_err


def test_resource_and_prompt():
    """Test that the MCP resource catalog and prompt generation work properly."""
    # Test resource returns catalog with headers
    catalog_text = server.get_catalog()
    assert "Library Book Catalog" in catalog_text
    assert "The Hobbit" in catalog_text

    # Test prompt generation contains real books and instructions
    prompt_output = server.recommend_book("software engineering")
    assert "Clean Code" in prompt_output
    assert "CRITICAL RULES" in prompt_output
    assert "software engineering" in prompt_output
