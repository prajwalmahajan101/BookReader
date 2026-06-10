"""Phase 5.0 — reader-side library actions.

The reader screen now exposes ``c`` (toggle complete), ``C``
(collections overview), and ``W`` (wishlist overview) so users don't
have to quit the reader to reach those library features. These tests
exercise each key end-to-end with Textual's pilot harness.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bookreader.epub.reader import open_book
from bookreader.library.database import Database
from bookreader.library.service import LibraryService
from bookreader.state.positions import PositionStore
from bookreader.ui.app import BookReaderApp
from bookreader.ui.screens.collections import CollectionsScreen
from bookreader.ui.screens.wishlist import WishlistScreen


@pytest.fixture
def service(tmp_path: Path) -> LibraryService:
    return LibraryService(Database(tmp_path / "lib.db"))


def _make_app(service: LibraryService, sample_epub: Path) -> BookReaderApp:
    """Build a reader-mode app wired to a library and a parsed sample EPUB."""
    parsed = open_book(sample_epub)
    lib_book = service.add_book(sample_epub)
    return BookReaderApp(
        book=parsed,
        positions=PositionStore(),
        library=service,
        library_book_id=lib_book.id,
    )


@pytest.mark.asyncio
async def test_c_toggles_complete_from_reader(service: LibraryService, sample_epub: Path) -> None:
    """Pressing ``c`` inside the reader marks the current book finished."""
    app = _make_app(service, sample_epub)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("c")
        await pilot.pause()

    refreshed = service.find_book_by_identifier(open_book(sample_epub).identifier)
    assert refreshed is not None
    assert refreshed.completed_at is not None


@pytest.mark.asyncio
async def test_shift_c_pushes_collections_modal(service: LibraryService, sample_epub: Path) -> None:
    """Pressing ``C`` inside the reader pushes the collections overview."""
    app = _make_app(service, sample_epub)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("C")
        await pilot.pause()
        assert isinstance(app.screen, CollectionsScreen)


@pytest.mark.asyncio
async def test_shift_w_pushes_wishlist_modal(service: LibraryService, sample_epub: Path) -> None:
    """Pressing ``W`` inside the reader pushes the wishlist overview."""
    service.add_wishlist("Babel", ["R.F. Kuang"])
    app = _make_app(service, sample_epub)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("W")
        await pilot.pause()
        assert isinstance(app.screen, WishlistScreen)


@pytest.mark.asyncio
async def test_lowercase_w_on_library_hints_shift(
    service: LibraryService,
) -> None:
    """Pressing ``w`` on the library screen must NOT silently noop."""
    app = BookReaderApp(library=service)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("w")
        await pilot.pause()
        # App is still running on the library screen — the hint fires
        # via a notify; we don't assert on the toast text because
        # Textual's notification API doesn't expose a stable hook
        # to read it back. The smoke test is: pressing 'w' didn't
        # crash and didn't change screens.
        assert app.is_running
        # The default Screen sits at index 0 with LibraryScreen above it.
        # The hint must NOT push anything further (would indicate the bind
        # accidentally opened a modal).
        from bookreader.ui.screens.library import LibraryScreen

        assert isinstance(app.screen, LibraryScreen)
