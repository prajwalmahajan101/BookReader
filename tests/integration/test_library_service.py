"""End-to-end tests for the library service against a temp SQLite DB."""

from __future__ import annotations

from pathlib import Path

import pytest

from bookreader.library.database import Database
from bookreader.library.service import DEFAULT_COLLECTIONS, LibraryService


@pytest.fixture
def service(tmp_path: Path) -> LibraryService:
    db = Database(tmp_path / "lib.db")
    return LibraryService(db)


def test_default_collections_seeded(service: LibraryService) -> None:
    names = {c.name for c in service.list_collections()}
    assert set(DEFAULT_COLLECTIONS).issubset(names)


def test_add_book_idempotent(service: LibraryService, sample_epub: Path) -> None:
    a = service.add_book(sample_epub)
    b = service.add_book(sample_epub)
    assert a.id == b.id  # same row updated, not duplicated
    assert len(service.list_books()) == 1


def test_rate_and_complete_flow(service: LibraryService, sample_epub: Path) -> None:
    book = service.add_book(sample_epub)
    service.rate(book.id, 4)
    service.mark_complete(book.id)

    refreshed = service.find_book_by_identifier(book.identifier)
    assert refreshed is not None
    assert refreshed.rating == 4
    assert refreshed.completed_at is not None

    finished = next(c for c in service.list_collections() if c.name == "Finished")
    assert any(b.id == book.id for b in service.list_books_in(finished.id))


def test_collection_sync_replaces_membership(service: LibraryService, sample_epub: Path) -> None:
    book = service.add_book(sample_epub)
    a = service.create_collection("A")
    b = service.create_collection("B")
    service.sync_collections(book.id, [a.id, b.id])
    assert {c.id for c in service.collections_for(book.id)} == {a.id, b.id}

    service.sync_collections(book.id, [a.id])
    assert {c.id for c in service.collections_for(book.id)} == {a.id}


def test_position_roundtrips(service: LibraryService, sample_epub: Path) -> None:
    book = service.add_book(sample_epub)
    service.save_position(book.id, chapter_index=2, scroll_offset=120, page_index=None)

    pos = service.get_position(book.id)
    assert pos is not None
    assert pos.chapter_index == 2
    assert pos.scroll_offset == 120
    assert pos.page_index is None


def test_recents_orders_by_last_opened(service: LibraryService, sample_epub: Path) -> None:
    book = service.add_book(sample_epub)
    assert service.list_recent() == []  # not opened yet
    service.touch_opened(book.id)
    assert [b.id for b in service.list_recent()] == [book.id]


def test_remove_book_cascades(service: LibraryService, sample_epub: Path) -> None:
    book = service.add_book(sample_epub)
    a = service.create_collection("A")
    service.assign_to_collection(book.id, a.id)
    service.save_position(book.id, chapter_index=0, scroll_offset=0)

    service.remove_book(book.id)
    assert service.find_book_by_identifier(book.identifier) is None
    assert service.list_books_in(a.id) == []
    assert service.get_position(book.id) is None
