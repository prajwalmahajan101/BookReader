"""Integration tests for the Collections / Wishlist modal screens.

These exercise the screens end-to-end against a real ``LibraryService``
using Textual's :py:meth:`App.run_test` harness, mirroring the existing
bookmarks integration coverage.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from textual.app import App, ComposeResult
from textual.widgets import OptionList

from bookreader.library.database import Database
from bookreader.library.service import LibraryService
from bookreader.ui.screens.collections import CollectionGroup, CollectionsScreen
from bookreader.ui.screens.wishlist import WishlistScreen


@pytest.fixture
def service(tmp_path: Path) -> LibraryService:
    return LibraryService(Database(tmp_path / "lib.db"))


class _Harness(App[None]):
    """Bare app used solely to host modal pushes during tests."""

    def compose(self) -> ComposeResult:  # pragma: no cover - empty shell
        return iter(())


def _groups_from(service: LibraryService) -> list[CollectionGroup]:
    return [
        CollectionGroup(c.name, tuple(service.list_books_in(c.id)))
        for c in service.list_collections()
    ]


@pytest.mark.asyncio
async def test_collections_screen_groups_real_and_phantom_books(
    service: LibraryService, sample_epub: Path
) -> None:
    real = service.add_book(sample_epub)
    phantom = service.add_wishlist("Babel", ["R.F. Kuang"])
    currently_reading = next(c for c in service.list_collections() if c.name == "Currently Reading")
    service.assign_to_collection(real.id, currently_reading.id)

    async with _Harness().run_test() as pilot:
        pilot.app.push_screen(CollectionsScreen(_groups_from(service)))
        await pilot.pause()

        screen = pilot.app.screen
        assert isinstance(screen, CollectionsScreen)
        lst = screen.query_one("#collections-list", OptionList)
        book_ids = [lst.get_option_at_index(i).id for i in range(lst.option_count)]
        # Two real picks (one real book, one phantom); the rest are headers.
        assert sum(1 for oid in book_ids if oid is not None) == 2

    assert real.file_path is not None
    assert phantom.file_path is None


@pytest.mark.asyncio
async def test_collections_screen_empty_state(service: LibraryService) -> None:
    async with _Harness().run_test() as pilot:
        pilot.app.push_screen(CollectionsScreen(_groups_from(service)))
        await pilot.pause()
        screen = pilot.app.screen
        assert isinstance(screen, CollectionsScreen)
        # No OptionList — empty placeholder instead.
        with pytest.raises(Exception, match="No nodes match"):
            screen.query_one("#collections-list", OptionList)


@pytest.mark.asyncio
async def test_wishlist_screen_lists_phantoms_and_tracks_deletions(
    service: LibraryService, sample_epub: Path
) -> None:
    service.add_book(sample_epub)
    a = service.add_wishlist("A Title", ["Author A"])
    b = service.add_wishlist("B Title", ["Author B"])

    async with _Harness().run_test() as pilot:
        screen = WishlistScreen(service.list_phantoms())
        pilot.app.push_screen(screen)
        await pilot.pause()

        lst = screen.query_one("#wishlist-list", OptionList)
        assert lst.option_count == 2

        # Highlight the first row and press 'd' — it should be removed
        # from the visible list and recorded in deleted_ids.
        lst.highlighted = 0
        await pilot.press("d")
        await pilot.pause()

        assert lst.option_count == 1
        # One of the two phantoms is now in deleted_ids.
        assert len(screen.deleted_ids) == 1
        assert screen.deleted_ids.issubset({a.id, b.id})


@pytest.mark.asyncio
async def test_wishlist_screen_empty_state(service: LibraryService) -> None:
    async with _Harness().run_test() as pilot:
        pilot.app.push_screen(WishlistScreen(service.list_phantoms()))
        await pilot.pause()
        screen = pilot.app.screen
        assert isinstance(screen, WishlistScreen)
        with pytest.raises(Exception, match="No nodes match"):
            screen.query_one("#wishlist-list", OptionList)
