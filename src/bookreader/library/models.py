"""Frozen dataclasses for the library domain.

These are pure data carriers. They do not hit the database; the repository
layer constructs them from rows and consumes them on writes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Book:
    """A book row.

    Attributes:
        id: Surrogate primary key.
        identifier: EPUB ``dc:identifier`` or SHA-1 fallback. Unique.
        file_path: Filesystem location of the EPUB.
        title: Book title.
        authors: Tuple of author names.
        rating: User rating ``1..5`` or ``None``.
        added_at: ISO-8601 UTC timestamp.
        completed_at: ISO-8601 UTC timestamp; set when marked finished.
        last_opened_at: ISO-8601 UTC timestamp of the last reader session.
    """

    id: int
    identifier: str
    file_path: Path
    title: str
    authors: tuple[str, ...]
    rating: int | None
    added_at: str
    completed_at: str | None
    last_opened_at: str | None


@dataclass(frozen=True, slots=True)
class Collection:
    """A named grouping of books.

    The three default collections — ``Currently Reading``, ``Want to Read``,
    ``Finished`` — are seeded on first run.
    """

    id: int
    name: str
    created_at: str


@dataclass(frozen=True, slots=True)
class StoredPosition:
    """Last-read location for a book (library-backed)."""

    book_id: int
    chapter_index: int
    scroll_offset: int
    page_index: int | None
    updated_at: str


@dataclass(frozen=True, slots=True)
class Bookmark:
    """A user bookmark inside a book."""

    id: int
    book_id: int
    chapter_index: int
    scroll_offset: int
    note: str
    created_at: str
