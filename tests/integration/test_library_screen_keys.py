"""Regression tests for library/reader key bindings under modals.

ISSUE-004: typing a `q` inside a modal Input must NOT trigger the
underlying library screen's quit binding. Textual's ModalScreen +
Input combination is supposed to isolate this; we lock it in with
an end-to-end pilot test so a future re-bind can't silently regress
into a data-loss path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bookreader.library.database import Database
from bookreader.library.service import LibraryService
from bookreader.ui.app import BookReaderApp


@pytest.fixture
def service(tmp_path: Path) -> LibraryService:
    return LibraryService(Database(tmp_path / "lib.db"))


@pytest.mark.asyncio
async def test_q_in_wishlist_modal_does_not_quit_app(service: LibraryService) -> None:
    """Press 'A' to open the wishlist modal, type a title containing 'q'.

    The app must still be running with the modal on top after the keystrokes.
    """
    app = BookReaderApp(library=service)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Library screen is on top.
        await pilot.press("A")  # open wishlist modal
        await pilot.pause()
        # Type a title that includes the letter 'q'.
        for ch in "Quiet":
            await pilot.press(ch.lower() if ch.isupper() else ch)
        await pilot.pause()
        # App must still be running; the screen stack must contain the modal.
        assert app.is_running
        assert len(app.screen_stack) >= 2  # library + modal


@pytest.mark.asyncio
async def test_q_on_library_screen_quits(service: LibraryService) -> None:
    """Confirm the documented behaviour: 'q' on the library screen quits."""
    app = BookReaderApp(library=service)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("q")
        await pilot.pause()
        assert not app.is_running
