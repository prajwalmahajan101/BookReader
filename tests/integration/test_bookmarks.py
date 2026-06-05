"""End-to-end tests for bookmark persistence (library + JSON fallback)."""

from __future__ import annotations

from pathlib import Path

import pytest

from bookreader.library.database import Database
from bookreader.library.service import LibraryService
from bookreader.state.bookmarks_json import JsonBookmarkStore


@pytest.fixture
def service(tmp_path: Path) -> LibraryService:
    return LibraryService(Database(tmp_path / "lib.db"))


def test_library_bookmark_roundtrip(service: LibraryService, sample_epub: Path) -> None:
    book = service.add_book(sample_epub)
    bm = service.bookmarks.add(book.id, chapter_index=2, scroll_offset=40, note="hi")
    rows = service.bookmarks.list_for(book.id)
    assert any(r.id == bm.id and r.note == "hi" for r in rows)

    service.bookmarks.delete(bm.id)
    assert service.bookmarks.list_for(book.id) == []


def test_json_bookmark_roundtrip(tmp_path: Path) -> None:
    store = JsonBookmarkStore(tmp_path / "bookmarks.json")
    a = store.add("book-1", chapter_index=0, scroll_offset=5, note="A")
    b = store.add("book-1", chapter_index=3, scroll_offset=0, note="")
    rows = store.list_for("book-1")
    assert {r.id for r in rows} == {a.id, b.id}
    # Newest first ordering
    assert rows[0].id >= rows[-1].id

    store.delete("book-1", a.id)
    assert {r.id for r in store.list_for("book-1")} == {b.id}


def test_json_bookmark_persists_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "bookmarks.json"
    JsonBookmarkStore(path).add("book-x", chapter_index=1, scroll_offset=2, note="n")
    rows = JsonBookmarkStore(path).list_for("book-x")
    assert len(rows) == 1
    assert rows[0].note == "n"
