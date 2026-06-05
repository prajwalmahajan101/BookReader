"""Tests for ``bookreader.epub.reader``."""

from __future__ import annotations

from pathlib import Path

import pytest

from bookreader.core.exceptions import EpubParseError
from bookreader.epub.reader import open_book


def test_open_book_parses_metadata_and_spine(sample_epub: Path) -> None:
    book = open_book(sample_epub)
    assert book.title == "The Sample Book"
    assert book.authors == ("Test Author",)
    assert book.identifier == "urn:test:bookreader:sample-001"
    # 3 chapters + the nav doc
    assert len(book.chapters) >= 3
    assert book.chapters[0].title.startswith("Chapter")


def test_open_book_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(EpubParseError):
        open_book(tmp_path / "does-not-exist.epub")


def test_open_book_invalid_file_raises(tmp_path: Path) -> None:
    bad = tmp_path / "not.epub"
    bad.write_text("not an epub")
    with pytest.raises(EpubParseError):
        open_book(bad)


def test_toc_entries_resolve_to_spine_indices(sample_epub: Path) -> None:
    book = open_book(sample_epub)
    assert book.toc, "expected at least one TOC entry"
    for entry in book.toc:
        assert 0 <= entry.chapter_index < len(book.chapters)
