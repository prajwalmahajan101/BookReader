"""Regression: paged-view re-render must not raise DuplicateIds.

The first widget-mounting version of PagedView used hardcoded child
IDs (``id="spread"``, ``id="left-page"``, etc.). Because
``remove_children()`` is asynchronous, a quick re-render (resize,
toggle, chapter jump) could fire ``mount(Horizontal(id="spread"))``
while the previous Horizontal was still in the parent's node list,
raising ``DuplicateIds`` and crashing the reader.

This test mounts a PagedView inside a minimal harness app and calls
``show_chapter`` three times in succession. If the IDs regress, the
third call raises and this test fails.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from textual.app import App, ComposeResult
from textual.containers import Vertical

from bookreader.epub.reader import open_book
from bookreader.ui.widgets.paged_view import PagedView


class _Harness(App[None]):
    def __init__(self, book_path: Path) -> None:
        super().__init__()
        self._book = open_book(book_path)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield PagedView(id="paged")

    def on_mount(self) -> None:
        paged = self.query_one("#paged", PagedView)
        paged.attach_book(self._book)


@pytest.mark.asyncio
async def test_repeated_show_chapter_does_not_raise(sample_epub: Path) -> None:
    """Re-rendering the same chapter three times must not raise."""
    app = _Harness(sample_epub)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        paged = app.query_one("#paged", PagedView)
        chapter = app._book.chapters[0]
        paged.show_chapter(chapter)
        await pilot.pause()
        paged.show_chapter(chapter)
        await pilot.pause()
        paged.show_chapter(chapter)
        await pilot.pause()
        # If we got here without DuplicateIds, the regression is sealed.
        assert app.is_running


@pytest.mark.asyncio
async def test_show_chapter_then_set_page_index(sample_epub: Path) -> None:
    """show_chapter followed by set_page_index must not crash."""
    app = _Harness(sample_epub)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        paged = app.query_one("#paged", PagedView)
        paged.show_chapter(app._book.chapters[0])
        await pilot.pause()
        paged.set_page_index(0)
        await pilot.pause()
        paged.set_page_index(2)
        await pilot.pause()
        assert app.is_running
