"""End-to-end tests for the phantom (wishlist) book flow."""

from __future__ import annotations

from pathlib import Path

import pytest

from bookreader.library.database import Database
from bookreader.library.service import LibraryService


@pytest.fixture
def service(tmp_path: Path) -> LibraryService:
    return LibraryService(Database(tmp_path / "lib.db"))


def test_add_wishlist_creates_phantom_row(service: LibraryService) -> None:
    book = service.add_wishlist("Project Hail Mary", ["Andy Weir"])
    assert book.is_phantom
    assert book.file_path is None
    assert book.identifier.startswith("phantom:")
    assert book.title == "Project Hail Mary"
    assert book.authors == ("Andy Weir",)


def test_add_wishlist_assigns_default_collection(service: LibraryService) -> None:
    book = service.add_wishlist("The Bee Sting", ["Paul Murray"])
    cols = {c.name for c in service.collections_for(book.id)}
    assert "Want to Read" in cols


def test_attach_epub_promotes_phantom(service: LibraryService, sample_epub: Path) -> None:
    phantom = service.add_wishlist("Whatever", [])
    promoted = service.attach_epub(phantom.id, sample_epub)

    assert not promoted.is_phantom
    assert promoted.file_path == sample_epub
    assert promoted.title  # set from EPUB metadata
    assert not promoted.identifier.startswith("phantom:")
    # Collection membership survives the promotion
    cols = {c.name for c in service.collections_for(promoted.id)}
    assert "Want to Read" in cols


def test_attach_rejects_already_real_book(
    service: LibraryService, sample_epub: Path
) -> None:
    from bookreader.library.repository import RepositoryError

    real = service.add_book(sample_epub)
    with pytest.raises(RepositoryError):
        service.attach_epub(real.id, sample_epub)


def test_list_phantoms_filters_correctly(
    service: LibraryService, sample_epub: Path
) -> None:
    service.add_book(sample_epub)
    service.add_wishlist("A", [])
    service.add_wishlist("B", [])
    phantoms = service.list_phantoms()
    assert {b.title for b in phantoms} == {"A", "B"}
    assert all(b.is_phantom for b in phantoms)
