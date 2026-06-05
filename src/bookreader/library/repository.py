"""Repository layer — thin sqlite3 wrappers around the library tables.

Repositories are constructed with a :class:`Database` and reuse its
connection. They return :mod:`bookreader.library.models` dataclasses; they
never expose raw rows to callers. Business logic (defaults, ordering,
validation) belongs in :mod:`bookreader.library.service`.
"""

from __future__ import annotations

import contextlib
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from bookreader.core.exceptions import BookReaderError
from bookreader.library.models import (
    Book,
    Bookmark,
    Collection,
    Session,
    StoredPosition,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from bookreader.library.database import Database


_AUTHORS_SEP = "\x1f"  # ASCII unit separator — vanishingly unlikely in author names


class RepositoryError(BookReaderError):
    """Raised when a repository operation fails for a non-IntegrityError reason."""


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string (seconds precision)."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def _join_authors(authors: Iterable[str]) -> str:
    """Join author names with the unit separator."""
    return _AUTHORS_SEP.join(a for a in authors if a)


def _split_authors(value: str) -> tuple[str, ...]:
    """Split the stored author string back into a tuple."""
    return tuple(a for a in value.split(_AUTHORS_SEP) if a) if value else ()


# ---------------------------------------------------------------------------
# BookRepo
# ---------------------------------------------------------------------------


class BookRepo:
    """CRUD for the ``books`` table."""

    def __init__(self, db: Database) -> None:
        """Initialize the repo with a connected :class:`Database`."""
        self._db = db

    def upsert(
        self,
        *,
        identifier: str,
        file_path: Path,
        title: str,
        authors: Iterable[str],
    ) -> Book:
        """Insert *identifier* if new, else update its file path and metadata.

        Returns:
            The resulting :class:`Book` row.
        """
        now = _now()
        existing = self.find_by_identifier(identifier)
        if existing:
            self._db.conn.execute(
                "UPDATE books SET file_path = ?, title = ?, authors = ? WHERE id = ?",
                (str(file_path), title, _join_authors(authors), existing.id),
            )
            return self._require(existing.id)
        cur = self._db.conn.execute(
            "INSERT INTO books "
            "  (identifier, file_path, title, authors, added_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (identifier, str(file_path), title, _join_authors(authors), now),
        )
        return self._require(int(cur.lastrowid or 0))

    def find_by_id(self, book_id: int) -> Book | None:
        """Return the book with primary key *book_id*, or ``None``."""
        row = self._db.conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return _row_to_book(row) if row else None

    def find_by_identifier(self, identifier: str) -> Book | None:
        """Return the book with EPUB *identifier*, or ``None``."""
        row = self._db.conn.execute(
            "SELECT * FROM books WHERE identifier = ?", (identifier,)
        ).fetchone()
        return _row_to_book(row) if row else None

    def list_all(self) -> list[Book]:
        """Return every book in the library, newest first."""
        rows = self._db.conn.execute(
            "SELECT * FROM books ORDER BY COALESCE(last_opened_at, added_at) DESC"
        ).fetchall()
        return [_row_to_book(r) for r in rows]

    def list_recent(self, limit: int = 10) -> list[Book]:
        """Return up to *limit* most-recently-opened books."""
        rows = self._db.conn.execute(
            "SELECT * FROM books WHERE last_opened_at IS NOT NULL "
            "ORDER BY last_opened_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_book(r) for r in rows]

    def list_phantoms(self) -> list[Book]:
        """Return every phantom (wishlist) row, newest first."""
        rows = self._db.conn.execute(
            "SELECT * FROM books WHERE is_phantom = 1 ORDER BY added_at DESC"
        ).fetchall()
        return [_row_to_book(r) for r in rows]

    def create_phantom(self, *, title: str, authors: Iterable[str]) -> Book:
        """Insert a phantom (wishlist) row with no file.

        The identifier is a generated ``phantom:<uuid4>`` so it can never
        collide with a real EPUB ``dc:identifier``. Call
        :meth:`attach_epub` once a file is available.
        """
        identifier = f"phantom:{uuid.uuid4()}"
        cur = self._db.conn.execute(
            "INSERT INTO books "
            "  (identifier, file_path, title, authors, added_at, is_phantom) "
            "VALUES (?, NULL, ?, ?, ?, 1)",
            (identifier, title, _join_authors(authors), _now()),
        )
        return self._require(int(cur.lastrowid or 0))

    def attach_epub(
        self,
        book_id: int,
        *,
        identifier: str,
        file_path: Path,
        title: str,
        authors: Iterable[str],
    ) -> Book:
        """Flip a phantom row into a real book once we have the EPUB.

        Raises:
            RepositoryError: If *book_id* doesn't exist or already points
                at a real file.
        """
        existing = self.find_by_id(book_id)
        if existing is None:
            raise RepositoryError(f"book {book_id} not found")
        if not existing.is_phantom:
            raise RepositoryError(f"book {book_id} is already attached")
        self._db.conn.execute(
            "UPDATE books SET "
            "  identifier = ?, file_path = ?, title = ?, authors = ?, "
            "  is_phantom = 0 "
            "WHERE id = ?",
            (identifier, str(file_path), title, _join_authors(authors), book_id),
        )
        return self._require(book_id)

    def list_in_collection(self, collection_id: int) -> list[Book]:
        """Return every book in *collection_id*, ordered by most recent."""
        rows = self._db.conn.execute(
            "SELECT b.* FROM books b "
            "JOIN book_collections bc ON bc.book_id = b.id "
            "WHERE bc.collection_id = ? "
            "ORDER BY COALESCE(b.last_opened_at, b.added_at) DESC",
            (collection_id,),
        ).fetchall()
        return [_row_to_book(r) for r in rows]

    def set_rating(self, book_id: int, rating: int | None) -> None:
        """Set or clear a book's rating (1..5 or ``None``)."""
        if rating is not None and not 1 <= rating <= 5:
            raise RepositoryError(f"rating out of range: {rating}")
        self._db.conn.execute("UPDATE books SET rating = ? WHERE id = ?", (rating, book_id))

    def mark_completed(self, book_id: int, completed: bool = True) -> None:
        """Stamp or clear ``completed_at`` for *book_id*."""
        value = _now() if completed else None
        self._db.conn.execute("UPDATE books SET completed_at = ? WHERE id = ?", (value, book_id))

    def touch_opened(self, book_id: int) -> None:
        """Record that *book_id* was opened just now."""
        self._db.conn.execute("UPDATE books SET last_opened_at = ? WHERE id = ?", (_now(), book_id))

    def delete(self, book_id: int) -> None:
        """Remove a book and all its FK-cascaded children."""
        self._db.conn.execute("DELETE FROM books WHERE id = ?", (book_id,))

    def _require(self, book_id: int) -> Book:
        """Return the book with id *book_id* or raise."""
        book = self.find_by_id(book_id)
        if book is None:
            raise RepositoryError(f"book {book_id} missing after write")
        return book


# ---------------------------------------------------------------------------
# CollectionRepo
# ---------------------------------------------------------------------------


class CollectionRepo:
    """CRUD for the ``collections`` and ``book_collections`` tables."""

    def __init__(self, db: Database) -> None:
        """Initialize the repo."""
        self._db = db

    def create(self, name: str) -> Collection:
        """Create a new named collection (idempotent on ``name``)."""
        with contextlib.suppress(sqlite3.IntegrityError):
            self._db.conn.execute(
                "INSERT INTO collections (name, created_at) VALUES (?, ?)",
                (name, _now()),
            )
        return self._require_by_name(name)

    def delete(self, collection_id: int) -> None:
        """Delete a collection. Books are not deleted; assignments are."""
        self._db.conn.execute("DELETE FROM collections WHERE id = ?", (collection_id,))

    def rename(self, collection_id: int, name: str) -> None:
        """Rename a collection."""
        self._db.conn.execute("UPDATE collections SET name = ? WHERE id = ?", (name, collection_id))

    def list_all(self) -> list[Collection]:
        """Return every collection in name order."""
        rows = self._db.conn.execute(
            "SELECT * FROM collections ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [_row_to_collection(r) for r in rows]

    def find_by_name(self, name: str) -> Collection | None:
        """Return the collection named *name*, or ``None``."""
        row = self._db.conn.execute("SELECT * FROM collections WHERE name = ?", (name,)).fetchone()
        return _row_to_collection(row) if row else None

    def add_book(self, collection_id: int, book_id: int) -> None:
        """Assign *book_id* to *collection_id* (idempotent)."""
        self._db.conn.execute(
            "INSERT OR IGNORE INTO book_collections (book_id, collection_id) VALUES (?, ?)",
            (book_id, collection_id),
        )

    def remove_book(self, collection_id: int, book_id: int) -> None:
        """Remove *book_id* from *collection_id*."""
        self._db.conn.execute(
            "DELETE FROM book_collections WHERE collection_id = ? AND book_id = ?",
            (collection_id, book_id),
        )

    def collections_for(self, book_id: int) -> list[Collection]:
        """Return the collections a given book belongs to."""
        rows = self._db.conn.execute(
            "SELECT c.* FROM collections c "
            "JOIN book_collections bc ON bc.collection_id = c.id "
            "WHERE bc.book_id = ? "
            "ORDER BY c.name COLLATE NOCASE",
            (book_id,),
        ).fetchall()
        return [_row_to_collection(r) for r in rows]

    def _require_by_name(self, name: str) -> Collection:
        """Return the collection named *name* or raise."""
        c = self.find_by_name(name)
        if c is None:
            raise RepositoryError(f"collection {name!r} missing after write")
        return c


# ---------------------------------------------------------------------------
# PositionRepo
# ---------------------------------------------------------------------------


class PositionRepo:
    """CRUD for the ``positions`` table."""

    def __init__(self, db: Database) -> None:
        """Initialize the repo."""
        self._db = db

    def get(self, book_id: int) -> StoredPosition | None:
        """Return the saved position for *book_id*, or ``None``."""
        row = self._db.conn.execute(
            "SELECT * FROM positions WHERE book_id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return None
        return StoredPosition(
            book_id=row["book_id"],
            chapter_index=row["chapter_index"],
            scroll_offset=row["scroll_offset"],
            page_index=row["page_index"],
            updated_at=row["updated_at"],
        )

    def save(
        self,
        book_id: int,
        chapter_index: int,
        scroll_offset: int,
        page_index: int | None = None,
    ) -> StoredPosition:
        """Insert or update the position for *book_id*."""
        now = _now()
        self._db.conn.execute(
            "INSERT INTO positions "
            "  (book_id, chapter_index, scroll_offset, page_index, updated_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(book_id) DO UPDATE SET "
            "  chapter_index = excluded.chapter_index, "
            "  scroll_offset = excluded.scroll_offset, "
            "  page_index    = excluded.page_index, "
            "  updated_at    = excluded.updated_at",
            (book_id, chapter_index, scroll_offset, page_index, now),
        )
        return StoredPosition(
            book_id=book_id,
            chapter_index=chapter_index,
            scroll_offset=scroll_offset,
            page_index=page_index,
            updated_at=now,
        )


# ---------------------------------------------------------------------------
# BookmarkRepo
# ---------------------------------------------------------------------------


class BookmarkRepo:
    """CRUD for the ``bookmarks`` table."""

    def __init__(self, db: Database) -> None:
        """Initialize the repo."""
        self._db = db

    def add(self, book_id: int, chapter_index: int, scroll_offset: int, note: str = "") -> Bookmark:
        """Insert a new bookmark and return it."""
        now = _now()
        cur = self._db.conn.execute(
            "INSERT INTO bookmarks "
            "  (book_id, chapter_index, scroll_offset, note, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (book_id, chapter_index, scroll_offset, note, now),
        )
        return Bookmark(
            id=int(cur.lastrowid or 0),
            book_id=book_id,
            chapter_index=chapter_index,
            scroll_offset=scroll_offset,
            note=note,
            created_at=now,
        )

    def list_for(self, book_id: int) -> list[Bookmark]:
        """Return all bookmarks for *book_id*, newest first."""
        rows = self._db.conn.execute(
            "SELECT * FROM bookmarks WHERE book_id = ? ORDER BY created_at DESC",
            (book_id,),
        ).fetchall()
        return [
            Bookmark(
                id=row["id"],
                book_id=row["book_id"],
                chapter_index=row["chapter_index"],
                scroll_offset=row["scroll_offset"],
                note=row["note"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def delete(self, bookmark_id: int) -> None:
        """Delete one bookmark."""
        self._db.conn.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))


# ---------------------------------------------------------------------------
# SessionRepo
# ---------------------------------------------------------------------------


class SessionRepo:
    """CRUD for the ``sessions`` table."""

    def __init__(self, db: Database) -> None:
        """Initialize the repo."""
        self._db = db

    def start(self, book_id: int) -> Session:
        """Insert a fresh session row for *book_id* and return it."""
        now = _now()
        cur = self._db.conn.execute(
            "INSERT INTO sessions (book_id, started_at) VALUES (?, ?)",
            (book_id, now),
        )
        return Session(
            id=int(cur.lastrowid or 0),
            book_id=book_id,
            started_at=now,
            ended_at=None,
            pages_advanced=0,
        )

    def end(self, session_id: int, *, pages_advanced: int = 0) -> None:
        """Stamp ``ended_at`` on *session_id* if still open. Idempotent."""
        self._db.conn.execute(
            "UPDATE sessions SET ended_at = ?, pages_advanced = ? "
            "WHERE id = ? AND ended_at IS NULL",
            (_now(), max(0, pages_advanced), session_id),
        )

    def close_orphans(self) -> int:
        """Close any sessions that were left open by a crash. Returns count.

        Uses ``started_at`` as the close time so we never inflate stats.
        """
        cur = self._db.conn.execute(
            "UPDATE sessions SET ended_at = started_at WHERE ended_at IS NULL"
        )
        return cur.rowcount or 0

    def list_for(self, book_id: int, limit: int = 10) -> list[Session]:
        """Return the most recent sessions for *book_id*."""
        rows = self._db.conn.execute(
            "SELECT * FROM sessions WHERE book_id = ? "
            "ORDER BY started_at DESC LIMIT ?",
            (book_id, limit),
        ).fetchall()
        return [_row_to_session(r) for r in rows]

    def total_minutes_for(self, book_id: int) -> int:
        """Return the total reading time for *book_id*, in whole minutes."""
        row = self._db.conn.execute(
            "SELECT COALESCE(SUM(strftime('%s', ended_at) - strftime('%s', started_at)), 0) "
            "AS seconds FROM sessions "
            "WHERE book_id = ? AND ended_at IS NOT NULL",
            (book_id,),
        ).fetchone()
        return int((row["seconds"] or 0) // 60)

    def last_session_for(self, book_id: int) -> Session | None:
        """Return the most recent closed session for *book_id*, or ``None``."""
        row = self._db.conn.execute(
            "SELECT * FROM sessions WHERE book_id = ? AND ended_at IS NOT NULL "
            "ORDER BY started_at DESC LIMIT 1",
            (book_id,),
        ).fetchone()
        return _row_to_session(row) if row else None


# ---------------------------------------------------------------------------
# Row → model adapters
# ---------------------------------------------------------------------------


def _row_to_book(row: sqlite3.Row) -> Book:
    """Build a :class:`Book` from a ``books`` row."""
    raw_path = row["file_path"]
    # Older schemas have no ``is_phantom`` column; default false if absent.
    try:
        phantom = bool(row["is_phantom"])
    except (IndexError, KeyError):
        phantom = False
    return Book(
        id=row["id"],
        identifier=row["identifier"],
        file_path=Path(raw_path) if raw_path else None,
        title=row["title"],
        authors=_split_authors(row["authors"] or ""),
        rating=row["rating"],
        added_at=row["added_at"],
        completed_at=row["completed_at"],
        last_opened_at=row["last_opened_at"],
        is_phantom=phantom,
    )


def _row_to_collection(row: sqlite3.Row) -> Collection:
    """Build a :class:`Collection` from a ``collections`` row."""
    return Collection(id=row["id"], name=row["name"], created_at=row["created_at"])


def _row_to_session(row: sqlite3.Row) -> Session:
    """Build a :class:`Session` from a ``sessions`` row."""
    return Session(
        id=row["id"],
        book_id=row["book_id"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
        pages_advanced=row["pages_advanced"],
    )
