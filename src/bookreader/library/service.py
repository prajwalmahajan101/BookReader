"""Library service — the only consumer of the repositories.

The UI imports from here. Business decisions (which collections to seed,
what "mark complete" means, when to bump ``last_opened_at``) live in this
file so the repositories remain mechanical CRUD.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bookreader.core.logging import get_logger
from bookreader.epub.reader import open_book
from bookreader.library.database import Database
from bookreader.library.models import Book, Collection, StoredPosition
from bookreader.library.repository import (
    BookmarkRepo,
    BookRepo,
    CollectionRepo,
    PositionRepo,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

log = get_logger(__name__)

DEFAULT_COLLECTIONS: tuple[str, ...] = (
    "Currently Reading",
    "Want to Read",
    "Finished",
)


class LibraryService:
    """Coordinated access to the library.

    Construct once per app session; close on shutdown.
    """

    def __init__(self, db: Database | None = None) -> None:
        """Open the library and seed default collections on first run.

        Also runs the Phase-1 ``positions.json`` migrator opportunistically;
        a missing or already-migrated file is a no-op.
        """
        self._db = db or Database()
        self._books = BookRepo(self._db)
        self._collections = CollectionRepo(self._db)
        self._positions = PositionRepo(self._db)
        self._bookmarks = BookmarkRepo(self._db)
        self._seed_default_collections()
        # Late import — ``migrate_positions_json`` imports from this module.
        from bookreader.library.migrate import migrate_positions_json

        migrate_positions_json(self)

    def close(self) -> None:
        """Close the underlying database."""
        self._db.close()

    # ----- exposed sub-APIs ------------------------------------------------

    @property
    def positions(self) -> PositionRepo:
        """Direct access to the position repository (read/write)."""
        return self._positions

    @property
    def bookmarks(self) -> BookmarkRepo:
        """Direct access to the bookmark repository."""
        return self._bookmarks

    # ----- books -----------------------------------------------------------

    def add_book(self, path: Path) -> Book:
        """Parse *path* and insert (or refresh) a book row.

        The EPUB is parsed once to extract identifier, title, and authors.
        If a row already exists for that identifier we update its file path
        and metadata in place (handles re-imports from a moved file).
        """
        parsed = open_book(path)
        book = self._books.upsert(
            identifier=parsed.identifier,
            file_path=path,
            title=parsed.title,
            authors=parsed.authors,
        )
        log.info("library add: %s [%s]", parsed.title, parsed.identifier)
        return book

    def add_wishlist(
        self,
        title: str,
        authors: Iterable[str] = (),
        *,
        collection_name: str | None = "Want to Read",
    ) -> Book:
        """Insert a phantom (file-less) book and add it to a collection.

        Args:
            title: Book title.
            authors: Author names, may be empty.
            collection_name: Collection to assign the row to; defaults to
                the seeded ``Want to Read`` collection. Pass ``None`` to
                skip assignment.

        Returns:
            The newly-inserted phantom :class:`Book`.
        """
        if not title.strip():
            raise ValueError("title must not be empty")
        book = self._books.create_phantom(title=title.strip(), authors=list(authors))
        if collection_name:
            col = self._collections.find_by_name(collection_name)
            if col is not None:
                self._collections.add_book(col.id, book.id)
        log.info("library wishlist add: %s", title)
        return book

    def attach_epub(self, book_id: int, path: Path) -> Book:
        """Parse *path* and promote a phantom row into a real book.

        Existing collection memberships, ratings, and completion stamps
        survive the upgrade.

        Raises:
            BookReaderError: From the EPUB parser if *path* is unreadable.
            RepositoryError: If *book_id* is missing or already attached.
        """
        parsed = open_book(path)
        book = self._books.attach_epub(
            book_id,
            identifier=parsed.identifier,
            file_path=path,
            title=parsed.title,
            authors=parsed.authors,
        )
        log.info("library attach: book=%s file=%s", book_id, path)
        return book

    def list_phantoms(self) -> list[Book]:
        """Return every phantom (wishlist) book."""
        return self._books.list_phantoms()

    def remove_book(self, book_id: int) -> None:
        """Delete a book and all its dependent rows."""
        self._books.delete(book_id)

    def list_books(self) -> list[Book]:
        """Return all books, most-recently-touched first."""
        return self._books.list_all()

    def list_recent(self, limit: int = 10) -> list[Book]:
        """Return up to *limit* recently-opened books."""
        return self._books.list_recent(limit=limit)

    def find_book_by_identifier(self, identifier: str) -> Book | None:
        """Return the book with EPUB *identifier* if known."""
        return self._books.find_by_identifier(identifier)

    def touch_opened(self, book_id: int) -> None:
        """Bump the ``last_opened_at`` timestamp for *book_id*."""
        self._books.touch_opened(book_id)

    def rate(self, book_id: int, rating: int | None) -> None:
        """Set or clear a book's 1..5 star rating."""
        self._books.set_rating(book_id, rating)

    def mark_complete(self, book_id: int) -> None:
        """Mark *book_id* as finished and add it to the ``Finished`` collection."""
        self._books.mark_completed(book_id, completed=True)
        finished = self._collections.find_by_name("Finished")
        if finished is not None:
            self._collections.add_book(finished.id, book_id)

    def mark_incomplete(self, book_id: int) -> None:
        """Clear the ``completed_at`` stamp for *book_id*."""
        self._books.mark_completed(book_id, completed=False)

    # ----- collections -----------------------------------------------------

    def list_collections(self) -> list[Collection]:
        """Return every collection in name order."""
        return self._collections.list_all()

    def list_books_in(self, collection_id: int) -> list[Book]:
        """Return books in *collection_id*."""
        return self._books.list_in_collection(collection_id)

    def collections_for(self, book_id: int) -> list[Collection]:
        """Return collections containing *book_id*."""
        return self._collections.collections_for(book_id)

    def create_collection(self, name: str) -> Collection:
        """Create a new collection (idempotent on name)."""
        return self._collections.create(name)

    def rename_collection(self, collection_id: int, name: str) -> None:
        """Rename a collection."""
        self._collections.rename(collection_id, name)

    def delete_collection(self, collection_id: int) -> None:
        """Delete a collection. Books survive; assignments are removed."""
        self._collections.delete(collection_id)

    def assign_to_collection(self, book_id: int, collection_id: int) -> None:
        """Add a book to a collection (idempotent)."""
        self._collections.add_book(collection_id, book_id)

    def unassign_from_collection(self, book_id: int, collection_id: int) -> None:
        """Remove a book from a collection."""
        self._collections.remove_book(collection_id, book_id)

    def sync_collections(self, book_id: int, collection_ids: Iterable[int]) -> None:
        """Replace a book's collection membership with *collection_ids*.

        Convenient when the book-detail screen lets the user check/uncheck
        boxes and commit on Enter.
        """
        target = set(collection_ids)
        current = {c.id for c in self._collections.collections_for(book_id)}
        for cid in current - target:
            self._collections.remove_book(cid, book_id)
        for cid in target - current:
            self._collections.add_book(cid, book_id)

    # ----- positions / bookmarks (passthrough convenience) -----------------

    def save_position(
        self,
        book_id: int,
        chapter_index: int,
        scroll_offset: int,
        page_index: int | None = None,
    ) -> StoredPosition:
        """Persist a reading position."""
        return self._positions.save(book_id, chapter_index, scroll_offset, page_index)

    def get_position(self, book_id: int) -> StoredPosition | None:
        """Return the saved position for *book_id*."""
        return self._positions.get(book_id)

    # ----- internals -------------------------------------------------------

    def _seed_default_collections(self) -> None:
        """Idempotently insert the seed collections."""
        for name in DEFAULT_COLLECTIONS:
            self._collections.create(name)
