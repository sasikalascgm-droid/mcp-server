
"""Database layer for the Book Library MCP Server.

Manages persistent book records in SQLite, including initialization,
sample data seeding, searching, adding, borrowing, deleting, and listing.
"""

import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "library.db",
)

SAMPLE_BOOKS = [
    ("The Hobbit", "J.R.R. Tolkien"),
    ("1984", "George Orwell"),
    ("To Kill a Mockingbird", "Harper Lee"),
    ("Clean Code", "Robert C. Martin"),
    ("The Pragmatic Programmer", "Andrew Hunt, David Thomas"),
]


def get_db_path(db_path: Optional[str] = None) -> str:
    """Return the effective database path."""
    if db_path is not None:
        return db_path
    return os.environ.get("LIBRARY_DB_PATH", DEFAULT_DB_PATH)


def get_connection(
    db_path: Optional[str] = None,
) -> sqlite3.Connection:
    """Create a SQLite connection with named-column access."""
    target_path = get_db_path(db_path)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Create the books table and seed sample books if it is empty."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                is_borrowed INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        cursor.execute("SELECT COUNT(*) AS count FROM books")
        count = cursor.fetchone()["count"]

        if count == 0:
            cursor.executemany(
                """
                INSERT INTO books (title, author, is_borrowed)
                VALUES (?, ?, 0)
                """,
                SAMPLE_BOOKS,
            )

        conn.commit()


def search_books(
    query: str,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search books by title or author, ignoring letter case."""
    cleaned_query = (query or "").strip()

    if not cleaned_query:
        return []

    pattern = f"%{cleaned_query}%"

    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, title, author, is_borrowed
            FROM books
            WHERE title LIKE ? OR author LIKE ?
            ORDER BY id ASC
            """,
            (pattern, pattern),
        )

        rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "title": row["title"],
                "author": row["author"],
                "is_borrowed": bool(row["is_borrowed"]),
                "status": (
                    "Borrowed" if row["is_borrowed"] else "Available"
                ),
            }
            for row in rows
        ]


def add_book(
    title: str,
    author: str,
    db_path: Optional[str] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Add a book after validating its details and checking duplicates."""
    clean_title = (title or "").strip()
    clean_author = (author or "").strip()

    if not clean_title:
        return (
            False,
            "Validation error: Book title cannot be empty or whitespace.",
            None,
        )

    if not clean_author:
        return (
            False,
            "Validation error: Book author cannot be empty or whitespace.",
            None,
        )

    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, title, author
            FROM books
            WHERE LOWER(title) = LOWER(?)
              AND LOWER(author) = LOWER(?)
            """,
            (clean_title, clean_author),
        )

        existing = cursor.fetchone()

        if existing:
            return (
                False,
                (
                    f"Duplicate entry: '{existing['title']}' by "
                    f"{existing['author']} already exists with "
                    f"ID {existing['id']}."
                ),
                None,
            )

        cursor.execute(
            """
            INSERT INTO books (title, author, is_borrowed)
            VALUES (?, ?, 0)
            """,
            (clean_title, clean_author),
        )

        new_id = cursor.lastrowid
        conn.commit()

        new_book = {
            "id": new_id,
            "title": clean_title,
            "author": clean_author,
            "is_borrowed": False,
            "status": "Available",
        }

        return (
            True,
            f"Successfully added book '{clean_title}' by {clean_author} with ID {new_id}.",
            new_book,
        )


def borrow_book(
    book_id: int,
    db_path: Optional[str] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Borrow a book if it exists and is currently available."""
    try:
        book_id = int(book_id)
    except (ValueError, TypeError):
        return (
            False,
            f"Validation error: Book ID '{book_id}' is invalid.",
            None,
        )

    if book_id <= 0:
        return (
            False,
            "Validation error: Book ID must be a positive integer.",
            None,
        )

    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, title, author, is_borrowed
            FROM books
            WHERE id = ?
            """,
            (book_id,),
        )

        book = cursor.fetchone()

        if book is None:
            return (
                False,
                f"Borrow error: Book with ID {book_id} was not found.",
                None,
            )

        if book["is_borrowed"]:
            return (
                False,
                f"Borrow error: '{book['title']}' (ID: {book_id}) is already borrowed.",
                None,
            )

        cursor.execute(
            """
            UPDATE books
            SET is_borrowed = 1
            WHERE id = ? AND is_borrowed = 0
            """,
            (book_id,),
        )

        if cursor.rowcount != 1:
            return (
                False,
                "Borrow error: The book is no longer available.",
                None,
            )

        conn.commit()

        updated_book = {
            "id": book["id"],
            "title": book["title"],
            "author": book["author"],
            "is_borrowed": True,
            "status": "Borrowed",
        }

        return (
            True,
            f"Successfully borrowed '{book['title']}' by {book['author']} (ID: {book_id}).",
            updated_book,
        )


def get_all_books(
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return all books ordered by ID."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, title, author, is_borrowed
            FROM books
            ORDER BY id ASC
            """
        )

        rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "title": row["title"],
                "author": row["author"],
                "is_borrowed": bool(row["is_borrowed"]),
                "status": (
                    "Borrowed" if row["is_borrowed"] else "Available"
                ),
            }
            for row in rows
        ]


def delete_book(
    book_id: int,
    db_path: Optional[str] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Delete a book by ID if it exists."""
    try:
        book_id = int(book_id)
    except (ValueError, TypeError):
        return (
            False,
            f"Validation error: Invalid book ID '{book_id}'.",
            None,
        )

    if book_id <= 0:
        return (
            False,
            "Validation error: Book ID must be a positive integer.",
            None,
        )

    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, title, author, is_borrowed
            FROM books
            WHERE id = ?
            """,
            (book_id,),
        )

        book = cursor.fetchone()

        if book is None:
            return (
                False,
                f"Delete error: Book with ID {book_id} was not found.",
                None,
            )

        deleted_book = {
            "id": book["id"],
            "title": book["title"],
            "author": book["author"],
            "is_borrowed": bool(book["is_borrowed"]),
            "status": (
                "Borrowed" if book["is_borrowed"] else "Available"
            ),
        }

        cursor.execute(
            "DELETE FROM books WHERE id = ?",
            (book_id,),
        )

        if cursor.rowcount != 1:
            return (
                False,
                "Delete error: The book could not be deleted.",
                None,
            )

        conn.commit()

        return (
            True,
            f"Successfully deleted '{book['title']}' (ID: {book_id}).",
            deleted_book,
        )


# Do not call database.init_db() inside this file.
# Initialize the database from server.py instead.
