
import uuid

import database
import server


def test_search_books():
    """Test searching for existing books."""
    results = database.search_books("Orwell")

    assert isinstance(results, list)
    assert any("Orwell" in book["author"] for book in results)


def test_add_valid_book():
    """Test adding a unique book through the database and MCP tool."""
    unique_id = uuid.uuid4().hex[:8]
    title = f"Design Patterns {unique_id}"
    author = "Erich Gamma et al."

    success, message, new_book = database.add_book(
        title=title,
        author=author,
    )

    assert success is True, message
    assert new_book is not None
    assert new_book["id"] > 0
    assert new_book["title"] == title

    search_results = database.search_books(title)

    assert len(search_results) == 1
    assert search_results[0]["author"] == author

    tool_title = f"Refactoring {unique_id}"

    tool_result = server.add_book(
        title=tool_title,
        author="Martin Fowler",
        confirmation="ADD BOOK",
    )

    assert "success" in str(tool_result).lower()

    tool_search_results = database.search_books(tool_title)

    assert len(tool_search_results) == 1
    assert tool_search_results[0]["author"] == "Martin Fowler"


def test_add_invalid_or_duplicate_book():
    """Test rejection of invalid and duplicate books."""
    unique_id = uuid.uuid4().hex[:8]
    title = f"Duplicate Test {unique_id}"

    first = database.add_book(
        title=title,
        author="Test Author",
    )

    assert first[0] is True

    second = database.add_book(
        title=title,
        author="Test Author",
    )

    assert second[0] is False

    invalid = database.add_book(
        title="",
        author="Test Author",
    )

    assert invalid[0] is False


def test_borrow_available_book():
    """Test borrowing a newly added book."""
    unique_id = uuid.uuid4().hex[:8]

    success, message, book = database.add_book(
        title=f"Borrow Test {unique_id}",
        author="Test Author",
    )

    assert success is True, message
    assert book is not None

    result = server.borrow_book(
        book_id=book["id"],
        confirmation="BORROW BOOK",
    )

    assert (
        "success" in str(result).lower()
        or "borrowed" in str(result).lower()
    )


def test_borrow_unknown_book():
    """Test borrowing a book that does not exist."""
    result = server.borrow_book(
        book_id=999999999,
        confirmation="BORROW BOOK",
    )

    result_text = str(result).lower()

    assert (
        "not found" in result_text
        or "unknown" in result_text
        or "does not exist" in result_text
    )


def test_resource_and_prompt():
    """Test the catalogue resource and recommendation prompt."""
    resource_text = str(server.get_catalog())

    assert resource_text.strip()

    # The actual prompt function in server.py is recommend_book.
    prompt_text = str(server.recommend_book())

    assert prompt_text.strip()


def test_add_requires_confirmation():
    """Test that adding a book requires confirmation."""
    title = f"No Confirmation {uuid.uuid4().hex[:8]}"

    result = server.add_book(
        title=title,
        author="Test Author",
    )

    assert "confirmation" in str(result).lower()
    assert database.search_books(title) == []


def test_add_rejects_wrong_confirmation():
    """Test that incorrect add confirmation is rejected."""
    title = f"Wrong Confirmation {uuid.uuid4().hex[:8]}"

    result = server.add_book(
        title=title,
        author="Test Author",
        confirmation="YES",
    )

    assert "confirmation" in str(result).lower()
    assert database.search_books(title) == []


def test_borrow_requires_confirmation():
    """Test that borrowing requires confirmation."""
    result = server.borrow_book(book_id=1)

    assert "confirmation" in str(result).lower()


def test_borrow_rejects_wrong_confirmation():
    """Test that incorrect borrow confirmation is rejected."""
    result = server.borrow_book(
        book_id=1,
        confirmation="YES",
    )

    assert "confirmation" in str(result).lower()
